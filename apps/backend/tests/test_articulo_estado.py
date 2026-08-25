"""PUT /pedidos/articulos/{id}: un solo commit, lock de pedido (S2 2.5)."""

from app.models import ArticuloPedido, Pedido


def _crear_pedido_preparando(db_session, seed, n_articulos=2):
    pedido = Pedido(
        numero_display="901",
        total=200,
        estado="preparando",
        tipo_orden="aqui",
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
    )
    db_session.add(pedido)
    db_session.flush()
    articulos = [
        ArticuloPedido(
            pedido_id=pedido.id,
            platillo_id=seed["platillos"][i].id,
            cantidad=1,
            precio_cobrado=100,
            estado_item="preparando",
        )
        for i in range(n_articulos)
    ]
    db_session.add_all(articulos)
    db_session.commit()
    for a in articulos:
        db_session.refresh(a)
    return pedido, articulos


def test_marcar_ultimo_articulo_listo_pasa_pedido_a_listo(como_rol, seed, db_session):
    pedido, articulos = _crear_pedido_preparando(db_session, seed, n_articulos=2)

    r1 = como_rol("cocina").put(
        f"/pedidos/articulos/{articulos[0].id}", json={"estado_item": "listo"}
    )
    assert r1.status_code == 200
    assert r1.json()["pedido_estado"] == "preparando"  # falta el segundo artículo

    r2 = como_rol("cocina").put(
        f"/pedidos/articulos/{articulos[1].id}", json={"estado_item": "listo"}
    )
    assert r2.status_code == 200
    assert r2.json()["pedido_estado"] == "listo"


def test_articulo_entregado_tambien_cuenta_como_completado(como_rol, seed, db_session):
    pedido, articulos = _crear_pedido_preparando(db_session, seed, n_articulos=2)
    articulos[0].estado_item = "entregado"
    db_session.commit()

    r = como_rol("cocina").put(
        f"/pedidos/articulos/{articulos[1].id}", json={"estado_item": "listo"}
    )
    assert r.status_code == 200
    assert r.json()["pedido_estado"] == "listo"


def test_pedido_no_pasa_a_listo_si_no_estaba_preparando(como_rol, seed, db_session):
    pedido, articulos = _crear_pedido_preparando(db_session, seed, n_articulos=1)
    pedido.estado = "pendiente"
    db_session.commit()

    r = como_rol("cocina").put(
        f"/pedidos/articulos/{articulos[0].id}", json={"estado_item": "listo"}
    )
    assert r.status_code == 200
    assert r.json()["pedido_estado"] == "pendiente"


def test_articulo_inexistente_404(como_rol):
    r = como_rol("cocina").put("/pedidos/articulos/999999", json={"estado_item": "listo"})
    assert r.status_code == 404


def test_estado_item_invalido_400(como_rol, seed, db_session):
    pedido, articulos = _crear_pedido_preparando(db_session, seed, n_articulos=1)
    r = como_rol("cocina").put(
        f"/pedidos/articulos/{articulos[0].id}", json={"estado_item": "no-existe"}
    )
    assert r.status_code == 400
