from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PedidoViewSet, cocina_estado, cocina_list

router = DefaultRouter()
router.register(r'', PedidoViewSet, basename='pedido')

urlpatterns = [
    path("cocina/estado/", cocina_estado, name="cocina-estado"),
    path("cocina/lista/", cocina_list, name="cocina-lista"),
]

urlpatterns += router.urls
