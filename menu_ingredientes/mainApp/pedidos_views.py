from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils.timezone import localtime
import datetime

from pedidos.models import Pedido
from .models import Plato


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
    platos = Plato.objects.filter(activo=True)
    ctx = {'pedidos': pedidos_ui, 'platos': platos}
    return render(request, 'mainApp/mesero.html', ctx)


@require_http_methods(["POST"])
def crear_pedido(request):
    mesa = (request.POST.get('mesa') or '').strip()
    cliente = (request.POST.get('cliente') or '').strip()
    plato = (request.POST.get('plato') or '').strip()
    if not mesa or not cliente or not plato:
        messages.warning(request, 'Debes ingresar mesa, cliente y seleccionar un plato.')
        return redirect('pedidos_mesero')

    # validar mesa
    activos = Pedido.objects.exclude(estado__in=['CERRADO', 'CANCELADO'])
    if activos.filter(mesa=mesa).exists():
        messages.error(request, f'La mesa {mesa} ya tiene un pedido activo.')
        return redirect('pedidos_mesero')

    p = Pedido.objects.create(mesa=mesa, cliente=cliente, plato=plato)
    messages.success(request, f'Pedido para mesa {mesa} creado.')
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
        messages.success(request, 'Pedido confirmado (EN_PREPARACION).')
    except Exception as e:
        messages.error(request, f'No se pudo confirmar: {e}')
    return redirect('pedidos_mesero')


def accion_cancelar(request, pedido_id):
    try:
        p = Pedido.objects.get(pk=pedido_id)
        p.cancelar()
        messages.info(request, 'Pedido cancelado (stock liberado).')
    except Exception as e:
        messages.error(request, f'No se pudo cancelar: {e}')
    return redirect('pedidos_mesero')


def accion_entregar(request, pedido_id):
    try:
        p = Pedido.objects.get(pk=pedido_id)
        p.entregar()
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
    pedidos = Pedido.objects.exclude(estado__in=['CANCELADO', 'CERRADO']).order_by('creado_en')
    pedidos_ui = [_enriquecer_pedido(p) for p in pedidos]
    ctx = {'pedidos': pedidos_ui}
    return render(request, 'mainApp/cocina.html', ctx)


def cocina_en_preparacion(request, pedido_id):
    try:
        p = Pedido.objects.get(pk=pedido_id)
        p.confirmar()
        messages.success(request, 'Pedido EN_PREPARACION.')
    except Exception as e:
        messages.error(request, f'No se pudo cambiar estado: {e}')
    return redirect('pedidos_cocina')


def cocina_sin_ingredientes(request, pedido_id):
    try:
        p = Pedido.objects.get(pk=pedido_id)
        p.cancelar()
        messages.info(request, 'Cocina: sin ingredientes, pedido CANCELADO.')
    except Exception as e:
        messages.error(request, f'Error: {e}')
    return redirect('pedidos_cocina')


def cocina_listo(request, pedido_id):
    try:
        p = Pedido.objects.get(pk=pedido_id)
        p.marcar_listo()
        messages.success(request, 'Cocina: pedido LISTO para entregar.')
    except Exception as e:
        messages.error(request, f'Error: {e}')
    return redirect('pedidos_cocina')
