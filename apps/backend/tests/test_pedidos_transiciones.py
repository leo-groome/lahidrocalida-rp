"""PUT /pedidos/{id}: la máquina de estados real (S2 2.4) valida origen y
destino, no solo destino."""


def _crear_pedido_pendiente(db_session, seed):
    from app.models import Pedido

    pedido = Pedido(
        numero_display="900",
        total=100,
        estado="pendiente",
        tipo_orden="aqui",
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
    )
    db_session.add(pedido)
    db_session.commit()
    db_session.refresh(pedido)
    return pedido


def test_cocina_pasa_pendiente_a_preparando(como_rol, seed, db_session):
    pedido = _crear_pedido_pendiente(db_session, seed)
    r = como_rol("cocina").put(f"/pedidos/{pedido.id}", json={"estado": "preparando"})
    assert r.status_code == 200
    assert r.json()["estado"] == "preparando"


def test_mesero_no_puede_mandar_a_preparando(como_rol, seed, db_session):
    pedido = _crear_pedido_pendiente(db_session, seed)
    r = como_rol("mesero").put(f"/pedidos/{pedido.id}", json={"estado": "preparando"})
    assert r.status_code == 403


def test_pedido_pagado_no_admite_ninguna_transicion(como_rol, seed, db_session):
    """El bug que cierra 2.4: antes nada impedía reabrir un pedido ya pagado."""
    pedido = _crear_pedido_pendiente(db_session, seed)
    pedido.estado = "pagado"
    db_session.commit()

    r = como_rol("administrador").put(f"/pedidos/{pedido.id}", json={"estado": "pendiente"})
    assert r.status_code == 403


def test_estado_invalido_devuelve_400(como_rol, seed, db_session):
    pedido = _crear_pedido_pendiente(db_session, seed)
    r = como_rol("administrador").put(f"/pedidos/{pedido.id}", json={"estado": "no-existe"})
    assert r.status_code == 400


def test_administrador_con_pin_puede_editar_propina_de_pedido_pagado(
    como_rol, seed, db_session, admin_pin
):
    pedido = _crear_pedido_pendiente(db_session, seed)
    pedido.estado = "pagado"
    pedido.propina_tarjeta = 0
    db_session.commit()

    r = como_rol("administrador").put(
        f"/pedidos/{pedido.id}",
        json={
            "estado": "pagado",
            "propina_tarjeta": 50.0,
            "propina_efectivo": 0.0,
            "pin_autorizacion": admin_pin["pin"],
        },
    )
    assert r.status_code == 200
    assert float(r.json()["propina_tarjeta"]) == 50.0
    assert float(r.json()["propina_efectivo"]) == 0.0


def test_administrador_sin_pin_no_puede_editar_propina_de_pedido_pagado(
    como_rol, seed, db_session, admin_pin
):
    """Sin cajero fijo, ni el propio administrador queda exento: debe
    reconfirmar con PIN aunque su sesión ya sea de rol administrador."""
    pedido = _crear_pedido_pendiente(db_session, seed)
    pedido.estado = "pagado"
    db_session.commit()

    r = como_rol("administrador").put(
        f"/pedidos/{pedido.id}",
        json={"estado": "pagado", "propina_tarjeta": 50.0},
    )
    assert r.status_code == 400


def test_cajero_con_pin_de_admin_puede_editar_propina_de_pedido_pagado(
    como_rol, seed, db_session, admin_pin
):
    """Antes bloqueado por completo para cajero; ahora se abre con PIN."""
    pedido = _crear_pedido_pendiente(db_session, seed)
    pedido.estado = "pagado"
    db_session.commit()

    r = como_rol("cajero").put(
        f"/pedidos/{pedido.id}",
        json={
            "estado": "pagado",
            "propina_tarjeta": 50.0,
            "pin_autorizacion": admin_pin["pin"],
        },
    )
    assert r.status_code == 200
    assert float(r.json()["propina_tarjeta"]) == 50.0


def test_cajero_con_pin_incorrecto_no_puede_editar_propina_de_pedido_pagado(
    como_rol, seed, db_session, admin_pin
):
    pedido = _crear_pedido_pendiente(db_session, seed)
    pedido.estado = "pagado"
    db_session.commit()

    r = como_rol("cajero").put(
        f"/pedidos/{pedido.id}",
        json={
            "estado": "pagado",
            "propina_tarjeta": 50.0,
            "pin_autorizacion": "0000",
        },
    )
    assert r.status_code == 403


def test_cancelar_cuenta_requiere_pin_de_admin(como_rol, seed, db_session, admin_pin):
    pedido = _crear_pedido_pendiente(db_session, seed)
    db_session.commit()

    sin_pin = como_rol("cajero").put(f"/pedidos/{pedido.id}", json={"estado": "cancelado"})
    assert sin_pin.status_code == 400

    con_pin = como_rol("cajero").put(
        f"/pedidos/{pedido.id}",
        json={"estado": "cancelado", "pin_autorizacion": admin_pin["pin"]},
    )
    assert con_pin.status_code == 200
    assert con_pin.json()["estado"] == "cancelado"


def test_pedido_cancelado_o_dividido_no_admite_modificaciones(como_rol, seed, db_session):
    pedido = _crear_pedido_pendiente(db_session, seed)
    pedido.estado = "cancelado"
    db_session.commit()

    r = como_rol("administrador").put(
        f"/pedidos/{pedido.id}",
        json={"estado": "cancelado", "propina_tarjeta": 20.0},
    )
    assert r.status_code == 403


def test_cambio_manual_cajero_con_pin_admin_cambia_estatus(como_rol, seed, db_session, admin_pin):
    from app.models import AutorizacionPin

    pedido = _crear_pedido_pendiente(db_session, seed)
    r = como_rol("cajero").put(
        f"/pedidos/{pedido.id}",
        json={
            "estado": "preparando",  # un cajero no podría sin override
            "cambio_manual": True,
            "pin_autorizacion": admin_pin["pin"],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "preparando"
    auth = db_session.query(AutorizacionPin).filter_by(pedido_id=pedido.id).one()
    assert auth.accion == "cambio_estatus_manual"


def test_cambio_manual_sin_pin_o_pin_malo_es_rechazado(como_rol, seed, db_session, admin_pin):
    pedido = _crear_pedido_pendiente(db_session, seed)
    cliente = como_rol("cajero")
    r = cliente.put(f"/pedidos/{pedido.id}", json={"estado": "listo", "cambio_manual": True})
    assert r.status_code == 400
    r = cliente.put(
        f"/pedidos/{pedido.id}",
        json={"estado": "listo", "cambio_manual": True, "pin_autorizacion": "0000"},
    )
    assert r.status_code == 403
    db_session.refresh(pedido)
    assert pedido.estado == "pendiente"


def test_cambio_manual_no_reabre_pedido_terminal(como_rol, seed, db_session, admin_pin):
    pedido = _crear_pedido_pendiente(db_session, seed)
    pedido.estado = "pagado"
    db_session.commit()
    r = como_rol("cajero").put(
        f"/pedidos/{pedido.id}",
        json={"estado": "pendiente", "cambio_manual": True, "pin_autorizacion": admin_pin["pin"]},
    )
    assert r.status_code == 403
