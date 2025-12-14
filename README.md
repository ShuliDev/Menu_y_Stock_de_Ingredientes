# Sistema de Gestión de Restaurante - Integración Completa

## Descripción
Sistema integral de gestión para restaurante que integra:
- **Módulo 1**: Gestión de menú, ingredientes y stock
- **Módulo 2**: Sistema de clientes, mesas y reservas
- **Módulo 3**: Sistema de pedidos (mesero)
- **Módulo 4**: Monitor de cocina en tiempo real

## 🌐 Acceso al Sistema

### Página Principal
**URL:** https://web-production-2d3fb.up.railway.app/

- Por defecto redirige al login
- Usuarios pueden crear cuenta de cliente o iniciar sesión
- **Admin:** usuario `admin` / contraseña `admin`

### 📋 Vista de Cliente (Pública/Autenticada)
**URL:** https://web-production-2d3fb.up.railway.app/menu/

Funcionalidades:
- Ver menú de platos disponibles (público)
- Filtrar por categoría
- Hacer reservas de mesa (requiere autenticación)
- Ver mis reservas (requiere autenticación)

### 🔧 Panel de Administración
**URL:** https://web-production-2d3fb.up.railway.app/admin-dashboard/

**Acceso:** Solo usuarios con rol `admin` o superusers

Funcionalidades completas:
- Gestión de platos, ingredientes, categorías y stock
- Gestión de mesas
- Gestión de reservas (ver, editar estado, cancelar)
- Gestión de pedidos
- Monitor de cocina

### 🍽️ Sistema de Pedidos (Mesero)
**URL:** https://web-production-2d3fb.up.railway.app/pedidos/

**Acceso:** Usuarios autenticados

Funcionalidades:
- Crear nuevos pedidos (mesa, cliente, plato)
- Ver pedidos activos e inactivos
- Estados: CREADO → EN_PREPARACION → LISTO → ENTREGADO → CERRADO

### 👨‍🍳 Monitor de Cocina
**URL:** https://web-production-2d3fb.up.railway.app/cocina/monitor/

**Acceso:** Usuarios autenticados

Funcionalidades:
- Vista en tiempo real de pedidos por estado
- Gestión de flujo de cocina:
- Pedidos Nuevos → Botón "Preparar"
- En Preparación → Botón "Listo" / "Sin ingredientes"
- Listos → Botón "Entregar"
- Sincronización automática con sistema de pedidos
- Contadores por estado
- Interfaz intuitiva con colores por estado

### Django Admin
**URL:** https://web-production-2d3fb.up.railway.app/admin/

**Acceso:** Solo superusers

## Roles de Usuario

### Cliente (`rol='cliente'`)
- Se crea mediante registro público en `/registro/`
- Puede ver menú, hacer reservas y gestionar sus propias reservas
- No tiene acceso al panel de administración

### Administrador (`rol='admin'`)
- Debe ser creado manualmente:
  1. Crear superuser: `python manage.py createsuperuser`
  2. O crear perfil con `rol='admin'` en Django Admin
- Acceso completo al panel de administración
- Puede gestionar todas las reservas y recursos del restaurante

### Superuser
- Creado con `python manage.py createsuperuser`
- Acceso automático al panel de administración (sin necesidad de perfil)
- Acceso a Django Admin

---

## 🔌 API REST

### Documentación Interactiva

**Base URL:** https://web-production-2d3fb.up.railway.app/api/

#### Swagger UI (Recomendado)
**URL:** https://web-production-2d3fb.up.railway.app/swagger/

Documentación interactiva de todos los endpoints disponibles con pruebas en vivo

#### ReDoc
**URL:** https://web-production-2d3fb.up.railway.app/redoc/

Documentación alternativa más detallada y legible

#### Schema OpenAPI
**URL:** https://web-production-2d3fb.up.railway.app/swagger.json

### Endpoints Principales

#### Autenticación
- `POST /api/register/` - Registro de nuevos clientes
- `POST /api/login/` - Login y obtención de token
- `GET /api/perfil/` - Ver perfil del usuario autenticado

#### Gestión de Menú
- `GET/POST /api/platos/` - Listar y crear platos
- `GET/PUT/PATCH/DELETE /api/platos/{id}/` - Detalle, editar y eliminar plato
- `GET/POST /api/ingredientes/` - Listar y crear ingredientes
- `GET/PUT/PATCH/DELETE /api/ingredientes/{id}/` - Gestión de ingrediente específico
- `GET/POST /api/categorias/` - Gestión de categorías

#### Gestión de Stock
- `GET/POST /api/stock/` - Listar y crear registros de stock
- `GET/PUT/PATCH/DELETE /api/stock/{id}/` - Gestión de stock específico

#### Gestión de Mesas y Reservas
- `GET/POST /api/mesas/` - Listar y crear mesas
- `GET/PUT/PATCH/DELETE /api/mesas/{id}/` - Gestión de mesa específica
- `GET/POST /api/reservas/` - Listar y crear reservas
- `GET/PUT/PATCH/DELETE /api/reservas/{id}/` - Gestión de reserva específica
- `GET /api/consultar-mesas/` - Consultar disponibilidad de mesas

#### Pedidos
- `GET/POST /api/pedidos/` - Listar y crear pedidos
- `GET/PUT/PATCH/DELETE /api/pedidos/{id}/` - Gestión de pedido específico

#### Cocina
- `GET/POST /cocina/api/pedidos/` - Pedidos en cocina
- `GET/PUT/PATCH/DELETE /cocina/api/pedidos/{id}/` - Gestión de pedido en cocina

---

## 🔐 Autenticación

### API REST
- **Token-based authentication** (Django REST Framework)
- Header requerido: `Authorization: Token <tu_token>`
- Obtener token: `POST /api/login/` con `username` y `password`

### Interfaz Web
- **Session-based authentication** (Django sessions)
- Login: `/login/`
- Logout: `/logout/` (redirige a menú público)
- Registro: `/registro/`

---

## 📱 Flujo de Trabajo - Pedidos y Cocina

1. **Mesero** crea pedido en `/pedidos/`
   - Selecciona mesa, cliente y plato
   - Estado inicial: `CREADO`

2. **Cocina** recibe pedido en `/cocina/monitor/`
   - Aparece en sección "Pedidos Nuevos"
   - Click "Preparar" → estado `EN_PREPARACION`

3. **Cocinero** gestiona el pedido
   - Pedido en sección "En Preparación"
   - Click "Listo" → estado `LISTO`
   - Click "Sin ingredientes" → pedido `CANCELADO`

4. **Mesero/Cocina** entrega pedido
   - Pedido en tabla "Listos para Entregar"
   - Click "Entregar" → estado `ENTREGADO`

5. **Mesero** cierra pedido en `/pedidos/`
   - Pedido en estado `ENTREGADO`
   - Click "Cerrar" → estado `CERRADO`
   - Aparece en sección "Pedidos Inactivos"

---

## 🗂️ Estructura de Endpoints

### Web Endpoints (Admin)
- `/admin-dashboard/` - Dashboard principal
- `/platos/`, `/ingredientes/`, `/categorias/` - Gestión de menú
- `/stock/` - Gestión de stock
- `/mesas/` - Gestión de mesas
- `/reservas/` - Gestión de reservas
- `/pedidos/` - Gestión de pedidos (mesero)
- `/cocina/monitor/` - Monitor de cocina en tiempo real

### Web Endpoints (Cliente)
- `/menu/` - Menú público
- `/registro/` - Registro de cuenta
- `/reservar/` - Hacer reserva (autenticado)
- `/mis-reservas/` - Ver mis reservas (autenticado)

---

## 🛠️ Tecnologías
- **Backend:** Django 5.2.5
- **API:** Django REST Framework 3.16.1
- **Base de datos:** PostgreSQL (Railway)
- **Documentación:** drf-yasg (Swagger/OpenAPI)
- **Filtros API:** django-filter 24.3
- **Frontend:** Bootstrap 5.1.3
- **Producción:** Gunicorn + WhiteNoise
- **Despliegue:** Railway

---

## 🚀 Instalación Local

```bash
# Clonar repositorio
git clone <repo-url>
cd Menu_y_Stock_de_Ingredientes

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar base de datos
cd menu_ingredientes
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar servidor
python manage.py runserver
```

Acceder a: http://127.0.0.1:8000/

---
