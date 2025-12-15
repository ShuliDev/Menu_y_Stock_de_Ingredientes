# mainApp/urls_api.py - VERSIÓN COMPLETA

from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views_api

router = DefaultRouter()

# Registrar ViewSets existentes
router.register(r'categorias', views_api.CategoriaMenuViewSet)
router.register(r'ingredientes', views_api.IngredienteViewSet)
router.register(r'platos', views_api.PlatoViewSet)
router.register(r'stock', views_api.StockViewSet)

# URLs adicionales
urlpatterns = [
    path('dashboard/', views_api.DashboardAPIView.as_view(), name='dashboard'),
    path('validar-stock/', views_api.ValidarStockAPIView.as_view(), name='validar-stock'),
    
    # NUEVAS APIS INTEGRADAS
    path('estado-integrado/', views_api.dashboard_integracion, name='estado_integrado'),
    path('crear-pedido-integrado/', views_api.crear_pedido_integrado, name='crear_pedido_integrado'),
    path('dashboard-restaurante/', views_api.dashboard_restaurante, name='dashboard_restaurante'),
    path('verificar-disponibilidad/', views_api.verificar_disponibilidad, name='verificar_disponibilidad'),
]

# Incluir rutas del router
urlpatterns += router.urls
