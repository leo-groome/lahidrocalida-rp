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

**Imports:** Standard library first, third‑party second, local imports grouped by module.

**Function Signatures:** Use type hints and docstrings for public functions.

**Error Handling:** Use try/except with specific exceptions; return user‑friendly error messages.

**Naming Conventions:**
- Functions: `snake_case`
- Classes: `PascalCase`
- Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

**Database Queries:** Use SQLAlchemy ORM methods; for complex queries use `func` and proper joins.

### TypeScript/Vue (Frontend)

**File Structure:** Follow Vue 3 `<script setup>` composition API.

**Component Structure:** Use reactive state (`ref`, `reactive`), computed properties, and lifecycle hooks.

**Type Definitions:** Use TypeScript interfaces with union types for enums; mark nullable fields optional.

**API Calls:** Centralized Axios client with request/response interceptors.

**State Management:** Pinia stores with Composition API syntax.

**Naming Conventions:**
- Components: `PascalCase`
- Files: `PascalCase` for components, `kebab‑case` for others
- Variables/Functions: `camelCase`
- Types: `PascalCase`
- Constants: `camelCase` or `UPPER_SNAKE_CASE`

**Error Handling:** Wrap async operations in try/catch; display user‑friendly error messages.

## 🔧 Development Workflow

### Adding New Features
**Backend:** Update schemas → add router endpoint → include auth → implement DB operations → test.
**Frontend:** Define types → create component → add reactive state → implement error handling → add to router.

### Database Changes
**Modifying models:** Update SQLAlchemy model and Pydantic schemas; test endpoints.
**New entities:** Create model, schemas, router, frontend types, and test CRUD cycle.

### Code Quality Checks
1. Run backend server and test endpoints manually.
2. Build frontend to verify TypeScript compilation.
3. Test critical user flows.
4. Verify database health endpoint.

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

- No automated test framework configured.
- Manual testing via API endpoints and UI.
- Utility test scripts in `print_service/` (run individually).
- Recommended future setup: pytest (backend), Vitest/Playwright (frontend).

## 🚨 Critical Patterns to Follow

1. **Always use virtual environment** for Python development.
2. **Always use pnpm** instead of npm for frontend dependencies.
3. **Validate user permissions** on all protected endpoints.
4. **Use proper TypeScript typing** throughout the frontend.
5. **Handle errors gracefully** with user‑friendly messages.
6. **Follow existing naming conventions** for consistency.
7. **Test WebSocket functionality** when modifying real‑time features.
8. **Document API changes** in the FastAPI automatic documentation.
9. **Implement tip modal flow correctly**: Show tip modal only after selecting card/transfer payment method with quick percentage buttons (10%/15%/20%) and specific amount field. For cash payments, display cash received field before optional tip.

## 📚 Key Files Reference

**Backend:**
- `app/main.py` – FastAPI app setup and CORS
- `app/models.py` – SQLAlchemy database models
- `app/schemas.py` – Pydantic request/response models
- `app/routers/` – API endpoint definitions

**Frontend:**
- `src/types.ts` – TypeScript type definitions
- `src/api/client.ts` – Axios HTTP client configuration
- `src/stores/` – Pinia state management stores
- `src/views/` – Main application views/pages

---

*No Cursor rules (`/.cursor/rules/`) or Copilot instructions (`/.github/copilot‑instructions.md`) are present in this repository.*
