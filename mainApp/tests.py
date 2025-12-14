from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import CategoriaMenu, Ingrediente, Plato, Receta, Stock, ReservaStock
from .services import StockService

class PlatoAPITests(APITestCase):
    
    def setUp(self):
        # Crear datos de prueba
        self.categoria = CategoriaMenu.objects.create(
            nombre="Platos Principales",
            descripcion="Platos fuertes del menú"
        )
        
        self.plato_data = {
            'nombre': 'Pizza Margarita',
            'descripcion': 'Pizza con tomate y queso',
            'precio': '12.99',
            'categoria': self.categoria.id  # ✅ Cambié categoria_id por categoria
        }
    
    def test_crear_plato_exitoso(self):
        """
        Test para crear un plato exitosamente
        """
        url = reverse('plato-list')
        response = self.client.post(url, self.plato_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Plato.objects.count(), 1)
        self.assertEqual(Plato.objects.get().nombre, 'Pizza Margarita')
        self.assertIn('id', response.data)
        self.assertIn('message', response.data)
    
    def test_crear_plato_sin_nombre(self):
        """
        Test para crear plato sin nombre (debe fallar)
        """
        data_invalido = self.plato_data.copy()
        data_invalido['nombre'] = ''  # Nombre vacío
        
        url = reverse('plato-list')
        response = self.client.post(url, data_invalido, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_crear_plato_precio_negativo(self):
        """
        Test para crear plato con precio negativo (debe fallar)
        """
        data_invalido = self.plato_data.copy()
        data_invalido['precio'] = '-5.00'  # Precio negativo
        
        url = reverse('plato-list')
        response = self.client.post(url, data_invalido, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_crear_plato_categoria_inexistente(self):
        """
        Test para crear plato con categoría que no existe
        """
        data_invalido = self.plato_data.copy()
        data_invalido['categoria'] = 999  # ID que no existe
        
        url = reverse('plato-list')
        response = self.client.post(url, data_invalido, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_listar_platos(self):
        """
        Test para listar platos
        """
        # Crear un plato primero
        Plato.objects.create(
            nombre="Test Plato",
            descripcion="Descripción test",
            precio=10.99,
            categoria=self.categoria
        )
        
        url = reverse('plato-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nombre'], 'Test Plato')
    
    def test_obtener_plato_especifico(self):
        """
        Test para obtener un plato específico
        """
        plato = Plato.objects.create(
            nombre="Plato Específico",
            descripcion="Descripción",
            precio=15.99,
            categoria=self.categoria
        )
        
        url = reverse('plato-detail', kwargs={'pk': plato.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nombre'], 'Plato Específico')
        self.assertEqual(response.data['precio'], '15.99')
    
    def test_obtener_plato_inexistente(self):
        """
        Test para obtener un plato que no existe
        """
        url = reverse('plato-detail', kwargs={'pk': 999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_actualizar_plato(self):
        """
        Test para actualizar un plato existente
        """
        plato = Plato.objects.create(
            nombre="Plato Original",
            descripcion="Descripción original",
            precio=10.00,
            categoria=self.categoria
        )
        
        url = reverse('plato-detail', kwargs={'pk': plato.id})
        datos_actualizacion = {
            'nombre': 'Plato Actualizado',
            'precio': '15.99',
            'categoria': self.categoria.id
        }
        
        response = self.client.put(url, datos_actualizacion, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plato.refresh_from_db()
        self.assertEqual(plato.nombre, 'Plato Actualizado')
        self.assertEqual(plato.precio, 15.99)
    
    def test_eliminar_plato(self):
        """
        Test para desactivar un plato (soft delete)
        """
        plato = Plato.objects.create(
            nombre="Plato a Eliminar",
            descripcion="Descripción",
            precio=10.00,
            categoria=self.categoria
        )
        
        url = reverse('plato-detail', kwargs={'pk': plato.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plato.refresh_from_db()
        self.assertFalse(plato.activo)  # Debe estar desactivado, no eliminado


class StockServiceTests(TestCase):
    """
    Tests para el servicio de stock
    """
    
    def setUp(self):
        # Configurar datos para pruebas de stock
        self.categoria = CategoriaMenu.objects.create(nombre="Principal")
        
        self.ingrediente1 = Ingrediente.objects.create(
            nombre="Tomate", unidad_medida="un", stock_minimo=5
        )
        self.ingrediente2 = Ingrediente.objects.create(
            nombre="Queso", unidad_medida="gr", stock_minimo=100
        )
        
        self.plato = Plato.objects.create(
            nombre="Pizza Margarita",
            descripcion="Pizza con tomate y queso",
            precio=12.99,
            categoria=self.categoria
        )
        
        # Crear recetas
        Receta.objects.create(
            plato=self.plato, 
            ingrediente=self.ingrediente1, 
            cantidad=2.00
        )
        Receta.objects.create(
            plato=self.plato, 
            ingrediente=self.ingrediente2, 
            cantidad=200.00
        )
        
        # Crear stock
        Stock.objects.create(
            ingrediente=self.ingrediente1, 
            cantidad_disponible=10.00
        )
        Stock.objects.create(
            ingrediente=self.ingrediente2, 
            cantidad_disponible=500.00
        )
    
    def test_validar_stock_suficiente(self):
        """
        Test cuando hay stock suficiente
        """
        service = StockService()
        
        # Debe funcionar con cantidad 2
        reserva = service.validar_y_reservar_stock(
            plato_id=self.plato.id, 
            cantidad=2, 
            pedido_id="TEST-001"
        )
        
        self.assertIsNotNone(reserva)
        self.assertEqual(reserva.cantidad, 2)
        self.assertEqual(reserva.estado, 'reservado')
        
        # Verificar que el stock se actualizó
        stock_tomate = Stock.objects.get(ingrediente=self.ingrediente1)
        self.assertEqual(stock_tomate.cantidad_disponible, 6.00)  # 10 - (2*2)
    
    def test_validar_stock_insuficiente(self):
        """
        Test cuando NO hay stock suficiente
        """
        service = StockService()
        
        # Debe fallar con cantidad 10 (necesita 20 tomates, solo hay 10)
        with self.assertRaises(ValidationError) as context:
            service.validar_y_reservar_stock(
                plato_id=self.plato.id, 
                cantidad=10,  # Demasiado
                pedido_id="TEST-002"
            )
        
        self.assertIn("Stock insuficiente", str(context.exception))
    
    def test_validar_plato_inexistente(self):
        """
        Test con plato que no existe
        """
        service = StockService()
        
        with self.assertRaises(ValidationError) as context:
            service.validar_y_reservar_stock(
                plato_id=999,  # No existe
                cantidad=1,
                pedido_id="TEST-003"
            )
        
        self.assertIn("no encontrado", str(context.exception).lower())


class StockAPITests(APITestCase):
    """
    Tests para los endpoints de stock
    """
    
    def setUp(self):
        # Configuración similar a StockServiceTests
        self.categoria = CategoriaMenu.objects.create(nombre="Principal")
        self.ingrediente = Ingrediente.objects.create(nombre="Tomate", unidad_medida="un")
        self.plato = Plato.objects.create(
            nombre="Pizza Test",
            descripcion="Test",
            precio=10.00,
            categoria=self.categoria
        )
        Receta.objects.create(plato=self.plato, ingrediente=self.ingrediente, cantidad=2)
        Stock.objects.create(ingrediente=self.ingrediente, cantidad_disponible=10)
    
    def test_validar_reservar_stock_exitoso(self):
        """
        Test del endpoint validar/reservar stock exitoso
        """
        url = reverse('stock-validar-reservar')
        data = {
            'plato_id': self.plato.id,
            'cantidad': 2,
            'pedido_id': 'PED-001'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('reserva_id', response.data)
    
    def test_validar_reservar_stock_insuficiente(self):
        """
        Test del endpoint cuando no hay stock suficiente
        """
        url = reverse('stock-validar-reservar')
        data = {
            'plato_id': self.plato.id,
            'cantidad': 10,  # Demasiado
            'pedido_id': 'PED-002'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('insuficiente', response.data['message'].lower())
