# cocina/urls.py
from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'pedidos', views.PedidoCocinaViewSet, basename='pedido-cocina')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Estadísticas
    path('api/estadisticas/tiempos/', views.estadisticas_tiempos, name='cocina_estadisticas_tiempos'),
    
    # Web views
    path('monitor/', views.monitor, name='cocina_monitor'),
    path('administrar/', views.administrar_pedidos, name='cocina_administrar_pedidos'),
    path('editar/<int:pedido_id>/', views.editar_pedido, name='cocina_editar_pedido'),
    path('historial/', views.historial_pedidos, name='cocina_historial_pedidos'),
]
