"""El fallback de comparación en texto plano fue removido de verify_password.

Un PIN guardado sin hashear (sin prefijo `$`) ya NO autentica, aunque el texto
coincida exactamente. Verificado en producción: 0 filas con PIN en claro, así
que esto no bloquea a nadie — solo cierra la puerta a que un INSERT manual o
una migración futura reintroduzcan credenciales en claro sin que nadie note.
"""

import pytest

from app.auth import get_password_hash, verify_password
from app.models import Usuario


@pytest.fixture()
def usuario_pin_plano(db_session, seed):
    usuario = Usuario(
        nombre="Legado Plano",
        pin="1234",  # texto plano a propósito
        rol="mesero",
        sucursal_id=seed["sucursal"].id,
        activo=True,
    )
    db_session.add(usuario)
    db_session.commit()
    return usuario


def test_verify_password_rechaza_texto_plano_identico():
    assert verify_password("1234", "1234") is False


@pytest.mark.parametrize("stored", ["", "1234", "admin", "no-es-un-hash", "argon2$falso"])
def test_verify_password_rechaza_cualquier_valor_sin_prefijo_hash(stored):
    assert verify_password(stored, stored) is False


def test_verify_password_sigue_aceptando_hash_valido():
    hashed = get_password_hash("1234")
    assert hashed.startswith("$")
    assert verify_password("1234", hashed) is True
    assert verify_password("4321", hashed) is False


def test_login_simple_falla_con_pin_plano_correcto(client, usuario_pin_plano):
    """El PIN enviado coincide byte a byte con lo almacenado y aun así rebota."""
    r = client.post(
        "/auth/login-simple",
        json={"user_id": str(usuario_pin_plano.id), "pin": "1234"},
    )
    assert r.status_code == 401
    assert "access_token" not in r.json()


def test_login_oauth2_falla_con_pin_plano_correcto(client, usuario_pin_plano):
    r = client.post(
        "/auth/login",
        data={"username": str(usuario_pin_plano.id), "password": "1234"},
    )
    assert r.status_code == 401


def test_asistencia_falla_con_pin_plano_correcto(client, usuario_pin_plano):
    r = client.post(
        "/auth/asistencia",
        json={"usuario_id": usuario_pin_plano.id, "pin": "1234"},
    )
    assert r.status_code == 401


def test_login_admin_falla_con_password_plano_correcto(client, db_session, seed):
    admin = Usuario(
        nombre="admin@lahidrocalida.com",
        pin="superadmin",  # texto plano a propósito
        rol="administrador",
        sucursal_id=seed["sucursal"].id,
        activo=True,
    )
    db_session.add(admin)
    db_session.commit()

    r = client.post(
        "/auth/login-admin",
        json={"email": "admin@lahidrocalida.com", "password": "superadmin"},
    )
    assert r.status_code == 401


def test_login_simple_funciona_con_pin_hasheado(client, db_session, seed):
    """Control positivo: el camino legítimo sigue vivo tras el hardening."""
    usuario = Usuario(
        nombre="Mesero Hash",
        pin=get_password_hash("5678"),
        rol="mesero",
        sucursal_id=seed["sucursal"].id,
        activo=True,
    )
    db_session.add(usuario)
    db_session.commit()

    r = client.post(
        "/auth/login-simple",
        json={"user_id": str(usuario.id), "pin": "5678"},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]
