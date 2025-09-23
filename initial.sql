-- ==========================================
-- CREAR TABLAS EN ESPAÑOL - VERSIÓN SIMPLE
-- ==========================================

-- 1. SUCURSALES (branches)
CREATE TABLE sucursales (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    direccion TEXT
);

-- 2. USUARIOS/EMPLEADOS (users) 
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('cajero', 'cocina', 'administrador', 'compras')),
    pin VARCHAR(6) NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    sucursal_id INTEGER REFERENCES sucursales(id)
);

-- 3. PLATILLOS DEL MENÚ (products)
CREATE TABLE platillos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(8,2) NOT NULL CHECK (precio >= 0),
    categoria VARCHAR(50) NOT NULL,
    estado VARCHAR(20) DEFAULT 'disponible' CHECK (estado IN ('disponible', 'no_disponible'))
);

-- 4. PEDIDOS (orders)
CREATE TABLE pedidos (
    id SERIAL PRIMARY KEY,
    numero_display VARCHAR(10) NOT NULL UNIQUE,  -- ⚠️ AGREGUÉ UNIQUE
    nombre_cliente VARCHAR(100),
    total DECIMAL(8,2) NOT NULL CHECK (total >= 0),
    estado VARCHAR(20) DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'preparando', 'listo', 'completado')),
    metodo_pago VARCHAR(20) CHECK (metodo_pago IN ('efectivo', 'tarjeta', 'transferencia')),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sucursal_id INTEGER REFERENCES sucursales(id),
    usuario_id INTEGER REFERENCES usuarios(id)
);

-- 5. ARTÍCULOS DEL PEDIDO (order_items)
CREATE TABLE articulos_pedido (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    platillo_id INTEGER NOT NULL REFERENCES platillos(id),  -- ⚠️ CAMBIÉ NOMBRE
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_cobrado DECIMAL(8,2) NOT NULL CHECK (precio_cobrado >= 0),
    modificaciones TEXT
);

-- 6. GASTOS (expenses)
CREATE TABLE gastos (
    id SERIAL PRIMARY KEY,
    descripcion VARCHAR(255) NOT NULL,
    monto DECIMAL(8,2) NOT NULL CHECK (monto >= 0),
    categoria VARCHAR(50) NOT NULL,
    fecha_gasto TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sucursal_id INTEGER REFERENCES sucursales(id)
);

-- ==========================================
-- ÍNDICES BÁSICOS (Solo los necesarios)
-- ==========================================

-- Índices para búsquedas frecuentes de pedidos
CREATE INDEX idx_pedidos_estado ON pedidos(estado);
CREATE INDEX idx_pedidos_fecha ON pedidos(fecha_creacion);
CREATE INDEX idx_pedidos_numero ON pedidos(numero_display);  -- ⚠️ AGREGUÉ ESTE

-- Índice para artículos de pedido (JOIN frecuente)
CREATE INDEX idx_articulos_pedido_id ON articulos_pedido(pedido_id);

-- Índice para platillos por categoría
CREATE INDEX idx_platillos_categoria ON platillos(categoria);