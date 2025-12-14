import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'menu_ingredientes.settings')
django.setup()

from cocina.models import PedidoCocina
from pedidos.models import Pedido

p = Pedido.objects.first()
if p:
    mesa_num = int(p.mesa) if p.mesa and p.mesa.isdigit() else 1
    cliente_nombre = p.cliente if p.cliente else "Cliente Test"
    pc = PedidoCocina.objects.create(
        id_modulo3=str(p.id),
        mesa=mesa_num,
        cliente=cliente_nombre,
        descripcion=p.plato if p.plato else 'Pedido de prueba',
        estado=p.estado
    )
    print(f'✓ Creado PedidoCocina {pc.id}: Mesa {pc.mesa}, Cliente: {pc.cliente}, Estado: {pc.estado}')
else:
    print('No hay pedidos en pedidos.Pedido')

print(f'Total PedidoCocina: {PedidoCocina.objects.count()}')
