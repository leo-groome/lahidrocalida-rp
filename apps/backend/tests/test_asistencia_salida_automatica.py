"""Salida automática de asistencia a las 00:30 hora México (SA PR2).

A quien no registró salida se le registra la de las 00:30 de la noche de su jornada.
Los turnos de caja no se tocan. Se inyecta `ahora` para no depender del reloj.
"""

from datetime import datetime

from app.auth import get_password_hash
from app.models import RegistroAsistencia, Turno, Usuario
from app.services.jornada import reconciliar_jornada, salida_automatica
from app.utils.timezone import MEXICO_TZ, to_mexico_aware


def _mx(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 10, dia, hora, minuto, tzinfo=MEXICO_TZ)


def _registro(db, seed, entrada):
    r = RegistroAsistencia(usuario_id=seed["usuario"].id, fecha_entrada=entrada)
    db.add(r)
    db.commit()
    return r


def test_salida_automatica_es_las_0030_de_la_noche_de_la_jornada():
    assert salida_automatica(_mx(16, 21, 0)) == _mx(17, 0, 30)
    assert salida_automatica(_mx(16, 14, 0)) == _mx(17, 0, 30)


def test_salida_automatica_no_aplica_a_entradas_fuera_de_regla():
    assert salida_automatica(_mx(17, 0, 10)) is None  # <1 h antes del corte: anomalía
    assert salida_automatica(_mx(17, 0, 45)) is None  # ya pasó el corte de esa noche
    assert salida_automatica(_mx(16, 6, 0)) is None  # >16 h de turno


def test_pasadas_las_0030_se_registra_la_salida(db_session, seed):
    r = _registro(db_session, seed, _mx(16, 21, 0))

    reconciliar_jornada(db_session, seed["sucursal"].id, ahora=_mx(17, 0, 31))
    db_session.refresh(r)

    assert to_mexico_aware(r.fecha_salida) == _mx(17, 0, 30)
    assert r.cierre_automatico is True
    assert r.requiere_revision is False  # cuenta para horas
    assert r.fecha_salida_estimada is None


def test_antes_de_las_0030_sigue_abierto(db_session, seed):
    r = _registro(db_session, seed, _mx(16, 21, 0))

    reconciliar_jornada(db_session, seed["sucursal"].id, ahora=_mx(17, 0, 29))
    db_session.refresh(r)

    assert r.fecha_salida is None
    assert r.cierre_automatico is False


def test_se_aplica_aunque_la_reconciliacion_corra_dias_despues(db_session, seed):
    r = _registro(db_session, seed, _mx(14, 20, 0))

    reconciliar_jornada(db_session, seed["sucursal"].id, ahora=_mx(17, 12, 0))
    db_session.refresh(r)

    assert to_mexico_aware(r.fecha_salida) == _mx(15, 0, 30)  # no "ahora"
    assert r.requiere_revision is False


def test_entrada_de_madrugada_se_conserva_como_anomalia(db_session, seed):
    r = _registro(db_session, seed, _mx(17, 0, 45))

    reconciliar_jornada(db_session, seed["sucursal"].id, ahora=_mx(17, 12, 0))
    db_session.refresh(r)

    assert r.fecha_salida is None
    assert r.cierre_automatico is True
    assert r.requiere_revision is True


def test_idempotente_y_no_toca_turnos_de_caja(db_session, seed):
    r = _registro(db_session, seed, _mx(16, 21, 0))
    turno = Turno(
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
        fecha_apertura=_mx(16, 14, 0),
        total_inicial=100,
        estado="abierto",
    )
    db_session.add(turno)
    db_session.commit()

    for _ in range(2):
        reconciliar_jornada(db_session, seed["sucursal"].id, ahora=_mx(17, 1, 0))
    db_session.refresh(r)
    db_session.refresh(turno)

    assert to_mexico_aware(r.fecha_salida) == _mx(17, 0, 30)
    assert turno.estado == "abierto"
    assert turno.cerrado_automatico is False


def test_checar_en_la_madrugada_no_abre_entrada_fantasma(client, db_session, seed, monkeypatch):
    """A las 00:40 el empleado intenta checar su salida: ya tiene la automática de las
    00:30. No se crea una entrada nueva que luego sería anomalía."""
    import app.routers.auth as auth_router

    usuario = Usuario(
        nombre="Mesero Tarde",
        pin=get_password_hash("1234"),
        rol="mesero",
        sucursal_id=seed["sucursal"].id,
        activo=True,
    )
    db_session.add(usuario)
    db_session.commit()
    entrada = RegistroAsistencia(usuario_id=usuario.id, fecha_entrada=_mx(16, 20, 0))
    db_session.add(entrada)
    db_session.commit()
    entrada_id = entrada.id

    ahora = _mx(17, 0, 40)
    monkeypatch.setattr(auth_router, "get_mexico_now", lambda: ahora)
    monkeypatch.setattr("app.services.jornada.get_mexico_now", lambda: ahora)

    r = client.post("/auth/asistencia", json={"usuario_id": usuario.id, "pin": "1234"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == entrada_id
    assert body["cierre_automatico"] is True
    assert body["horas_trabajadas"] == 4.5
    assert db_session.query(RegistroAsistencia).filter_by(usuario_id=usuario.id).count() == 1


def test_checar_pin_incorrecto_sigue_dando_401(client, db_session, seed):
    usuario = Usuario(
        nombre="Mesero X",
        pin=get_password_hash("1234"),
        rol="mesero",
        sucursal_id=seed["sucursal"].id,
        activo=True,
    )
    db_session.add(usuario)
    db_session.commit()
    r = client.post("/auth/asistencia", json={"usuario_id": usuario.id, "pin": "9999"})
    assert r.status_code == 401


def test_backfill_resuelve_anomalias_viejas_y_deja_las_no_cubiertas(db_session, seed):
    uid = seed["usuario"].id
    cubierta = RegistroAsistencia(
        usuario_id=uid,
        fecha_entrada=_mx(10, 21, 0),
        cierre_automatico=True,
        requiere_revision=True,
        fecha_salida_estimada=_mx(11, 5, 0),
    )
    no_cubierta = RegistroAsistencia(
        usuario_id=uid,
        fecha_entrada=_mx(11, 6, 0),  # >16 h: no hay salida confiable
        cierre_automatico=True,
        requiere_revision=True,
    )
    db_session.add_all([cubierta, no_cubierta])
    db_session.commit()

    from app.services.jornada import backfill_salidas_automaticas

    # Dry-run: reporta pero no escribe.
    assert backfill_salidas_automaticas(db_session) == [(cubierta.id, _mx(11, 0, 30))]
    db_session.refresh(cubierta)
    assert cubierta.fecha_salida is None

    backfill_salidas_automaticas(db_session, aplicar=True)
    db_session.refresh(cubierta)
    db_session.refresh(no_cubierta)
    assert to_mexico_aware(cubierta.fecha_salida) == _mx(11, 0, 30)
    assert cubierta.requiere_revision is False
    assert no_cubierta.requiere_revision is True
    assert backfill_salidas_automaticas(db_session, aplicar=True) == []  # idempotente
