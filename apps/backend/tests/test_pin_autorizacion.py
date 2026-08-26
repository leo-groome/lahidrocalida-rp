"""PIN de administrador para acciones sensibles de caja: cancelar cuenta y
editar propina de ticket pagado (cubiertos en test_pedidos_transiciones.py),
borrar artículo desde caja, y el gate de analíticas del turno.

Borrar artículo tiene dos caminos: desde la tablet del mesero (sin PIN, solo
mientras el pedido sigue 'pendiente') o desde caja como cajero/administrador
(con PIN de un administrador activo, sin restricción de estado) — sin cajero
fijo, el control real vive ahí, no en el rol de la sesión."""

from app.models import ArticuloPedido, Pedido


def _crear_pedido_con_articulo(db_session, seed):
    pedido = Pedido(
        numero_display="901",
        total=100,
        estado="pendiente",
        tipo_orden="aqui",
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
    )
    db_session.add(pedido)
    db_session.flush()
    articulo = ArticuloPedido(
        pedido_id=pedido.id,
        platillo_id=seed["platillos"][0].id,
        cantidad=1,
        precio_cobrado=100,
    )
    db_session.add(articulo)
    db_session.commit()
    db_session.refresh(pedido)
    db_session.refresh(articulo)
    return pedido, articulo


def test_mesero_borra_articulo_de_pedido_pendiente_sin_pin(como_rol, seed, db_session, admin_pin):
    pedido, articulo = _crear_pedido_con_articulo(db_session, seed)

    r = como_rol("mesero").put(
        f"/pedidos/{pedido.id}/actualizar-articulos",
        json={"articulos": [{"id": articulo.id, "cantidad": 0}]},
    )
    assert r.status_code == 200
    assert r.json()["articulos_pedido"] == []


def test_mesero_no_puede_borrar_articulo_fuera_de_pendiente(como_rol, seed, db_session, admin_pin):
    pedido, articulo = _crear_pedido_con_articulo(db_session, seed)
    pedido.estado = "preparando"
    db_session.commit()

    r = como_rol("mesero").put(
        f"/pedidos/{pedido.id}/actualizar-articulos",
        json={"articulos": [{"id": articulo.id, "cantidad": 0}]},
    )
    assert r.status_code == 403


def test_editar_cantidad_sin_borrar_no_pide_pin(como_rol, seed, db_session, admin_pin):
    pedido, articulo = _crear_pedido_con_articulo(db_session, seed)

    r = como_rol("mesero").put(
        f"/pedidos/{pedido.id}/actualizar-articulos",
        json={"articulos": [{"id": articulo.id, "cantidad": 3}]},
    )
    assert r.status_code == 200
    assert r.json()["articulos_pedido"][0]["cantidad"] == 3


def test_cajero_borrar_articulo_sin_pin_es_rechazado(como_rol, seed, db_session, admin_pin):
    pedido, articulo = _crear_pedido_con_articulo(db_session, seed)

    r = como_rol("cajero").put(
        f"/pedidos/{pedido.id}/actualizar-articulos",
        json={"articulos": [{"id": articulo.id, "cantidad": 0}]},
    )
    assert r.status_code == 400


def test_cajero_borrar_articulo_con_pin_de_admin_funciona(como_rol, seed, db_session, admin_pin):
    pedido, articulo = _crear_pedido_con_articulo(db_session, seed)

    r = como_rol("cajero").put(
        f"/pedidos/{pedido.id}/actualizar-articulos",
        json={
            "articulos": [{"id": articulo.id, "cantidad": 0}],
            "pin_autorizacion": admin_pin["pin"],
        },
    )
    assert r.status_code == 200
    assert r.json()["articulos_pedido"] == []


def test_cajero_borra_articulo_de_pedido_no_pendiente_con_pin(como_rol, seed, db_session, admin_pin):
    """A diferencia del mesero, cajero/admin no tienen la restricción de
    estado 'pendiente' — solo necesitan el PIN."""
    pedido, articulo = _crear_pedido_con_articulo(db_session, seed)
    pedido.estado = "preparando"
    db_session.commit()

    r = como_rol("cajero").put(
        f"/pedidos/{pedido.id}/actualizar-articulos",
        json={
            "articulos": [{"id": articulo.id, "cantidad": 0}],
            "pin_autorizacion": admin_pin["pin"],
        },
    )
    assert r.status_code == 200


def test_cajero_borrar_articulo_con_pin_incorrecto_es_rechazado(como_rol, seed, db_session, admin_pin):
    pedido, articulo = _crear_pedido_con_articulo(db_session, seed)

    r = como_rol("cajero").put(
        f"/pedidos/{pedido.id}/actualizar-articulos",
        json={
            "articulos": [{"id": articulo.id, "cantidad": 0}],
            "pin_autorizacion": "0000",
        },
    )
    assert r.status_code == 401


def test_verify_admin_pin_con_pin_correcto(client, admin_pin):
    r = client.post("/auth/verify-admin-pin", json={"pin": admin_pin["pin"]})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_verify_admin_pin_con_pin_incorrecto(client, admin_pin):
    r = client.post("/auth/verify-admin-pin", json={"pin": "0000"})
    assert r.status_code == 401


def test_verify_admin_pin_sin_administradores_activos(client):
    r = client.post("/auth/verify-admin-pin", json={"pin": "1234"})
    assert r.status_code == 401


def test_pin_incorrecto_repetido_dispara_rate_limit(client, admin_pin):
    """Un PIN de 4 dígitos sin límite de intentos es fuerza-bruta trivial
    (10 000 combinaciones) para cualquiera con un JWT de mesero/cajero
    válido — debe cortar igual que el rate limit de login."""
    for _ in range(8):
        r = client.post("/auth/verify-admin-pin", json={"pin": "0000"})
        assert r.status_code == 401

    r = client.post("/auth/verify-admin-pin", json={"pin": "0000"})
    assert r.status_code == 429

    # Ni siquiera el PIN correcto pasa mientras el presupuesto está agotado
    r = client.post("/auth/verify-admin-pin", json={"pin": admin_pin["pin"]})
    assert r.status_code == 429
