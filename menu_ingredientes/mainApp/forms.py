from django import forms
from .models import Plato, Receta, Ingrediente, Stock, CategoriaMenu, Mesa, Reserva


class PlatoForm(forms.ModelForm):
    class Meta:
        model = Plato
        fields = ['nombre', 'descripcion', 'precio', 'categoria', 'activo']


class RecetaInlineForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = ['ingrediente', 'cantidad']


class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['ingrediente', 'cantidad_disponible']


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = CategoriaMenu
        fields = ['nombre', 'descripcion']


class IngredienteForm(forms.ModelForm):
    class Meta:
        model = Ingrediente
        fields = ['nombre', 'unidad_medida', 'stock_minimo']


# ==================== MÓDULO 2: FORMULARIOS ====================

class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero', 'capacidad']  # Eliminado 'estado'
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'capacidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }


class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['cliente', 'mesa', 'fecha_reserva', 'hora_inicio', 'num_personas', 'estado', 'notas']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'mesa': forms.Select(attrs={'class': 'form-select'}),
            'fecha_reserva': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'num_personas': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
