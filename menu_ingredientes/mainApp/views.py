# IMPORTS
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import CategoriaMenu, Ingrediente, Plato, Receta, Stock, ReservaStock, Mesa, Reserva
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.forms import inlineformset_factory
from .forms import PlatoForm, StockForm, CategoriaForm, IngredienteForm, RecetaInlineForm, MesaForm, ReservaForm
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from functools import wraps

# Decorador personalizado para verificar que el usuario sea administrador
def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        # Permitir acceso a superusers y staff
        if request.user.is_superuser or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        # Verificar si tiene perfil de admin
        if hasattr(request.user, 'perfil') and request.user.perfil.rol == 'admin':
            return view_func(request, *args, **kwargs)
        # Si no es admin, redirigir al menú de cliente
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('cliente_menu')
    return wrapper

# SERIALIZERS (Simples, sin DRF)
class PlatoSerializer:
    def __init__(self, instance=None, data=None, partial=False):
        self.instance = instance  # ✅ Esta línea estaba sin indentación
        self.data = data
        self.partial = partial  # Para soportar PATCH
    
    def to_representation(self, instance):
        return {
            'id': instance.id,
            'nombre': instance.nombre,
            'descripcion': instance.descripcion,
            'precio': str(instance.precio),
            'categoria': {
                'id': instance.categoria.id if instance.categoria else None,
                'nombre': instance.categoria.nombre if instance.categoria else None
            },
            'activo': instance.activo,
            'recetas': [
                {
                    'id': receta.id,
                    'ingrediente': receta.ingrediente.nombre,
                    'unidad_medida': receta.ingrediente.unidad_medida,
                    'cantidad': str(receta.cantidad)
                } for receta in instance.recetas.all()
            ]
        }

    def is_valid(self):
        if not self.data:
            return False
        
        # Para PATCH, no requerimos todos los campos
        if not self.partial:
            required_fields = ['nombre', 'precio', 'categoria']
            for field in required_fields:
                if field not in self.data or not self.data[field]:
                    return False
        
        # Validar precio si se está actualizando
        if 'precio' in self.data:
            try:
                precio = float(self.data['precio'])
                if precio <= 0:
                    return False
            except (TypeError, ValueError):
                return False
        
        # Validar categoría si se está actualizando
        if 'categoria' in self.data:
            try:
                CategoriaMenu.objects.get(id=self.data['categoria'])
            except CategoriaMenu.DoesNotExist:
                return False

        return True

    def save(self):
        if self.instance:
            # UPDATE - Solo actualizar campos que vienen en data
            if 'nombre' in self.data:
                self.instance.nombre = self.data['nombre']
            if 'descripcion' in self.data:
                self.instance.descripcion = self.data.get('descripcion', '')
            if 'precio' in self.data:
                self.instance.precio = self.data['precio']
            if 'categoria' in self.data:
                self.instance.categoria_id = self.data['categoria']
            
            self.instance.save()
            
            # Manejar recetas si vienen en los datos
            if 'recetas' in self.data:
                # Eliminar recetas existentes y crear nuevas
                self.instance.recetas.all().delete()
                recetas_data = self.data.get('recetas', [])
                for receta_data in recetas_data:
                    ingrediente_id = receta_data.get('ingrediente_id')
                    cantidad = receta_data.get('cantidad')
                    if ingrediente_id and cantidad:
                        try:
                            ingrediente = Ingrediente.objects.get(id=ingrediente_id)
                            Receta.objects.create(
                                plato=self.instance,
                                ingrediente=ingrediente,
                                cantidad=cantidad
                            )
                        except Ingrediente.DoesNotExist:
                            continue
            
            return self.instance
        else:
            # CREATE - Código existente
            plato = Plato.objects.create(
                nombre=self.data['nombre'],
                descripcion=self.data.get('descripcion', ''),
                precio=self.data['precio'],
                categoria_id=self.data['categoria']
            )
            
            recetas_data = self.data.get('recetas', [])
            for receta_data in recetas_data:
                ingrediente_id = receta_data.get('ingrediente_id')
                cantidad = receta_data.get('cantidad')
                if ingrediente_id and cantidad:
                    try:
                        ingrediente = Ingrediente.objects.get(id=ingrediente_id)
                        Receta.objects.create(
                            plato=plato,
                            ingrediente=ingrediente,
                            cantidad=cantidad
                        )
                    except Ingrediente.DoesNotExist:
                        continue
            return plato

class IngredienteSerializer:
    def to_representation(self, instance):
        return {
            'id': instance.id,
            'nombre': instance.nombre,
            'unidad_medida': instance.unidad_medida,
            'stock_minimo': instance.stock_minimo
        }


class StockSerializer:
    def to_representation(self, instance):
        return {
            'id': instance.id,
            'ingrediente': instance.ingrediente.nombre,
            'cantidad_disponible': str(instance.cantidad_disponible)
        }

# SERVICIO DE STOCK
class StockService:
    
    @transaction.atomic
    def validar_y_reservar_stock(self, plato_id, cantidad, pedido_id):
        try:
            plato = Plato.objects.get(id=plato_id, activo=True)
            
            # Verificar stock para cada ingrediente
            for receta in plato.recetas.all():
                stock = Stock.objects.get(ingrediente=receta.ingrediente)
                cantidad_necesaria = receta.cantidad * cantidad
                
                if stock.cantidad_disponible < cantidad_necesaria:
                    raise ValidationError(
                        f"Stock insuficiente de {receta.ingrediente.nombre}. "
                        f"Necesario: {cantidad_necesaria}, Disponible: {stock.cantidad_disponible}"
                    )
            
            # Crear reserva
            reserva = ReservaStock.objects.create(
                plato=plato,
                cantidad=cantidad,
                pedido_id=pedido_id,
                estado='reservado'
            )
            
            # Bloquear stock reservado
            for receta in plato.recetas.all():
                stock = Stock.objects.get(ingrediente=receta.ingrediente)
                cantidad_necesaria = receta.cantidad * cantidad
                stock.cantidad_disponible -= cantidad_necesaria
                stock.save()
            
            return reserva
            
        except Plato.DoesNotExist:
            raise ValidationError("Plato no encontrado o inactivo")
        except Stock.DoesNotExist:
            raise ValidationError("Error en configuración de stock")

# VIEWSETS
class PlatoViewSet(viewsets.ViewSet):

    # ... tus métodos existentes (list, retrieve, create, destroy) ...
    
    def update(self, request, pk=None):
        """
        PUT /api/platos/{id}/ - Actualizar plato existente
        """
        try:
            plato = Plato.objects.get(pk=pk, activo=True)
        except Plato.DoesNotExist:
            return Response(
                {'error': 'Plato no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PlatoSerializer(instance=plato, data=request.data)
        if serializer.is_valid():
            plato_actualizado = serializer.save()
            return Response({
                'id': plato_actualizado.id,
                'message': 'Plato actualizado exitosamente',
                'nombre': plato_actualizado.nombre
            })
        
        return Response(
            {'error': 'Datos inválidos para actualización'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def partial_update(self, request, pk=None):
        """
        PATCH /api/platos/{id}/ - Actualización parcial del plato
        """
        try:
            plato = Plato.objects.get(pk=pk, activo=True)
        except Plato.DoesNotExist:
            return Response(
                {'error': 'Plato no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Para PATCH, permitimos actualización parcial
        serializer = PlatoSerializer(instance=plato, data=request.data, partial=True)
        if serializer.is_valid():
            plato_actualizado = serializer.save()
            return Response({
                'id': plato_actualizado.id,
                'message': 'Plato actualizado parcialmente',
                'nombre': plato_actualizado.nombre
            })
        
        return Response(
            {'error': 'Datos inválidos para actualización'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    def list(self, request):
        platos = Plato.objects.filter(activo=True).select_related('categoria')
        serializer = PlatoSerializer()
        data = [serializer.to_representation(plato) for plato in platos]
        return Response(data)
    
    def retrieve(self, request, pk=None):
        try:
            plato = Plato.objects.get(pk=pk, activo=True)
            serializer = PlatoSerializer()
            return Response(serializer.to_representation(plato))
        except Plato.DoesNotExist:
            return Response(
                {'error': 'Plato no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def create(self, request):
        serializer = PlatoSerializer(data=request.data)
        if serializer.is_valid():
            plato = serializer.save()
            return Response(
                {'id': plato.id, 'message': 'Plato creado exitosamente'},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {'error': 'Datos inválidos o categoría inexistente o precio no válido'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def destroy(self, request, pk=None):
        try:
            plato = Plato.objects.get(pk=pk)
            plato.activo = False
            plato.save()
            return Response({'message': 'Plato desactivado exitosamente'})
        except Plato.DoesNotExist:
            return Response(
                {'error': 'Plato no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class IngredienteViewSet(viewsets.ViewSet):
    
    def list(self, request):
        ingredientes = Ingrediente.objects.all()
        serializer = IngredienteSerializer()
        data = [serializer.to_representation(ing) for ing in ingredientes]
        return Response(data)

class StockViewSet(viewsets.ViewSet):
    
    def list(self, request):
        stocks = Stock.objects.all()
        serializer = StockSerializer()
        data = [serializer.to_representation(stock) for stock in stocks]
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def validar_reservar(self, request):
        plato_id = request.data.get('plato_id')
        cantidad = request.data.get('cantidad')
        pedido_id = request.data.get('pedido_id')
        
        # Validaciones básicas
        if not plato_id or not cantidad or not pedido_id:
            return Response(
                {'error': 'plato_id, cantidad y pedido_id son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cantidad = int(cantidad)
            if cantidad <= 0:
                return Response(
                    {'error': 'cantidad debe ser mayor a 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (TypeError, ValueError):
            return Response(
                {'error': 'cantidad debe ser un número válido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stock_service = StockService()
            reserva = stock_service.validar_y_reservar_stock(plato_id, cantidad, pedido_id)
            return Response({
                'success': True,
                'reserva_id': reserva.id,
                'message': 'Stock reservado exitosamente'
            })
        except ValidationError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# -------------------- VISTAS WEB (interfaz tradicional) --------------------
@admin_required
def plato_list(request):
    platos = Plato.objects.filter(activo=True).select_related('categoria')
    return render(request, 'mainApp/plato_list.html', {'platos': platos})

@admin_required
def plato_create(request):
    RecetaFormSet = inlineformset_factory(Plato, Receta, form=RecetaInlineForm, extra=1, can_delete=True)
    if request.method == 'POST':
        form = PlatoForm(request.POST)
        if form.is_valid():
            plato = form.save()
            formset = RecetaFormSet(request.POST, instance=plato)
            if formset.is_valid():
                formset.save()
                messages.success(request, 'Plato creado exitosamente')
                return redirect('plato_list')
            else:
                # si el formset no es válido, borrar el plato creado para mantener consistencia
                plato.delete()
        else:
            formset = RecetaFormSet(request.POST)
    else:
        form = PlatoForm()
        formset = RecetaFormSet()
    return render(request, 'mainApp/plato_form.html', {'form': form, 'formset': formset, 'title': 'Nuevo Plato'})


@admin_required
def plato_update(request, pk):
    plato = get_object_or_404(Plato, pk=pk)
    RecetaFormSet = inlineformset_factory(Plato, Receta, form=RecetaInlineForm, extra=1, can_delete=True)
    if request.method == 'POST':
        form = PlatoForm(request.POST, instance=plato)
        formset = RecetaFormSet(request.POST, instance=plato)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Plato actualizado')
            return redirect('plato_list')
    else:
        form = PlatoForm(instance=plato)
        formset = RecetaFormSet(instance=plato)
    return render(request, 'mainApp/plato_form.html', {'form': form, 'formset': formset, 'title': 'Editar Plato'})


@admin_required
def plato_delete(request, pk):
    plato = get_object_or_404(Plato, pk=pk)
    plato.activo = False
    plato.save()
    messages.success(request, 'Plato desactivado')
    return redirect('plato_list')


@admin_required
def stock_list(request):
    stocks = Stock.objects.select_related('ingrediente').all()
    return render(request, 'mainApp/stock_list.html', {'stocks': stocks})


@admin_required
def stock_update(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == 'POST':
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stock actualizado')
            return redirect('stock_list')
    else:
        form = StockForm(instance=stock)
    return render(request, 'mainApp/stock_form.html', {'form': form, 'title': 'Editar Stock'})


@admin_required
def stock_create(request):
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stock creado')
            return redirect('stock_list')
    else:
        form = StockForm()
    return render(request, 'mainApp/stock_form.html', {'form': form, 'title': 'Nuevo Stock'})


# -------------------- VISTAS CATEGORÍAS --------------------
@admin_required
def categoria_list(request):
    categorias = CategoriaMenu.objects.all()
    return render(request, 'mainApp/categoria_list.html', {'categorias': categorias})


@admin_required
def categoria_create(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría creada exitosamente')
            return redirect('categoria_list')
    else:
        form = CategoriaForm()
    return render(request, 'mainApp/categoria_form.html', {'form': form, 'title': 'Nueva Categoría'})


@admin_required
def categoria_update(request, pk):
    categoria = get_object_or_404(CategoriaMenu, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada')
            return redirect('categoria_list')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'mainApp/categoria_form.html', {'form': form, 'title': 'Editar Categoría'})


@admin_required
def categoria_delete(request, pk):
    categoria = get_object_or_404(CategoriaMenu, pk=pk)
    categoria.delete()
    messages.success(request, 'Categoría eliminada')
    return redirect('categoria_list')


@admin_required
def ingrediente_list(request):
    ingredientes = Ingrediente.objects.all()
    return render(request, 'mainApp/ingrediente_list.html', {'ingredientes': ingredientes})


@admin_required
def ingrediente_create(request):
    if request.method == 'POST':
        form = IngredienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ingrediente creado')
            return redirect('ingrediente_list')
    else:
        form = IngredienteForm()
    return render(request, 'mainApp/ingrediente_form.html', {'form': form, 'title': 'Nuevo Ingrediente'})


@admin_required
def ingrediente_update(request, pk):
    ingrediente = get_object_or_404(Ingrediente, pk=pk)
    if request.method == 'POST':
        form = IngredienteForm(request.POST, instance=ingrediente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ingrediente actualizado')
            return redirect('ingrediente_list')
    else:
        form = IngredienteForm(instance=ingrediente)
    return render(request, 'mainApp/ingrediente_form.html', {'form': form, 'title': 'Editar Ingrediente'})


@admin_required
def ingrediente_delete(request, pk):
    ingrediente = get_object_or_404(Ingrediente, pk=pk)
    ingrediente.delete()
    messages.success(request, 'Ingrediente eliminado')
    return redirect('ingrediente_list')


# ==================== MÓDULO 2: VISTAS WEB - MESAS ====================

@admin_required
def mesa_list(request):
    mesas = Mesa.objects.all().order_by('numero')
    return render(request, 'mainApp/mesa_list.html', {'mesas': mesas})


@admin_required
def mesa_create(request):
    if request.method == 'POST':
        form = MesaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mesa creada exitosamente')
            return redirect('mesa_list')
    else:
        form = MesaForm()
    return render(request, 'mainApp/mesa_form.html', {'form': form, 'title': 'Nueva Mesa'})


@admin_required
def mesa_update(request, pk):
    mesa = get_object_or_404(Mesa, pk=pk)
    if request.method == 'POST':
        form = MesaForm(request.POST, instance=mesa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mesa actualizada exitosamente')
            return redirect('mesa_list')
    else:
        form = MesaForm(instance=mesa)
    return render(request, 'mainApp/mesa_form.html', {'form': form, 'title': 'Editar Mesa'})


@admin_required
def mesa_delete(request, pk):
    mesa = get_object_or_404(Mesa, pk=pk)
    if request.method == 'POST':
        mesa.delete()
        messages.success(request, 'Mesa eliminada exitosamente')
    return redirect('mesa_list')


# ==================== MÓDULO 2: VISTAS WEB - RESERVAS (ADMIN) ====================

@admin_required
@admin_required
def reserva_list(request):
    reservas = Reserva.objects.all().select_related('cliente__perfil', 'mesa')
    
    # Filtros
    estado = request.GET.get('estado')
    fecha = request.GET.get('fecha')
    
    if estado:
        reservas = reservas.filter(estado=estado)
    if fecha:
        reservas = reservas.filter(fecha_reserva=fecha)
    
    reservas = reservas.order_by('-created_at')
    
    return render(request, 'mainApp/reserva_list.html', {'reservas': reservas})


@admin_required
def reserva_create(request):
    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            reserva = form.save(commit=False)
            # Calcular hora_fin (2 horas después)
            hora_inicio = form.cleaned_data['hora_inicio']
            reserva.hora_fin = (timezone.datetime.combine(timezone.datetime.today(), hora_inicio) + timedelta(hours=2)).time()
            reserva.save()
            messages.success(request, 'Reserva creada exitosamente')
            return redirect('reserva_list')
    else:
        form = ReservaForm()
    return render(request, 'mainApp/reserva_form.html', {'form': form, 'title': 'Nueva Reserva'})


@admin_required
def reserva_update(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva)
        if form.is_valid():
            form.save()
            messages.success(request, 'Reserva actualizada exitosamente')
            return redirect('reserva_list')
    else:
        form = ReservaForm(instance=reserva)
    return render(request, 'mainApp/reserva_form.html', {'form': form, 'title': 'Editar Reserva'})


@admin_required
def reserva_cancelar(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    if request.method == 'POST':
        reserva.estado = 'cancelada'
        reserva.save()
        messages.success(request, 'Reserva cancelada exitosamente')
    return redirect('reserva_list')


# ==================== MÓDULO 2: VISTAS WEB - CLIENTES ====================

def custom_login_redirect(request):
    """Redirige según el rol del usuario después del login"""
    if request.user.is_authenticated:
        # Superusers siempre van al panel de admin
        if request.user.is_superuser or request.user.is_staff:
            return redirect('admin_dashboard')
        # Usuarios con perfil de admin
        if hasattr(request.user, 'perfil'):
            if request.user.perfil.rol == 'admin':
                return redirect('admin_dashboard')
        # Usuarios cliente o sin perfil van al menú
        return redirect('cliente_menu')
    return redirect('login')


def custom_logout(request):
    """Logout personalizado que acepta GET y POST"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente')
    return redirect('cliente_menu')


def cliente_menu(request):
    """Vista pública del menú para clientes"""
    platos = Plato.objects.filter(activo=True).select_related('categoria')
    categorias = CategoriaMenu.objects.all()
    
    # Filtro por categoría
    categoria_filtro = request.GET.get('categoria')
    if categoria_filtro:
        platos = platos.filter(categoria_id=categoria_filtro)
    
    return render(request, 'mainApp/cliente_menu.html', {
        'platos': platos,
        'categorias': categorias,
        'categoria_filtro': categoria_filtro
    })


def cliente_register(request):
    """Registro de nuevos clientes"""
    if request.method == 'POST':
        from django.contrib.auth.models import User
        
        email = request.POST.get('email')
        username = request.POST.get('username')
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        telefono = request.POST.get('telefono')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validaciones básicas
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso')
            return render(request, 'mainApp/cliente_register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'El correo electrónico ya está registrado')
            return render(request, 'mainApp/cliente_register.html')
        
        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden')
            return render(request, 'mainApp/cliente_register.html')
        
        # Crear usuario y perfil
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        from .models import Perfil
        Perfil.objects.create(
            user=user,
            rol='cliente',  # Siempre crea clientes
            nombre_completo=f"{nombre} {apellido}",
            telefono=telefono
        )
        
        messages.success(request, 'Cuenta de cliente creada exitosamente. Ya puedes iniciar sesión.')
        return redirect('login')
    
    return render(request, 'mainApp/cliente_register.html')


def cliente_reservar(request):
    """Vista para que clientes hagan reservas"""
    from datetime import date, time
    
    if not request.user.is_authenticated:
        messages.warning(request, 'Debes iniciar sesión para hacer una reserva')
        return redirect('login')
    
    if request.method == 'POST':
        fecha_reserva = request.POST.get('fecha_reserva')
        hora_inicio = request.POST.get('hora_inicio')
        mesa_id = request.POST.get('mesa')
        num_personas = request.POST.get('num_personas')
        notas = request.POST.get('notas', '')
        
        # Validaciones básicas
        mesa = get_object_or_404(Mesa, pk=mesa_id)
        
        # Crear reserva
        from datetime import datetime
        hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
        hora_fin_obj = (datetime.combine(date.today(), hora_inicio_obj) + timedelta(hours=2)).time()
        
        try:
            reserva = Reserva(
                cliente=request.user,
                mesa=mesa,
                fecha_reserva=fecha_reserva,
                hora_inicio=hora_inicio_obj,
                hora_fin=hora_fin_obj,
                num_personas=num_personas,
                notas=notas,
                estado='pendiente'
            )
            reserva.full_clean()  # Ejecutar validaciones del modelo
            reserva.save()
            
            messages.success(request, f'¡Reserva creada exitosamente! Tu reserva es la #{reserva.id}')
            return redirect('cliente_mis_reservas')
        except ValidationError as e:
            # Mostrar errores de validación
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, error)
    
    # GET - Mostrar formulario
    mesas = Mesa.objects.all().order_by('numero')  # Mostrar todas las mesas
    
    # Generar horarios disponibles (12:00 - 21:00, cada 30 min)
    horarios = []
    for h in range(12, 21):
        horarios.append(f"{h:02d}:00")
        horarios.append(f"{h:02d}:30")
    
    from datetime import date
    fecha_min = date.today().isoformat()
    
    return render(request, 'mainApp/cliente_reservar.html', {
        'mesas': mesas,
        'horarios': horarios,
        'fecha_min': fecha_min
    })


def cliente_mis_reservas(request):
    """Ver reservas del cliente autenticado"""
    if not request.user.is_authenticated:
        messages.warning(request, 'Debes iniciar sesión')
        return redirect('login')
    
    reservas = Reserva.objects.filter(cliente=request.user).select_related('mesa').order_by('-created_at')
    
    return render(request, 'mainApp/cliente_mis_reservas.html', {
        'reservas': reservas
    })


def cliente_cancelar_reserva(request, pk):
    """Cancelar una reserva del cliente"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    reserva = get_object_or_404(Reserva, pk=pk, cliente=request.user)
    
    if request.method == 'POST':
        if reserva.estado == 'cancelada':
            messages.warning(request, 'Esta reserva ya está cancelada')
        else:
            reserva.estado = 'cancelada'
            reserva.save()
            messages.success(request, 'Reserva cancelada exitosamente')
    
    return redirect('cliente_mis_reservas')
