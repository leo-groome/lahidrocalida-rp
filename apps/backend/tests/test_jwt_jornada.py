"""JWT con claim `jornada`: un token cuya jornada ya no coincide con la
jornada actual se rechaza en el próximo request — sin cron, sin blacklist,
solo comparación en vivo contra `jornada_de(now())`. Tokens legado sin el
claim (emitidos antes de S3) se siguen aceptando. `sesiones_validas_desde`
permite revocar selectivamente sin esperar a que el token expire.
"""

from datetime import datetime, timedelta

from jose import jwt

from app.auth import ALGORITHM, SECRET_KEY, _resolve_user_from_token, create_access_token
from app.utils.timezone import get_mexico_now, jornada_de


def _token_con_jornada(usuario_id: int, jornada: str) -> str:
    payload = {
        "sub": str(usuario_id),
        "jornada": jornada,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=30),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def test_create_access_token_lleva_jornada_e_iat():
    token = create_access_token(data={"sub": "1"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["jornada"] == jornada_de(get_mexico_now()).isoformat()
    assert "iat" in payload


def test_token_con_jornada_distinta_se_rechaza(db_session, seed):
    token = _token_con_jornada(seed["usuario"].id, "2000-01-01")
    assert _resolve_user_from_token(token, db_session) is None


def test_token_con_jornada_actual_se_acepta(db_session, seed):
    jornada_actual = jornada_de(get_mexico_now()).isoformat()
    token = _token_con_jornada(seed["usuario"].id, jornada_actual)
    user = _resolve_user_from_token(token, db_session)
    assert user is not None
    assert user.id == seed["usuario"].id


def test_token_legacy_sin_claim_jornada_se_acepta(db_session, seed):
    payload = {
        "sub": str(seed["usuario"].id),
        "exp": datetime.utcnow() + timedelta(minutes=30),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    user = _resolve_user_from_token(token, db_session)
    assert user is not None


def test_sesion_revocada_selectivamente_se_rechaza(db_session, seed):
    jornada_actual = jornada_de(get_mexico_now()).isoformat()
    token = _token_con_jornada(seed["usuario"].id, jornada_actual)

    seed["usuario"].sesiones_validas_desde = get_mexico_now() + timedelta(minutes=5)
    db_session.commit()

    assert _resolve_user_from_token(token, db_session) is None


def test_sesion_emitida_despues_de_la_revocacion_se_acepta(db_session, seed):
    seed["usuario"].sesiones_validas_desde = get_mexico_now() - timedelta(minutes=5)
    db_session.commit()

    jornada_actual = jornada_de(get_mexico_now()).isoformat()
    token = _token_con_jornada(seed["usuario"].id, jornada_actual)

    user = _resolve_user_from_token(token, db_session)
    assert user is not None
