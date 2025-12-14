from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Pedido',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('mesa', models.CharField(blank=True, max_length=20, null=True)),
                ('cliente', models.CharField(blank=True, max_length=100, null=True)),
                ('plato', models.CharField(blank=True, default='', max_length=60)),
                ('estado', models.CharField(choices=[('CREADO', 'Creado'), ('EN_PREPARACION', 'En preparación'), ('LISTO', 'Listo'), ('ENTREGADO', 'Entregado'), ('CERRADO', 'Cerrado'), ('CANCELADO', 'Cancelado')], default='CREADO', max_length=20)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('entregado_en', models.DateTimeField(blank=True, null=True)),
            ],
        ),
    ]
