from rest_framework.routers import DefaultRouter
from django.urls import path
from . import views_api
from .views import PlatoViewSet, IngredienteViewSet, StockViewSet
from .views_modulo2 import (
    MesaViewSet, ReservaViewSet,
    register_user, login_user, get_perfil, update_perfil,
    ConsultaMesasView
)

# Router para ViewSets
router = DefaultRouter()
# Registrar ViewSets
router.register(r'categorias', views_api.CategoriaMenuViewSet)
router.register(r'ingredientes', views_api.IngredienteViewSet)
router.register(r'platos', views_api.PlatoViewSet)
router.register(r'stock', views_api.StockViewSet)

# URLs adicionales
urlpatterns = [
    path('dashboard/', views_api.DashboardAPIView.as_view(), name='dashboard'),
    path('validar-stock/', views_api.ValidarStockAPIView.as_view(), name='validar-stock'),
]

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
