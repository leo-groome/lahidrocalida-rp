"""Configuración de sueldo y horario por empleado."""

from app.models import Sucursal, Usuario

PAGO = {"tarifa_hora": 40, "tarifa_hora_extra": 80, "horas_jornada": 8}


def _empleado(db_session, seed, nombre="Ana", rol="mesero", sucursal_id=None):
    u = Usuario(
        nombre=nombre, pin="x", rol=rol, activo=True, sucursal_id=sucursal_id or seed["sucursal"].id
    )
    db_session.add(u)
    db_session.flush()
    return u


def test_pago_y_horario_happy_path(como_rol, seed, db_session):
    emp = _empleado(db_session, seed)
    admin = como_rol("administrador")
    r = admin.put(f"/nomina/empleados/{emp.id}/pago", json=PAGO)
    assert r.status_code == 200, r.text
    assert r.json()["tarifa_hora"] == "40.00"
    # Reemplazo: el segundo PUT actualiza, no duplica.
    admin.put(f"/nomina/empleados/{emp.id}/pago", json={**PAGO, "tarifa_hora_extra": 60})
    h = admin.put(
        f"/nomina/empleados/{emp.id}/horario",
        json={
            "dias": [
                {"dia_semana": d, "hora_entrada": "08:00", "hora_salida": "16:00"}
                for d in (1, 2, 3)
            ]
        },
    )
    assert h.status_code == 200, h.text
    admin.put(
        f"/nomina/empleados/{emp.id}/horario",
        json={"dias": [{"dia_semana": 5, "hora_entrada": "18:00", "hora_salida": "02:00"}]},
    )
    fila = next(e for e in admin.get("/nomina/empleados").json() if e["usuario_id"] == emp.id)
    assert fila["pago"]["tarifa_hora_extra"] == "60.00"
    assert [d["dia_semana"] for d in fila["horario"]] == [5]


def test_validaciones(como_rol, seed, db_session):
    emp = _empleado(db_session, seed)
    admin = como_rol("administrador")
    sin_tarifa = {**PAGO, "tarifa_hora": 0}
    assert admin.put(f"/nomina/empleados/{emp.id}/pago", json=sin_tarifa).status_code == 422
    faltante = {"tarifa_hora": 40}
    assert admin.put(f"/nomina/empleados/{emp.id}/pago", json=faltante).status_code == 422
    repetido = {"dias": [{"dia_semana": 1, "hora_entrada": "08:00", "hora_salida": "16:00"}] * 2}
    assert admin.put(f"/nomina/empleados/{emp.id}/horario", json=repetido).status_code == 422
    igual = {"dias": [{"dia_semana": 1, "hora_entrada": "08:00", "hora_salida": "08:00"}]}
    assert admin.put(f"/nomina/empleados/{emp.id}/horario", json=igual).status_code == 422


def test_solo_admin_y_aislamiento_de_sucursal(como_rol, seed, db_session):
    emp = _empleado(db_session, seed)
    assert como_rol("cajero").get("/nomina/empleados").status_code == 403
    assert como_rol("compras").put(f"/nomina/empleados/{emp.id}/pago", json=PAGO).status_code == 403
    otra = Sucursal(nombre="Norte")
    db_session.add(otra)
    db_session.flush()
    ajeno = como_rol("administrador", sucursal_id=otra.id)
    assert ajeno.put(f"/nomina/empleados/{emp.id}/pago", json=PAGO).status_code == 404
    assert ajeno.put(f"/nomina/empleados/{emp.id}/horario", json={"dias": []}).status_code == 404
    assert ajeno.get("/nomina/empleados").json() == []


def test_admin_no_entra_a_nomina(como_rol, seed, db_session):
    jefe = _empleado(db_session, seed, nombre="Jefe", rol="administrador")
    admin = como_rol("administrador")
    assert admin.put(f"/nomina/empleados/{jefe.id}/pago", json=PAGO).status_code == 404
    assert all(e["usuario_id"] != jefe.id for e in admin.get("/nomina/empleados").json())
