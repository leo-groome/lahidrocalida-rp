"""Regresiones con locks reales; SQLite no representa estas carreras."""

import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.models import Gasto, GastoAdjunto, Pedido, Turno, Usuario
from app.routers.gasto_adjuntos import subir_adjunto
from app.routers.gastos import create_gasto
from app.routers.pedidos import update_pedido
from app.routers.turnos import cerrar_turno
from app.schemas import GastoCreate, PedidoUpdate, TurnoCierreRequest
from app.services.storage import LocalStorage


def postgres(db_engine):
    if db_engine.dialect.name != "postgresql":
        pytest.skip("Requiere TEST_DATABASE_URL PostgreSQL desechable")


def test_creacion_concurrente_no_duplica(db_engine, seed):
    postgres(db_engine)
    factory = sessionmaker(bind=db_engine)
    barrier = Barrier(2)
    payload = GastoCreate(
        client_request_id=uuid4(), tipo_gasto="directo", metodo_pago="efectivo", total_manual=100
    )

    def create():
        with factory() as db:
            user = db.get(Usuario, seed["usuario"].id)
            barrier.wait(timeout=10)
            return create_gasto(payload, db, user).id

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _: create(), range(2)))
    assert ids[0] == ids[1]
    with factory() as db:
        assert db.query(Gasto).count() == 1


def test_cuota_adjuntos_es_atomica(db_engine, seed, tmp_path):
    postgres(db_engine)
    factory = sessionmaker(bind=db_engine)
    with factory() as db:
        gasto = Gasto(
            tipo_gasto="directo",
            metodo_pago="efectivo",
            subtotal=100,
            total=100,
            sucursal_id=seed["sucursal"].id,
        )
        db.add(gasto)
        db.commit()
        gasto_id = gasto.id
    output = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(output, "JPEG")
    barrier = Barrier(6)

    def upload():
        with factory() as db:
            user = db.get(Usuario, seed["usuario"].id)
            barrier.wait(timeout=10)
            try:
                asyncio.run(
                    subir_adjunto(
                        gasto_id,
                        UploadFile(io.BytesIO(output.getvalue())),
                        uuid4(),
                        db,
                        user,
                        LocalStorage(str(tmp_path)),
                    )
                )
                return 201
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=6) as pool:
        codes = list(pool.map(lambda _: upload(), range(6)))
    assert sorted(codes) == [201, 201, 201, 201, 201, 400]
    with factory() as db:
        assert db.query(GastoAdjunto).count() == 5


def test_cierre_concurrente_con_entrega_no_pierde_uber(db_engine, seed):
    postgres(db_engine)
    factory = sessionmaker(bind=db_engine)
    with factory() as db:
        turno = Turno(
            sucursal_id=seed["sucursal"].id,
            usuario_id=seed["usuario"].id,
            estado="abierto",
            total_inicial=Decimal("500"),
        )
        db.add(turno)
        db.flush()
        pedido = Pedido(
            numero_display="UC1",
            tipo_orden="uber_eats",
            estado="listo",
            total=250,
            sucursal_id=seed["sucursal"].id,
            usuario_id=seed["usuario"].id,
            turno_id=turno.id,
        )
        db.add(pedido)
        db.commit()
        tid, pid = turno.id, pedido.id
    barrier = Barrier(2)

    def deliver():
        with factory() as db:
            user = db.get(Usuario, seed["usuario"].id)
            user.rol = "administrador"
            barrier.wait(timeout=10)
            try:
                asyncio.run(
                    update_pedido(
                        pid,
                        PedidoUpdate(estado="entregado_repartidor"),
                        Request({"type": "http"}),
                        db,
                        user,
                    )
                )
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    def close():
        with factory() as db:
            user = db.get(Usuario, seed["usuario"].id)
            user.rol = "administrador"
            barrier.wait(timeout=10)
            return cerrar_turno(
                tid,
                TurnoCierreRequest(
                    conteo_final={"denominaciones": [{"denominacion": 100, "cantidad": 5}]}
                ),
                db,
                user,
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(deliver)
        b = pool.submit(close)
        code = a.result(timeout=15)
        b.result(timeout=15)
    with factory() as db:
        turno = db.get(Turno, tid)
        pedido = db.get(Pedido, pid)
        assert turno.estado == "cerrado"
        if code == 200:
            assert pedido.estado == "entregado_repartidor"
            assert turno.pedidos_uber == 1 and turno.ventas_uber == 250
        else:
            assert code == 409
            assert pedido.estado == "listo"
            assert turno.pedidos_uber == 0 and turno.ventas_uber == 0
