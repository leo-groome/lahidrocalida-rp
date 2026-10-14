"""Canal Uber Eats: no se cobra en Caja, se marca entregado al repartidor y
se reporta aparte — fuera del efectivo esperado y de los ingresos de terminal."""

from decimal import Decimal

from app.models import Pedido, Turno

CONTEO = {"denominaciones": [{"denominacion": 100, "cantidad": 5}]}  # $500


def _turno_abierto(db_session, seed) -> Turno:
    turno = Turno(
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
        total_inicial=Decimal("500"),
        estado="abierto",
    )
    db_session.add(turno)
    db_session.commit()
    db_session.refresh(turno)
    return turno


def _pedido(db_session, seed, turno, *, tipo, estado, total, metodo_pago=None, numero="U1"):
    pedido = Pedido(
        numero_display=numero,
        total=total,
        estado=estado,
        tipo_orden=tipo,
        metodo_pago=metodo_pago,
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
        turno_id=turno.id,
    )
    db_session.add(pedido)
    db_session.commit()
    db_session.refresh(pedido)
    return pedido


def test_mesero_marca_uber_entregado_al_repartidor(como_rol, seed, db_session):
    turno = _turno_abierto(db_session, seed)
    pedido = _pedido(db_session, seed, turno, tipo="uber_eats", estado="listo", total=250)

    r = como_rol("mesero").put(f"/pedidos/{pedido.id}", json={"estado": "entregado_repartidor"})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "entregado_repartidor"

    db_session.refresh(pedido)
    assert pedido.fecha_pago is not None
    assert pedido.turno_id == turno.id


def test_uber_no_puede_pasar_a_pagado(como_rol, seed, db_session):
    turno = _turno_abierto(db_session, seed)
    pedido = _pedido(db_session, seed, turno, tipo="uber_eats", estado="listo", total=250)

    r = como_rol("administrador").put(
        f"/pedidos/{pedido.id}", json={"estado": "pagado", "metodo_pago": "efectivo"}
    )
    assert r.status_code == 403


def test_pedido_normal_no_puede_marcarse_entregado_repartidor(como_rol, seed, db_session):
    turno = _turno_abierto(db_session, seed)
    pedido = _pedido(db_session, seed, turno, tipo="llevar", estado="listo", total=100)

    r = como_rol("administrador").put(
        f"/pedidos/{pedido.id}", json={"estado": "entregado_repartidor"}
    )
    assert r.status_code == 403


def test_entregado_repartidor_es_terminal(como_rol, seed, db_session):
    turno = _turno_abierto(db_session, seed)
    pedido = _pedido(db_session, seed, turno, tipo="uber_eats", estado="listo", total=250)
    como_rol("mesero").put(f"/pedidos/{pedido.id}", json={"estado": "entregado_repartidor"})

    r = como_rol("administrador").put(f"/pedidos/{pedido.id}", json={"estado": "listo"})
    assert r.status_code == 403


def test_uber_no_se_puede_dividir(como_rol, seed, db_session):
    turno = _turno_abierto(db_session, seed)
    pedido = _pedido(db_session, seed, turno, tipo="uber_eats", estado="entregado", total=250)

    r = como_rol("administrador").post(
        f"/pedidos/{pedido.id}/dividir_por_montos",
        json={"cuentas": [{"monto": 100}, {"monto": 150}], "client_request_id": "x"},
    )
    assert r.status_code == 400


def test_corte_turno_separa_uber_del_efectivo(como_rol, seed, db_session):
    turno = _turno_abierto(db_session, seed)
    # $300 cobrados en efectivo + 2 Uber ($250 y $150) entregados al repartidor.
    _pedido(
        db_session, seed, turno, tipo="aqui", estado="pagado", total=300,
        metodo_pago="efectivo", numero="A1",
    )  # fmt: skip
    _pedido(db_session, seed, turno, tipo="uber_eats", estado="entregado_repartidor",
            total=250, numero="U1")  # fmt: skip
    _pedido(db_session, seed, turno, tipo="uber_eats", estado="entregado_repartidor",
            total=150, numero="U2")  # fmt: skip

    client = como_rol("administrador")

    r = client.get(f"/turnos/{turno.id}/resumen")
    assert r.status_code == 200, r.text
    resumen = r.json()
    assert resumen["uber_eats"] == {"pedidos": 2, "total": 400.0}
    # Efectivo esperado = fondo 500 + ventas efectivo 300; el Uber no entra.
    assert resumen["ventas_hasta_ahora"]["total_esperado"] == 800.0

    # Cierre con el conteo exacto esperado => diferencia 0 aunque haya Uber.
    conteo_final = {
        "denominaciones": [
            {"denominacion": 500, "cantidad": 1},
            {"denominacion": 200, "cantidad": 1},
            {"denominacion": 100, "cantidad": 1},
        ]
    }  # $800
    r = client.post(f"/turnos/{turno.id}/cerrar", json={"conteo_final": conteo_final})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["diferencia"] == 0.0
    assert body["pedidos_uber"] == 2
    assert body["ventas_uber"] == 400.0


def test_analytics_dia_no_suma_uber_en_ingresos(como_rol, seed, db_session):
    turno = _turno_abierto(db_session, seed)
    _pedido(
        db_session, seed, turno, tipo="aqui", estado="pagado", total=300,
        metodo_pago="tarjeta", numero="A1",
    )  # fmt: skip
    _pedido(db_session, seed, turno, tipo="uber_eats", estado="entregado_repartidor",
            total=250, numero="U1")  # fmt: skip

    r = como_rol("cajero").get("/reportes/dia/analytics")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ingresos"]["total"] == 300.0
    assert body["uber_eats"] == {"pedidos": 1, "total": 250.0}


def test_mesero_de_otra_sucursal_no_marca_entregado_repartidor(como_rol, seed, db_session):
    turno = _turno_abierto(db_session, seed)
    pedido = _pedido(db_session, seed, turno, tipo="uber_eats", estado="listo", total=250)

    r = como_rol("mesero", sucursal_id=seed["sucursal"].id + 1).put(
        f"/pedidos/{pedido.id}", json={"estado": "entregado_repartidor"}
    )
    assert r.status_code == 403


def test_no_se_agregan_ni_editan_articulos_tras_entrega_al_repartidor(como_rol, seed, db_session):
    turno = _turno_abierto(db_session, seed)
    pedido = _pedido(
        db_session, seed, turno, tipo="uber_eats", estado="entregado_repartidor", total=250
    )

    client = como_rol("administrador")
    r = client.put(f"/pedidos/{pedido.id}/agregar-articulos", json={"articulos": []})
    assert r.status_code == 400
    r = client.put(f"/pedidos/{pedido.id}/actualizar-articulos", json={"articulos": []})
    assert r.status_code == 400
    db_session.refresh(pedido)
    assert float(pedido.total) == 250.0


def test_tickets_del_dia_incluye_uber_entregado_con_su_estado(como_rol, seed, db_session):
    turno = _turno_abierto(db_session, seed)
    _pedido(
        db_session, seed, turno, tipo="aqui", estado="pagado", total=300,
        metodo_pago="efectivo", numero="A1",
    )  # fmt: skip
    uber = _pedido(db_session, seed, turno, tipo="uber_eats", estado="listo", total=250,
                   numero="U1")  # fmt: skip
    como_rol("mesero").put(f"/pedidos/{uber.id}", json={"estado": "entregado_repartidor"})

    r = como_rol("cajero").get("/reportes/dia/tickets")
    assert r.status_code == 200, r.text
    por_numero = {t["numero_display"]: t for t in r.json()}
    assert set(por_numero) == {"A1", "U1"}
    assert por_numero["U1"]["estado"] == "entregado_repartidor"
    assert por_numero["U1"]["tipo_orden"] == "uber_eats"
    assert por_numero["U1"]["metodo_pago"] is None
    # La hora del evento es la de entrega al repartidor, no la de creación.
    assert por_numero["U1"]["fecha_evento"] == por_numero["U1"]["fecha_pago"]


def test_entrega_uber_pertenece_al_turno_abierto_actual(como_rol, seed, db_session):
    t1 = _turno_abierto(db_session, seed)
    pedido = _pedido(db_session, seed, t1, tipo="uber_eats", estado="listo", total=250)
    client = como_rol("administrador")
    assert client.post(f"/turnos/{t1.id}/cerrar", json={"conteo_final": CONTEO}).status_code == 200
    t2 = _turno_abierto(db_session, seed)
    assert (
        client.put(f"/pedidos/{pedido.id}", json={"estado": "entregado_repartidor"}).status_code
        == 200
    )
    db_session.refresh(pedido)
    assert pedido.turno_id == t2.id
    assert client.get(f"/turnos/{t1.id}/resumen").json()["uber_eats"] == {"pedidos": 0, "total": 0}
    assert client.get(f"/turnos/{t2.id}/resumen").json()["uber_eats"] == {
        "pedidos": 1,
        "total": 250,
    }


def test_entrega_uber_sin_turno_no_modifica_pedido(como_rol, seed, db_session):
    turno = _turno_abierto(db_session, seed)
    pedido = _pedido(db_session, seed, turno, tipo="uber_eats", estado="listo", total=250)
    turno.estado = "cerrado"
    db_session.commit()
    r = como_rol("mesero").put(f"/pedidos/{pedido.id}", json={"estado": "entregado_repartidor"})
    assert r.status_code == 409
    db_session.refresh(pedido)
    assert pedido.estado == "listo"
    assert pedido.fecha_pago is None
