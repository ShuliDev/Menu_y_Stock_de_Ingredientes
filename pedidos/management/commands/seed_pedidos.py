from django.core.management.base import BaseCommand
from pedidos.models import Pedido

class Command(BaseCommand):
    help = "Crea pedidos de ejemplo"

    def handle(self, *args, **kwargs):
        data = [
            {"mesa": "A1", "cliente": "Juan"},
            {"mesa": "B7", "cliente": "María"},
        ]
        for d in data:
            obj, created = Pedido.objects.get_or_create(mesa=d["mesa"], cliente=d["cliente"])
            self.stdout.write(f"{'CREADO' if created else 'EXISTE'}: {obj.id} {obj.mesa} {obj.cliente}")
