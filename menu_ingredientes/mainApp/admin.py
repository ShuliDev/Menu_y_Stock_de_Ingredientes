from django.contrib import admin
from .models import CategoriaMenu, Ingrediente, Plato, Receta, Stock, ReservaStock, Perfil, Mesa, Reserva

@admin.register(CategoriaMenu)
class CategoriaMenuAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    search_fields = ['nombre']

@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'unidad_medida', 'stock_minimo']
    list_filter = ['unidad_medida']
    search_fields = ['nombre']

class RecetaInline(admin.TabularInline):
    model = Receta
    extra = 1

@admin.register(Plato)
class PlatoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'precio', 'categoria', 'activo']
    list_filter = ['categoria', 'activo']
    search_fields = ['nombre']
    inlines = [RecetaInline]

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['ingrediente', 'cantidad_disponible']
    search_fields = ['ingrediente__nombre']

@admin.register(ReservaStock)
class ReservaStockAdmin(admin.ModelAdmin):
    list_display = ['plato', 'cantidad', 'estado', 'fecha_creacion', 'pedido_id']
    list_filter = ['estado', 'fecha_creacion']
    search_fields = ['plato__nombre', 'pedido_id']


# ==================== MÓDULO 2: CLIENTES Y MESAS ====================

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ['user', 'rol', 'nombre_completo', 'telefono']
    list_filter = ['rol']
    search_fields = ['user__username', 'nombre_completo']
    list_editable = ['rol']  # Permite editar rol directamente desde la lista
    fields = ['user', 'rol', 'nombre_completo', 'telefono', 'rut']  # Campos editables en el formulario

@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'capacidad', 'estado']
    list_filter = ['estado']
    search_fields = ['numero']
    ordering = ['numero']

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['id', 'cliente', 'mesa', 'fecha_reserva', 'hora_inicio', 'num_personas', 'estado']
    list_filter = ['estado', 'fecha_reserva']
    search_fields = ['cliente__username', 'mesa__numero']
    ordering = ['-created_at']
