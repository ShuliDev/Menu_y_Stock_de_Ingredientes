from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from . import views
from . import pedidos_views

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False), name='index'),
    path('admin-dashboard/', views.plato_list, name='admin_dashboard'),
    path('platos/', views.plato_list, name='plato_list'),
    path('plato/new/', views.plato_create, name='plato_create'),
    path('plato/<int:pk>/edit/', views.plato_update, name='plato_update'),
    path('plato/<int:pk>/delete/', views.plato_delete, name='plato_delete'),

    # Categorías
    path('categorias/', views.categoria_list, name='categoria_list'),
    path('categoria/new/', views.categoria_create, name='categoria_create'),
    path('categoria/<int:pk>/edit/', views.categoria_update, name='categoria_update'),
    path('categoria/<int:pk>/delete/', views.categoria_delete, name='categoria_delete'),

    path('stock/', views.stock_list, name='stock_list'),
    path('stock/new/', views.stock_create, name='stock_create'),
    # Ingredientes
    path('ingredientes/', views.ingrediente_list, name='ingrediente_list'),
    path('ingrediente/new/', views.ingrediente_create, name='ingrediente_create'),
    path('ingrediente/<int:pk>/edit/', views.ingrediente_update, name='ingrediente_update'),
    path('ingrediente/<int:pk>/delete/', views.ingrediente_delete, name='ingrediente_delete'),
    path('stock/<int:pk>/edit/', views.stock_update, name='stock_update'),

    # ==================== MÓDULO 2: RUTAS WEB ====================
    
    # Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='mainApp/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('dashboard/', views.custom_login_redirect, name='dashboard_redirect'),
    
    # Mesas
    path('mesas/', views.mesa_list, name='mesa_list'),
    path('mesa/new/', views.mesa_create, name='mesa_create'),
    path('mesa/<int:pk>/edit/', views.mesa_update, name='mesa_update'),
    path('mesa/<int:pk>/delete/', views.mesa_delete, name='mesa_delete'),
    
    # Reservas
    path('reservas/', views.reserva_list, name='reserva_list'),
    path('reserva/new/', views.reserva_create, name='reserva_create'),
    path('reserva/<int:pk>/edit/', views.reserva_update, name='reserva_update'),
    path('reserva/<int:pk>/cancelar/', views.reserva_cancelar, name='reserva_cancelar'),
    
    # ==================== VISTAS PARA CLIENTES ====================
    
    # Vistas públicas
    path('menu/', views.cliente_menu, name='cliente_menu'),
    path('registro/', views.cliente_register, name='cliente_register'),
    
    # Vistas de cliente autenticado
    path('reservar/', views.cliente_reservar, name='cliente_reservar'),
    path('mis-reservas/', views.cliente_mis_reservas, name='cliente_mis_reservas'),
    path('mis-reservas/<int:pk>/cancelar/', views.cliente_cancelar_reserva, name='cliente_cancelar_reserva'),
    
    # ==================== MÓDULO 3: PEDIDOS (ADMIN/MESERO) ====================
    
    # Pedidos - UI
    path('pedidos/', pedidos_views.mesero, name='pedidos_mesero'),
    path('pedidos/crear/', pedidos_views.crear_pedido, name='pedidos_crear'),
    path('pedidos/confirmar/<uuid:pedido_id>/', pedidos_views.accion_confirmar, name='pedidos_confirmar'),
    path('pedidos/cancelar/<uuid:pedido_id>/', pedidos_views.accion_cancelar, name='pedidos_cancelar'),
    path('pedidos/entregar/<uuid:pedido_id>/', pedidos_views.accion_entregar, name='pedidos_entregar'),
    path('pedidos/cerrar/<uuid:pedido_id>/', pedidos_views.accion_cerrar, name='pedidos_cerrar'),
    path('cocina/', pedidos_views.cocina, name='pedidos_cocina'),
    path('cocina/en-preparacion/<uuid:pedido_id>/', pedidos_views.cocina_en_preparacion, name='pedidos_cocina_en_preparacion'),
    path('cocina/sin-ingredientes/<uuid:pedido_id>/', pedidos_views.cocina_sin_ingredientes, name='pedidos_cocina_sin_ingredientes'),
    path('cocina/listo/<uuid:pedido_id>/', pedidos_views.cocina_listo, name='pedidos_cocina_listo'),
    path('cocina/entregar/<uuid:pedido_id>/', pedidos_views.cocina_entregar, name='pedidos_cocina_entregar'),
]
