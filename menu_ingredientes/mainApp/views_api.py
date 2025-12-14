# mainApp/views_api.py - VERSIÓN CORREGIDA Y FUNCIONAL

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, F

from .models import CategoriaMenu, Ingrediente, Plato, Receta, Stock, ReservaStock
from .serializers import (
    CategoriaMenuSerializer, IngredienteSerializer, 
    PlatoSerializer, StockSerializer
)

# ==================== VIEWSETS BÁSICOS ====================

class CategoriaMenuViewSet(viewsets.ModelViewSet):
    """
    API para gestión de categorías de menú
    """
    queryset = CategoriaMenu.objects.all()
    serializer_class = CategoriaMenuSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]


class IngredienteViewSet(viewsets.ModelViewSet):
    """
    API para gestión de ingredientes
    """
    queryset = Ingrediente.objects.all()
    serializer_class = IngredienteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['nombre']
    filterset_fields = ['unidad_medida']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]


class PlatoViewSet(viewsets.ModelViewSet):
    """
    API para gestión de platos del menú
    """
    queryset = Plato.objects.filter(activo=True)
    serializer_class = PlatoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['nombre', 'descripcion']
    filterset_fields = ['categoria', 'activo']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        """Platos activos disponibles"""
        platos = Plato.objects.filter(activo=True)
        serializer = self.get_serializer(platos, many=True)
        return Response(serializer.data)


class StockViewSet(viewsets.ModelViewSet):
    """
    API para gestión de stock
    """
    queryset = Stock.objects.select_related('ingrediente').all()
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['ingrediente__nombre']

    @action(detail=False, methods=['get'])
    def bajo_stock(self, request):
        """Ingredientes con stock bajo"""
        stock_bajo = self.get_queryset().filter(
            cantidad_disponible__lte=F('ingrediente__stock_minimo')
        )
        serializer = self.get_serializer(stock_bajo, many=True)
        return Response(serializer.data)


# ==================== APIViews SIMPLES ====================

class DashboardAPIView(APIView):
    """
    Dashboard administrativo
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = {
            'total_categorias': CategoriaMenu.objects.count(),
            'total_ingredientes': Ingrediente.objects.count(),
            'total_platos': Plato.objects.filter(activo=True).count(),
            'platos_por_categoria': Plato.objects.values('categoria__nombre')
                .annotate(total=Count('id'))
                .order_by('categoria__nombre'),
            'ingredientes_bajo_stock': Stock.objects.filter(
                cantidad_disponible__lte=F('ingrediente__stock_minimo')
            ).count(),
        }
        return Response(stats)


class ValidarStockAPIView(APIView):
    """
    Validar stock para un plato
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plato_id = request.data.get('plato_id')
        cantidad = request.data.get('cantidad', 1)

        if not plato_id:
            return Response(
                {'error': 'plato_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            plato = Plato.objects.get(id=plato_id, activo=True)
        except Plato.DoesNotExist:
            return Response(
                {'error': 'Plato no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verificar stock para cada ingrediente
        faltantes = []
        for receta in plato.recetas.all():
            stock = Stock.objects.filter(ingrediente=receta.ingrediente).first()
            if stock and stock.cantidad_disponible < (receta.cantidad * cantidad):
                faltantes.append({
                    'ingrediente': receta.ingrediente.nombre,
                    'necesario': receta.cantidad * cantidad,
                    'disponible': stock.cantidad_disponible
                })

        return Response({
            'plato': plato.nombre,
            'cantidad': cantidad,
            'stock_suficiente': len(faltantes) == 0,
            'ingredientes_faltantes': faltantes
        })


# ==================== VIEWSETS ADICIONALES (si los necesitas) ====================

class RecetaViewSet(viewsets.ModelViewSet):
    """
    API para recetas (relación plato-ingrediente)
    """
    queryset = Receta.objects.select_related('plato', 'ingrediente').all()
    serializer_class = None  # Necesitarías crear RecetaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Receta.objects.all()
        plato_id = self.request.query_params.get('plato_id')
        if plato_id:
            queryset = queryset.filter(plato_id=plato_id)
        return queryset


class ReservaStockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para consultar reservas de stock
    """
    queryset = ReservaStock.objects.select_related('plato').all()
    serializer_class = None  # Necesitarías crear ReservaStockSerializer
    permission_classes = [IsAuthenticated]