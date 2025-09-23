# **Guía de Implementación: Sistema de Gestión para La Hidrocálida Pozolería**

**Versión:** 1.0  
**Fecha:** 12 de septiembre de 2025  
**Objetivo:** Guía paso a paso para implementar el sistema POS completo

---

## **📋 Resumen del Proyecto**

Sistema de Punto de Venta (POS) completo para La Hidrocálida Pozolería que incluye:
- **Caja (POS):** Computadora con interfaz para tomar pedidos
- **Cocina (KDS):** Monitor + Tablet para gestionar pedidos
- **Clientes:** TV pública para mostrar pedidos listos
- **Administración:** Panel web para gestión y reportes
- **Monitoreo:** Acceso remoto desde cualquier lugar

---

## **🏗️ Arquitectura Técnica**

### **Stack Tecnológico:**
- **Backend:** FastAPI (Python 3.12+)
- **Frontend:** Vue.js 3 + Tailwind CSS
- **Base de Datos:** PostgreSQL (Neon Cloud)
- **Hosting:** Vercel (Frontend) + Railway/Render (Backend)
- **Comunicación:** WebSockets para tiempo real

### **Dispositivos:**
- **Caja:** 1 Computadora con 2 monitores
- **Cocina:** 1 Monitor + 1 Tablet
- **Clientes:** 1 TV pública
- **Total:** 5 usuarios simultáneos

---

## **📊 Estructura de Base de Datos**

### **Tablas Principales:**
```sql
-- Sucursales
branches (id, name, address)

-- Usuarios/Empleados
users (id, name, role, pin, branch_id)

-- Productos del Menú
products (id, name, description, price, category, status)

-- Pedidos
orders (id, display_id, customer_name, total_amount, status, payment_method, created_at, branch_id, user_id)

-- Items del Pedido
order_items (id, order_id, product_id, quantity, unit_price, modifications)

-- Gastos
expenses (id, description, amount, category, expense_date, branch_id)
```

---

## **🎯 Fases de Implementación**

### **FASE 1: Configuración Inicial (Semana 1)**

#### **Paso 1.1: Configuración del Entorno**
```bash
# Crear estructura del proyecto
mkdir lahidrocalida-system
cd lahidrocalida-system

# Backend
mkdir backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-multipart

# Frontend
cd ..
mkdir frontend
cd frontend
npm create vue@latest . --yes
npm install @tailwindcss/forms @headlessui/vue socket.io-client
```

#### **Paso 1.2: Configuración de Base de Datos**
1. **Crear cuenta en Neon:**
   - Ir a [neon.tech](https://neon.tech)
   - Crear proyecto "lahidrocalida-db"
   - Copiar string de conexión

2. **Crear esquema inicial:**
   ```sql
   -- Ejecutar en Neon SQL Editor
   CREATE TABLE branches (
       id SERIAL PRIMARY KEY,
       name VARCHAR(100) NOT NULL,
       address TEXT
   );

   CREATE TABLE users (111111111111111111111111111
       id SERIAL PRIMARY KEY,
       name VARCHAR(100) NOT NULL,
       role VARCHAR(50) CHECK (role IN ('cashier', 'kitchen', 'admin')),
       pin VARCHAR(255) NOT NULL,
       branch_id INTEGER REFERENCES branches(id)
   );

   CREATE TABLE products (
       id SERIAL PRIMARY KEY,
       name VARCHAR(100) NOT NULL,
       description TEXT,
       price DECIMAL(10,2) NOT NULL,
       category VARCHAR(50) NOT NULL,
       status VARCHAR(50) DEFAULT 'available'
   );

   CREATE TABLE orders (
       id SERIAL PRIMARY KEY,
       display_id VARCHAR(10) NOT NULL,
       customer_name VARCHAR(100),
       total_amount DECIMAL(10,2) NOT NULL,
       status VARCHAR(50) DEFAULT 'pending',
       payment_method VARCHAR(50),
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       branch_id INTEGER REFERENCES branches(id),
       user_id INTEGER REFERENCES users(id)
   );

   CREATE TABLE order_items (
       id SERIAL PRIMARY KEY,
       order_id INTEGER REFERENCES orders(id),
       product_id INTEGER REFERENCES products(id),
       quantity INTEGER NOT NULL,
       unit_price DECIMAL(10,2) NOT NULL,
       modifications TEXT
   );

   CREATE TABLE expenses (
       id SERIAL PRIMARY KEY,
       description VARCHAR(255) NOT NULL,
       amount DECIMAL(10,2) NOT NULL,
       category VARCHAR(50) NOT NULL,
       expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       branch_id INTEGER REFERENCES branches(id)
   );
   ```

#### **Paso 1.3: Configuración del Backend**
1. **Crear archivo `backend/main.py`:**
   ```python
   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware
   import uvicorn

   app = FastAPI(title="La Hidrocálida POS API")

   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )

   @app.get("/")
   async def root():
       return {"message": "La Hidrocálida POS API"}

   if __name__ == "__main__":
       uvicorn.run(app, host="0.0.0.0", port=8000)
   ```

2. **Configurar variables de entorno:**
   ```bash
   # backend/.env
   DATABASE_URL=postgresql://usuario:password@host:port/database
   SECRET_KEY=tu_clave_secreta_aqui
   ```

### **FASE 2: Desarrollo del Backend (Semana 2)**

#### **Paso 2.1: Modelos de Base de Datos**
```python
# backend/models.py
from sqlalchemy import Column, Integer, String, Decimal, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Branch(Base):
    __tablename__ = "branches"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(Text)
    users = relationship("User", back_populates="branch")
    orders = relationship("Order", back_populates="branch")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    pin = Column(String(255), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"))
    branch = relationship("Branch", back_populates="users")
    orders = relationship("Order", back_populates="user")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Decimal(10,2), nullable=False)
    category = Column(String(50), nullable=False)
    status = Column(String(50), default="available")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    display_id = Column(String(10), nullable=False)
    customer_name = Column(String(100))
    total_amount = Column(Decimal(10,2), nullable=False)
    status = Column(String(50), default="pending")
    payment_method = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    branch_id = Column(Integer, ForeignKey("branches.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    branch = relationship("Branch", back_populates="orders")
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Decimal(10,2), nullable=False)
    modifications = Column(Text)
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True)
    description = Column(String(255), nullable=False)
    amount = Column(Decimal(10,2), nullable=False)
    category = Column(String(50), nullable=False)
    expense_date = Column(DateTime, default=datetime.utcnow)
    branch_id = Column(Integer, ForeignKey("branches.id"))
```

#### **Paso 2.2: Endpoints de la API**
```python
# backend/routers/orders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Order, OrderItem, Product
from database import get_db
from schemas import OrderCreate, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderResponse)
async def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    # Lógica para crear pedido
    pass

@router.get("/", response_model=list[OrderResponse])
async def get_orders(db: Session = Depends(get_db)):
    # Lógica para obtener pedidos
    pass

@router.patch("/{order_id}/status")
async def update_order_status(order_id: int, status: str, db: Session = Depends(get_db)):
    # Lógica para actualizar estado
    pass
```

### **FASE 3: Desarrollo del Frontend (Semana 3-4)**

#### **Paso 3.1: Configuración de Vue.js**
```bash
cd frontend
npm install @vueuse/core socket.io-client
```

#### **Paso 3.2: Estructura de Componentes**
```
frontend/src/
├── components/
│   ├── pos/
│   │   ├── ProductGrid.vue
│   │   ├── OrderSummary.vue
│   │   └── PaymentModal.vue
│   ├── kitchen/
│   │   ├── OrderCards.vue
│   │   └── StatusControls.vue
│   ├── customer/
│   │   └── ReadyOrders.vue
│   └── admin/
│       ├── MenuManager.vue
│       ├── ExpenseTracker.vue
│       └── ReportsView.vue
├── views/
│   ├── POSView.vue
│   ├── KitchenView.vue
│   ├── CustomerView.vue
│   └── AdminView.vue
└── stores/
    ├── orderStore.js
    ├── productStore.js
    └── userStore.js
```

#### **Paso 3.3: Implementación del POS (Caja)**
```vue
<!-- frontend/src/views/POSView.vue -->
<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header con logo -->
    <header class="bg-blue-900 text-white p-4">
      <div class="flex items-center justify-between">
        <img src="/logo.png" alt="La Hidrocálida" class="h-12">
        <h1 class="text-2xl font-bold">Sistema de Caja</h1>
        <div class="text-sm">
          Usuario: {{ currentUser.name }}
        </div>
      </div>
    </header>

    <div class="flex h-screen">
      <!-- Panel de Productos -->
      <div class="w-2/3 p-6">
        <div class="grid grid-cols-2 gap-4">
          <div v-for="category in categories" :key="category">
            <h2 class="text-xl font-bold mb-4 text-blue-900">{{ category }}</h2>
            <div class="grid grid-cols-3 gap-3">
              <button 
                v-for="product in getProductsByCategory(category)" 
                :key="product.id"
                @click="addToOrder(product)"
                class="bg-white p-4 rounded-lg shadow hover:shadow-lg transition-shadow border-2 border-transparent hover:border-yellow-400"
              >
                <h3 class="font-semibold">{{ product.name }}</h3>
                <p class="text-gray-600 text-sm">{{ product.description }}</p>
                <p class="text-blue-900 font-bold">${{ product.price }}</p>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Panel de Pedido -->
      <div class="w-1/3 bg-white border-l p-6">
        <h2 class="text-xl font-bold mb-4 text-blue-900">Pedido Actual</h2>
        
        <!-- Items del pedido -->
        <div class="space-y-2 mb-4">
          <div v-for="item in currentOrder.items" :key="item.id" class="flex justify-between items-center p-2 bg-gray-50 rounded">
            <div>
              <span class="font-medium">{{ item.product.name }}</span>
              <span class="text-gray-600">x{{ item.quantity }}</span>
              <p v-if="item.modifications" class="text-sm text-gray-500">{{ item.modifications }}</p>
            </div>
            <span class="font-bold">${{ item.total }}</span>
          </div>
        </div>

        <!-- Total -->
        <div class="border-t pt-4 mb-4">
          <div class="flex justify-between text-xl font-bold">
            <span>Total:</span>
            <span class="text-blue-900">${{ currentOrder.total }}</span>
          </div>
        </div>

        <!-- Botones de acción -->
        <div class="space-y-2">
          <button 
            @click="processPayment"
            :disabled="currentOrder.items.length === 0"
            class="w-full bg-yellow-500 text-white py-3 rounded-lg font-bold hover:bg-yellow-600 disabled:bg-gray-300"
          >
            Procesar Pago
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
```

### **FASE 4: Sistema de Cocina (KDS) (Semana 5)**

#### **Paso 4.1: Monitor de Cocina**
```vue
<!-- frontend/src/views/KitchenView.vue -->
<template>
  <div class="min-h-screen bg-gray-100 p-4">
    <header class="bg-blue-900 text-white p-4 rounded-lg mb-6">
      <h1 class="text-3xl font-bold text-center">Cocina - La Hidrocálida</h1>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div 
        v-for="order in pendingOrders" 
        :key="order.id"
        class="bg-white rounded-lg shadow-lg p-6 border-l-4"
        :class="getOrderBorderColor(order.status)"
      >
        <div class="flex justify-between items-start mb-4">
          <div>
            <h3 class="text-2xl font-bold text-blue-900">Pedido #{{ order.display_id }}</h3>
            <p class="text-gray-600">{{ order.customer_name }}</p>
            <p class="text-sm text-gray-500">{{ formatTime(order.created_at) }}</p>
          </div>
          <span class="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-medium">
            {{ order.status }}
          </span>
        </div>

        <div class="space-y-2 mb-4">
          <div v-for="item in order.items" :key="item.id" class="flex justify-between">
            <span class="font-medium">{{ item.product.name }} x{{ item.quantity }}</span>
            <span class="text-gray-600">${{ item.total }}</span>
          </div>
        </div>

        <div class="flex space-x-2">
          <button 
            @click="updateOrderStatus(order.id, 'preparing')"
            class="flex-1 bg-blue-500 text-white py-2 rounded hover:bg-blue-600"
          >
            En Preparación
          </button>
          <button 
            @click="updateOrderStatus(order.id, 'ready')"
            class="flex-1 bg-green-500 text-white py-2 rounded hover:bg-green-600"
          >
            Listo
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
```

### **FASE 5: Pantalla de Clientes (Semana 6)**

#### **Paso 5.1: TV Pública**
```vue
<!-- frontend/src/views/CustomerView.vue -->
<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-900 to-blue-700 text-white">
    <div class="container mx-auto px-6 py-12">
      <!-- Header -->
      <div class="text-center mb-12">
        <img src="/logo.png" alt="La Hidrocálida" class="h-24 mx-auto mb-6">
        <h1 class="text-5xl font-bold mb-4">La Hidrocálida Pozolería</h1>
        <p class="text-2xl text-blue-200">Pedidos Listos para Recoger</p>
      </div>

      <!-- Pedidos Listos -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <div 
          v-for="order in readyOrders" 
          :key="order.id"
          class="bg-white text-blue-900 rounded-lg shadow-2xl p-8 transform hover:scale-105 transition-transform"
        >
          <div class="text-center">
            <div class="text-6xl font-bold text-yellow-500 mb-4">
              #{{ order.display_id }}
            </div>
            <h3 class="text-2xl font-bold mb-2">{{ order.customer_name }}</h3>
            <p class="text-lg text-gray-600">¡Tu pedido está listo!</p>
            <div class="mt-4 text-sm text-gray-500">
              Listo desde: {{ formatTime(order.ready_at) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Mensaje cuando no hay pedidos -->
      <div v-if="readyOrders.length === 0" class="text-center mt-12">
        <p class="text-2xl text-blue-200">No hay pedidos listos en este momento</p>
      </div>
    </div>
  </div>
</template>
```

### **FASE 6: Panel de Administración (Semana 7)**

#### **Paso 6.1: Gestión de Menú**
```vue
<!-- frontend/src/components/admin/MenuManager.vue -->
<template>
  <div class="bg-white rounded-lg shadow p-6">
    <h2 class="text-2xl font-bold mb-6 text-blue-900">Gestión de Menú</h2>
    
    <!-- Formulario para agregar producto -->
    <form @submit.prevent="addProduct" class="mb-8 p-4 bg-gray-50 rounded-lg">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Nombre</label>
          <input v-model="newProduct.name" type="text" class="w-full border rounded-lg px-3 py-2" required>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Precio</label>
          <input v-model="newProduct.price" type="number" step="0.01" class="w-full border rounded-lg px-3 py-2" required>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Categoría</label>
          <select v-model="newProduct.category" class="w-full border rounded-lg px-3 py-2" required>
            <option value="Pozoles">Pozoles</option>
            <option value="Flautas">Flautas</option>
            <option value="Tacos">Tacos</option>
            <option value="Sopes">Sopes</option>
            <option value="Enchiladas">Enchiladas</option>
            <option value="Tostadas">Tostadas</option>
            <option value="Tamales">Tamales</option>
            <option value="Bebidas">Bebidas</option>
            <option value="Postres">Postres</option>
            <option value="Extras">Extras</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Descripción</label>
          <input v-model="newProduct.description" type="text" class="w-full border rounded-lg px-3 py-2">
        </div>
      </div>
      <button type="submit" class="mt-4 bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600">
        Agregar Producto
      </button>
    </form>

    <!-- Lista de productos -->
    <div class="space-y-4">
      <div v-for="product in products" :key="product.id" class="flex items-center justify-between p-4 border rounded-lg">
        <div>
          <h3 class="font-semibold">{{ product.name }}</h3>
          <p class="text-gray-600">{{ product.description }}</p>
          <span class="text-sm text-blue-600">{{ product.category }}</span>
        </div>
        <div class="flex items-center space-x-4">
          <span class="font-bold text-green-600">${{ product.price }}</span>
          <button @click="editProduct(product)" class="text-blue-500 hover:text-blue-700">Editar</button>
          <button @click="deleteProduct(product.id)" class="text-red-500 hover:text-red-700">Eliminar</button>
        </div>
      </div>
    </div>
  </div>
</template>
```

### **FASE 7: Reportes y Análisis (Semana 8)**

#### **Paso 7.1: Dashboard de Reportes**
```vue
<!-- frontend/src/components/admin/ReportsView.vue -->
<template>
  <div class="space-y-6">
    <!-- Filtros de fecha -->
    <div class="bg-white p-6 rounded-lg shadow">
      <h2 class="text-2xl font-bold mb-4 text-blue-900">Reportes de Ventas</h2>
      <div class="flex space-x-4 mb-6">
        <select v-model="selectedPeriod" @change="loadReports" class="border rounded-lg px-3 py-2">
          <option value="today">Hoy</option>
          <option value="week">Esta Semana</option>
          <option value="month">Este Mes</option>
          <option value="year">Este Año</option>
          <option value="custom">Personalizado</option>
        </select>
        <input v-if="selectedPeriod === 'custom'" v-model="startDate" type="date" class="border rounded-lg px-3 py-2">
        <input v-if="selectedPeriod === 'custom'" v-model="endDate" type="date" class="border rounded-lg px-3 py-2">
      </div>

      <!-- Métricas principales -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div class="bg-blue-50 p-6 rounded-lg">
          <h3 class="text-lg font-semibold text-blue-900">Total Ventas</h3>
          <p class="text-3xl font-bold text-blue-600">${{ reports.totalSales }}</p>
        </div>
        <div class="bg-green-50 p-6 rounded-lg">
          <h3 class="text-lg font-semibold text-green-900">Pedidos</h3>
          <p class="text-3xl font-bold text-green-600">{{ reports.totalOrders }}</p>
        </div>
        <div class="bg-yellow-50 p-6 rounded-lg">
          <h3 class="text-lg font-semibold text-yellow-900">Ticket Promedio</h3>
          <p class="text-3xl font-bold text-yellow-600">${{ reports.averageTicket }}</p>
        </div>
        <div class="bg-red-50 p-6 rounded-lg">
          <h3 class="text-lg font-semibold text-red-900">Gastos</h3>
          <p class="text-3xl font-bold text-red-600">${{ reports.totalExpenses }}</p>
        </div>
      </div>

      <!-- Gráfico de ventas por día -->
      <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-xl font-bold mb-4">Ventas por Día</h3>
        <canvas ref="salesChart"></canvas>
      </div>

      <!-- Top productos -->
      <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-xl font-bold mb-4">Productos Más Vendidos</h3>
        <div class="space-y-2">
          <div v-for="product in reports.topProducts" :key="product.id" class="flex justify-between items-center p-2 bg-gray-50 rounded">
            <span>{{ product.name }}</span>
            <span class="font-bold">{{ product.quantity }} vendidos</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
```

### **FASE 8: Despliegue y Configuración (Semana 9)**

#### **Paso 8.1: Configuración de Hosting**

1. **Backend en Railway:**
   ```bash
   # Instalar Railway CLI
   npm install -g @railway/cli
   
   # Login y deploy
   railway login
   railway init
   railway up
   ```

2. **Frontend en Vercel:**
   ```bash
   # Instalar Vercel CLI
   npm install -g vercel
   
   # Deploy
   cd frontend
   vercel --prod
   ```

#### **Paso 8.2: Configuración de Dominio**
- Comprar dominio (ej: lahidrocalida.com)
- Configurar subdominios:
  - `pos.lahidrocalida.com` - Sistema de Caja
  - `cocina.lahidrocalida.com` - Monitor de Cocina
  - `clientes.lahidrocalida.com` - TV Pública
  - `admin.lahidrocalida.com` - Panel de Administración

#### **Paso 8.3: Configuración de Dispositivos**

1. **Computadora de Caja:**
   - Instalar navegador Chrome
   - Configurar para abrir automáticamente `pos.lahidrocalida.com`
   - Configurar pantalla extendida para segundo monitor

2. **Monitor de Cocina:**
   - Configurar Chromecast o computadora dedicada
   - Abrir `cocina.lahidrocalida.com` en pantalla completa

3. **TV Pública:**
   - Configurar Chromecast o computadora dedicada
   - Abrir `clientes.lahidrocalida.com` en pantalla completa

4. **Tablet de Cocina:**
   - Instalar navegador
   - Configurar acceso a `cocina.lahidrocalida.com`

### **FASE 9: Datos Iniciales y Capacitación (Semana 10)**

#### **Paso 9.1: Carga de Datos Iniciales**

1. **Crear sucursal:**
   ```sql
   INSERT INTO branches (name, address) VALUES 
   ('Pozolería Centro', 'Av. Siglo XXI esq. con prol. Zaragoza');
   ```

2. **Crear usuarios:**
   ```sql
   INSERT INTO users (name, role, pin, branch_id) VALUES 
   ('Admin', 'admin', '1234', 1),
   ('Cajero 1', 'cashier', '1111', 1),
   ('Cocina 1', 'kitchen', '2222', 1);
   ```

3. **Cargar menú completo:**
   ```sql
   -- Pozoles
   INSERT INTO products (name, description, price, category) VALUES 
   ('Pozole Verde Puerco Infantil', 'Pozole verde con puerco, tamaño infantil', 75.00, 'Pozoles'),
   ('Pozole Verde Puerco Regular', 'Pozole verde con puerco, tamaño regular', 95.00, 'Pozoles'),
   ('Pozole Verde Puerco Grande', 'Pozole verde con puerco, tamaño grande', 115.00, 'Pozoles'),
   ('Pozole Verde Pollo Infantil', 'Pozole verde con pollo, tamaño infantil', 85.00, 'Pozoles'),
   ('Pozole Verde Pollo Regular', 'Pozole verde con pollo, tamaño regular', 110.00, 'Pozoles'),
   ('Pozole Verde Pollo Grande', 'Pozole verde con pollo, tamaño grande', 130.00, 'Pozoles');
   
   -- Flautas
   INSERT INTO products (name, description, price, category) VALUES 
   ('Orden Flautas de Puerco', 'Orden de 5 flautas de puerco', 70.00, 'Flautas'),
   ('Orden Flautas de Pollo', 'Orden de 5 flautas de pollo', 90.00, 'Flautas'),
   ('1/2 Orden Flautas (3 pz)', 'Media orden de 3 flautas', 50.00, 'Flautas');
   
   -- Continuar con todos los productos del menú...
   ```

#### **Paso 9.2: Capacitación del Personal**

1. **Manual de Usuario:**
   - Crear guía paso a paso para cada rol
   - Incluir capturas de pantalla
   - Proporcionar casos de uso comunes

2. **Sesiones de Capacitación:**
   - 2 horas para cajeros
   - 1 hora para personal de cocina
   - 1 hora para administradores

3. **Período de Acompañamiento:**
   - Primera semana: Soporte completo
   - Segunda semana: Soporte parcial
   - Tercera semana: Monitoreo remoto

---

## **🔧 Configuración de Desarrollo Local**

### **Requisitos:**
- Python 3.12+
- Node.js 18+
- PostgreSQL (local o Neon)
- Git

### **Comandos de Inicio Rápido:**
```bash
# Clonar repositorio
git clone [tu-repositorio]
cd lahidrocalida-system

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd ../frontend
npm install
npm run dev

# Base de datos
# Configurar DATABASE_URL en backend/.env
```

---

## **📱 URLs de Acceso**

Una vez desplegado:
- **Caja:** `https://pos.lahidrocalida.com`
- **Cocina:** `https://cocina.lahidrocalida.com`
- **Clientes:** `https://clientes.lahidrocalida.com`
- **Admin:** `https://admin.lahidrocalida.com`

---

## **💰 Estimación de Costos Mensuales**

- **Neon Database:** $0-25/mes (plan gratuito inicial)
- **Railway Backend:** $5-20/mes
- **Vercel Frontend:** $0-20/mes (plan gratuito inicial)
- **Dominio:** $10-15/año
- **Total estimado:** $15-60/mes

---

## **🚀 Próximos Pasos Inmediatos**

1. **Crear repositorio en GitHub**
2. **Configurar cuenta en Neon**
3. **Comenzar con Fase 1: Configuración Inicial**
4. **Diseñar mockups de las interfaces**
5. **Configurar entorno de desarrollo local**

---

**Nota:** Esta guía está diseñada para ser seguida paso a paso. Cada fase incluye tareas específicas y código de ejemplo que puedes copiar y adaptar según tus necesidades específicas.
