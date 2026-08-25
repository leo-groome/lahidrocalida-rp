"""GET /ws/stats expone el conteo de sesiones activas: solo administrador.

Antes de la tarea 1.7b el endpoint no tenía ningún chequeo de auth — cualquiera
con acceso de red al backend podía enumerar conexiones por sucursal y rol.
"""

from app.auth import get_current_active_user
from app.main import app


def test_ws_stats_sin_auth_rechaza(client):
    """Sin token no hay estadísticas: 401 de get_current_user."""
    # El fixture `client` inyecta un usuario; quitarlo ejercita el path real
    # de OAuth2PasswordBearer (sin Authorization header).
    original = app.dependency_overrides.pop(get_current_active_user)
    try:
        response = client.get("/ws/stats")
    finally:
        app.dependency_overrides[get_current_active_user] = original

    assert response.status_code in (401, 403)


def test_ws_stats_rol_no_admin_rechaza(como_rol):
    """Un mesero autenticado tampoco puede ver el mapa de conexiones."""
    response = como_rol("mesero").get("/ws/stats")

    assert response.status_code == 403


def test_ws_stats_admin_ok(admin_client):
    response = admin_client.get("/ws/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert "connections" in body
