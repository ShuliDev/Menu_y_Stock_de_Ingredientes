from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views_api

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

# Incluir rutas del router
urlpatterns += router.urls
