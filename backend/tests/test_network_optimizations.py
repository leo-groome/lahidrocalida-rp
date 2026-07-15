"""Tests de las optimizaciones de network transfer (Neon):
eager loading en /pedidos, caché de catálogos y proyecciones de columnas."""


class TestListPedidos:
    def test_kds_sin_n_mas_uno(self, client, query_counter):
        """Path KDS público (sin auth): 20 pedidos x 3 artículos deben
        resolverse en <=4 queries, no 1+3N."""
        query_counter["n"] = 0
        r = client.get("/pedidos")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 20
        # Contrato intacto: artículos con platillo anidado y nombre del mesero
        assert data[0]["articulos_pedido"][0]["platillo"]["nombre"].startswith("P")
        assert data[0]["usuario_nombre"] == "Leo"
        assert query_counter["n"] <= 4, f"N+1 detectado: {query_counter['n']} queries"

    def test_autenticado_sin_n_mas_uno(self, auth_client, query_counter):
        """Path autenticado (sin turno activo cae al filtro por fecha del día):
        también debe usar eager loading."""
        query_counter["n"] = 0
        r = auth_client.get("/pedidos")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 20
        assert data[0]["usuario_nombre"] == "Leo"
        # 1 query extra vs KDS: el lookup del turno activo
        assert query_counter["n"] <= 5, f"N+1 detectado: {query_counter['n']} queries"

    def test_estado_invalido_da_400(self, client):
        r = client.get("/pedidos?estado=invalido")
        assert r.status_code == 400


class TestCachePlatillos:
    def test_segunda_llamada_no_toca_db(self, client, query_counter):
        client.get("/platillos")
        query_counter["n"] = 0
        r = client.get("/platillos")
        assert r.status_code == 200
        assert len(r.json()) == 5
        assert query_counter["n"] == 0, "la 2a llamada debió salir de caché"

    def test_crear_platillo_invalida_cache(self, admin_client):
        assert len(admin_client.get("/platillos").json()) == 5
        r = admin_client.post(
            "/platillos/",
            json={"nombre": "Nuevo", "precio": 50, "categoria": "c", "estado": "disponible"},
        )
        assert r.status_code == 201
        assert len(admin_client.get("/platillos").json()) == 6


class TestProyecciones:
    def test_tickets_del_dia_paginado(self, admin_client):
        r = admin_client.get("/reportes/dia/tickets?limit=5&offset=0")
        assert r.status_code == 200
        assert len(r.json()) <= 5

    def test_tickets_limit_excesivo_da_422(self, admin_client):
        r = admin_client.get("/reportes/dia/tickets?limit=9999")
        assert r.status_code == 422

    def test_propinas_detalle_una_query(self, admin_client, query_counter, db_session, seed):
        from app.models import Pedido

        db_session.query(Pedido).update({"estado": "pagado"})
        db_session.commit()

        query_counter["n"] = 0
        r = admin_client.get("/propinas/detalle")
        assert r.status_code == 200
        body = r.json()
        assert body["total_pedidos"] == 20
        assert body["detalle"][0]["mesero_nombre"] == "Leo"
        assert query_counter["n"] <= 2, f"N+1 detectado: {query_counter['n']} queries"
