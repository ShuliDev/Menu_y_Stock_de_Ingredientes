import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Pedido(models.Model):
    class Estado(models.TextChoices):
        CREADO = "CREADO", "Creado"
        EN_PREPARACION = "EN_PREPARACION", "En preparación"
        LISTO = "LISTO", "Listo"
        ENTREGADO = "ENTREGADO", "Entregado"
        CERRADO = "CERRADO", "Cerrado"
        CANCELADO = "CANCELADO", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    mesa = models.CharField(max_length=20, null=True, blank=True)
    cliente = models.CharField(max_length=100, null=True, blank=True)
    plato = models.CharField(max_length=60, blank=True, default="")

    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.CREADO
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    entregado_en = models.DateTimeField(null=True, blank=True)

    def puede_modificarse(self):
        return self.estado == Pedido.Estado.CREADO

    def clean(self):
        if self.mesa:
            activos = Pedido.objects.exclude(estado__in=[self.Estado.CERRADO, self.Estado.CANCELADO])
            if self.pk:
                activos = activos.exclude(pk=self.pk)
            if activos.filter(mesa=self.mesa).exists():
                raise ValidationError("La mesa ya tiene un pedido activo.")

    def save(self, *args, **kwargs):
        if self.pk:
            prev = Pedido.objects.filter(pk=self.pk).values_list("estado", flat=True).first()
        else:
            prev = None

        super_set_entregado = False
        if self.estado == self.Estado.ENTREGADO and self.entregado_en is None:
            self.entregado_en = timezone.now()
            super_set_entregado = True

        super().save(*args, **kwargs)

    def confirmar(self):
        if self.estado != self.Estado.CREADO:
            raise ValidationError("Solo se puede confirmar un pedido en estado CREADO.")
        self.estado = self.Estado.EN_PREPARACION
        self.full_clean()
        self.save(update_fields=["estado", "actualizado_en"])

    def marcar_listo(self):
        if self.estado not in [self.Estado.EN_PREPARACION]:
            raise ValidationError("Solo se puede marcar LISTO desde EN_PREPARACION.")
        self.estado = self.Estado.LISTO
        self.full_clean()
        self.save(update_fields=["estado", "actualizado_en"])

    def entregar(self):
        if self.estado != self.Estado.LISTO:
            raise ValidationError("Solo se puede ENTREGAR un pedido LISTO.")
        self.estado = self.Estado.ENTREGADO
        self.full_clean()
        self.save(update_fields=["estado", "actualizado_en", "entregado_en"])

    def cerrar(self):
        if self.estado != self.Estado.ENTREGADO:
            raise ValidationError("Solo se puede CERRAR un pedido ENTREGADO.")
        self.estado = self.Estado.CERRADO
        self.full_clean()
        self.save(update_fields=["estado", "actualizado_en"])

    def cancelar(self):
        if self.estado in [self.Estado.CERRADO, self.Estado.CANCELADO]:
            raise ValidationError("El pedido ya está finalizado.")
        self.estado = self.Estado.CANCELADO
        self.full_clean()
        self.save(update_fields=["estado", "actualizado_en"])

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Pedido {self.id} (mesa={self.mesa or '-'}, estado={self.estado})"
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Pedido(models.Model):
    class Estado(models.TextChoices):
        CREADO = "CREADO", "Creado"
        EN_PREPARACION = "EN_PREPARACION", "En preparación"
        LISTO = "LISTO", "Listo"
        ENTREGADO = "ENTREGADO", "Entregado"
        CERRADO = "CERRADO", "Cerrado"
        CANCELADO = "CANCELADO", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    mesa = models.CharField(max_length=20, null=True, blank=True)
    cliente = models.CharField(max_length=100, null=True, blank=True)
    plato = models.CharField(max_length=60, blank=True, default="")

    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.CREADO
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    entregado_en = models.DateTimeField(null=True, blank=True)

    def puede_modificarse(self):
        return self.estado == Pedido.Estado.CREADO

    def clean(self):
        if self.mesa:
            activos = Pedido.objects.exclude(estado__in=[self.Estado.CERRADO, self.Estado.CANCELADO])
            if self.pk:
                activos = activos.exclude(pk=self.pk)
            if activos.filter(mesa=self.mesa).exists():
                raise ValidationError("La mesa ya tiene un pedido activo.")

    def save(self, *args, **kwargs):
        if self.pk:
            prev = Pedido.objects.filter(pk=self.pk).values_list("estado", flat=True).first()
        else:
            prev = None

        super_set_entregado = False
        if self.estado == self.Estado.ENTREGADO and self.entregado_en is None:
            self.entregado_en = timezone.now()
            super_set_entregado = True

        super().save(*args, **kwargs)

    def confirmar(self):
        if self.estado != self.Estado.CREADO:
            raise ValidationError("Solo se puede confirmar un pedido en estado CREADO.")
        self.estado = self.Estado.EN_PREPARACION
        self.full_clean()
        self.save(update_fields=["estado", "actualizado_en"])

    def marcar_listo(self):
        if self.estado not in [self.Estado.EN_PREPARACION]:
            raise ValidationError("Solo se puede marcar LISTO desde EN_PREPARACION.")
        self.estado = self.Estado.LISTO
        self.full_clean()
        self.save(update_fields=["estado", "actualizado_en"])

    def entregar(self):
        if self.estado != self.Estado.LISTO:
            raise ValidationError("Solo se puede ENTREGAR un pedido LISTO.")
        self.estado = self.Estado.ENTREGADO
        self.full_clean()
        self.save(update_fields=["estado", "actualizado_en", "entregado_en"])

    def cerrar(self):
        if self.estado != self.Estado.ENTREGADO:
            raise ValidationError("Solo se puede CERRAR un pedido ENTREGADO.")
        self.estado = self.Estado.CERRADO
        self.full_clean()
        self.save(update_fields=["estado", "actualizado_en"])

    def cancelar(self):
        if self.estado in [self.Estado.CERRADO, self.Estado.CANCELADO]:
            raise ValidationError("El pedido ya está finalizado.")
        self.estado = self.Estado.CANCELADO
        self.full_clean()
        self.save(update_fields=["estado", "actualizado_en"])

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Pedido {self.id} (mesa={self.mesa or '-'}, estado={self.estado})"
