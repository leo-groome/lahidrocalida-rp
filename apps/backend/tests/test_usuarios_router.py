"""Tests para app/routers/users.py: verificar gate de autorización en GET /usuarios/."""


class TestListUsuarios:
    def test_lista_usuarios_requiere_administrador(self, client):
        """GET /usuarios/ con rol mesero debe devolver 403."""
        r = client.get("/usuarios/")
        assert r.status_code == 403
        assert "administrador" in r.json()["detail"].lower()

    def test_lista_usuarios_con_admin(self, admin_client):
        """GET /usuarios/ con rol administrador devuelve 200 y lista."""
        r = admin_client.get("/usuarios/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
