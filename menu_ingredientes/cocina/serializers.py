# cocina/serializers.py
from rest_framework import serializers 
from .models import PedidoCocina

class PedidoCocinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PedidoCocina
        fields = '__all__'
