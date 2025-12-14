# cocina/models.py
from django.db import models

class PedidoCocina(models.Model):
    class EstadoPedido(models.TextChoices):
        URGENTE = 'URGENTE', 'Urgente'
        CREADO = 'CREADO', 'Creado'
        EN_PREPARACION = 'EN_PREPARACION', 'En preparación'
        LISTO = 'LISTO', 'Listo'
        ENTREGADO = 'ENTREGADO', 'Entregado'

    # ID del pedido que viene del Módulo 03
    id_modulo3 = models.CharField(max_length=100, unique=True, null=True, blank=True)

    mesa = models.IntegerField(default=1)
    cliente = models.CharField(max_length=100)
    descripcion = models.TextField(default="", blank=True)

    estado = models.CharField(
        max_length=20,
        choices=EstadoPedido.choices,
        default=EstadoPedido.CREADO
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    # Se guarda SOLO cuando llega a LISTO
    hora_listo = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Pedido Cocina'
        verbose_name_plural = 'Pedidos Cocina'

    def __str__(self):
        return f"Mesa {self.mesa} - {self.cliente} - {self.get_estado_display()}"
