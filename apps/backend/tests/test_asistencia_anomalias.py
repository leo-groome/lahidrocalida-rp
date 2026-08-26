"""GET /asistencia/anomalias (S3.9) y PATCH /asistencia/{id}/confirmar-salida
(S3.10): admin ve los registros que reconciliar_jornada marcó para revisión y
puede fijar la hora real de salida, lo que los saca de la lista.
"""

from datetime import timedelta

from app.models import RegistroAsistencia
from app.utils.timezone import get_mexico_now


def _registro_pendiente_revision(db_session, seed):
    ayer = get_mexico_now() - timedelta(days=2)
    registro = RegistroAsistencia(
        usuario_id=seed["usuario"].id,
        fecha_entrada=ayer,
        cierre_automatico=True,
        requiere_revision=True,
        fecha_salida_estimada=ayer + timedelta(hours=8),
    )
    db_session.add(registro)
    db_session.commit()
    return registro


def test_anomalias_requiere_admin(como_rol, db_session, seed):
    _registro_pendiente_revision(db_session, seed)
    r = como_rol("mesero").get("/asistencia/anomalias")
    assert r.status_code == 403


def test_anomalias_lista_solo_requiere_revision(admin_client, db_session, seed):
    pendiente = _registro_pendiente_revision(db_session, seed)

    normal = RegistroAsistencia(usuario_id=seed["usuario"].id, fecha_entrada=get_mexico_now())
    db_session.add(normal)
    db_session.commit()

    r = admin_client.get("/asistencia/anomalias")
    assert r.status_code == 200
    ids = [item["id"] for item in r.json()]
    assert pendiente.id in ids
    assert normal.id not in ids


def test_confirmar_salida_limpia_requiere_revision(admin_client, db_session, seed):
    pendiente = _registro_pendiente_revision(db_session, seed)
    hora_real = pendiente.fecha_salida_estimada

    r = admin_client.patch(
        f"/asistencia/{pendiente.id}/confirmar-salida",
        json={"fecha_salida": hora_real.isoformat()},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["requiere_revision"] is False
    assert body["cierre_automatico"] is True  # se conserva como histórico
    assert body["fecha_salida"] is not None

    r = admin_client.get("/asistencia/anomalias")
    assert pendiente.id not in [item["id"] for item in r.json()]


def test_anomalias_resumen_accesible_a_cajero(como_rol, db_session, seed):
    _registro_pendiente_revision(db_session, seed)
    r = como_rol("cajero").get("/asistencia/anomalias/resumen")
    assert r.status_code == 200
    assert r.json()["pendientes"] >= 1
