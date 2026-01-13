# AGENTS.md - Development Guidelines for AI Agents

## 🚀 Build, Lint & Test Commands

### Backend (FastAPI/Python)

**Environment Setup:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

**Development Server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Database Health Check:**
```bash
curl http://localhost:8000/health/database
```

**API Documentation:**
- Auto-generated docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

**Run Single Test File:**
```bash
# No automated test framework configured
# Run individual test files manually:
python print_service/test_escpos_format.py
python print_service/test_connection.py
python print_service/test_ticket.py
```

### Frontend (Vue.js/TypeScript)

**Environment Setup:**
```bash
cd frontend/pos-system
pnpm install  # Always use pnpm, never npm
cp .env.example .env
# Edit .env with correct VITE_API_URL
```

**Development Server:**
```bash
pnpm run dev  # Port 5173
```

**Build Commands:**
```bash
pnpm run build              # Production build
pnpm run build:analyze      # Bundle analysis with visualizer
pnpm run bundle-size        # Show bundle sizes
pnpm run preview           # Preview production build
```

**Type Checking:**
```bash
# No dedicated type check script
# Types checked during build
pnpm run build  # Includes TypeScript compilation
```

## 📝 Code Style Guidelines

### Python (Backend)

**Imports:**
```python
# Standard library imports first
from datetime import datetime, date
from typing import List, Optional
import pytz

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

# Local imports (grouped by module)
from app.db.session import get_db
from app.models import Pedido, ArticuloPedido
from app.auth import get_current_active_user
```

**Function Signatures:**
```python
def generate_numero_display(db: Session, sucursal_id: int) -> str:
    """
    Generate sequential display number per day and branch.
    Format: 001, 002, 003, etc.
    Automatically resets each day in local timezone.
    """
    # Implementation
```

**Error Handling:**
```python
try:
    # Database operations
    result = db.execute(text("SELECT 5 as test"))
    test_value = result.fetchone()

    return {
        "status": "success",
        "result": test_value[0] if test_value else None
    }
except Exception as e:
    return {
        "status": "error",
        "message": f"Database error: {str(e)}"
    }
```

**Naming Conventions:**
- Functions: `snake_case` (e.g., `get_current_active_user`)
- Classes: `PascalCase` (e.g., `PedidoCreate`)
- Variables: `snake_case` (e.g., `current_user`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `ACCESS_TOKEN_EXPIRE_MINUTES`)

**Database Queries:**
```python
# Use SQLAlchemy ORM methods
pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()

# Complex queries with proper joins
max_number = (
    db.query(func.max(cast(Pedido.numero_display, SAInteger)))
    .filter(
        and_(
            Pedido.sucursal_id == sucursal_id,
            Pedido.fecha_creacion >= start_dt,
            Pedido.fecha_creacion < end_dt,
        )
    )
    .scalar()
)
```

### TypeScript/Vue (Frontend)

**File Structure:**
```
src/
├── api/           # HTTP client and API calls
├── components/    # Reusable Vue components
├── stores/        # Pinia state management
├── views/         # Page-level components
├── router/        # Vue Router configuration
└── types.ts       # TypeScript type definitions
```

**Component Structure:**
```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { PlatilloResponse } from '@/types'

// Reactive state
const platillos = ref<PlatilloResponse[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// Store access
const auth = useAuthStore()
const router = useRouter()

// Computed properties
const filteredPlatillos = computed(() => {
  return platillos.value.filter(p => p.estado === 'disponible')
})

// Lifecycle hooks
onMounted(async () => {
  await loadPlatillos()
})

// Functions
const loadPlatillos = async () => {
  try {
    loading.value = true
    const response = await api.get('/platillos')
    platillos.value = response.data
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Error loading platillos'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <!-- Template content -->
</template>
```

**Type Definitions:**
```typescript
// Use union types for enums
export type Rol = 'mesero' | 'cajero' | 'cocina' | 'administrador'

// Interface naming: PascalCase with descriptive names
export interface PlatilloResponse {
  id: number
  nombre: string
  precio: number
  categoria: string
  estado: 'disponible' | 'no_disponible'
  kds_name?: string
}

// Use optional properties for nullable fields
export interface PedidoResponse {
  id: number
  mesa: string | null
  nombre_cliente: string | null
  total: string | number
  articulos_pedido?: ArticuloPedidoResponse[]
}
```

**API Calls:**
```typescript
// Centralized API client with interceptors
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000,
})

// Request interceptor for auth
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      router.replace({ name: 'login' })
    }
    return Promise.reject(error)
  }
)
```

**State Management (Pinia):**
```typescript
// Store definition
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const userRole = computed(() => user.value?.rol || '')

  // Actions
  const login = async (credentials: LoginCredentials) => {
    try {
      const response = await api.post('/auth/login', credentials)
      token.value = response.data.access_token
      user.value = response.data.user
      localStorage.setItem('token', token.value)
    } catch (error) {
      throw new Error('Login failed')
    }
  }

  const logout = () => {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
  }

  return {
    user,
    token,
    isAuthenticated,
    userRole,
    login,
    logout
  }
})
```

**Naming Conventions:**
- Components: `PascalCase` (e.g., `MeseroView.vue`, `AppHeader.vue`)
- Files: `PascalCase` for components, `kebab-case` for other files
- Variables: `camelCase` (e.g., `platillos`, `isAuthenticated`)
- Functions: `camelCase` (e.g., `loadPlatillos`, `handleSubmit`)
- Types: `PascalCase` (e.g., `PlatilloResponse`, `PedidoCreate`)
- Constants: `camelCase` or `UPPER_SNAKE_CASE` for global constants

**Error Handling:**
```typescript
// Async operations with proper error handling
try {
  const { data } = await api.get<PedidoResponse[]>('/pedidos')
  pedidos.value = data
} catch (e: any) {
  error.value = e?.response?.data?.detail || 'Error genérico'
  console.error('Error loading pedidos:', e)
} finally {
  loading.value = false
}
```

## 🔧 Development Workflow

### Adding New Features

**Backend API:**
1. Create/update Pydantic schemas in `schemas.py`
2. Add route handler in appropriate router file
3. Include proper authentication/authorization
4. Add database operations using SQLAlchemy ORM
5. Test endpoint manually with curl or FastAPI docs

**Frontend Components:**
1. Define TypeScript interfaces in `types.ts`
2. Create Vue component with `<script setup>` syntax
3. Add reactive state with proper typing
4. Implement error handling and loading states
5. Add component to router if it's a new page

### Database Changes

**When modifying models:**
1. Update SQLAlchemy model in `models.py`
2. Update corresponding Pydantic schemas
3. Test with existing endpoints
4. Document changes in migration comments

**When adding new entities:**
1. Create new SQLAlchemy model
2. Add Pydantic schemas for CRUD operations
3. Create router with proper endpoints
4. Update frontend types and API calls
5. Test full CRUD cycle

### Code Quality Checks

**Before committing:**
1. Run backend: `uvicorn app.main:app --reload` and test endpoints
2. Run frontend: `pnpm run build` to check TypeScript compilation
3. Test critical user flows manually
4. Check that database health endpoint works: `GET /health/database`

## 📋 Environment Configuration

**Backend (.env):**
```env
DATABASE_URL=postgresql://user:pass@host:port/db
SECRET_KEY=your-super-secret-jwt-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
TIMEZONE=America/Mexico_City
```

**Frontend (.env):**
```env
VITE_API_URL=http://localhost:8000
```

## 🧪 Testing Strategy

**Current State:**
- No automated test framework configured
- Manual testing via API endpoints and UI
- Some utility test scripts in `print_service/`

**Recommended Testing Approach:**
```bash
# For future automated tests, consider:
# Backend: pytest with fixtures for database
# Frontend: Vitest for unit tests, Playwright for E2E
# API testing: Postman collections or automated API tests
```

## 🚨 Critical Patterns to Follow

1. **Always use virtual environment** for Python development
2. **Always use pnpm** instead of npm for frontend dependencies
3. **Validate user permissions** on all protected endpoints
4. **Use proper TypeScript typing** throughout the frontend
5. **Handle errors gracefully** with user-friendly messages
6. **Follow existing naming conventions** for consistency
7. **Test WebSocket functionality** when modifying real-time features
8. **Document API changes** in the FastAPI automatic documentation

## 📚 Key Files Reference

**Backend:**
- `app/main.py` - FastAPI app setup and CORS
- `app/models.py` - SQLAlchemy database models
- `app/schemas.py` - Pydantic request/response models
- `app/routers/` - API endpoint definitions

**Frontend:**
- `src/types.ts` - TypeScript type definitions
- `src/api/client.ts` - Axios HTTP client configuration
- `src/stores/` - Pinia state management stores
- `src/views/` - Main application views/pages

---

*This document focuses on technical development guidelines for AI agents working on this codebase. For business logic and project context, see the detailed AGENTS.md file in the root directory.*