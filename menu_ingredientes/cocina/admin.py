# cocina/admin.py
from django.contrib import admin
from .models import PedidoCocina

@admin.register(PedidoCocina)
class PedidoCocinaAdmin(admin.ModelAdmin):
    list_display = ('id', 'mesa', 'cliente', 'estado', 'fecha_creacion', 'hora_listo')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('cliente', 'descripcion', 'id_modulo3')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    ordering = ('-fecha_creacion',)
