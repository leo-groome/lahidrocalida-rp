# La Hidrocalida Print Service v2.0

Servicio de impresión térmica POS escrito en Go.  
**System Designed by Valta Operative**

## Requisitos

- Windows 10/11
- Impresora Easytime SP-POS891ED (o cualquier impresora térmica 80mm) instalada via USB con driver genérico Windows

## Instalación rápida

1. Copiar `go-print-service.exe` y `config.yaml` al PC de punto de venta
2. Editar `config.yaml` con el nombre exacto de la impresora:
   - Ir a **Inicio → Dispositivos e impresoras**
   - Copiar el nombre exacto de la impresora térmica al campo `printer.name`
3. Abrir **CMD como Administrador** y ejecutar:

```batch
go-print-service.exe install
net start LaHidrocalidaPrint
```

4. Verificar: `sc query LaHidrocalidaPrint` → debe decir `STATE: 4 RUNNING`

## Comandos del servicio

```batch
go-print-service.exe install    # Instalar como Windows Service
go-print-service.exe start      # Iniciar
go-print-service.exe stop       # Detener
go-print-service.exe restart    # Reiniciar
go-print-service.exe uninstall  # Desinstalar
```

## Probar sin instalar (modo consola)

```batch
# En CMD normal:
go-print-service.exe

# En otra ventana:
curl http://localhost:3001/health
curl -X POST http://localhost:3001/test
```

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del servicio |
| POST | `/print` | Imprimir ticket (mismo JSON que el Python service) |
| POST | `/test` | Ticket de prueba físico |
| GET | `/printers` | Listar impresoras instaladas en Windows |

## Compilar desde Linux

```bash
cd apps/go-print-service
make build-windows   # genera go-print-service.exe
```

## Logs

El archivo `print-service.log` se crea en el mismo directorio que el `.exe`.
