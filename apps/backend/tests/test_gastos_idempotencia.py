"""Replays de gastos sin duplicados ni recreación tras borrado."""

from uuid import uuid4

from app.models import Gasto


def payload():
    return {
        "client_request_id": str(uuid4()),
        "tipo_gasto": "directo",
        "metodo_pago": "efectivo",
        "total_manual": 100,
        "detalles": [],
        "fecha_gasto": "2026-10-13T12:00:00-06:00",
    }


def test_reintento_devuelve_mismo_gasto(como_rol, seed, db_session):
    client = como_rol("compras", id=seed["usuario"].id)
    data = payload()
    first = client.post("/gastos/", json=data)
    assert first.status_code == 201, first.text
    second = client.post("/gastos/", json=data)
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert db_session.query(Gasto).count() == 1
    data["total_manual"] = 200
    assert client.post("/gastos/", json=data).status_code == 409


def test_replay_no_recrea_gasto_borrado(como_rol, seed, tmp_path, monkeypatch):
    from app.main import app
    from app.services.storage import LocalStorage, get_storage

    app.dependency_overrides[get_storage] = lambda: LocalStorage(str(tmp_path))
    client = como_rol("compras", id=seed["usuario"].id)
    data = payload()
    first = client.post("/gastos/", json=data)
    assert first.status_code == 201
    assert client.delete(f"/gastos/{first.json()['id']}").status_code == 204
    assert client.post("/gastos/", json=data).status_code == 410


def test_replay_otro_actor_no_recupera_resultado(como_rol, seed):
    data = payload()
    assert como_rol("compras", id=seed["usuario"].id).post("/gastos/", json=data).status_code == 201
    assert como_rol("compras", id=999).post("/gastos/", json=data).status_code == 403


def test_peticion_invalida_no_reserva_uuid(como_rol, seed):
    client = como_rol("compras", id=seed["usuario"].id)
    data = payload()
    data["total_manual"] = 0
    assert client.post("/gastos/", json=data).status_code == 400
    data["total_manual"] = 100
    assert client.post("/gastos/", json=data).status_code == 201


def test_idempotencia_nomina_y_gasto_con_lineas(como_rol, seed, db_session):
    from app.models import Articulo, CategoriaArticulo

    categoria = CategoriaArticulo(nombre="Prueba")
    db_session.add(categoria)
    db_session.flush()
    articulo = Articulo(nombre="Insumo", unidad="kg", costo_estandar=30, categoria_id=categoria.id)
    db_session.add(articulo)
    db_session.commit()
    client = como_rol("compras", id=seed["usuario"].id)
    nomina = {
        "client_request_id": str(uuid4()),
        "tipo_gasto": "nomina",
        "metodo_pago": "efectivo",
        "nomina_detalles": [{"usuario_id": seed["usuario"].id, "monto": 500}],
    }
    compra = {
        "client_request_id": str(uuid4()),
        "tipo_gasto": "directo",
        "metodo_pago": "tarjeta",
        "detalles": [{"articulo_id": articulo.id, "cantidad": 2, "precio_unitario": 30}],
    }
    for data, total in [(nomina, 500), (compra, 60)]:
        first = client.post("/gastos/", json=data)
        assert first.status_code == 201, first.text
        replay = client.post("/gastos/", json=data)
        assert replay.status_code == 201 and replay.json()["id"] == first.json()["id"]
        assert float(replay.json()["total"]) == total
    assert db_session.query(Gasto).count() == 2


def test_gasto_con_turno_de_caja_se_vincula_y_turno_ajeno_es_rechazado(como_rol, seed):
    client = como_rol("cajero", id=seed["usuario"].id)
    conteo = {"denominaciones": [{"denominacion": 100, "cantidad": 5}]}
    turno_id = client.post("/turnos/iniciar", json={"conteo_inicial": conteo}).json()["id"]

    ok = client.post("/gastos/", json={**payload(), "turno_id": turno_id})
    assert ok.status_code == 201, ok.text
    assert ok.json()["turno_id"] == turno_id

    malo = client.post("/gastos/", json={**payload(), "turno_id": 999999})
    assert malo.status_code == 400
