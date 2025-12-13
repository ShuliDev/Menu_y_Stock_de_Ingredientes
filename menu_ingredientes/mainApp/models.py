from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

class CategoriaMenu(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    
    def __str__(self):
        return self.nombre

class Ingrediente(models.Model):
    UNIDADES = [
        ('gr', 'Gramos'),
        ('kg', 'Kilogramos'),
        ('un', 'Unidades'),
        ('lt', 'Litros'),
    ]
    
    nombre = models.CharField(max_length=100)
    unidad_medida = models.CharField(max_length=2, choices=UNIDADES)
    stock_minimo = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.nombre} ({self.unidad_medida})"

class Plato(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(CategoriaMenu, on_delete=models.CASCADE)
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nombre

class Receta(models.Model):
    plato = models.ForeignKey(Plato, on_delete=models.CASCADE, related_name='recetas')
    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=8, decimal_places=2)
    
    class Meta:
        unique_together = ['plato', 'ingrediente']

class Stock(models.Model):
    ingrediente = models.OneToOneField(Ingrediente, on_delete=models.CASCADE, related_name='stock')
    cantidad_disponible = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Stock {self.ingrediente.nombre}: {self.cantidad_disponible}"

class ReservaStock(models.Model):
    ESTADOS = [
        ('reservado', 'Reservado'),
        ('confirmado', 'Confirmado'),
        ('liberado', 'Liberado'),
    ]
    
    plato = models.ForeignKey(Plato, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='reservado')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    pedido_id = models.CharField(max_length=100)
    
    def __str__(self):
        return f"Reserva {self.plato.nombre} - {self.estado}"


# ==================== MÓDULO 2: CLIENTES Y MESAS ====================

class Perfil(models.Model):
    """Perfil de usuario extendido con roles"""
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('cliente', 'Cliente'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='cliente')
    nombre_completo = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=15, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_rol_display()}"
    
    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"


class Mesa(models.Model):
    """Mesas del restaurante"""
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('reservada', 'Reservada'),
        ('ocupada', 'Ocupada'),
    ]
    
    numero = models.IntegerField(unique=True)
    capacidad = models.IntegerField(default=4)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='disponible')
    
    def clean(self):
        if self.capacidad < 1:
            raise ValidationError({'capacidad': 'La capacidad debe ser al menos 1 persona.'})
    
    def __str__(self):
        return f"Mesa {self.numero} - {self.get_estado_display()} (Cap: {self.capacidad})"
    
    class Meta:
        verbose_name = "Mesa"
        verbose_name_plural = "Mesas"
        ordering = ['numero']


class Reserva(models.Model):
    """Reservas de mesas"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
    ]
    
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservas')
    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE, related_name='reservas')
    fecha_reserva = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    num_personas = models.IntegerField(default=1)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    notas = models.TextField(blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        # Validar que hora_fin sea después de hora_inicio
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError({'hora_fin': 'La hora de fin debe ser posterior a la hora de inicio.'})
        
        # Validar que num_personas no exceda capacidad de la mesa
        if self.mesa and self.num_personas > self.mesa.capacidad:
            raise ValidationError({
                'num_personas': f'El número de personas ({self.num_personas}) excede la capacidad de la mesa ({self.mesa.capacidad}).'
            })
    
    def __str__(self):
        return f"Reserva {self.id} - {self.cliente.username} - Mesa {self.mesa.numero} ({self.fecha_reserva})"
    
    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ['-created_at']