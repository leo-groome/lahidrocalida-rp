"""Propina en efectivo sobre cuenta pagada con tarjeta (y viceversa): suma en
el resumen del día y en el efectivo esperado del turno, sin importar el método
de pago de la cuenta."""

from datetime import UTC, datetime

from app.models import Pedido

CONTEO = {"denominaciones": [{"denominacion": 100, "cantidad": 5}]}


def _pedido_pagado(db_session, seed, turno_id, *, metodo, total, prop_ef=0, prop_tj=0, n="1"):
    p = Pedido(
        numero_display=n,
        total=total,
        estado="pagado",
        tipo_orden="aqui",
        metodo_pago=metodo,
        propina_efectivo=prop_ef,
        propina_tarjeta=prop_tj,
        fecha_pago=datetime.now(UTC),
        turno_id=turno_id,
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
    )
    db_session.add(p)
    db_session.commit()
    return p


def test_propinas_cruzadas_en_resumen_y_turno(como_rol, seed, db_session):
    client = como_rol("cajero")
    turno_id = client.post("/turnos/iniciar", json={"conteo_inicial": CONTEO}).json()["id"]

    # Tarjeta con propina en efectivo, y efectivo con propina en tarjeta.
    _pedido_pagado(db_session, seed, turno_id, metodo="tarjeta", total=200, prop_ef=20, n="1")
    _pedido_pagado(db_session, seed, turno_id, metodo="efectivo", total=100, prop_tj=15, n="2")

    r = client.get("/reportes/dia/analytics", params={"turno_id": turno_id})
    assert r.status_code == 200, r.text
    assert r.json()["propinas"] == {"efectivo": 20.0, "tarjeta": 15.0, "total": 35.0}

    r = client.get(f"/turnos/{turno_id}/resumen")
    assert r.status_code == 200, r.text
    vha = r.json()["ventas_hasta_ahora"]
    assert vha["ventas_efectivo"] == 100.0  # solo la cuenta pagada en efectivo
    assert vha["propinas_efectivo"] == 20.0  # la propina en efectivo de la tarjeta cuenta
    assert vha["total_esperado"] == 500.0 + 100.0 + 20.0


def test_resumen_turno_inexistente_da_404(como_rol):
    r = como_rol("cajero").get("/turnos/999999/resumen")
    assert r.status_code == 404
