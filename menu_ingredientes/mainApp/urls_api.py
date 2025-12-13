from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import PlatoViewSet, IngredienteViewSet, StockViewSet
from .views_modulo2 import (
    MesaViewSet, ReservaViewSet,
    register_user, login_user, get_perfil, update_perfil,
    ConsultaMesasView
)

# Router para ViewSets
router = DefaultRouter()
# Módulo 1: Menú y Stock
router.register(r'platos', PlatoViewSet, basename='plato')
router.register(r'ingredientes', IngredienteViewSet, basename='ingrediente')
router.register(r'stock', StockViewSet, basename='stock')

# Módulo 2: Mesas y Reservas
router.register(r'mesas', MesaViewSet, basename='mesa')
router.register(r'reservas', ReservaViewSet, basename='reserva')

# URLs adicionales del Módulo 2
urlpatterns = [
    # Autenticación
    path('register/', register_user, name='register'),
    path('login/', login_user, name='login'),
    path('perfil/', get_perfil, name='perfil'),
    path('perfil/actualizar/', update_perfil, name='actualizar-perfil'),
    
    # Consultas de mesas
    path('consultar-mesas/', ConsultaMesasView.as_view(), name='consultar-mesas'),
]

# Agregar las rutas del router
urlpatterns += router.urls
