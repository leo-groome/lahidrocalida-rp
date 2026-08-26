"""POST /auth/asistencia deja de ser un toggle ciego (S3.5): un registro
abierto de una jornada anterior nunca se lee como "salida" de hoy — eso es
trabajo de `reconciliar_jornada`, no de este endpoint. El toggle solo cierra
un registro si su `fecha_entrada` cae en la jornada operativa actual.
"""

from datetime import timedelta

from app.auth import get_password_hash
from app.models import RegistroAsistencia, Usuario
from app.utils.timezone import get_mexico_now


def _usuario_con_pin(db_session, seed, pin="1234"):
    usuario = Usuario(
        nombre="Mesero Check-in",
        pin=get_password_hash(pin),
        rol="mesero",
        sucursal_id=seed["sucursal"].id,
        activo=True,
    )
    db_session.add(usuario)
    db_session.commit()
    return usuario


def test_checkin_checkout_mismo_dia_funciona(client, db_session, seed):
    usuario = _usuario_con_pin(db_session, seed)

    r = client.post("/auth/asistencia", json={"usuario_id": usuario.id, "pin": "1234"})
    assert r.status_code == 200
    assert r.json()["fecha_salida"] is None  # clock-in

    r = client.post("/auth/asistencia", json={"usuario_id": usuario.id, "pin": "1234"})
    assert r.status_code == 200
    assert r.json()["fecha_salida"] is not None  # clock-out del mismo registro
    assert r.json()["horas_trabajadas"] is not None


def test_registro_huerfano_de_ayer_no_se_lee_como_salida_de_hoy(client, db_session, seed):
    usuario = _usuario_con_pin(db_session, seed)
    ayer = get_mexico_now() - timedelta(days=2)
    huerfano = RegistroAsistencia(usuario_id=usuario.id, fecha_entrada=ayer)
    db_session.add(huerfano)
    db_session.commit()
    huerfano_id = huerfano.id

    r = client.post("/auth/asistencia", json={"usuario_id": usuario.id, "pin": "1234"})
    assert r.status_code == 200
    body = r.json()

    # Se abrió un check-in NUEVO, no se cerró el huérfano de ayer.
    assert body["id"] != huerfano_id
    assert body["fecha_salida"] is None

    db_session.refresh(huerfano)
    assert huerfano.fecha_salida is None  # sigue sin fecha_salida real


def test_registro_ya_reconciliado_tampoco_se_lee_como_salida(client, db_session, seed):
    """Un huérfano que reconciliar_jornada ya marcó (cierre_automatico=True)
    tiene fecha_salida NULL a propósito — el toggle no debe confundirlo con
    "el abierto de hoy" ni al cerrarlo ni al decidir si crear uno nuevo."""
    usuario = _usuario_con_pin(db_session, seed)
    ayer = get_mexico_now() - timedelta(days=2)
    reconciliado = RegistroAsistencia(
        usuario_id=usuario.id,
        fecha_entrada=ayer,
        cierre_automatico=True,
        requiere_revision=True,
    )
    db_session.add(reconciliado)
    db_session.commit()

    r = client.post("/auth/asistencia", json={"usuario_id": usuario.id, "pin": "1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] != reconciliado.id
    assert body["fecha_salida"] is None
