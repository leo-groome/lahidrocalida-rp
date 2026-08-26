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
