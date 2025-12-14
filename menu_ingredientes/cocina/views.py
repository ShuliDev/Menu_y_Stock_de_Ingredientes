# cocina/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Q, Avg, Min, Max, F, ExpressionWrapper, DurationField
from django import forms

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import PedidoCocina
from .serializers import PedidoCocinaSerializer


def monitor(request):
    """Vista principal del monitor de cocina"""
    from django.utils.timezone import localtime
    from mainApp.models import Plato
    import datetime
    
    def _nombre_plato(codigo: str) -> str:
        try:
            p = Plato.objects.get(pk=codigo)
            return p.nombre
        except Exception:
            return codigo or "-"
    
    def _fmt_hhmm(iso_dt):
        if not iso_dt:
            return "—"
        try:
            dt = localtime(iso_dt)
            return dt.strftime("%d/%m %H:%M")
        except Exception:
            return str(iso_dt)
    
    def _tiempo_transcurrido(creado):
        if not creado:
            return "—"
        try:
            ahora = datetime.datetime.now(datetime.timezone.utc)
            delta = ahora - creado
            minutos = int(delta.total_seconds() / 60)
            if minutos < 60:
                return f"{minutos} min"
            horas = minutos // 60
            mins = minutos % 60
            return f"{horas}h {mins}m"
        except Exception:
            return "—"
    
    # Obtener pedidos de PedidoCocina agrupados por estado (solo activos)
    pedidos_todos = PedidoCocina.objects.exclude(
        estado__in=['ENTREGADO', 'CANCELADO']
    ).order_by('-fecha_creacion')
    
    pedidos_pendientes = []
    pedidos_en_preparacion = []
    pedidos_listos = []
    
    for p in pedidos_todos:
        p_dict = {
            'id': p.id_modulo3 or str(p.id),
            'mesa': p.mesa,
            'cliente': p.cliente,
            'plato_nombre': p.descripcion,
            'cantidad': 1,  # PedidoCocina no tiene cantidad, asumir 1
            'creado_str': _fmt_hhmm(p.fecha_creacion),
            'tiempo_preparacion': _tiempo_transcurrido(p.fecha_creacion),
            'estado': p.estado,
        }
        
        if p.estado in ['CREADO', 'URGENTE']:
            pedidos_pendientes.append(p_dict)
        elif p.estado == 'EN_PREPARACION':
            pedidos_en_preparacion.append(p_dict)
        elif p.estado == 'LISTO':
            pedidos_listos.append(p_dict)
    
    context = {
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_en_preparacion': pedidos_en_preparacion,
        'pedidos_listos': pedidos_listos,
    }
    
    return render(request, 'cocina/monitor.html', context)


class PedidoCocinaViewSet(viewsets.ModelViewSet):
    """API ViewSet para gestionar pedidos en cocina"""
    queryset = PedidoCocina.objects.all().order_by('-fecha_creacion')
    serializer_class = PedidoCocinaSerializer

    # Transiciones de estado permitidas
    transiciones = {
        "URGENTE": ["EN_PREPARACION"],
        "CREADO": ["URGENTE", "EN_PREPARACION"],
        "EN_PREPARACION": ["LISTO"],
        "LISTO": ["ENTREGADO"],
        "ENTREGADO": []
    }

    def update(self, request, *args, **kwargs):
        """Actualizar pedido con validación de transiciones de estado"""
        instance = self.get_object()
        nuevo_estado = request.data.get("estado", None)

        if nuevo_estado is None:
            return super().update(request, *args, **kwargs)

        if nuevo_estado not in self.transiciones[instance.estado]:
            return Response(
                {"error": f"No puedes pasar de {instance.estado} a {nuevo_estado}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.estado = nuevo_estado

        # Si pasa a LISTO, guardamos hora_listo 1 sola vez
        if nuevo_estado == "LISTO" and instance.hora_listo is None:
            instance.hora_listo = timezone.now()

        instance.save()

        # Notificar al módulo 03 si es necesario
        if nuevo_estado == "LISTO":
            try:
                self._notificar_modulo3_listo(instance)
            except Exception as e:
                return Response(
                    {
                        "pedido": PedidoCocinaSerializer(instance).data,
                        "warning": f"Pedido pasó a LISTO pero no se pudo notificar a Módulo 03: {str(e)}"
                    },
                    status=status.HTTP_200_OK
                )

        return Response(PedidoCocinaSerializer(instance).data)

    def _notificar_modulo3_listo(self, pedido):
        """Notifica al módulo 3 que el pedido está listo"""
        # Importar aquí para evitar circular imports
        from pedidos.models import Pedido as PedidoM3
        
        if pedido.id_modulo3:
            try:
                pedido_m3 = PedidoM3.objects.get(id=pedido.id_modulo3)
                if pedido_m3.estado != PedidoM3.Estado.LISTO:
                    pedido_m3.marcar_listo()
            except PedidoM3.DoesNotExist:
                pass

    @action(detail=False, methods=['get'])
    def filtrados(self, request):
        """Filtrar pedidos por estado"""
        estado = request.query_params.get('estado', 'CREADO').upper()
        pedidos = PedidoCocina.objects.filter(estado=estado)
        return Response({
            "estado": estado,
            "cantidad": pedidos.count(),
            "resultados": PedidoCocinaSerializer(pedidos, many=True).data
        })

    @action(detail=False, methods=['get'])
    def entregados(self, request):
        """Obtener todos los pedidos entregados"""
        pedidos = PedidoCocina.objects.filter(estado="ENTREGADO")
        return Response(PedidoCocinaSerializer(pedidos, many=True).data)
    
    @action(detail=False, methods=["post"], url_path="desde-modulo3")
    def desde_modulo3(self, request):
        """
        Recibe pedido desde Módulo 03 y lo crea (o actualiza si ya existe).
        
        Campos esperados:
        - id_pedido (UUID del módulo 3)
        - nro_mesa
        - nombre_cliente
        - orden (descripción del plato/pedido)
        """
        id_pedido = request.data.get("id_pedido")
        nro_mesa = request.data.get("nro_mesa")
        nombre_cliente = request.data.get("nombre_cliente")
        orden = request.data.get("orden")

        if not all([id_pedido, nro_mesa, nombre_cliente, orden]):
            return Response(
                {"error": "Faltan campos. Requeridos: id_pedido, nro_mesa, nombre_cliente, orden"},
                status=status.HTTP_400_BAD_REQUEST
            )

        pedido, creado = PedidoCocina.objects.get_or_create(
            id_modulo3=str(id_pedido),
            defaults={
                "mesa": int(nro_mesa),
                "cliente": str(nombre_cliente),
                "descripcion": str(orden),
                "estado": PedidoCocina.EstadoPedido.CREADO,
            }
        )

        # Si ya existía, actualizamos datos
        if not creado:
            pedido.mesa = int(nro_mesa)
            pedido.cliente = str(nombre_cliente)
            pedido.descripcion = str(orden)
            pedido.save()

        return Response(
            {"ok": True, "creado": creado, "pedido": PedidoCocinaSerializer(pedido).data},
            status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK
        )


def administrar_pedidos(request):
    """Vista para administrar pedidos"""
    if request.method == "POST":
        eliminar_id = request.POST.get("eliminar_id")
        if eliminar_id:
            PedidoCocina.objects.filter(pk=eliminar_id).delete()
            return redirect("cocina_administrar_pedidos")

    consulta = request.GET.get("q", "").strip()
    pedidos = PedidoCocina.objects.all().order_by("-fecha_creacion")

    if consulta:
        filtro = Q(cliente__icontains=consulta) | Q(descripcion__icontains=consulta)
        if consulta.isdigit():
            filtro |= Q(id=int(consulta))
        pedidos = pedidos.filter(filtro)
    else:
        pedidos = pedidos[:10]

    contexto = {"pedidos": pedidos, "consulta": consulta}
    return render(request, "cocina/administrar_pedidos.html", contexto)


class FormPedidoCocina(forms.ModelForm):
    class Meta:
        model = PedidoCocina
        fields = ["mesa", "cliente", "descripcion", "estado"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}


def editar_pedido(request, pedido_id):
    """Vista para editar un pedido"""
    pedido = get_object_or_404(PedidoCocina, pk=pedido_id)

    if request.method == "POST":
        formulario = FormPedidoCocina(request.POST, instance=pedido)
        if formulario.is_valid():
            formulario.save()
            return redirect("cocina_administrar_pedidos")
    else:
        formulario = FormPedidoCocina(instance=pedido)

    contexto = {"pedido": pedido, "formulario": formulario}
    return render(request, "cocina/editar_pedido.html", contexto)


def historial_pedidos(request):
    """Vista de historial de pedidos del día"""
    hoy = timezone.localdate()
    pedidos = PedidoCocina.objects.filter(fecha_creacion__date=hoy).order_by('fecha_creacion')

    registros = []
    for p in pedidos:
        hora_ingreso = p.fecha_creacion
        hora_salida = p.fecha_actualizacion if p.estado == PedidoCocina.EstadoPedido.ENTREGADO else None
        registros.append({
            "pedido": p,
            "hora_ingreso": hora_ingreso,
            "hora_salida": hora_salida,
        })

    contexto = {"registros": registros}
    return render(request, "cocina/historial_pedidos.html", contexto)


@api_view(["GET"])
def estadisticas_tiempos(request):
    """Estadísticas de tiempos de preparación de pedidos"""
    pedidos = PedidoCocina.objects.filter(estado="LISTO", fecha_actualizacion__isnull=False)

    if not pedidos.exists():
        return Response({
            "promedio_minutos": 0,
            "minimo_minutos": 0,
            "maximo_minutos": 0,
            "cantidad_pedidos": 0
        }, status=status.HTTP_200_OK)

    diff = ExpressionWrapper(
        F("fecha_actualizacion") - F("fecha_creacion"),
        output_field=DurationField()
    )

    datos = pedidos.aggregate(
        promedio=Avg(diff),
        minimo=Min(diff),
        maximo=Max(diff),
    )

    def to_minutes(td):
        return round(td.total_seconds() / 60, 2) if td else 0

    return Response({
        "promedio_minutos": to_minutes(datos["promedio"]),
        "minimo_minutos": to_minutes(datos["minimo"]),
        "maximo_minutos": to_minutes(datos["maximo"]),
        "cantidad_pedidos": pedidos.count(),
    }, status=status.HTTP_200_OK)
