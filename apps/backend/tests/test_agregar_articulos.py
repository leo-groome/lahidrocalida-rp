"""PUT /pedidos/{id}/agregar-articulos: UniqueConstraint + IntegrityError (S2 2.7)."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import ArticuloPedido, Pedido


def _crear_pedido_pendiente(db_session, seed):
    pedido = Pedido(
        numero_display="920",
        total=0,
        estado="pendiente",
        tipo_orden="aqui",
        sucursal_id=seed["sucursal"].id,
        usuario_id=seed["usuario"].id,
    )
    db_session.add(pedido)
    db_session.commit()
    db_session.refresh(pedido)
    return pedido


def test_batch_de_varios_articulos_con_mismo_client_request_id_no_colisiona(
    como_rol, seed, db_session
):
    """El índice dentro del batch (":<i>") evita que 2+ artículos del MISMO
    request con el MISMO client_request_id violen la unicidad entre sí."""
    pedido = _crear_pedido_pendiente(db_session, seed)
    r = como_rol("mesero").put(
        f"/pedidos/{pedido.id}/agregar-articulos",
        json={
            "articulos": [
                {"platillo_id": seed["platillos"][0].id, "cantidad": 1},
                {"platillo_id": seed["platillos"][1].id, "cantidad": 1},
                {"platillo_id": seed["platillos"][2].id, "cantidad": 1},
            ],
            "client_request_id": "batch-1",
        },
    )
    assert r.status_code == 200
    articulos = db_session.query(ArticuloPedido).filter(ArticuloPedido.pedido_id == pedido.id).all()
    assert len(articulos) == 3
    assert {a.client_request_id for a in articulos} == {"batch-1:0", "batch-1:1", "batch-1:2"}


def test_replay_con_mismo_client_request_id_no_duplica(como_rol, seed, db_session):
    pedido = _crear_pedido_pendiente(db_session, seed)
    payload = {
        "articulos": [{"platillo_id": seed["platillos"][0].id, "cantidad": 2}],
        "client_request_id": "batch-2",
    }
    mesero = como_rol("mesero")
    r1 = mesero.put(f"/pedidos/{pedido.id}/agregar-articulos", json=payload)
    assert r1.status_code == 200

    r2 = mesero.put(f"/pedidos/{pedido.id}/agregar-articulos", json=payload)
    assert r2.status_code == 200

    articulos = db_session.query(ArticuloPedido).filter(ArticuloPedido.pedido_id == pedido.id).all()
    assert len(articulos) == 1  # no se duplicó


def test_constraint_rechaza_fila_duplicada_a_nivel_db(db_session, seed):
    """La unicidad es real a nivel de DB, no solo un chequeo de aplicación:
    dos filas con el mismo (pedido_id, client_request_id) deben violarla."""
    pedido = _crear_pedido_pendiente(db_session, seed)
    db_session.add(
        ArticuloPedido(
            pedido_id=pedido.id,
            platillo_id=seed["platillos"][0].id,
            cantidad=1,
            precio_cobrado=100,
            client_request_id="dup:0",
        )
    )
    db_session.commit()

    db_session.add(
        ArticuloPedido(
            pedido_id=pedido.id,
            platillo_id=seed["platillos"][1].id,
            cantidad=1,
            precio_cobrado=100,
            client_request_id="dup:0",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
