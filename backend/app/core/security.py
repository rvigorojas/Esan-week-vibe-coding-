"""
JWT con mecanismo de "token blando" (ADR-7, Paso 8 de la bitacora):
el cliente PMM puede seguir encolando acciones offline con un token ya
vencido, mientras la desincronizacion no supere jwt_soft_token_grace_hours.
Al reconectar y reenviar la cola, el backend acepta el token si esta dentro
de esa ventana de gracia (soft-expired), y lo rechaza fuera de ella.

Nota (hueco 6.4, aun pendiente de decision con Renzo): si el token ya vencio
*antes* de que el dispositivo perdiera conexion (no durante), el backend igual
lo acepta dentro de la ventana de gracia porque hoy no distinguimos ambos casos.
"""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(usuario_id: int, rol: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class SoftTokenExpired(Exception):
    """Token vencido pero aun dentro de la ventana de gracia offline."""


class TokenInvalid(Exception):
    pass


def decode_token(token: str) -> dict:
    """
    Decodifica el token SIN validar 'exp' automaticamente (para poder aplicar
    la ventana de gracia nosotros mismos), y luego valida la expiracion a mano.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
    except JWTError:
        raise TokenInvalid()

    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)

    if now <= exp:
        return payload

    grace_limit = exp + timedelta(hours=settings.jwt_soft_token_grace_hours)
    if now <= grace_limit:
        raise SoftTokenExpired()

    raise TokenInvalid()
