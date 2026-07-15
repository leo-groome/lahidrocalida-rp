# DATABASE_URL debe apuntar a una DB de test ANTES de cualquier import de
# app.*: app/db/session.py crea el engine al importar y app/main.py corre
# create_all(bind=engine) — sin esto los tests pegarían a Neon.
# TEST_DATABASE_URL permite correr la suite contra un Postgres local
# (docker run postgres) para validar dialecto; default: SQLite in-memory.
import os

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "sqlite://")
os.environ["DATABASE_URL"] = TEST_DB_URL

import asyncio  # noqa: E402

# websocket_manager crea un task de limpieza al importar; fuera de un event
# loop corriendo (pytest) eso truena — degradar a no-op
_orig_create_task = asyncio.create_task


def _safe_create_task(coro, **kwargs):
    try:
        return _orig_create_task(coro, **kwargs)
    except RuntimeError:
        coro.close()
        return None


asyncio.create_task = _safe_create_task

from datetime import datetime, timezone  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.auth import get_current_active_user, get_optional_current_user  # noqa: E402
from app.core import cache as cache_module  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    ArticuloPedido,
    Base,
    Pedido,
    Platillo,
    Sucursal,
    Usuario,
)


@pytest.fixture()
def db_engine():
    if TEST_DB_URL.startswith("sqlite"):
        engine = create_engine(
            TEST_DB_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(TEST_DB_URL)
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    if not TEST_DB_URL.startswith("sqlite"):
        Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def query_counter(db_engine):
    """Cuenta queries ejecutadas contra el engine de test."""
    count = {"n": 0}

    def _count(conn, cursor, statement, parameters, context, executemany):
        count["n"] += 1

    event.listen(db_engine, "before_cursor_execute", _count)
    yield count
    event.remove(db_engine, "before_cursor_execute", _count)


@pytest.fixture()
def seed(db_session):
    """Sucursal + usuario + 5 platillos + 20 pedidos con 3 artículos c/u."""
    sucursal = Sucursal(nombre="Centro")
    db_session.add(sucursal)
    db_session.flush()

    usuario = Usuario(nombre="Leo", pin="x", rol="mesero", sucursal_id=sucursal.id, activo=True)
    db_session.add(usuario)
    db_session.flush()

    platillos = [
        Platillo(nombre=f"P{i}", precio=100, categoria="c", estado="disponible", kds_name=f"P{i}")
        for i in range(5)
    ]
    db_session.add_all(platillos)
    db_session.flush()

    for n in range(20):
        pedido = Pedido(
            numero_display=f"A{n}",
            total=100,
            estado="pendiente",
            tipo_orden="aqui",
            sucursal_id=sucursal.id,
            usuario_id=usuario.id,
            fecha_creacion=datetime.now(timezone.utc),
        )
        db_session.add(pedido)
        db_session.flush()
        for a in range(3):
            db_session.add(
                ArticuloPedido(
                    pedido_id=pedido.id,
                    platillo_id=platillos[a].id,
                    cantidad=1,
                    precio_cobrado=100,
                )
            )
    db_session.commit()
    return {"sucursal": sucursal, "usuario": usuario, "platillos": platillos}


@pytest.fixture()
def client(db_engine, db_session, seed):
    Session = sessionmaker(bind=db_engine)

    def override_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = lambda: seed["usuario"]

    # Caché limpia por test para que un test no vea datos cacheados de otro
    cache_module.platillos_cache._data.clear()
    cache_module.catalogos_cache._data.clear()

    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_client(client, seed):
    """Cliente donde get_optional_current_user también resuelve al usuario
    seed — ejercita el path autenticado de GET /pedidos (no el KDS público)."""
    app.dependency_overrides[get_optional_current_user] = lambda: seed["usuario"]
    yield client
    app.dependency_overrides.pop(get_optional_current_user, None)


@pytest.fixture()
def admin_client(client, seed):
    admin = Usuario(
        id=999,
        nombre="Admin",
        pin="x",
        rol="administrador",
        sucursal_id=seed["sucursal"].id,
        activo=True,
    )
    app.dependency_overrides[get_current_active_user] = lambda: admin
    yield client
    app.dependency_overrides.clear()
