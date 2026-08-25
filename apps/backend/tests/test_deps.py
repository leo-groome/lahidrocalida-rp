"""Tests de app/deps.py: require_roles y get_turno_activo.

Se monta una app FastAPI mínima en lugar de usar `app.main.app`: las
dependencias son el objeto bajo prueba, así que los endpoints reales (que
todavía traen sus checks inline de rol, migración = tarea 1.5) solo
introducirían ruido.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.auth import get_current_active_user, get_current_user
from app.db.session import get_db
from app.deps import get_turno_activo, require_roles
from app.models import Turno, Usuario


@pytest.fixture()
def deps_app(db_engine):
    """App mínima con un endpoint por dependency bajo prueba."""
    application = FastAPI()

    @application.get("/solo-admin")
    def solo_admin(current_user: Usuario = Depends(require_roles("administrador", "cajero"))):
        return {"rol": current_user.rol}

    @application.get("/turno")
    def turno(turno_activo: Turno = Depends(get_turno_activo)):
        return {"turno_id": turno_activo.id if turno_activo else None}

    Session = sessionmaker(bind=db_engine)

    def override_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    application.dependency_overrides[get_db] = override_db
    yield application
    application.dependency_overrides.clear()


def _usuario(db_session, rol: str, sucursal_id: int, activo: bool = True) -> Usuario:
    u = Usuario(nombre=f"U-{rol}", pin="x", rol=rol, sucursal_id=sucursal_id, activo=activo)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


class TestRequireRoles:
    def test_rol_permitido_pasa(self, deps_app, db_session, seed):
        user = _usuario(db_session, "administrador", seed["sucursal"].id)
        deps_app.dependency_overrides[get_current_active_user] = lambda: user

        r = TestClient(deps_app).get("/solo-admin")

        assert r.status_code == 200
        assert r.json() == {"rol": "administrador"}

    def test_rol_no_permitido_da_403(self, deps_app, db_session, seed):
        user = _usuario(db_session, "mesero", seed["sucursal"].id)
        deps_app.dependency_overrides[get_current_active_user] = lambda: user

        r = TestClient(deps_app).get("/solo-admin")

        assert r.status_code == 403
        # El detail nombra los roles requeridos, no filtra nada interno
        assert "administrador" in r.json()["detail"]

    def test_usuario_inactivo_es_rechazado(self, deps_app, db_session, seed):
        """Se overridea get_current_user (no get_current_active_user) para que
        corra el chequeo real de `activo`.

        NOTA: `get_current_active_user` responde 400 ("Usuario inactivo"), no
        403. Ese contrato es preexistente y lo comparten todos los endpoints
        actuales; cambiarlo está fuera del scope de 1.4.
        """
        user = _usuario(db_session, "administrador", seed["sucursal"].id, activo=False)
        deps_app.dependency_overrides[get_current_user] = lambda: user

        r = TestClient(deps_app).get("/solo-admin")

        assert r.status_code == 400
        assert r.json()["detail"] == "Usuario inactivo"

    def test_sin_roles_es_error_de_programacion(self):
        with pytest.raises(ValueError):
            require_roles()


class TestGetTurnoActivo:
    def test_devuelve_turno_abierto_de_su_sucursal(self, deps_app, db_session, seed):
        turno = Turno(
            sucursal_id=seed["sucursal"].id,
            usuario_id=seed["usuario"].id,
            estado="abierto",
            total_inicial=0,
        )
        db_session.add(turno)
        db_session.commit()
        db_session.refresh(turno)

        deps_app.dependency_overrides[get_current_active_user] = lambda: seed["usuario"]
        r = TestClient(deps_app).get("/turno")

        assert r.status_code == 200
        assert r.json() == {"turno_id": turno.id}

    def test_sin_turno_abierto_devuelve_none(self, deps_app, seed):
        deps_app.dependency_overrides[get_current_active_user] = lambda: seed["usuario"]

        r = TestClient(deps_app).get("/turno")

        assert r.status_code == 200
        assert r.json() == {"turno_id": None}

    def test_no_ve_turno_de_otra_sucursal(self, deps_app, db_session, seed):
        """Aislamiento: la sucursal sale de current_user, no del request."""
        from app.models import Sucursal

        otra = Sucursal(nombre="Norte")
        db_session.add(otra)
        db_session.commit()
        db_session.add(
            Turno(
                sucursal_id=otra.id,
                usuario_id=seed["usuario"].id,
                estado="abierto",
                total_inicial=0,
            )
        )
        db_session.commit()

        deps_app.dependency_overrides[get_current_active_user] = lambda: seed["usuario"]
        r = TestClient(deps_app).get("/turno")

        assert r.status_code == 200
        assert r.json() == {"turno_id": None}
