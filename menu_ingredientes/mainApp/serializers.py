from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Perfil, Mesa, Reserva
from datetime import date, time
import re


# ==================== MÓDULO 2: SERIALIZERS DE AUTENTICACIÓN ====================

class UserSerializer(serializers.ModelSerializer):
    """Serializer básico para usuarios"""
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer para registro de clientes con validaciones"""
    password = serializers.CharField(write_only=True, required=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    # Campos adicionales del Perfil
    nombre = serializers.CharField(required=True, max_length=100, write_only=True)
    apellido = serializers.CharField(required=True, max_length=100, write_only=True)
    telefono = serializers.CharField(required=True, max_length=15)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm',
                  'nombre', 'apellido', 'telefono')

    def validate_telefono(self, value):
        """Validar formato de teléfono chileno"""
        telefono_limpio = value.replace(' ', '').replace('-', '')
        patron_movil = r'^(\+?56)?9\d{8}$'

        if not re.match(patron_movil, telefono_limpio):
            raise serializers.ValidationError(
                'Formato de teléfono inválido. Use formato chileno: +56912345678 o 912345678'
            )

        # Normalizar a formato +56912345678
        if telefono_limpio.startswith('+56'):
            return telefono_limpio
        elif telefono_limpio.startswith('56'):
            return f'+{telefono_limpio}'
        else:
            return f'+56{telefono_limpio}'

    def validate(self, data):
        """Validaciones cruzadas"""
        email = data.get('email')
        username = data.get('username') or email

        # Validar que el email/username no esté en uso
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                'email': 'Este correo ya está registrado.'
            })

        if username and User.objects.filter(username=username).exists():
            raise serializers.ValidationError({
                'username': 'Este nombre de usuario ya está en uso.'
            })

        # Validar que las contraseñas coincidan
        password = data.get('password')
        password_confirm = data.get('password_confirm')

        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden'
            })

        # Validar complejidad de contraseña
        if len(password) < 8:
            raise serializers.ValidationError({
                'password': 'La contraseña debe tener al menos 8 caracteres'
            })

        if not any(c.isupper() for c in password):
            raise serializers.ValidationError({
                'password': 'La contraseña debe contener al menos una letra mayúscula'
            })

        if not any(c.islower() for c in password):
            raise serializers.ValidationError({
                'password': 'La contraseña debe contener al menos una letra minúscula'
            })

        if not any(c.isdigit() for c in password):
            raise serializers.ValidationError({
                'password': 'La contraseña debe contener al menos un número'
            })

        return data

    def create(self, validated_data):
        """Crear usuario y perfil con todos los datos"""
        # Extraer campos que no pertenecen al modelo User
        nombre = validated_data.pop('nombre')
        apellido = validated_data.pop('apellido')
        nombre_completo = f"{nombre} {apellido}"
        telefono = validated_data.pop('telefono')
        validated_data.pop('password_confirm')

        # Crear usuario
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )

        # Crear perfil
        Perfil.objects.create(
            user=user,
            rol='cliente',
            nombre_completo=nombre_completo,
            telefono=telefono
        )

        return user


class PerfilSerializer(serializers.ModelSerializer):
    """Serializer para perfiles de usuario"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)

    class Meta:
        model = Perfil
        fields = ('id', 'username', 'email', 'rol', 'rol_display',
                  'nombre_completo', 'telefono')


# ==================== MÓDULO 2: SERIALIZERS DE MESAS ====================

class MesaSerializer(serializers.ModelSerializer):
    """Serializer para mesas"""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = Mesa
        fields = ['id', 'numero', 'capacidad', 'estado', 'estado_display']
        read_only_fields = ['id']
    
    def validate_capacidad(self, value):
        if value < 1:
            raise serializers.ValidationError("La capacidad debe ser al menos 1 persona.")
        return value


# ==================== MÓDULO 2: SERIALIZERS DE RESERVAS ====================

class ReservaSerializer(serializers.ModelSerializer):
    """Serializer completo para reservas"""
    cliente_nombre = serializers.CharField(source='cliente.perfil.nombre_completo', read_only=True)
    cliente_email = serializers.EmailField(source='cliente.email', read_only=True)
    cliente_telefono = serializers.CharField(source='cliente.perfil.telefono', read_only=True)
    mesa_numero = serializers.IntegerField(source='mesa.numero', read_only=True)
    mesa_info = MesaSerializer(source='mesa', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = Reserva
        fields = ('id', 'cliente', 'cliente_nombre', 'cliente_email', 'cliente_telefono',
                  'mesa', 'mesa_numero', 'mesa_info',
                  'fecha_reserva', 'hora_inicio', 'hora_fin',
                  'num_personas', 'estado', 'estado_display', 'notas',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'hora_fin', 'created_at', 'updated_at')
    
    def validate(self, data):
        """Validaciones de negocio para reservas"""
        # Validar fecha no sea en el pasado
        if data.get('fecha_reserva') and data['fecha_reserva'] < date.today():
            raise serializers.ValidationError({
                'fecha_reserva': 'No se pueden crear reservas para fechas pasadas'
            })

        # Validar horario de operación (12:00 - 21:00)
        if data.get('hora_inicio'):
            hora_apertura = time(12, 0)
            hora_ultimo_turno = time(21, 0)

            if data['hora_inicio'] < hora_apertura or data['hora_inicio'] > hora_ultimo_turno:
                raise serializers.ValidationError({
                    'hora_inicio': 'El horario de atención es de 12:00 a 21:00'
                })

        # Validar capacidad de la mesa
        if 'mesa' in data and 'num_personas' in data:
            if data['num_personas'] > data['mesa'].capacidad:
                raise serializers.ValidationError({
                    'num_personas': f"El número de personas ({data['num_personas']}) excede la capacidad de la mesa ({data['mesa'].capacidad})."
                })
            
            if data['num_personas'] < 1:
                raise serializers.ValidationError({
                    'num_personas': 'El número de personas debe ser al menos 1'
                })
        
        return data


class ReservaListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar reservas"""
    cliente_nombre = serializers.CharField(source='cliente.perfil.nombre_completo', read_only=True)
    mesa_numero = serializers.IntegerField(source='mesa.numero', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = Reserva
        fields = ['id', 'cliente_nombre', 'mesa_numero', 'fecha_reserva',
                  'hora_inicio', 'hora_fin', 'num_personas', 'estado_display', 'created_at']
