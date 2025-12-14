from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils.timezone import localtime
import datetime

from pedidos.models import Pedido
from .models import Plato, Mesa


ESTADOS_ACTIVOS = {"CREADO", "EN_PREPARACION", "LISTO", "ENTREGADO"}


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


def _enriquecer_pedido(p):
    p_dict = {
        'id': str(p.id),
        'mesa': p.mesa,
        'cliente': p.cliente,
        'plato': p.plato,
        'plato_nombre': _nombre_plato(p.plato) if p.plato else '-',
        'estado': p.estado,
        'creado_en': p.creado_en,
        'actualizado_en': p.actualizado_en,
        'creado_str': _fmt_hhmm(p.creado_en),
        'actu_str': _fmt_hhmm(p.actualizado_en),
    }
    return p_dict


def mesero(request):
    pedidos = Pedido.objects.all().order_by('-creado_en')
    pedidos_ui = [_enriquecer_pedido(p) for p in pedidos]
    
    # Filtrar pedidos activos
    pedidos_activos_obj = Pedido.objects.filter(estado__in=ESTADOS_ACTIVOS).order_by('-creado_en')
    pedidos_activos_list = [_enriquecer_pedido(p) for p in pedidos_activos_obj]
    
    # Filtrar pedidos inactivos (CERRADO, CANCELADO)
    pedidos_inactivos_obj = Pedido.objects.filter(
        estado__in=['CERRADO', 'CANCELADO']
    ).order_by('-actualizado_en')[:20]  # Últimos 20
    pedidos_inactivos_list = [_enriquecer_pedido(p) for p in pedidos_inactivos_obj]
    
    # Agregar flag de modificación
    for p in pedidos_activos_list:
        p['puede_modificarse'] = p['estado'] == 'CREADO'
    
    platos = Plato.objects.filter(activo=True)
    mesas = Mesa.objects.all().order_by('numero')
    
    ctx = {
        'pedidos': pedidos_ui,
        'pedidos_activos_list': pedidos_activos_list,
        'pedidos_inactivos_list': pedidos_inactivos_list,
        'pedidos_activos': len(pedidos_activos_list),
        'total_pedidos': pedidos.count(),
        'platos': platos,
        'mesas': mesas
    }
    return render(request, 'mainApp/mesero.html', ctx)


@require_http_methods(["POST"])
def crear_pedido(request):
    mesa = (request.POST.get('mesa') or '').strip()
    cliente = (request.POST.get('cliente') or '').strip()
    plato = (request.POST.get('plato') or '').strip()
    if not mesa or not cliente or not plato:
        messages.warning(request, 'Debes seleccionar mesa, cliente y plato.')
        return redirect('pedidos_mesero')

    try:
        mesa_num = int(mesa)
    except ValueError:
        messages.error(request, 'Selecciona una mesa válida.')
        return redirect('pedidos_mesero')

    if not Mesa.objects.filter(numero=mesa_num).exists():
        messages.error(request, f'La mesa {mesa_num} no existe.')
        return redirect('pedidos_mesero')

    # validar mesa
    activos = Pedido.objects.exclude(estado__in=['CERRADO', 'CANCELADO'])
    if activos.filter(mesa=mesa_num).exists():
        messages.error(request, f'La mesa {mesa_num} ya tiene un pedido activo.')
        return redirect('pedidos_mesero')

    p = Pedido.objects.create(mesa=mesa_num, cliente=cliente, plato=plato)
    
    # Crear también en cocina (Módulo 4)
    try:
        from cocina.models import PedidoCocina
        plato_obj = Plato.objects.filter(id=plato).first()
        plato_nombre = plato_obj.nombre if plato_obj else f"Plato #{plato}"
        PedidoCocina.objects.create(
            id_modulo3=str(p.id),
            mesa=mesa_num,
            cliente=cliente,
            descripcion=plato_nombre,
            estado='CREADO'
        )
    except Exception as e:
        pass  # No fallar si cocina no está disponible
    
    messages.success(request, f'Pedido para mesa {mesa_num} creado.')
    return redirect('pedidos_mesero')


def accion_confirmar(request, pedido_id):
    try:
        p = Pedido.objects.get(pk=pedido_id)
        # intentar reservar stock usando StockService (si está disponible)
        try:
            from mainApp.views import StockService
        except Exception:
            StockService = None
        if StockService:
            svc = StockService()
            try:
                svc.validar_y_reservar_stock(int(p.plato), 1, str(p.id))
            except Exception as e:
                messages.error(request, f'No se pudo reservar stock: {e}')
                return redirect('pedidos_mesero')
        p.confirmar()
        
        # Sincronizar con PedidoCocina
        try:
            from cocina.models import PedidoCocina
            p_cocina = PedidoCocina.objects.filter(id_modulo3=str(pedido_id)).first()
            if p_cocina:
                p_cocina.estado = 'EN_PREPARACION'
                p_cocina.save()
        except Exception:
            pass
        
        messages.success(request, 'Pedido confirmado (EN_PREPARACION).')
    except Exception as e:
        messages.error(request, f'No se pudo confirmar: {e}')
    return redirect('pedidos_mesero')


def accion_cancelar(request, pedido_id):
    try:
        p = Pedido.objects.get(pk=pedido_id)
        p.cancelar()
        
        # Eliminar de PedidoCocina
        try:
            from cocina.models import PedidoCocina
            p_cocina = PedidoCocina.objects.filter(id_modulo3=str(pedido_id)).first()
            if p_cocina:
                p_cocina.delete()
        except Exception:
            pass
        
        messages.info(request, 'Pedido cancelado (stock liberado).')
    except Exception as e:
        messages.error(request, f'No se pudo cancelar: {e}')
    return redirect('pedidos_mesero')


def accion_entregar(request, pedido_id):
    try:
        p = Pedido.objects.get(pk=pedido_id)
        p.entregar()
        
        # Sincronizar con PedidoCocina
        try:
            from cocina.models import PedidoCocina
            from django.utils import timezone
            p_cocina = PedidoCocina.objects.filter(id_modulo3=str(pedido_id)).first()
            if p_cocina:
                p_cocina.estado = 'ENTREGADO'
                p_cocina.save()
        except Exception:
            pass
        
        messages.success(request, 'Pedido marcado como ENTREGADO.')
    except Exception as e:
        messages.error(request, f'No se pudo entregar: {e}')
    return redirect('pedidos_mesero')


def accion_cerrar(request, pedido_id):
    try:
        p = Pedido.objects.get(pk=pedido_id)
        p.cerrar()
        messages.success(request, 'Pedido CERRADO.')
    except Exception as e:
        messages.error(request, f'No se pudo cerrar: {e}')
    return redirect('pedidos_mesero')


def cocina(request):
    """Redirigir al monitor de cocina (Módulo 4)"""
    from django.shortcuts import redirect
    return redirect('cocina_monitor')


def cocina_en_preparacion(request, pedido_id):
    """Cambiar pedido a EN_PREPARACION en módulo 4"""
    try:
        from cocina.models import PedidoCocina
        # Buscar en módulo 4 por id_modulo3
        p_cocina = PedidoCocina.objects.filter(id_modulo3=str(pedido_id)).first()
        if p_cocina and p_cocina.estado in ['CREADO', 'URGENTE']:
            p_cocina.estado = 'EN_PREPARACION'
            p_cocina.save()
            
            # Sincronizar con módulo 3
            try:
                p = Pedido.objects.get(pk=pedido_id)
                if p.estado == 'CREADO':
                    p.estado = 'EN_PREPARACION'
                    p.save()
            except Exception:
                pass
            
            messages.success(request, 'Pedido EN_PREPARACION.')
        else:
            messages.warning(request, 'El pedido no se puede preparar.')
    except Exception as e:
        messages.error(request, f'No se pudo cambiar estado: {e}')
    return redirect('cocina_monitor')


def cocina_sin_ingredientes(request, pedido_id):
    """Cancelar pedido por falta de ingredientes"""
    try:
        from cocina.models import PedidoCocina
        # Cancelar en módulo 4
        p_cocina = PedidoCocina.objects.filter(id_modulo3=str(pedido_id)).first()
        if p_cocina:
            p_cocina.delete()
        # Cancelar en módulo 3
        p = Pedido.objects.get(pk=pedido_id)
        p.cancelar()
        messages.info(request, 'Cocina: sin ingredientes, pedido CANCELADO.')
    except Exception as e:
        messages.error(request, f'Error: {e}')
    return redirect('cocina_monitor')


def cocina_listo(request, pedido_id):
    """Marcar pedido como LISTO"""
    try:
        from cocina.models import PedidoCocina
        from django.utils import timezone
        # Actualizar en módulo 4
        p_cocina = PedidoCocina.objects.filter(id_modulo3=str(pedido_id)).first()
        if p_cocina and p_cocina.estado == 'EN_PREPARACION':
            p_cocina.estado = 'LISTO'
            p_cocina.hora_listo = timezone.now()
            p_cocina.save()
            
            # Sincronizar con módulo 3
            try:
                p = Pedido.objects.get(pk=pedido_id)
                p.estado = 'LISTO'
                p.save()
            except Exception:
                pass
            
            messages.success(request, 'Cocina: pedido LISTO para entregar.')
        else:
            messages.warning(request, 'El pedido no está en preparación.')
    except Exception as e:
        messages.error(request, f'Error: {e}')
    return redirect('cocina_monitor')


def cocina_entregar(request, pedido_id):
    """Entregar pedido al cliente"""
    try:
        from cocina.models import PedidoCocina
        from django.utils import timezone
        # Actualizar en módulo 4
        p_cocina = PedidoCocina.objects.filter(id_modulo3=str(pedido_id)).first()
        if p_cocina and p_cocina.estado == 'LISTO':
            p_cocina.estado = 'ENTREGADO'
            p_cocina.save()
            
            # Sincronizar con módulo 3
            try:
                p = Pedido.objects.get(pk=pedido_id)
                p.estado = 'ENTREGADO'
                p.entregado_en = timezone.now()
                p.save()
            except Exception:
                pass
            
            # Eliminar de cocina después de entregar
            p_cocina.delete()
            
            messages.success(request, 'Pedido ENTREGADO. Puede cerrarse desde la vista de pedidos.')
        else:
            messages.warning(request, 'El pedido no está listo.')
    except Exception as e:
        messages.error(request, f'Error: {e}')
    return redirect('cocina_monitor')
