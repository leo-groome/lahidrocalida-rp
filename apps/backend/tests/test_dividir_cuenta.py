"""POST /pedidos/{id}/dividir y /dividir_por_montos: atomicidad (S2 2.6)."""

from app.models import ArticuloPedido, Pedido


def _crear_pedido_entregado(db_session, seed, precios=(100, 100)):
    pedido = Pedido(
        numero_display="910",
        total=sum(precios),
        estado="entregado",
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
            precio_cobrado=precio,
            estado_item="entregado",
        )
        for i, precio in enumerate(precios)
    ]
    db_session.add_all(articulos)
    db_session.commit()
    for a in articulos:
        db_session.refresh(a)
    return pedido, articulos


def test_dividir_por_articulos_crea_cuentas_hijas_atomicamente(como_rol, seed, db_session):
    pedido, articulos = _crear_pedido_entregado(db_session, seed)

    r = como_rol("administrador").post(
        f"/pedidos/{pedido.id}/dividir",
        json={
            "cuentas": [
                {"items": [{"articulo_id": articulos[0].id, "cantidad": 1}]},
                {"items": [{"articulo_id": articulos[1].id, "cantidad": 1}]},
            ]
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["cuentas"]) == 2

    db_session.refresh(pedido)
    assert pedido.estado == "dividido"


def test_dividir_por_articulos_replay_idempotente(como_rol, seed, db_session):
    pedido, articulos = _crear_pedido_entregado(db_session, seed)
    payload = {
        "cuentas": [
            {"items": [{"articulo_id": articulos[0].id, "cantidad": 1}]},
            {"items": [{"articulo_id": articulos[1].id, "cantidad": 1}]},
        ],
        "client_request_id": "retry-abc",
    }
    admin = como_rol("administrador")
    r1 = admin.post(f"/pedidos/{pedido.id}/dividir", json=payload)
    assert r1.status_code == 200
    cuentas_ids_1 = sorted(c["id"] for c in r1.json()["cuentas"])

    # Reintento tras el éxito: no debe crear cuentas nuevas ni duplicar.
    r2 = admin.post(f"/pedidos/{pedido.id}/dividir", json=payload)
    assert r2.status_code == 200
    cuentas_ids_2 = sorted(c["id"] for c in r2.json()["cuentas"])
    assert cuentas_ids_1 == cuentas_ids_2


def test_dividir_por_montos_crea_cuentas_hijas(como_rol, seed, db_session):
    pedido, articulos = _crear_pedido_entregado(db_session, seed)

    r = como_rol("administrador").post(
        f"/pedidos/{pedido.id}/dividir_por_montos",
        json={"cuentas": [{"monto": "100"}, {"monto": "100"}]},
    )
    assert r.status_code == 200
    assert len(r.json()["cuentas"]) == 2

    db_session.refresh(pedido)
    assert pedido.estado == "dividido"


def test_dividir_pedido_ya_dividido_sin_cuentas_hijas_es_error(como_rol, seed, db_session):
    """Estado inconsistente (dividido sin hijas): no debe fingir éxito."""
    pedido, _articulos = _crear_pedido_entregado(db_session, seed)
    pedido.estado = "dividido"
    db_session.commit()

    r = como_rol("administrador").post(
        f"/pedidos/{pedido.id}/dividir",
        json={"cuentas": [{"items": []}]},
    )
    assert r.status_code == 400
