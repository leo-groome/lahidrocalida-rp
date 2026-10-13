"""Fotos de tickets de gastos + registro rápido de gasto (proveedor opcional)."""

import pytest

from app.main import app
from app.models import Gasto, Sucursal
from app.services.storage import LocalStorage, get_storage

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 32
HEIC = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 32


@pytest.fixture(autouse=True)
def storage_tmp(tmp_path):
    app.dependency_overrides[get_storage] = lambda: LocalStorage(str(tmp_path))
    yield tmp_path
    app.dependency_overrides.pop(get_storage, None)


def _gasto(db_session, sucursal_id) -> Gasto:
    gasto = Gasto(
        tipo_gasto="directo",
        metodo_pago="efectivo",
        subtotal=100,
        total=100,
        sucursal_id=sucursal_id,
    )
    db_session.add(gasto)
    db_session.commit()
    db_session.refresh(gasto)
    return gasto


def _subir(client, gasto_id, contenido, nombre="ticket.jpg", tipo="image/jpeg"):
    return client.post(f"/gastos/{gasto_id}/adjuntos", files={"archivo": (nombre, contenido, tipo)})


@pytest.mark.parametrize(
    "contenido,tipo",
    [(JPEG, "image/jpeg"), (PNG, "image/png"), (WEBP, "image/webp"), (HEIC, "image/heic")],
)
def test_sube_y_descarga_imagen_valida(como_rol, seed, db_session, contenido, tipo):
    gasto = _gasto(db_session, seed["sucursal"].id)
    client = como_rol("compras")

    r = _subir(client, gasto.id, contenido)
    assert r.status_code == 201, r.text
    adj = r.json()
    assert adj["content_type"] == tipo
    assert adj["size"] == len(contenido)

    r = client.get(f"/gastos/{gasto.id}/adjuntos/{adj['id']}/archivo")
    assert r.status_code == 200
    assert r.content == contenido
    assert r.headers["content-type"] == tipo
    assert r.headers["x-content-type-options"] == "nosniff"

    assert client.get(f"/gastos/{gasto.id}").json()["num_adjuntos"] == 1
    assert len(client.get(f"/gastos/{gasto.id}/adjuntos").json()) == 1


def test_rechaza_archivo_que_no_es_imagen_aunque_diga_jpg(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    r = _subir(
        como_rol("compras"), gasto.id, b"<script>alert(1)</script>", "ticket.jpg", "image/jpeg"
    )
    assert r.status_code == 415


def test_rechaza_archivo_vacio(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    assert _subir(como_rol("compras"), gasto.id, b"").status_code == 400


def test_rechaza_archivo_demasiado_grande(como_rol, seed, db_session, monkeypatch):
    monkeypatch.setattr("app.routers.gasto_adjuntos.MAX_ADJUNTO_BYTES", 1024)
    gasto = _gasto(db_session, seed["sucursal"].id)
    r = _subir(como_rol("compras"), gasto.id, JPEG + b"\x00" * 2048)
    assert r.status_code == 413


def test_maximo_de_fotos_por_gasto(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    client = como_rol("compras")
    for _ in range(5):
        assert _subir(client, gasto.id, JPEG).status_code == 201
    assert _subir(client, gasto.id, JPEG).status_code == 400


def test_otra_sucursal_no_ve_ni_sube_ni_borra(como_rol, seed, db_session):
    otra = Sucursal(nombre="Norte")
    db_session.add(otra)
    db_session.commit()
    gasto = _gasto(db_session, seed["sucursal"].id)
    adj = _subir(como_rol("compras"), gasto.id, JPEG).json()

    # Ni siquiera un administrador de otra sucursal accede.
    intruso = como_rol("administrador", sucursal_id=otra.id)
    assert _subir(intruso, gasto.id, JPEG).status_code == 404
    assert intruso.get(f"/gastos/{gasto.id}/adjuntos").status_code == 404
    assert intruso.get(f"/gastos/{gasto.id}/adjuntos/{adj['id']}/archivo").status_code == 404
    assert intruso.delete(f"/gastos/{gasto.id}/adjuntos/{adj['id']}").status_code == 404


def test_mesero_no_puede_subir(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    assert _subir(como_rol("mesero"), gasto.id, JPEG).status_code == 403


def test_borrar_adjunto_elimina_registro_y_archivo(como_rol, seed, db_session, storage_tmp):
    gasto = _gasto(db_session, seed["sucursal"].id)
    client = como_rol("compras")
    adj = _subir(client, gasto.id, JPEG).json()
    assert len(list(storage_tmp.rglob("*.jpg"))) == 1

    assert client.delete(f"/gastos/{gasto.id}/adjuntos/{adj['id']}").status_code == 204
    assert list(storage_tmp.rglob("*.jpg")) == []
    assert client.get(f"/gastos/{gasto.id}/adjuntos").json() == []


def test_adjunto_con_gasto_id_equivocado_da_404(como_rol, seed, db_session):
    g1 = _gasto(db_session, seed["sucursal"].id)
    g2 = _gasto(db_session, seed["sucursal"].id)
    client = como_rol("compras")
    adj = _subir(client, g1.id, JPEG).json()
    assert client.get(f"/gastos/{g2.id}/adjuntos/{adj['id']}/archivo").status_code == 404


# ---- Registro rápido: proveedor opcional ----


def test_gasto_rapido_sin_proveedor_con_total_manual(como_rol, seed):
    r = como_rol("compras").post(
        "/gastos/",
        json={"tipo_gasto": "directo", "metodo_pago": "efectivo", "total_manual": 150.5},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["proveedor"] is None
    assert float(body["total"]) == 150.5
    assert body["num_adjuntos"] == 0


def test_gasto_sin_total_ni_articulos_es_invalido(como_rol, seed):
    r = como_rol("compras").post(
        "/gastos/", json={"tipo_gasto": "directo", "metodo_pago": "efectivo"}
    )
    assert r.status_code == 400


def test_gasto_total_manual_cero_sin_articulos_es_invalido(como_rol, seed):
    r = como_rol("compras").post(
        "/gastos/",
        json={"tipo_gasto": "directo", "metodo_pago": "efectivo", "total_manual": 0},
    )
    assert r.status_code == 400


def test_storage_local_prohibido_en_produccion(monkeypatch):
    from app.services import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_storage", None)
    monkeypatch.setattr(storage_mod.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(storage_mod.settings, "STORAGE_BACKEND", "local")
    with pytest.raises(RuntimeError, match="producción"):
        storage_mod.get_storage()


def test_storage_r2_exige_credenciales(monkeypatch):
    from app.services import storage as storage_mod

    monkeypatch.setattr(storage_mod, "_storage", None)
    monkeypatch.setattr(storage_mod.settings, "STORAGE_BACKEND", "r2")
    monkeypatch.setattr(storage_mod.settings, "R2_BUCKET", None)
    with pytest.raises(RuntimeError, match="R2_BUCKET"):
        storage_mod.get_storage()


def test_cajero_de_otra_sucursal_no_toca_gasto_ajeno(como_rol, seed, db_session):
    otra = Sucursal(nombre="Sur")
    db_session.add(otra)
    db_session.commit()
    gasto = _gasto(db_session, seed["sucursal"].id)
    intruso = como_rol("cajero", sucursal_id=otra.id)

    assert intruso.get(f"/gastos/{gasto.id}").status_code == 404
    assert intruso.delete(f"/gastos/{gasto.id}").status_code == 404
    assert db_session.get(Gasto, gasto.id) is not None


def test_borrar_gasto_elimina_sus_fotos_del_storage(como_rol, seed, db_session, storage_tmp):
    gasto = _gasto(db_session, seed["sucursal"].id)
    client = como_rol("compras")
    _subir(client, gasto.id, JPEG)
    assert len(list(storage_tmp.rglob("*.jpg"))) == 1

    assert client.delete(f"/gastos/{gasto.id}").status_code == 204
    assert list(storage_tmp.rglob("*.jpg")) == []


def test_body_gigante_se_rechaza_antes_de_parsear(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    r = _subir(como_rol("compras"), gasto.id, JPEG + b"\x00" * (10 * 1024 * 1024))
    assert r.status_code == 413
