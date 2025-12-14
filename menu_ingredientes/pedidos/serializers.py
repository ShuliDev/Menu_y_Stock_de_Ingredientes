from rest_framework import serializers
from .models import Pedido

class PedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedido
        fields = [
            "id", "mesa", "cliente", "plato",
            "estado",
            "creado_en", "actualizado_en", "entregado_en",
        ]
