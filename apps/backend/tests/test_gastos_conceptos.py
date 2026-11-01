"""Conceptos de gasto indirecto: catálogo, captura, pendientes y reporte."""

from datetime import date
from uuid import uuid4

from app.models import Sucursal
from app.services.conceptos_gasto import estado_concepto


def _crear_concepto(client, **extra):
    body = {"nombre": "Luz", "monto_tipico": 1500, "frecuencia": "mensual", **extra}
    r = client.post("/gastos/conceptos", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _gasto(concepto_id, **extra):
    return {
        "client_request_id": str(uuid4()),
        "tipo_gasto": "indirecto",
        "metodo_pago": "efectivo",
        "total_manual": 1500,
        "concepto_id": concepto_id,
        **extra,
    }


def test_indirecto_con_concepto_y_reporte(como_rol, seed):
    admin = como_rol("administrador")
    concepto = _crear_concepto(admin)
    r = admin.post("/gastos/", json=_gasto(concepto["id"]))
    assert r.status_code == 201, r.text
    assert r.json()["concepto_id"] == concepto["id"]
    resumen = admin.get("/gastos/analiticas/resumen").json()
    assert resumen["por_concepto"] == [
        {"id": concepto["id"], "nombre": "Luz", "total": 1500.0, "pagos": 1}
    ]


def test_solo_admin_gestiona_conceptos(como_rol, seed):
    r = como_rol("compras").post("/gastos/conceptos", json={"nombre": "Gas"})
    assert r.status_code == 403
    admin = como_rol("administrador")
    _crear_concepto(admin, nombre="Gas")
    assert admin.post("/gastos/conceptos", json={"nombre": "Gas"}).status_code == 409
    assert como_rol("compras").get("/gastos/conceptos").status_code == 200


def test_concepto_de_otra_sucursal_o_tipo_invalido(como_rol, seed, db_session):
    admin = como_rol("administrador")
    concepto = _crear_concepto(admin)
    otra = Sucursal(nombre="Norte")
    db_session.add(otra)
    db_session.flush()
    ajeno = como_rol("administrador", sucursal_id=otra.id)
    assert ajeno.post("/gastos/", json=_gasto(concepto["id"])).status_code == 404
    assert ajeno.get("/gastos/conceptos").json() == []
    directo = _gasto(concepto["id"], tipo_gasto="directo")
    assert como_rol("administrador").post("/gastos/", json=directo).status_code == 400


def test_pendientes_ordena_y_se_resuelve_al_pagar(como_rol, seed):
    admin = como_rol("administrador")
    luz = _crear_concepto(admin)
    _crear_concepto(admin, nombre="Eventual", frecuencia="eventual")
    antes = admin.get("/gastos/conceptos/pendientes").json()
    assert [i["estado"] for i in antes] == ["pendiente", "al_corriente"]
    assert admin.post("/gastos/", json=_gasto(luz["id"])).status_code == 201
    despues = admin.get("/gastos/conceptos/pendientes").json()
    assert all(i["estado"] == "al_corriente" for i in despues)


def test_estado_concepto_reglas():
    ident = lambda d: d.date() if hasattr(d, "date") else d  # noqa: E731
    hoy = date(2026, 10, 20)
    assert estado_concepto("mensual", 15, None, hoy, ident) == "vencido"
    assert estado_concepto("mensual", 25, None, hoy, ident) == "al_corriente"
    assert estado_concepto("semanal", None, date(2026, 10, 1), hoy, ident) == "vencido"
    assert estado_concepto("semanal", None, date(2026, 10, 14), hoy, ident) == "pendiente"
    assert estado_concepto("semanal", None, date(2026, 10, 18), hoy, ident) == "al_corriente"


def test_eventual_exige_descripcion(como_rol, seed):
    admin = como_rol("administrador")
    imprevisto = _crear_concepto(admin, nombre="Mantenimiento", frecuencia="eventual")
    sin = admin.post("/gastos/", json=_gasto(imprevisto["id"]))
    assert sin.status_code == 400
    ok = admin.post("/gastos/", json=_gasto(imprevisto["id"], descripcion="Tubería rota en cocina"))
    assert ok.status_code == 201, ok.text
    assert ok.json()["concepto"]["nombre"] == "Mantenimiento"
    assert ok.json()["descripcion"] == "Tubería rota en cocina"


def test_put_conserva_concepto_si_no_se_manda(como_rol, seed):
    admin = como_rol("administrador")
    luz = _crear_concepto(admin)
    creado = admin.post("/gastos/", json=_gasto(luz["id"])).json()
    editado = {k: v for k, v in _gasto(luz["id"], total_manual=1600).items() if k != "concepto_id"}
    r = admin.put(f"/gastos/{creado['id']}", json=editado)
    assert r.status_code == 200, r.text
    assert r.json()["concepto_id"] == luz["id"]
    quitado = admin.put(f"/gastos/{creado['id']}", json={**editado, "concepto_id": None})
    assert quitado.json()["concepto_id"] is None


def test_cada_n_dias_requiere_intervalo_y_calcula_estado(como_rol, seed):
    admin = como_rol("administrador")
    sin = admin.post("/gastos/conceptos", json={"nombre": "Gas", "frecuencia": "cada_n_dias"})
    assert sin.status_code == 422
    gas = _crear_concepto(admin, nombre="Gas", frecuencia="cada_n_dias", intervalo_dias=21)
    assert gas["intervalo_dias"] == 21
    ident = lambda d: d  # noqa: E731
    hoy = date(2026, 10, 30)
    assert (
        estado_concepto("cada_n_dias", None, date(2026, 10, 25), hoy, ident, 21) == "al_corriente"
    )
    assert estado_concepto("cada_n_dias", None, date(2026, 10, 8), hoy, ident, 21) == "pendiente"
    assert estado_concepto("cada_n_dias", None, date(2026, 9, 20), hoy, ident, 21) == "vencido"
    mensual = _crear_concepto(admin, nombre="Renta", intervalo_dias=7)
    assert mensual["intervalo_dias"] is None
