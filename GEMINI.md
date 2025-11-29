# GEMINI.md - AI Agent Project Context

This document provides essential context for AI agents interacting with the "La Hidrocálida" project codebase.

## 📋 Project Overview

**La Hidrocálida** is a comprehensive Point-of-Sale (POS) and management system designed for a "pozolería" (a specific type of Mexican restaurant). It features a post-payment workflow, real-time updates via WebSockets, and dedicated interfaces for waiters, kitchen staff, and cashiers.

The system is fully functional, including an admin panel, an optimized Kitchen Display System (KDS), real-time order tracking, and physical ticket printing.

### Architecture

The project is a monorepo with three main components:

1.  **Backend (Python/FastAPI):** A RESTful API that also handles WebSocket connections for real-time communication.
2.  **Frontend (Vue.js/TypeScript):** A Single Page Application (SPA) providing the user interfaces for all roles (Waiter, Cashier, Kitchen, Admin).
3.  **Print Service (Python):** A standalone local server that receives requests from the frontend to print tickets on thermal printers.

### Tech Stack

*   **Backend:** FastAPI, SQLAlchemy, PostgreSQL (Neon Cloud), Pydantic, python-jose (JWT), WebSockets.
*   **Frontend:** Vue 3, TypeScript, Vite, Pinia (state management), Vue Router, Tailwind CSS, Axios.
*   **Package Management:** `pnpm` for the frontend, `pip` with `requirements.txt` for the backend.

---

## 🚀 Building and Running

**❗️ IMPORTANT:**
*   **Backend:** Always use the `.venv/` Python virtual environment.
*   **Frontend:** Always use `pnpm` for package management.

### 1. Backend Server

```bash
# Navigate to the backend directory
cd backend

# Activate the virtual environment (create it if it doesn't exist)
source .venv/bin/activate  # On Linux/macOS
# .venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*   The API will be available at `http://localhost:8000`.
*   API documentation (Swagger UI) is at `http://localhost:8000/docs`.

### 2. Frontend Application

```bash
# Navigate to the frontend directory
cd frontend/pos-system

# Copy the environment file template
cp .env.example .env

# Edit the .env file to set VITE_API_URL to your backend's IP/URL
# Example: VITE_API_URL=http://localhost:8000

# Install dependencies
pnpm install

# Run the development server
pnpm run dev
```
*   The frontend will be available at `http://localhost:5173` (or another port if 5173 is busy).

### 3. Print Service

```bash
# Navigate to the print service directory
cd print_service

# Install dependencies (if not already done via install scripts)
pip install -r requirements.txt

# Run the print server
python print_server.py --port 3001
```
*   This service must be running on the cashier's machine for physical ticket printing to work.

---

## 🔧 Development Conventions

### Key Business Rules

*   **Order Numbering:** Sequentially generated per day and per branch (e.g., 001, 002), resetting daily.
*   **Order Flow (Post-Payment):** `pendiente` → `preparando` → `listo` → `entregado` → `cuenta_solicitada` → `pagado`.
*   **Role Permissions:** Actions are strictly controlled by user roles (`mesero`, `cajero`, 'cocina', `administrador`).
*   **Drinks & Desserts:** Drinks are automatically marked as `entregado` upon order creation and do not appear on the KDS to keep the kitchen focused on food.
*   **Sound Notifications:** The system provides audible alerts exclusively in the kitchen views (`/kds-view`, `/kds-manager`).
    *   `notification_in.mp3`: Plays for new orders or when items are added to an existing order.
    *   `notification_out.mp3`: Plays when an item or an entire order is marked as `listo`. This sound is throttled to prevent multiple plays when many items are marked simultaneously.

### Code Patterns

**Backend (FastAPI):**
*   Use dependency injection for database sessions and user authentication.
*   Validate roles for protected endpoints.
*   Business logic is primarily located in the `routers` directory.

```python
# Example from app/routers/pedidos.py
from app.db.session import get_db
from app.auth import get_current_active_user

@router.get("/")
def get_all_pedidos(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_active_user)):
    if current_user.rol not in ["administrador", "cajero"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    # ... implementation
```

**Frontend (Vue.js):**
*   State is managed centrally using Pinia stores (`auth.ts`, `pedidos.ts`).
*   API calls are encapsulated in an Axios client (`api/client.ts`).
*   Route guards in `router/index.ts` protect views based on authentication status and user roles.

---

## 📂 Key Files

*   `AGENTS.md`: The primary source of truth for AI agents, containing deep project context.
*   `backend/app/main.py`: FastAPI application entry point.
*   `backend/app/models.py`: SQLAlchemy database models.
*   `backend/app/routers/pedidos.py`: Core business logic for orders.
*   `backend/app/websocket_manager.py`: Server-side WebSocket connection management.
*   `frontend/pos-system/src/main.ts`: Vue application entry point.
*   `frontend/pos-system/src/stores/`: Pinia stores for global state.
*   `frontend/pos-system/src/views/`: Main application views for each role.
*   `frontend/pos-system/src/router/index.ts`: Frontend routes and authorization guards.
*   `print_service/print_server.py`: The standalone thermal printer server.
*   `pnpm-lock.yaml`: Defines exact frontend dependencies. Use `pnpm`.
*   `backend/requirements.txt`: Defines backend dependencies. Use `pip`.