"""Nómina semanal: reglas de cálculo, edición, bloqueos y pago."""

from datetime import date, datetime, time
from decimal import Decimal

from app.models import (
    EmpleadoPago,
    Gasto,
    HorarioEmpleado,
    NominaDetalle,
    RegistroAsistencia,
    Sucursal,
    Turno,
    Usuario,
)
from app.services.nomina import (
    Reglas,
    calcular_montos,
    dias_y_extras,
    horas_por_jornada,
    total_linea,
)
from app.utils.timezone import MEXICO_TZ

# Semana cerrada: martes 13 al lunes 19 de octubre de 2026.
DIA_SEMANA = "2026-10-15"
REGLAS = Reglas(Decimal(40), Decimal(80), Decimal(8))


def _dt(dia, h, m=0):
    return datetime(2026, 10, dia, h, m, tzinfo=MEXICO_TZ)


# ---- reglas puras ----------------------------------------------------------------------------


def test_horas_normales_y_extras_a_su_tarifa():
    # 50 h con 2 extras: 48 × 40 + 2 × 80
    m = calcular_montos(REGLAS, Decimal(50), Decimal(2))
    assert (m.base, m.extra_monto) == (Decimal("1920.00"), Decimal("160.00"))


def test_horas_extra_en_bloques_de_cuarto_y_jornada_minima():
    horas = horas_por_jornada(
        [(_dt(13, 8), _dt(13, 16, 7)), (_dt(14, 8), _dt(14, 17, 40)), (_dt(15, 8), _dt(15, 8, 30))]
    )
    dias, extra, total = dias_y_extras(horas, Decimal(8))
    assert dias == 2  # la checada de media hora no es un día
    assert extra == Decimal("1.50")  # 8h07 → 0 ; 9h40 → 1h40 → 1.5
    assert total > 17


def test_total_no_baja_de_cero():
    m = calcular_montos(REGLAS, Decimal(8), Decimal(0))
    assert total_linea(m, Decimal(0), Decimal(9999)) == Decimal(0)


# ---- endpoints -------------------------------------------------------------------------------


def _empleado(db, seed, nombre, extra=80, horario=(1, 2, 3, 4, 5, 6), sucursal_id=None):
    u = Usuario(
        nombre=nombre,
        pin="x",
        rol="mesero",
        activo=True,
        sucursal_id=sucursal_id or seed["sucursal"].id,
    )
    db.add(u)
    db.flush()
    db.add(
        EmpleadoPago(
            usuario_id=u.id,
            sucursal_id=u.sucursal_id,
            tarifa_hora=40,
            tarifa_hora_extra=extra,
            horas_jornada=8,
        )
    )
    db.add_all(
        HorarioEmpleado(
            usuario_id=u.id,
            sucursal_id=u.sucursal_id,
            dia_semana=d,
            hora_entrada=time(8),
            hora_salida=time(16),
        )
        for d in horario
    )
    db.flush()
    return u


def _asistencia(db, usuario, dias=(13, 14, 15, 16, 17, 18), salida_h=16):
    for d in dias:
        db.add(
            RegistroAsistencia(
                usuario_id=usuario.id, fecha_entrada=_dt(d, 8), fecha_salida=_dt(d, salida_h)
            )
        )
    db.flush()


def _abrir(admin):
    r = admin.post("/nomina/periodos", json={"fecha_inicio": DIA_SEMANA})
    assert r.status_code == 200, r.text
    return r.json()


def test_calcula_semana_desde_asistencia(como_rol, seed, db_session):
    ana = _empleado(db_session, seed, "Ana")
    _asistencia(db_session, ana, dias=(13, 14, 15, 16, 17))
    db_session.add(  # el sábado salió 2 h tarde → 2 h extra dobles
        RegistroAsistencia(usuario_id=ana.id, fecha_entrada=_dt(18, 8), fecha_salida=_dt(18, 18))
    )
    db_session.commit()
    p = _abrir(como_rol("administrador"))
    assert (p["fecha_inicio"], p["fecha_fin"], p["estado"]) == (
        "2026-10-13",
        "2026-10-19",
        "borrador",
    )
    linea = p["lineas"][0]
    assert linea["dias_trabajados"] == 6
    assert Decimal(linea["horas_extra"]) == Decimal("2.00")
    assert Decimal(linea["total"]) == Decimal("2080.00")  # 48 h × 40 + 2 h × 80


def test_anomalia_no_cuenta_y_lista_sin_configurar(como_rol, seed, db_session):
    ana = _empleado(db_session, seed, "Ana")
    _asistencia(db_session, ana, dias=(13, 14, 15, 16, 17, 18))
    db_session.add(
        Usuario(
            nombre="Sin Config", pin="x", rol="cajero", activo=True, sucursal_id=seed["sucursal"].id
        )
    )
    db_session.add(
        RegistroAsistencia(
            usuario_id=ana.id, fecha_entrada=_dt(19, 8), requiere_revision=True, fecha_salida=None
        )
    )
    db_session.commit()
    p = _abrir(como_rol("administrador"))
    assert "Sin Config" in p["sin_configurar"]
    assert p["pendientes_asistencia"] == 1
    assert p["lineas"][0]["dias_trabajados"] == 6


def test_editar_linea_recalcula_y_tarjeta_quita_caja(como_rol, seed, db_session):
    ana = _empleado(db_session, seed, "Ana")
    _asistencia(db_session, ana)
    db_session.commit()
    admin = como_rol("administrador")
    p = _abrir(admin)
    url = f"/nomina/periodos/{p['id']}/lineas/{ana.id}"
    r = admin.put(url, json={"bonos": 100, "descuentos": 50, "sale_de_caja": True})
    assert r.status_code == 200, r.text
    linea = r.json()["lineas"][0]
    assert Decimal(linea["total"]) == Decimal("1970.00") and linea["sale_de_caja"] is True
    linea = admin.put(url, json={"metodo_pago": "tarjeta"}).json()["lineas"][0]
    assert linea["sale_de_caja"] is False
    corregida = admin.put(url, json={"horas_trabajadas": 40, "horas_extra": 0}).json()["lineas"][0]
    assert Decimal(corregida["base"]) == Decimal("1600.00")
    mal = admin.put(url, json={"horas_extra": 41})
    assert mal.status_code == 400
    # Lo corregido a mano sobrevive a reabrir la semana; "Recalcular" lo descarta.
    assert Decimal(_abrir(admin)["lineas"][0]["horas_trabajadas"]) == Decimal("40")
    de_nuevo = admin.post(f"/nomina/periodos/{p['id']}/recalcular").json()["lineas"][0]
    assert Decimal(de_nuevo["horas_trabajadas"]) == Decimal("48")


def test_pagar_crea_gastos_por_metodo_e_idempotente(como_rol, seed, db_session, admin_pin):
    ana, beto = (
        _empleado(db_session, seed, "Ana"),
        _empleado(db_session, seed, "Beto", extra=40),
    )
    _asistencia(db_session, ana)
    _asistencia(db_session, beto)
    db_session.commit()
    admin = como_rol("administrador")
    p = _abrir(admin)
    admin.put(f"/nomina/periodos/{p['id']}/lineas/{beto.id}", json={"metodo_pago": "tarjeta"})
    body = {"pin_autorizacion": admin_pin["pin"]}
    malo = admin.post(f"/nomina/periodos/{p['id']}/pagar", json={"pin_autorizacion": "0000"})
    assert malo.status_code == 403
    r = admin.post(f"/nomina/periodos/{p['id']}/pagar", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "pagada" and all(ln["pagada"] for ln in r.json()["lineas"])
    gastos = db_session.query(Gasto).filter(Gasto.tipo_gasto == "nomina").all()
    assert sorted((g.metodo_pago, g.total, g.turno_id) for g in gastos) == [
        ("efectivo", Decimal("1920.00"), None),
        ("tarjeta", Decimal("1920.00"), None),
    ]
    assert db_session.query(NominaDetalle).count() == 2
    # Repetir no duplica.
    assert admin.post(f"/nomina/periodos/{p['id']}/pagar", json=body).status_code == 200
    assert db_session.query(Gasto).filter(Gasto.tipo_gasto == "nomina").count() == 2
    # Ya pagada: no se edita.
    assert (
        admin.put(f"/nomina/periodos/{p['id']}/lineas/{ana.id}", json={"bonos": 1}).status_code
        == 409
    )


def test_pagar_desde_caja_exige_turno_y_lo_liga(como_rol, seed, db_session, admin_pin):
    ana = _empleado(db_session, seed, "Ana")
    _asistencia(db_session, ana)
    db_session.commit()
    admin = como_rol("administrador")
    p = _abrir(admin)
    admin.put(f"/nomina/periodos/{p['id']}/lineas/{ana.id}", json={"sale_de_caja": True})
    body = {"pin_autorizacion": admin_pin["pin"]}
    sin = admin.post(f"/nomina/periodos/{p['id']}/pagar", json=body)
    assert sin.status_code == 409 and db_session.query(Gasto).count() == 0
    turno = Turno(sucursal_id=seed["sucursal"].id, usuario_id=seed["usuario"].id, total_inicial=500)
    db_session.add(turno)
    db_session.commit()
    assert admin.post(f"/nomina/periodos/{p['id']}/pagar", json=body).status_code == 200
    assert db_session.query(Gasto).one().turno_id == turno.id


def test_bloqueo_por_entrada_sin_salida_solo_a_su_dueno(como_rol, seed, db_session, admin_pin):
    ana, beto = _empleado(db_session, seed, "Ana"), _empleado(db_session, seed, "Beto")
    _asistencia(db_session, ana)
    _asistencia(db_session, beto)
    db_session.add(
        RegistroAsistencia(usuario_id=ana.id, fecha_entrada=_dt(19, 9), fecha_salida=None)
    )
    db_session.commit()
    admin = como_rol("administrador")
    p = _abrir(admin)
    bloqueos = {ln["nombre"]: ln["bloqueo"] for ln in p["lineas"]}
    assert "sin salida" in bloqueos["Ana"] and bloqueos["Beto"] is None
    body = {"pin_autorizacion": admin_pin["pin"], "usuario_ids": [ana.id]}
    r = admin.post(f"/nomina/periodos/{p['id']}/pagar", json=body)
    assert r.status_code == 409 and "sin salida" in r.json()["detail"]
    # Sin elegir a nadie se paga a quien sí se puede: Beto.
    r = admin.post(f"/nomina/periodos/{p['id']}/pagar", json={"pin_autorizacion": admin_pin["pin"]})
    assert r.status_code == 200, r.text
    pagadas = {ln["nombre"]: ln["pagada"] for ln in r.json()["lineas"]}
    assert pagadas == {"Ana": False, "Beto": True} and r.json()["estado"] == "borrador"
    assert db_session.query(Gasto).filter(Gasto.tipo_gasto == "nomina").count() == 1


def test_se_paga_desde_el_ultimo_dia_de_cada_quien(
    como_rol, seed, db_session, admin_pin, monkeypatch
):
    # Hoy es jueves 15/10: Ana solo va martes y miércoles; Beto, de martes a domingo.
    monkeypatch.setattr("app.routers.nomina.jornada_actual", lambda: date(2026, 10, 15))
    ana = _empleado(db_session, seed, "Ana", horario=(1, 2))
    beto = _empleado(db_session, seed, "Beto")
    _asistencia(db_session, ana, dias=(13, 14))
    _asistencia(db_session, beto, dias=(13, 14, 15))
    db_session.commit()
    admin = como_rol("administrador")
    p = _abrir(admin)
    lineas = {ln["nombre"]: ln for ln in p["lineas"]}
    assert lineas["Ana"]["bloqueo"] is None and lineas["Ana"]["ultimo_dia"] == "2026-10-14"
    assert lineas["Beto"]["ultimo_dia"] == "2026-10-18"
    assert "domingo 18/10" in lineas["Beto"]["bloqueo"]
    body = {"pin_autorizacion": admin_pin["pin"]}
    assert (
        admin.post(
            f"/nomina/periodos/{p['id']}/pagar", json={**body, "usuario_ids": [beto.id]}
        ).status_code
        == 409
    )
    r = admin.post(f"/nomina/periodos/{p['id']}/pagar", json=body)
    assert r.status_code == 200, r.text
    assert {ln["nombre"]: ln["pagada"] for ln in r.json()["lineas"]} == {"Ana": True, "Beto": False}
    assert r.json()["estado"] == "borrador"
    gasto = db_session.query(Gasto).filter(Gasto.tipo_gasto == "nomina").one()
    assert gasto.total == Decimal("640.00")  # 16 h × 40
    # Ana ya cobrada: ya no se edita ni se recalcula; Beto sigue abierto.
    assert (
        admin.put(f"/nomina/periodos/{p['id']}/lineas/{ana.id}", json={"bonos": 1}).status_code
        == 409
    )


def test_solo_admin_y_aislamiento_de_sucursal(como_rol, seed, db_session):
    ana = _empleado(db_session, seed, "Ana")
    _asistencia(db_session, ana)
    db_session.commit()
    assert (
        como_rol("cajero").post("/nomina/periodos", json={"fecha_inicio": DIA_SEMANA}).status_code
        == 403
    )
    p = _abrir(como_rol("administrador"))
    otra = Sucursal(nombre="Norte")
    db_session.add(otra)
    db_session.flush()
    ajeno = como_rol("administrador", sucursal_id=otra.id)
    assert (
        ajeno.put(f"/nomina/periodos/{p['id']}/lineas/{ana.id}", json={"bonos": 1}).status_code
        == 404
    )
    assert (
        ajeno.post(f"/nomina/periodos/{p['id']}/pagar", json={"pin_autorizacion": "1"}).status_code
        == 404
    )
    assert _abrir(ajeno)["lineas"] == []


def test_marca_salidas_automaticas_para_revision(como_rol, seed, db_session):
    ana = _empleado(db_session, seed, "Ana")
    _asistencia(db_session, ana, dias=(13, 14, 15, 16, 17))
    db_session.add(
        RegistroAsistencia(
            usuario_id=ana.id,
            fecha_entrada=_dt(18, 9),
            fecha_salida=datetime(2026, 10, 19, 0, 30, tzinfo=MEXICO_TZ),
            cierre_automatico=True,
        )
    )
    db_session.commit()
    linea = _abrir(como_rol("administrador"))["lineas"][0]
    assert linea["salidas_automaticas"] == 1
    assert Decimal(linea["horas_extra"]) == Decimal("7.50")  # 15.5 h: por eso se avisa
