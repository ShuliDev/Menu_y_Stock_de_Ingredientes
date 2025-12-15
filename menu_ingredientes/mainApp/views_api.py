# mainApp/views_api.py - VERSIÓN COMPLETA Y CORREGIDA

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from datetime import datetime, time as dt_time
import datetime as dt

# Importar todos los modelos necesarios
from .models import (
    CategoriaMenu, Ingrediente, Plato, Receta, Stock, ReservaStock, 
    Reserva, Mesa
)

from .serializers import (
    CategoriaMenuSerializer, IngredienteSerializer, 
    PlatoSerializer, StockSerializer
)

# ==================== VIEWSETS BÁSICOS ====================

class CategoriaMenuViewSet(viewsets.ModelViewSet):
    """
    API para gestión de categorías de menú
    """
    queryset = CategoriaMenu.objects.all()
    serializer_class = CategoriaMenuSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]


class IngredienteViewSet(viewsets.ModelViewSet):
    """
    API para gestión de ingredientes
    """
    queryset = Ingrediente.objects.all()
    serializer_class = IngredienteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['nombre']
    filterset_fields = ['unidad_medida']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]


class PlatoViewSet(viewsets.ModelViewSet):
    """
    API para gestión de platos del menú
    """
    queryset = Plato.objects.filter(activo=True)
    serializer_class = PlatoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['nombre', 'descripcion']
    filterset_fields = ['categoria', 'activo']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        """Platos activos disponibles"""
        platos = Plato.objects.filter(activo=True)
        serializer = self.get_serializer(platos, many=True)
        return Response(serializer.data)


class StockViewSet(viewsets.ModelViewSet):
    """
    API para gestión de stock
    """
    queryset = Stock.objects.select_related('ingrediente').all()
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['ingrediente__nombre']

    @action(detail=False, methods=['get'])
    def bajo_stock(self, request):
        """Ingredientes con stock bajo"""
        stock_bajo = self.get_queryset().filter(
            cantidad_disponible__lte=F('ingrediente__stock_minimo')
        )
        serializer = self.get_serializer(stock_bajo, many=True)
        return Response(serializer.data)


# ==================== APIViews SIMPLES ====================

class DashboardAPIView(APIView):
    """
    Dashboard administrativo
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = {
            'total_categorias': CategoriaMenu.objects.count(),
            'total_ingredientes': Ingrediente.objects.count(),
            'total_platos': Plato.objects.filter(activo=True).count(),
            'platos_por_categoria': Plato.objects.values('categoria__nombre')
                .annotate(total=Count('id'))
                .order_by('categoria__nombre'),
            'ingredientes_bajo_stock': Stock.objects.filter(
                cantidad_disponible__lte=F('ingrediente__stock_minimo')
            ).count(),
        }
        return Response(stats)


class ValidarStockAPIView(APIView):
    """
    Validar stock para un plato
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plato_id = request.data.get('plato_id')
        cantidad = request.data.get('cantidad', 1)

        if not plato_id:
            return Response(
                {'error': 'plato_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            plato = Plato.objects.get(id=plato_id, activo=True)
        except Plato.DoesNotExist:
            return Response(
                {'error': 'Plato no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verificar stock para cada ingrediente
        faltantes = []
        for receta in plato.recetas.all():
            stock = Stock.objects.filter(ingrediente=receta.ingrediente).first()
            if stock and stock.cantidad_disponible < (receta.cantidad * cantidad):
                faltantes.append({
                    'ingrediente': receta.ingrediente.nombre,
                    'necesario': receta.cantidad * cantidad,
                    'disponible': stock.cantidad_disponible
                })

        return Response({
            'plato': plato.nombre,
            'cantidad': cantidad,
            'stock_suficiente': len(faltantes) == 0,
            'ingredientes_faltantes': faltantes
        })


# ==================== VIEWSETS ADICIONALES ====================

class RecetaViewSet(viewsets.ModelViewSet):
    """
    API para recetas (relación plato-ingrediente)
    """
    queryset = Receta.objects.select_related('plato', 'ingrediente').all()
    serializer_class = None  # Necesitarías crear RecetaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Receta.objects.all()
        plato_id = self.request.query_params.get('plato_id')
        if plato_id:
            queryset = queryset.filter(plato_id=plato_id)
        return queryset


class ReservaStockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para consultar reservas de stock
    """
    queryset = ReservaStock.objects.select_related('plato').all()
    serializer_class = None  # Necesitarías crear ReservaStockSerializer
    permission_classes = [IsAuthenticated]


# ==================== APIS DE INTEGRACIÓN ====================

@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_integracion(request):
    """
    API que integra datos de los 4 módulos del sistema
    """
    try:
        # ========== DATOS DEL MÓDULO 1 ==========
        # Menú, ingredientes y stock
        platos_activos = Plato.objects.filter(activo=True)
        platos_count = platos_activos.count()
        
        # Platos con su stock disponible
        platos_con_stock = []
        for plato in platos_activos[:5]:  # Primeros 5 para ejemplo
            stock_suficiente = True
            for receta in plato.recetas.all():
                stock = Stock.objects.filter(ingrediente=receta.ingrediente).first()
                if stock and stock.cantidad_disponible < receta.cantidad:
                    stock_suficiente = False
                    break
            
            platos_con_stock.append({
                'id': plato.id,
                'nombre': plato.nombre,
                'categoria': plato.categoria.nombre,
                'precio': float(plato.precio),
                'stock_suficiente': stock_suficiente
            })
        
        # ========== DATOS DEL MÓDULO 2 ==========
        # Reservas activas para hoy
        hoy = timezone.now().date()
        reservas_hoy = Reserva.objects.filter(
            fecha_reserva=hoy,
            estado__in=['pendiente', 'confirmada']
        ).select_related('mesa', 'cliente')[:5]  # Primeras 5 reservas
        
        reservas_list = []
        for reserva in reservas_hoy:
            reservas_list.append({
                'id': reserva.id,
                'mesa': reserva.mesa.numero,
                'cliente': reserva.cliente.username,
                'hora': reserva.hora_inicio.strftime('%H:%M'),
                'personas': reserva.num_personas,
                'estado': reserva.estado
            })
        
        # ========== DATOS DEL MÓDULO 3 ==========
        pedidos_activos_list = []
        pedidos_count = 0
        
        try:
            from pedidos.models import Pedido
            
            pedidos_activos = Pedido.objects.exclude(
                estado__in=['CERRADO', 'CANCELADO']
            ).order_by('-creado_en')[:5]
            
            pedidos_count = Pedido.objects.exclude(
                estado__in=['CERRADO', 'CANCELADO']
            ).count()
            
            for pedido in pedidos_activos:
                pedidos_activos_list.append({
                    'id': str(pedido.id),
                    'mesa': pedido.mesa,
                    'cliente': pedido.cliente,
                    'plato': pedido.plato,
                    'estado': pedido.estado,
                    'creado': pedido.creado_en.strftime('%H:%M')
                })
                
        except Exception as e:
            pedidos_activos_list = [{'error': f'Error módulo pedidos: {str(e)}'}]
        
        # ========== DATOS DEL MÓDULO 4 ==========
        cocina_pedidos_list = []
        cocina_count = 0
        
        try:
            from cocina.models import PedidoCocina
            
            cocina_pedidos = PedidoCocina.objects.exclude(
                estado__in=['ENTREGADO']
            ).order_by('-fecha_creacion')[:5]
            
            cocina_count = PedidoCocina.objects.exclude(
                estado__in=['ENTREGADO']
            ).count()
            
            for pedido in cocina_pedidos:
                cocina_pedidos_list.append({
                    'id': pedido.id,
                    'mesa': pedido.mesa,
                    'cliente': pedido.cliente,
                    'descripcion': pedido.descripcion,
                    'estado': pedido.estado,
                    'creado': pedido.fecha_creacion.strftime('%H:%M')
                })
                
        except Exception as e:
            cocina_pedidos_list = [{'error': f'Error módulo cocina: {str(e)}'}]
        
        # ========== ESTADO GENERAL DEL SISTEMA ==========
        estado_sistema = {
            'menu': {
                'total_platos': platos_count,
                'platos_con_stock_insuficiente': len([p for p in platos_con_stock if not p['stock_suficiente']])
            },
            'reservas': {
                'total_hoy': len(reservas_list),
                'mesas_ocupadas': len(set(r['mesa'] for r in reservas_list))
            },
            'pedidos': {
                'total_activos': pedidos_count,
                'por_estado': {}
            },
            'cocina': {
                'total_preparando': cocina_count,
                'sincronizacion_pedidos': 'OK' if pedidos_count == cocina_count else 'PARCIAL'
            }
        }
        
        # Contar pedidos por estado (si hay datos)
        if pedidos_count > 0:
            try:
                from pedidos.models import Pedido
                por_estado = Pedido.objects.exclude(
                    estado__in=['CERRADO', 'CANCELADO']
                ).values('estado').annotate(total=Count('id'))
                estado_sistema['pedidos']['por_estado'] = {item['estado']: item['total'] for item in por_estado}
            except:
                pass
        
        return Response({
            'sistema': 'Restaurante - Estado Integrado',
            'timestamp': timezone.now().isoformat(),
            'datos': {
                'modulo_menu': {
                    'descripcion': 'Gestión de menú e ingredientes',
                    'platos_activos': platos_con_stock,
                    'resumen': {
                        'total_platos': platos_count,
                        'muestra': len(platos_con_stock)
                    }
                },
                'modulo_reservas': {
                    'descripcion': 'Clientes, mesas y reservas',
                    'reservas_hoy': reservas_list,
                    'resumen': {
                        'total_hoy': len(reservas_list),
                        'muestra': len(reservas_list)
                    }
                },
                'modulo_pedidos': {
                    'descripcion': 'Sistema de pedidos (mesero)',
                    'pedidos_activos': pedidos_activos_list,
                    'resumen': {
                        'total_activos': pedidos_count,
                        'muestra': len(pedidos_activos_list)
                    }
                },
                'modulo_cocina': {
                    'descripcion': 'Monitor de cocina en tiempo real',
                    'pedidos_en_cocina': cocina_pedidos_list,
                    'resumen': {
                        'total_preparando': cocina_count,
                        'muestra': len(cocina_pedidos_list)
                    }
                }
            },
            'estado_general': estado_sistema,
            'integracion': {
                'modulos_conectados': 4,
                'total_datos': platos_count + len(reservas_list) + pedidos_count + cocina_count,
                'actualizado': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        return Response({
            'error': f'Error en la integración: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_pedido_integrado(request):
    """
    Crea un pedido integrando múltiples módulos:
    1. Verifica stock (Módulo 1)
    2. Crea pedido (Módulo 3)
    3. Notifica a cocina (Módulo 4)
    """
    try:
        data = request.data
        
        # 1. Obtener datos del request
        plato_id = data.get('plato_id')
        mesa = data.get('mesa')
        cliente = data.get('cliente') or request.user.username
        cantidad = data.get('cantidad', 1)
        
        if not plato_id or not mesa:
            return Response(
                {'error': 'plato_id y mesa son requeridos'},
                status=400
            )
        
        # 2. Verificar que el plato existe (Módulo 1)
        try:
            plato = Plato.objects.get(id=plato_id, activo=True)
        except Plato.DoesNotExist:
            return Response(
                {'error': 'Plato no encontrado o inactivo'},
                status=404
            )
        
        # 3. Verificar stock (Módulo 1)
        ingredientes_faltantes = []
        for receta in plato.recetas.all():
            stock = Stock.objects.filter(ingrediente=receta.ingrediente).first()
            if stock and stock.cantidad_disponible < (receta.cantidad * cantidad):
                ingredientes_faltantes.append({
                    'ingrediente': receta.ingrediente.nombre,
                    'necesario': receta.cantidad * cantidad,
                    'disponible': stock.cantidad_disponible
                })
        
        if ingredientes_faltantes:
            return Response({
                'error': 'Stock insuficiente',
                'plato': plato.nombre,
                'ingredientes_faltantes': ingredientes_faltantes
            }, status=400)
        
        # 4. Crear pedido (Módulo 3)
        pedido = None
        try:
            from pedidos.models import Pedido
            
            pedido = Pedido.objects.create(
                mesa=mesa,
                cliente=cliente,
                plato=plato.nombre,
                estado=Pedido.Estado.CREADO
            )
            
            # Restar stock (Módulo 1)
            for receta in plato.recetas.all():
                stock = Stock.objects.filter(ingrediente=receta.ingrediente).first()
                if stock:
                    stock.cantidad_disponible -= receta.cantidad * cantidad
                    stock.save()
                    
        except Exception as e:
            return Response({
                'error': f'Error al crear pedido: {str(e)}'
            }, status=500)
        
        # 5. Notificar a cocina (Módulo 4)
        cocina_creado = False
        try:
            from cocina.models import PedidoCocina
            
            PedidoCocina.objects.create(
                id_modulo3=str(pedido.id),
                mesa=int(mesa) if mesa.isdigit() else 1,
                cliente=cliente,
                descripcion=f"{plato.nombre} x{cantidad}",
                estado=PedidoCocina.EstadoPedido.CREADO
            )
            cocina_creado = True
            
        except Exception as e:
            cocina_creado = False
        
        # 6. Respuesta integrada
        return Response({
            'mensaje': 'Pedido creado exitosamente',
            'pedido': {
                'id': str(pedido.id),
                'mesa': pedido.mesa,
                'cliente': pedido.cliente,
                'plato': pedido.plato,
                'estado': pedido.estado,
                'creado': pedido.creado_en.isoformat()
            },
            'modulos': {
                'modulo_1': {
                    'accion': 'Verificación de stock',
                    'resultado': 'OK',
                    'stock_actualizado': True
                },
                'modulo_3': {
                    'accion': 'Creación de pedido',
                    'resultado': 'OK',
                    'pedido_id': str(pedido.id)
                },
                'modulo_4': {
                    'accion': 'Notificación a cocina',
                    'resultado': 'OK' if cocina_creado else 'Parcial',
                    'cocina_notificada': cocina_creado
                }
            },
            'integracion': {
                'flujo': 'Completo',
                'timestamp': timezone.now().isoformat()
            }
        })
        
    except Exception as e:
        return Response({
            'error': f'Error en el proceso integrado: {str(e)}'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_restaurante(request):
    """
    Dashboard completo del restaurante con datos de todos los módulos
    """
    try:
        hoy = timezone.now().date()
        ahora = timezone.now()
        
        # ========== MÓDULO 1: INVENTARIO ==========
        ingredientes_bajo_stock = Stock.objects.filter(
            cantidad_disponible__lte=F('ingrediente__stock_minimo')
        ).count()
        
        # ========== MÓDULO 2: RESERVAS ==========
        reservas_hoy = Reserva.objects.filter(fecha_reserva=hoy).count()
        reservas_activas = Reserva.objects.filter(
            fecha_reserva=hoy,
            estado__in=['pendiente', 'confirmada']
        ).count()
        
        # Próximas reservas (en las próximas 2 horas)
        hora_actual = ahora.time()
        hora_limite = (datetime.combine(hoy, hora_actual) + dt.timedelta(hours=2)).time()
        
        proximas_reservas = Reserva.objects.filter(
            fecha_reserva=hoy,
            hora_inicio__gte=hora_actual,
            hora_inicio__lte=hora_limite,
            estado__in=['pendiente', 'confirmada']
        ).select_related('mesa', 'cliente')[:5]
        
        # ========== MÓDULO 3: PEDIDOS ==========
        pedidos_hoy_count = 0
        pedidos_por_estado = {}
        
        try:
            from pedidos.models import Pedido
            # Pedidos de hoy
            inicio_hoy = timezone.make_aware(datetime.combine(hoy, dt_time.min))
            fin_hoy = timezone.make_aware(datetime.combine(hoy, dt_time.max))
            
            pedidos_hoy = Pedido.objects.filter(
                creado_en__range=[inicio_hoy, fin_hoy]
            )
            pedidos_hoy_count = pedidos_hoy.count()
            
            # Agrupar por estado
            pedidos_por_estado_list = pedidos_hoy.values('estado').annotate(
                total=Count('id')
            )
            pedidos_por_estado = {item['estado']: item['total'] for item in pedidos_por_estado_list}
            
        except Exception as e:
            pedidos_por_estado = {'error': str(e)}
        
        # ========== MÓDULO 4: COCINA ==========
        cocina_pedidos_count = 0
        cocina_por_estado = {}
        
        try:
            from cocina.models import PedidoCocina
            
            cocina_pedidos = PedidoCocina.objects.filter(
                fecha_creacion__date=hoy
            )
            cocina_pedidos_count = cocina_pedidos.count()
            
            cocina_por_estado_list = cocina_pedidos.values('estado').annotate(
                total=Count('id')
            )
            cocina_por_estado = {item['estado']: item['total'] for item in cocina_por_estado_list}
            
        except Exception as e:
            cocina_por_estado = {'error': str(e)}
        
        # ========== MESAS DISPONIBLES ==========
        mesas_totales = Mesa.objects.count()
        mesas_disponibles = Mesa.objects.filter(estado='disponible').count()
        
        # ========== CONSTRUIR RESPUESTA ==========
        ocupacion_porcentaje = 0
        if mesas_totales > 0:
            ocupacion_porcentaje = ((mesas_totales - mesas_disponibles) / mesas_totales) * 100
        
        return Response({
            'dashboard': 'Estado del Restaurante',
            'fecha': hoy.isoformat(),
            'hora_actual': ahora.strftime('%H:%M'),
            
            'resumen': {
                'inventario': {
                    'ingredientes_bajo_stock': ingredientes_bajo_stock,
                    'alerta': ingredientes_bajo_stock > 0
                },
                'reservas': {
                    'total_hoy': reservas_hoy,
                    'activas': reservas_activas,
                    'ocupacion_mesas': f'{ocupacion_porcentaje:.1f}%'
                },
                'pedidos': {
                    'hoy': pedidos_hoy_count,
                    'por_estado': pedidos_por_estado
                },
                'cocina': {
                    'pedidos_hoy': cocina_pedidos_count,
                    'por_estado': cocina_por_estado
                },
                'mesas': {
                    'totales': mesas_totales,
                    'disponibles': mesas_disponibles,
                    'ocupadas': mesas_totales - mesas_disponibles
                }
            },
            
            'proximas_reservas': [
                {
                    'id': r.id,
                    'mesa': r.mesa.numero,
                    'cliente': r.cliente.username,
                    'hora': r.hora_inicio.strftime('%H:%M'),
                    'personas': r.num_personas
                }
                for r in proximas_reservas
            ] if proximas_reservas else [],
            
            'modulos': {
                'modulo_1': 'Menú e Inventario',
                'modulo_2': 'Reservas y Mesas',
                'modulo_3': 'Sistema de Pedidos',
                'modulo_4': 'Monitor de Cocina'
            }
        })
        
    except Exception as e:
        return Response({
            'error': f'Error en el dashboard: {str(e)}'
        }, status=500)


# ==================== API ADICIONAL: VERIFICAR DISPONIBILIDAD ====================

@api_view(['GET'])
@permission_classes([AllowAny])
def verificar_disponibilidad(request):
    """
    Verifica disponibilidad integrada para una reserva:
    - Mesa disponible (Módulo 2)
    - Ingredientes disponibles (Módulo 1)
    """
    try:
        # Parámetros de la consulta
        fecha = request.query_params.get('fecha')
        hora = request.query_params.get('hora')
        personas = request.query_params.get('personas', 1)
        plato_id = request.query_params.get('plato_id')
        
        resultado = {
            'disponibilidad': True,
            'detalles': {},
            'alertas': []
        }
        
        # 1. Verificar mesas disponibles (Módulo 2)
        if fecha and hora and personas:
            try:
                fecha_date = datetime.strptime(fecha, '%Y-%m-%d').date()
                hora_time = datetime.strptime(hora, '%H:%M').time()
                
                # Mesas con capacidad suficiente
                mesas_capacidad = Mesa.objects.filter(capacidad__gte=personas, estado='disponible')
                
                # Filtrar mesas con reservas en ese horario
                mesas_ocupadas = Reserva.objects.filter(
                    fecha_reserva=fecha_date,
                    estado__in=['pendiente', 'confirmada'],
                    hora_inicio__lt=hora_time
                ).filter(
                    hora_fin__gt=hora_time
                ).values_list('mesa_id', flat=True)
                
                mesas_disponibles = mesas_capacidad.exclude(id__in=mesas_ocupadas)
                
                resultado['detalles']['mesas'] = {
                    'disponibles': mesas_disponibles.count(),
                    'suficiente': mesas_disponibles.count() > 0
                }
                
                if mesas_disponibles.count() == 0:
                    resultado['disponibilidad'] = False
                    resultado['alertas'].append('No hay mesas disponibles en ese horario')
                    
            except ValueError as e:
                resultado['detalles']['mesas'] = {'error': 'Formato de fecha/hora inválido'}
        
        # 2. Verificar stock para plato (Módulo 1)
        if plato_id:
            try:
                plato = Plato.objects.get(id=plato_id, activo=True)
                
                ingredientes_faltantes = []
                for receta in plato.recetas.all():
                    stock = Stock.objects.filter(ingrediente=receta.ingrediente).first()
                    if stock and stock.cantidad_disponible < receta.cantidad:
                        ingredientes_faltantes.append(receta.ingrediente.nombre)
                
                resultado['detalles']['stock'] = {
                    'plato': plato.nombre,
                    'ingredientes_faltantes': ingredientes_faltantes,
                    'suficiente': len(ingredientes_faltantes) == 0
                }
                
                if len(ingredientes_faltantes) > 0:
                    resultado['disponibilidad'] = False
                    resultado['alertas'].append(f'Faltan ingredientes: {", ".join(ingredientes_faltantes)}')
                    
            except Plato.DoesNotExist:
                resultado['detalles']['stock'] = {'error': 'Plato no encontrado'}
        
        return Response(resultado)
        
    except Exception as e:
        return Response({
            'error': f'Error verificando disponibilidad: {str(e)}'
        }, status=500)