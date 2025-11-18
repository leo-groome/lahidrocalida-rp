-- Script para agregar todas las variaciones de pozoles con las nuevas proteínas
-- Formato: Pozole [Tamaño] [Color] [Proteína]
-- Precios: Puerco/Surtida (75,95,115) - Pollo/Mixta (85,110,130)
-- KDS: Inf/Med/Gde + Color + Proteína

-- Pozoles Verde con Surtida
INSERT INTO platillos (nombre, descripcion, precio, categoria, kds_name, estado) VALUES
('Pozole Infantil Verde Surtida', 'Delicioso pozole tradicional verde con carne surtida', 75.00, 'Pozole', 'Inf Verde Surtida', 'disponible'),
('Pozole Regular Verde Surtida', 'Delicioso pozole tradicional verde con carne surtida', 95.00, 'Pozole', 'Med Verde Surtida', 'disponible'),
('Pozole Grande Verde Surtida', 'Delicioso pozole tradicional verde con carne surtida', 115.00, 'Pozole', 'Gde Verde Surtida', 'disponible');

-- Pozoles Verde con Mixta
INSERT INTO platillos (nombre, descripcion, precio, categoria, kds_name, estado) VALUES
('Pozole Infantil Verde Mixta', 'Delicioso pozole tradicional verde con carne mixta', 85.00, 'Pozole', 'Inf Verde Mixta', 'disponible'),
('Pozole Regular Verde Mixta', 'Delicioso pozole tradicional verde con carne mixta', 110.00, 'Pozole', 'Med Verde Mixta', 'disponible'),
('Pozole Grande Verde Mixta', 'Delicioso pozole tradicional verde con carne mixta', 130.00, 'Pozole', 'Gde Verde Mixta', 'disponible');

-- Pozoles Blanco con Surtida
INSERT INTO platillos (nombre, descripcion, precio, categoria, kds_name, estado) VALUES
('Pozole Infantil Blanco Surtida', 'Delicioso pozole tradicional blanco con carne surtida', 75.00, 'Pozole', 'Inf Blanco Surtida', 'disponible'),
('Pozole Regular Blanco Surtida', 'Delicioso pozole tradicional blanco con carne surtida', 95.00, 'Pozole', 'Med Blanco Surtida', 'disponible'),
('Pozole Grande Blanco Surtida', 'Delicioso pozole tradicional blanco con carne surtida', 115.00, 'Pozole', 'Gde Blanco Surtida', 'disponible');

-- Pozoles Blanco con Mixta
INSERT INTO platillos (nombre, descripcion, precio, categoria, kds_name, estado) VALUES
('Pozole Infantil Blanco Mixta', 'Delicioso pozole tradicional blanco con carne mixta', 85.00, 'Pozole', 'Inf Blanco Mixta', 'disponible'),
('Pozole Regular Blanco Mixta', 'Delicioso pozole tradicional blanco con carne mixta', 110.00, 'Pozole', 'Med Blanco Mixta', 'disponible'),
('Pozole Grande Blanco Mixta', 'Delicioso pozole tradicional blanco con carne mixta', 130.00, 'Pozole', 'Gde Blanco Mixta', 'disponible');

-- Pozoles Rojo con Surtida
INSERT INTO platillos (nombre, descripcion, precio, categoria, kds_name, estado) VALUES
('Pozole Infantil Rojo Surtida', 'Delicioso pozole tradicional rojo con carne surtida', 75.00, 'Pozole', 'Inf Rojo Surtida', 'disponible'),
('Pozole Regular Rojo Surtida', 'Delicioso pozole tradicional rojo con carne surtida', 95.00, 'Pozole', 'Med Rojo Surtida', 'disponible'),
('Pozole Grande Rojo Surtida', 'Delicioso pozole tradicional rojo con carne surtida', 115.00, 'Pozole', 'Gde Rojo Surtida', 'disponible');

-- Pozoles Rojo con Mixta
INSERT INTO platillos (nombre, descripcion, precio, categoria, kds_name, estado) VALUES
('Pozole Infantil Rojo Mixta', 'Delicioso pozole tradicional rojo con carne mixta', 85.00, 'Pozole', 'Inf Rojo Mixta', 'disponible'),
('Pozole Regular Rojo Mixta', 'Delicioso pozole tradicional rojo con carne mixta', 110.00, 'Pozole', 'Med Rojo Mixta', 'disponible'),
('Pozole Grande Rojo Mixta', 'Delicioso pozole tradicional rojo con carne mixta', 130.00, 'Pozole', 'Gde Rojo Mixta', 'disponible');

-- Verificar que se agregaron correctamente
SELECT nombre, precio, kds_name FROM platillos WHERE categoria = 'Pozole' AND (nombre LIKE '%Surtida%' OR nombre LIKE '%Mixta%') ORDER BY nombre;