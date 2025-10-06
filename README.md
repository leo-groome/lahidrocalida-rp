# **Plan de Desarrollo de Software: Sistema de Gestión para Pozolería**

Versión: 1.2  
Fecha: 12 de septiembre de 2025

## **1\. Resumen del Proyecto**

El objetivo de este proyecto es desarrollar un Sistema de Punto de Venta (POS) y Gestión de Pedidos a medida para una pozolería. El sistema optimizará el flujo de trabajo desde que el cliente realiza el pedido en caja hasta que lo recoge, mejorando la eficiencia, reduciendo errores y agilizando la comunicación entre el personal de caja y la cocina.  
El sistema está diseñado inicialmente para una sola sucursal, pero su arquitectura se concebirá desde el principio para permitir una expansión sencilla a múltiples sucursales en el futuro.

## **2\. Objetivos**

* **Agilizar el Proceso de Pedido:** Reducir el tiempo que los clientes pasan en la caja.  
* **Centralizar y Digitalizar Pedidos:** Eliminar comandas en papel y la comunicación verbal, minimizando errores en la preparación.  
* **Mejorar la Eficiencia de la Cocina:** Proporcionar una vista clara y en tiempo real de los pedidos pendientes en una pantalla dedicada (KDS \- Kitchen Display System).  
* **Optimizar la Experiencia del Cliente:** Informar a los clientes de manera clara y visual cuando su pedido esté listo para ser recogido.  
* **Establecer una Base Escalable:** Construir una plataforma robusta que pueda crecer y adaptarse a futuras necesidades.

## **3\. Alcance del Proyecto**

### **Funcionalidades Incluidas (In-Scope):**

* **Módulo de Caja (POS):**  
  * Interfaz visual para tomar pedidos.  
  * Capacidad para añadir modificaciones a los productos (sin costo).  
  * Cálculo de totales.  
  * Registro de pagos en efectivo y con terminal externa (Banorte).  
  * Generación de un número de pedido secuencial (ej: 101, 102\) y solicitud del nombre del cliente.  
* **Módulo de Cocina (KDS):**  
  * Visualización en una TV de los pedidos entrantes en tiempo real.  
  * Interfaz en una tablet para marcar pedidos como "Listos" y "Entregados".  
* **Módulo de Notificación al Cliente:**  
  * Visualización en una TV pública de los pedidos listos para ser recogidos.  
* **Módulo de Administración (Básico):**  
  * Gestión de menú (productos y categorías).  
  * Gestión de usuarios y roles.  
  * Registro de Gastos.  
  * Reportes de Ventas (diarios, semanales y mensuales).

### **Funcionalidades Excluidas (Out-of-Scope para la v1.0):**

* Modificadores de productos con costo adicional.  
* Integración directa con la API de la terminal Banorte.  
* Sistema de gestión de inventario.  
* Pedidos en línea o a través de app móvil.

## **4\. Arquitectura del Sistema**

El sistema seguirá una arquitectura cliente-servidor desacoplada.

* **Frontend (Cliente):** Tres interfaces de usuario desarrolladas en **Vue.js con Tailwind CSS**.  
  1. Interfaz de Caja (POS)  
  2. Interfaz de Cocina (KDS)  
  3. Interfaz de Clientes  
* **Backend (Servidor):** API RESTful con **FastAPI (Python)** y WebSockets.  
* **Base de Datos:** **PostgreSQL**.

### **4.1. Diseño de Interfaz y Experiencia de Usuario (UI/UX) \- NUEVO**

El diseño visual de todas las interfaces se basará en la identidad de marca del restaurante, según lo establecido en el documento Menú V6.pdf.

* **Paleta de Colores:** Se utilizará la paleta de colores corporativa, principalmente el **azul oscuro y el amarillo/naranja** del logo, para botones, encabezados y elementos interactivos, garantizando una experiencia coherente con la marca.  
* **Logotipo:** El logo de "La Hidrocálida" se integrará en las interfaces donde sea apropiado, como la pantalla de bienvenida del POS y la pantalla de notificación para clientes.  
* **Legibilidad:** Se priorizará una tipografía clara y de alto contraste para asegurar que los pedidos y los estados sean fáciles de leer en las diferentes pantallas, especialmente en el ambiente de una cocina y en la pantalla pública.

## **5\. Modelo de Datos (según initial.sql)**

Sucursales (`sucursales`)  
| Columna | Tipo | Notas |  
|---|---|---|  
| id | SERIAL | Primary Key |  
| nombre | VARCHAR(100) | |  
| direccion | TEXT | |

Usuarios/Empleados (`usuarios`)  
| Columna | Tipo | Notas |  
|---|---|---|  
| id | SERIAL | Primary Key |  
| nombre | VARCHAR(100) | |  
| rol | VARCHAR(20) | CHECK (rol IN ('cajero','cocina','administrador','compras')) |  
| pin | VARCHAR(6) | |  
| activo | BOOLEAN | DEFAULT TRUE |  
| sucursal_id | INTEGER | Foreign Key -> sucursales.id |

Platillos del menú (`platillos`)  
| Columna | Tipo | Notas |  
|---|---|---|  
| id | SERIAL | Primary Key |  
| nombre | VARCHAR(100) | |  
| descripcion | TEXT | |  
| precio | DECIMAL(8,2) | CHECK (precio >= 0) |  
| categoria | VARCHAR(50) | |  
| estado | VARCHAR(20) | DEFAULT 'disponible' CHECK (estado IN ('disponible','no_disponible')) |

Pedidos (`pedidos`)  
| Columna | Tipo | Notas |  
|---|---|---|  
| id | SERIAL | Primary Key |  
| numero_display | VARCHAR(10) | UNIQUE (p. ej. "101") |  
| nombre_cliente | VARCHAR(100) | |  
| total | DECIMAL(8,2) | CHECK (total >= 0) |  
| estado | VARCHAR(20) | DEFAULT 'pendiente' CHECK (estado IN ('pendiente','preparando','listo','completado')) |  
| metodo_pago | VARCHAR(20) | CHECK (metodo_pago IN ('efectivo','tarjeta','transferencia')) |  
| fecha_creacion | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |  
| sucursal_id | INTEGER | Foreign Key -> sucursales.id |  
| usuario_id | INTEGER | Foreign Key -> usuarios.id |

Artículos de pedido (`articulos_pedido`)  
| Columna | Tipo | Notas |  
|---|---|---|  
| id | SERIAL | Primary Key |  
| pedido_id | INTEGER | FK -> pedidos.id ON DELETE CASCADE |  
| platillo_id | INTEGER | FK -> platillos.id |  
| cantidad | INTEGER | CHECK (cantidad > 0) |  
| precio_cobrado | DECIMAL(8,2) | CHECK (precio_cobrado >= 0) |  
| modificaciones | TEXT | |

Gastos (`gastos`)  
| Columna | Tipo | Notas |  
|---|---|---|  
| id | SERIAL | Primary Key |  
| descripcion | VARCHAR(255) | |  
| monto | DECIMAL(8,2) | CHECK (monto >= 0) |  
| categoria | VARCHAR(50) | |  
| fecha_gasto | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |  
| sucursal_id | INTEGER | Foreign Key -> sucursales.id |

Índices principales  
- `pedidos(estado)`, `pedidos(fecha_creacion)`, `pedidos(numero_display)`  
- `articulos_pedido(pedido_id)`  
- `platillos(categoria)`

## **6\. Fases de Desarrollo**

### **Fase 1: Cimientos y Backend (1-2 Semanas)**

* **Tareas:**  
  * Diseño final del modelo de datos y creación del esquema en PostgreSQL.  
  * Configuración del proyecto FastAPI.  
  * Desarrollo de endpoints para Menú, Pedidos, Autenticación y Gastos.  
  * Configuración de WebSockets.

### **Fase 2: Módulo de Caja (POS) (2-3 Semanas)**

* **Tareas:**  
  * **Diseño de la UI/UX en Vue.js y Tailwind CSS, aplicando la identidad de marca (ver sección 4.1).**  
  * Listado de productos y funcionalidad para añadir al pedido, **organizado por las categorías del menú (Pozoles, Flautas, Tacos, etc.).**  
  * Implementación de campo para añadir modificaciones de texto.  
  * Integración para registrar pagos y enviar el pedido finalizado.

### **Fase 3: Módulos de Visualización (KDS y Clientes) (2 Semanas)**

* **Tareas:**  
  * **KDS (Cocina):**  
    * Desarrollo de la vista de "tarjetas" de pedidos, consistente con la identidad de marca.  
    * Conexión vía WebSockets.  
    * Interfaz en tablet para actualizar estado de pedidos a "Listo" y a "Entregado".  
  * **Pantalla de Clientes:**  
    * Desarrollo de la vista que muestra pedidos listos, utilizando los colores de la marca para una clara identificación.  
    * Conexión vía WebSockets.

### **Fase 4: Módulo de Administración y Reportes (1-2 Semanas)**

* **Tareas:**  
  * Creación de una interfaz de administración protegida.  
  * Formularios para gestionar el menú.  
  * Formularios para registrar, ver y editar gastos.  
  * Creación de reportes de ventas detallados (diario, semanal, mensual).

### **Fase 5: Pruebas, Despliegue y Capacitación (1-2 Semanas)**

* **Tareas:**  
  * Pruebas integrales del flujo completo.  
  * Corrección de errores.  
  * Configuración del servidor y despliegue.  
  * Capacitación al personal.  
  * Acompañamiento en el lanzamiento.

## **7\. Próximos Pasos**

Con este plan de desarrollo actualizado y validado, el siguiente paso es comenzar con la **Fase 1: Cimientos y Backend**. El equipo de desarrollo puede proceder con el diseño final de la base de datos y la configuración inicial del proyecto FastAPI, mientras que el equipo de frontend puede comenzar a crear los primeros *mockups* basados en la identidad visual definida.

## **Guía Rápida (Backend) — Quickstart**

1. Variables de entorno
   - Crea un archivo `.env` en `backend/` con:
     - `DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST/DBNAME`
     - `SECRET_KEY=un_valor_secreto_aleatorio`
2. Instalar dependencias
   - `cd backend`
   - `pip install -r requirements.txt`
3. Ejecutar API
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
4. Probar salud y DB
   - `GET /` → mensaje de bienvenida
   - `GET /health/database` → verifica conexión Neon
5. Autenticación y pruebas
   - Crea un `usuario` admin via `POST /usuarios` (requiere token de un admin existente)
   - Inicia sesión `POST /auth/login` o `/auth/login-simple`
6. Hash de contraseñas
   - Se usa Argon2id por defecto; compatible con bcrypt existente
7. Gastos
   - Endpoints: `POST/GET/PUT/DELETE /gastos` (roles: administrador, compras)