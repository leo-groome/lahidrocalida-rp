"""Fotos de tickets de gastos + registro rápido de gasto (proveedor opcional)."""

import asyncio
import io
from uuid import uuid4

import pytest
from PIL import Image
from pillow_heif import from_pillow

from app.main import app
from app.models import Gasto, StorageBorrado, Sucursal
from app.services.storage import LocalStorage, get_storage
from app.services.storage_cleanup import procesar_borrados


def _imagen(formato):
    out = io.BytesIO()
    image = Image.new("RGB", (32, 24), "red")
    if formato == "HEIC":
        from_pillow(image).save(out)
    else:
        image.save(out, format=formato)
    return out.getvalue()


JPEG, PNG, WEBP, HEIC = [_imagen(f) for f in ("JPEG", "PNG", "WEBP", "HEIC")]


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
    client = como_rol("compras", id=seed["usuario"].id)

    r = _subir(client, gasto.id, contenido)
    assert r.status_code == 201, r.text
    adj = r.json()
    assert adj["content_type"] == "image/webp"
    assert adj["size"] > 0

    r = client.get(f"/gastos/{gasto.id}/adjuntos/{adj['id']}/archivo")
    assert r.status_code == 200
    assert Image.open(io.BytesIO(r.content)).format == "WEBP"
    assert r.headers["content-type"] == "image/webp"
    assert r.headers["x-content-type-options"] == "nosniff"

    assert client.get(f"/gastos/{gasto.id}").json()["num_adjuntos"] == 1
    assert len(client.get(f"/gastos/{gasto.id}/adjuntos").json()) == 1


def test_rechaza_archivo_que_no_es_imagen_aunque_diga_jpg(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    r = _subir(
        como_rol("compras", id=seed["usuario"].id),
        gasto.id,
        b"<script>alert(1)</script>",
        "ticket.jpg",
        "image/jpeg",
    )
    assert r.status_code == 415


def test_rechaza_archivo_vacio(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    assert _subir(como_rol("compras", id=seed["usuario"].id), gasto.id, b"").status_code == 400


def test_rechaza_archivo_demasiado_grande(como_rol, seed, db_session, monkeypatch):
    monkeypatch.setattr("app.routers.gasto_adjuntos.MAX_ADJUNTO_BYTES", 1024)
    gasto = _gasto(db_session, seed["sucursal"].id)
    r = _subir(como_rol("compras", id=seed["usuario"].id), gasto.id, JPEG + b"\x00" * 2048)
    assert r.status_code == 413


def test_maximo_de_fotos_por_gasto(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    client = como_rol("compras", id=seed["usuario"].id)
    for _ in range(5):
        assert _subir(client, gasto.id, JPEG).status_code == 201
    assert _subir(client, gasto.id, JPEG).status_code == 400


def test_otra_sucursal_no_ve_ni_sube_ni_borra(como_rol, seed, db_session):
    otra = Sucursal(nombre="Norte")
    db_session.add(otra)
    db_session.commit()
    gasto = _gasto(db_session, seed["sucursal"].id)
    adj = _subir(como_rol("compras", id=seed["usuario"].id), gasto.id, JPEG).json()

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
    client = como_rol("compras", id=seed["usuario"].id)
    adj = _subir(client, gasto.id, JPEG).json()
    assert len(list(storage_tmp.rglob("*.webp"))) == 1

    assert client.delete(f"/gastos/{gasto.id}/adjuntos/{adj['id']}").status_code == 204
    assert client.delete(f"/gastos/{gasto.id}/adjuntos/{adj['id']}").status_code == 204
    asyncio.run(procesar_borrados(db_session, LocalStorage(str(storage_tmp))))
    assert list(storage_tmp.rglob("*.webp")) == []
    assert client.get(f"/gastos/{gasto.id}/adjuntos").json() == []


def test_adjunto_con_gasto_id_equivocado_da_404(como_rol, seed, db_session):
    g1 = _gasto(db_session, seed["sucursal"].id)
    g2 = _gasto(db_session, seed["sucursal"].id)
    client = como_rol("compras", id=seed["usuario"].id)
    adj = _subir(client, g1.id, JPEG).json()
    assert client.get(f"/gastos/{g2.id}/adjuntos/{adj['id']}/archivo").status_code == 404


# ---- Registro rápido: proveedor opcional ----


def test_gasto_rapido_sin_proveedor_con_total_manual(como_rol, seed):
    r = como_rol("compras", id=seed["usuario"].id).post(
        "/gastos/",
        json={"tipo_gasto": "directo", "metodo_pago": "efectivo", "total_manual": 150.5},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["proveedor"] is None
    assert float(body["total"]) == 150.5
    assert body["num_adjuntos"] == 0


def test_gasto_sin_total_ni_articulos_es_invalido(como_rol, seed):
    r = como_rol("compras", id=seed["usuario"].id).post(
        "/gastos/", json={"tipo_gasto": "directo", "metodo_pago": "efectivo"}
    )
    assert r.status_code == 400


def test_gasto_total_manual_cero_sin_articulos_es_invalido(como_rol, seed):
    r = como_rol("compras", id=seed["usuario"].id).post(
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
    client = como_rol("compras", id=seed["usuario"].id)
    _subir(client, gasto.id, JPEG)
    assert len(list(storage_tmp.rglob("*.webp"))) == 1

    assert client.delete(f"/gastos/{gasto.id}").status_code == 204
    asyncio.run(procesar_borrados(db_session, LocalStorage(str(storage_tmp))))
    assert list(storage_tmp.rglob("*.webp")) == []


def test_body_gigante_se_rechaza_antes_de_parsear(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    r = _subir(
        como_rol("compras", id=seed["usuario"].id), gasto.id, JPEG + b"\x00" * (10 * 1024 * 1024)
    )
    assert r.status_code == 413


def test_adjunto_replay_no_duplica(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    client = como_rol("compras", id=seed["usuario"].id)
    path = f"/gastos/{gasto.id}/adjuntos?client_request_id={uuid4()}"
    first = client.post(path, files={"archivo": ("a.jpg", JPEG, "image/jpeg")})
    assert first.status_code == 201
    second = client.post(path, files={"archivo": ("a.jpg", JPEG, "image/jpeg")})
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert client.post(path, files={"archivo": ("a.png", PNG, "image/png")}).status_code == 409


def test_cabecera_valida_con_imagen_corrupta_se_rechaza(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    assert (
        _subir(
            como_rol("compras", id=seed["usuario"].id), gasto.id, b"\xff\xd8\xff" + b"0" * 100
        ).status_code
        == 415
    )


def test_limpieza_fallida_sobrevive_y_se_reintenta(como_rol, seed, db_session, storage_tmp):
    from app.utils.timezone import get_mexico_now

    gasto = _gasto(db_session, seed["sucursal"].id)
    client = como_rol("compras", id=seed["usuario"].id)
    adj = _subir(client, gasto.id, JPEG).json()
    assert client.delete(f"/gastos/{gasto.id}/adjuntos/{adj['id']}").status_code == 204

    class Caido:
        async def borrar(self, llave):
            raise OSError("offline")

    assert asyncio.run(procesar_borrados(db_session, Caido())) == 0
    task = db_session.query(StorageBorrado).one()
    assert task.intentos == 1
    task.proximo_intento = get_mexico_now()
    db_session.commit()
    assert asyncio.run(procesar_borrados(db_session, LocalStorage(str(storage_tmp)))) == 1
    assert db_session.query(StorageBorrado).count() == 0


def test_normalizacion_quita_exif_y_limita_dimensiones():
    from app.services.imagenes import normalizar_imagen

    image = Image.new("RGB", (2400, 1800), "white")
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = "metadata privada"
    source = io.BytesIO()
    image.save(source, format="JPEG", exif=exif)
    output = Image.open(io.BytesIO(normalizar_imagen(source.getvalue())))
    assert output.size == (1200, 1600)
    assert not output.getexif()


def test_commit_fallido_de_subida_conserva_limpieza_durable(
    como_rol, seed, db_session, storage_tmp, monkeypatch
):
    from sqlalchemy.orm import Session

    from app.models import GastoAdjunto
    from app.utils.timezone import get_mexico_now

    gasto = _gasto(db_session, seed["sucursal"].id)
    original = Session.commit

    def fallar_adjunto(session):
        if any(isinstance(row, GastoAdjunto) for row in session.new):
            raise RuntimeError("commit interrumpido")
        return original(session)

    monkeypatch.setattr(Session, "commit", fallar_adjunto)
    with pytest.raises(RuntimeError, match="commit interrumpido"):
        _subir(como_rol("compras", id=seed["usuario"].id), gasto.id, JPEG)
    assert db_session.query(GastoAdjunto).count() == 0
    assert len(list(storage_tmp.rglob("*.webp"))) == 1
    task = db_session.query(StorageBorrado).one()
    task.proximo_intento = get_mexico_now()
    db_session.commit()
    assert asyncio.run(procesar_borrados(db_session, LocalStorage(str(storage_tmp)))) == 1
    assert list(storage_tmp.rglob("*.webp")) == []


def test_adjunto_replay_con_cuota_llena_no_consume_plaza(como_rol, seed, db_session):
    gasto = _gasto(db_session, seed["sucursal"].id)
    client = como_rol("compras", id=seed["usuario"].id)
    path = f"/gastos/{gasto.id}/adjuntos?client_request_id={uuid4()}"
    first = client.post(path, files={"archivo": ("a.jpg", JPEG, "image/jpeg")})
    assert first.status_code == 201
    for _ in range(4):
        assert _subir(client, gasto.id, JPEG).status_code == 201
    replay = client.post(path, files={"archivo": ("a.jpg", JPEG, "image/jpeg")})
    assert replay.status_code == 201 and replay.json()["id"] == first.json()["id"]
    assert len(client.get(f"/gastos/{gasto.id}/adjuntos").json()) == 5
    assert _subir(client, gasto.id, JPEG).status_code == 400
