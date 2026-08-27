"""reconciliar_jornada: cierra turnos/asistencias huérfanos de una jornada
anterior sin inventar horas ni cifras de caja, y es idempotente — llamarla
dos veces sobre el mismo estado no cambia el resultado ni duplica efectos.
"""

from datetime import timedelta

from app.models import RegistroAsistencia, Turno
from app.services.jornada import reconciliar_jornada
from app.utils.timezone import get_mexico_now


def test_turno_de_jornada_anterior_permanece_abierto(db_session, seed):
    ayer = get_mexico_now() - timedelta(days=2)
    turno = Turno(
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
        fecha_apertura=ayer,
        total_inicial=100,
        estado="abierto",
    )
    db_session.add(turno)
    db_session.commit()

    reconciliar_jornada(db_session, seed["sucursal"].id)
    db_session.refresh(turno)

    assert turno.estado == "abierto"
    assert turno.cerrado_automatico is False


def test_turno_de_jornada_actual_no_se_toca(db_session, seed):
    turno = Turno(
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
        fecha_apertura=get_mexico_now(),
        total_inicial=100,
        estado="abierto",
    )
    db_session.add(turno)
    db_session.commit()

    reconciliar_jornada(db_session, seed["sucursal"].id)
    db_session.refresh(turno)

    assert turno.estado == "abierto"
    assert turno.cerrado_automatico is False


def test_asistencia_huerfana_se_marca_para_revision_sin_inventar_salida(db_session, seed):
    ayer = get_mexico_now() - timedelta(days=2)
    registro = RegistroAsistencia(usuario_id=seed["usuario"].id, fecha_entrada=ayer)
    db_session.add(registro)
    db_session.commit()

    reconciliar_jornada(db_session, seed["sucursal"].id)
    db_session.refresh(registro)

    assert registro.cierre_automatico is True
    assert registro.requiere_revision is True
    assert registro.fecha_salida is None  # nunca se inventa la hora real
    assert registro.fecha_salida_estimada is not None


def test_asistencia_de_jornada_actual_no_se_toca(db_session, seed):
    registro = RegistroAsistencia(usuario_id=seed["usuario"].id, fecha_entrada=get_mexico_now())
    db_session.add(registro)
    db_session.commit()

    reconciliar_jornada(db_session, seed["sucursal"].id)
    db_session.refresh(registro)

    assert registro.cierre_automatico is False
    assert registro.requiere_revision is False


def test_reconciliar_es_idempotente(db_session, seed):
    ayer = get_mexico_now() - timedelta(days=2)
    turno = Turno(
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
        fecha_apertura=ayer,
        total_inicial=100,
        estado="abierto",
    )
    registro = RegistroAsistencia(usuario_id=seed["usuario"].id, fecha_entrada=ayer)
    db_session.add_all([turno, registro])
    db_session.commit()

    reconciliar_jornada(db_session, seed["sucursal"].id)
    db_session.refresh(turno)
    db_session.refresh(registro)
    estado_1 = (turno.estado, turno.cerrado_automatico, registro.fecha_salida_estimada)

    reconciliar_jornada(db_session, seed["sucursal"].id)
    db_session.refresh(turno)
    db_session.refresh(registro)
    estado_2 = (turno.estado, turno.cerrado_automatico, registro.fecha_salida_estimada)

    assert estado_1 == estado_2
