"""
Vistas del Módulo 2: Clientes y Mesas
Incluye autenticación, gestión de mesas y reservas
"""

from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from datetime import date, time, timedelta

from rest_framework import viewsets, views, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token

from .models import Mesa, Perfil, Reserva
from .serializers import (
    MesaSerializer,
    PerfilSerializer,
    ReservaSerializer,
    ReservaListSerializer,
    RegisterSerializer
)
from .permissions import IsAdministrador, IsCliente, IsAdminOrCliente


# ============ ENDPOINTS DE AUTENTICACIÓN ============

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Registrar un nuevo usuario (Cliente)
    POST /api/register/
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()

        # Generar token para auto-login
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'rol': user.perfil.rol,
            'rol_display': user.perfil.get_rol_display(),
            'nombre_completo': user.perfil.nombre_completo,
            'message': 'Usuario registrado exitosamente'
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """
    Login de usuario
    POST /api/login/
    Body: { username, password }
    """
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({
            'error': 'Se requieren username y password'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Intentar autenticar
    from django.contrib.auth import authenticate
    user = authenticate(username=username, password=password)

    if user is None:
        return Response({
            'error': 'Credenciales inválidas'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Generar o recuperar token
    token, created = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'rol': user.perfil.rol,
        'rol_display': user.perfil.get_rol_display(),
        'nombre_completo': user.perfil.nombre_completo
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_perfil(request):
    """
    Obtener perfil del usuario autenticado
    GET /api/perfil/
    """
    serializer = PerfilSerializer(request.user.perfil, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_perfil(request):
    """
    Actualizar perfil del usuario autenticado
    PATCH /api/perfil/actualizar/
    """
    perfil = request.user.perfil
    
    # Actualizar campos permitidos
    if 'nombre_completo' in request.data:
        perfil.nombre_completo = request.data['nombre_completo']
    if 'telefono' in request.data:
        perfil.telefono = request.data['telefono']
    
    perfil.save()
    
    serializer = PerfilSerializer(perfil, context={'request': request})
    return Response({
        'mensaje': 'Perfil actualizado exitosamente',
        'perfil': serializer.data
    }, status=status.HTTP_200_OK)


# ============ VIEWSET DE MESAS ============

class MesaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de mesas
    GET /api/mesas/ - Listar todas las mesas
    POST /api/mesas/ - Crear mesa (solo admin)
    GET /api/mesas/{id}/ - Ver una mesa
    PUT/PATCH /api/mesas/{id}/ - Actualizar mesa (solo admin)
    DELETE /api/mesas/{id}/ - Eliminar mesa (solo admin)
    """
    queryset = Mesa.objects.all().order_by('numero')
    serializer_class = MesaSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero']
    ordering_fields = ['numero', 'capacidad', 'estado']

    def get_permissions(self):
        """Solo admin puede crear/editar/eliminar. Todos pueden ver."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdministrador()]
        return [AllowAny()]

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def disponibles(self, request):
        """
        Obtener mesas disponibles
        GET /api/mesas/disponibles/
        Query params: fecha, hora
        """
        fecha_str = request.query_params.get('fecha')
        hora_str = request.query_params.get('hora')

        mesas = Mesa.objects.filter(estado='disponible')

        # Si se proporciona fecha y hora, filtrar por reservas
        if fecha_str and hora_str:
            try:
                fecha = date.fromisoformat(fecha_str)
                hora = time.fromisoformat(hora_str)
                
                # Excluir mesas con reservas activas en ese horario
                reservas_activas = Reserva.objects.filter(
                    fecha_reserva=fecha,
                    estado__in=['pendiente', 'confirmada'],
                    hora_inicio__lte=hora,
                    hora_fin__gte=hora
                )
                
                mesas_reservadas = reservas_activas.values_list('mesa_id', flat=True)
                mesas = mesas.exclude(id__in=mesas_reservadas)
            except (ValueError, TypeError):
                pass

        serializer = self.get_serializer(mesas, many=True)
        return Response(serializer.data)


# ============ VIEWSET DE RESERVAS ============

class ReservaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de reservas
    GET /api/reservas/ - Listar reservas (filtradas por rol)
    POST /api/reservas/ - Crear reserva
    GET /api/reservas/{id}/ - Ver una reserva
    PATCH /api/reservas/{id}/ - Actualizar reserva
    DELETE /api/reservas/{id}/ - Cancelar reserva
    """
    serializer_class = ReservaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['cliente__username', 'cliente__perfil__nombre_completo', 'mesa__numero']
    ordering_fields = ['fecha_reserva', 'hora_inicio', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Clientes solo ven sus propias reservas
        Admins ven todas las reservas
        """
        user = self.request.user
        
        if hasattr(user, 'perfil') and user.perfil.rol == 'admin':
            queryset = Reserva.objects.all()
        else:
            queryset = Reserva.objects.filter(cliente=user)
        
        # Filtros opcionales
        estado = self.request.query_params.get('estado')
        fecha = self.request.query_params.get('fecha_reserva')
        
        if estado:
            queryset = queryset.filter(estado=estado)
        if fecha:
            queryset = queryset.filter(fecha_reserva=fecha)
        
        return queryset.select_related('cliente__perfil', 'mesa')

    def get_serializer_class(self):
        """Usar serializer simplificado para listado"""
        if self.action == 'list':
            return ReservaListSerializer
        return ReservaSerializer

    def perform_create(self, serializer):
        """Asignar automáticamente el cliente al usuario autenticado"""
        # Calcular hora_fin (2 horas después de hora_inicio)
        hora_inicio = serializer.validated_data['hora_inicio']
        hora_fin_calculada = (
            timezone.datetime.combine(date.today(), hora_inicio) + 
            timedelta(hours=2)
        ).time()
        
        serializer.save(
            cliente=self.request.user,
            hora_fin=hora_fin_calculada,
            estado='pendiente'
        )

    @action(detail=True, methods=['patch'], permission_classes=[IsAdministrador])
    def cambiar_estado(self, request, pk=None):
        """
        Cambiar estado de una reserva (solo admin)
        PATCH /api/reservas/{id}/cambiar_estado/
        Body: { estado: 'confirmada'|'cancelada' }
        """
        reserva = self.get_object()
        nuevo_estado = request.data.get('estado')

        estados_validos = ['pendiente', 'confirmada', 'cancelada']
        if nuevo_estado not in estados_validos:
            return Response({
                'error': f'Estado inválido. Debe ser uno de: {", ".join(estados_validos)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        reserva.estado = nuevo_estado
        reserva.save()

        serializer = self.get_serializer(reserva)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancelar una reserva (cliente o admin)
        POST /api/reservas/{id}/cancelar/
        """
        reserva = self.get_object()

        # Verificar permisos: el dueño o admin
        if reserva.cliente != request.user and (not hasattr(request.user, 'perfil') or request.user.perfil.rol != 'admin'):
            return Response({
                'error': 'No tienes permiso para cancelar esta reserva'
            }, status=status.HTTP_403_FORBIDDEN)

        if reserva.estado == 'cancelada':
            return Response({
                'error': 'La reserva ya está cancelada'
            }, status=status.HTTP_400_BAD_REQUEST)

        reserva.estado = 'cancelada'
        reserva.save()

        return Response({
            'mensaje': 'Reserva cancelada exitosamente'
        }, status=status.HTTP_200_OK)


# ============ VISTAS AUXILIARES ============

class ConsultaMesasView(views.APIView):
    """
    Consultar mesas disponibles con filtros avanzados
    GET /api/consultar-mesas/?fecha=2025-12-25&hora=12:00&personas=4
    """
    permission_classes = [AllowAny]

    def get(self, request):
        fecha_str = request.query_params.get('fecha')
        hora_str = request.query_params.get('hora')
        personas = request.query_params.get('personas')

        mesas = Mesa.objects.filter(estado='disponible')

        # Filtrar por capacidad
        if personas:
            try:
                mesas = mesas.filter(capacidad__gte=int(personas))
            except (ValueError, TypeError):
                pass

        # Filtrar por disponibilidad en fecha/hora
        if fecha_str and hora_str:
            try:
                fecha = date.fromisoformat(fecha_str)
                hora = time.fromisoformat(hora_str)
                
                reservas_activas = Reserva.objects.filter(
                    fecha_reserva=fecha,
                    estado__in=['pendiente', 'confirmada'],
                    hora_inicio__lte=hora,
                    hora_fin__gte=hora
                )
                
                mesas_reservadas = reservas_activas.values_list('mesa_id', flat=True)
                mesas = mesas.exclude(id__in=mesas_reservadas)
            except (ValueError, TypeError):
                return Response({
                    'error': 'Formato de fecha u hora inválido'
                }, status=status.HTTP_400_BAD_REQUEST)

        serializer = MesaSerializer(mesas, many=True)
        return Response(serializer.data)
