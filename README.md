# La Hidrocálida POS

Sistema de punto de venta para pozolería. Flujo mesero → cocina → caja, en tiempo real, con turnos
de caja, gastos, propinas e impresión térmica.

En producción: https://lahidrocalida.vercel.app

## Documentación

- **[docs/ESTADO_ACTUAL.md](docs/ESTADO_ACTUAL.md)** — cómo funciona el sistema hoy: arquitectura,
  modelo de datos, endpoints, roles, flujo operativo y deuda técnica conocida.
- **[docs/PLAN_V2.md](docs/PLAN_V2.md)** — el plan de la siguiente versión: inventario,
  aprobaciones con PIN de admin, métricas de cocina y propinas, IVA, sesiones por jornada.
- **[docs/SPRINTS.md](docs/SPRINTS.md)** — tablero de avance: qué sprint está en curso, qué tareas
  faltan, qué se decidió por el camino. Empieza aquí si vas a trabajar en el plan v2.
- **[AGENTS.md](AGENTS.md)** — convenciones de código y flujo de contribución.

## Levantar el proyecto

Requisitos: Python 3.12, Node 20+, `uv`, `pnpm`, y una `DATABASE_URL` de PostgreSQL.

### Backend

```bash
cd backend
cp .env.example .env          # editar DATABASE_URL y SECRET_KEY
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Docs de la API en http://localhost:8000/docs · health en `/health`.

> El esquema hoy se completa con `Base.metadata.create_all()` al arrancar; las migraciones de
> Alembic por sí solas **no** reconstruyen una base vacía. Se arregla en el Bloque 0 del plan v2.

### Frontend

```bash
cd frontend/pos-system
cp .env.example .env          # editar VITE_API_URL
pnpm install
pnpm dev                      # http://localhost:5173
```

### Servicio de impresión (opcional, solo Windows)

```batch
cd print_service
install.bat
start_service.bat             # escucha en localhost:3001
```

## Variables de entorno

**`backend/.env`**

```env
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
SECRET_KEY=<secreto-aleatorio>
ACCESS_TOKEN_EXPIRE_MINUTES=1440
TIMEZONE=America/Mexico_City
```

**`frontend/pos-system/.env`**

```env
VITE_API_URL=http://localhost:8000
```

Nunca commitear `.env`. Los secretos van solo por variables de entorno.

## Tests

```bash
cd backend && uv run pytest
```

Hoy la cobertura es casi nula (un solo archivo en `backend/tests/`). El plan v2 define el mínimo
por bloque.

## Referencia rápida

**Usuarios de desarrollo** (PIN `1111`):

| ID | Rol | Ruta |
|---|---|---|
| 3 | administrador | `/admin-login` |
| 6 | cocina | `/login` |
| 7 | mesero | `/login` |

**Numeración de mesas:** piso 1 → 11-15 · piso 2 → 21-25 · piso 3 → 31-35

**Colores corporativos:** `#00126D` (azul) · `#FDB700` (amarillo)

**Puertos:** backend `8000` · frontend `5173` · print service `3001`

## Deploy

Frontend en Vercel (push a `main`). Backend en Railway vía Docker. DB en Neon.
