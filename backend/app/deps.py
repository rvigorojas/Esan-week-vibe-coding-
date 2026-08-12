"""Dependencias compartidas: sesion de DB, usuario autenticado, control de
acceso por rol."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SoftTokenExpired, TokenInvalid, decode_token
from app.db.base import get_db
from app.models.models import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    try:
        payload = decode_token(token)
    except SoftTokenExpired:
        # Token blando (ADR-7): vencido pero dentro de la ventana de gracia
        # offline -- se acepta igual. El cliente deberia refrescar el token
        # en cuanto recupere conexion. decode_token ya valido la firma; solo
        # nos falta el payload sin la verificacion de 'exp'.
        from jose import jwt as _jwt

        from app.core.config import settings as _settings

        payload = _jwt.decode(
            token,
            _settings.jwt_secret,
            algorithms=[_settings.jwt_algorithm],
            options={"verify_exp": False},
        )
    except TokenInvalid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o vencido fuera de la ventana de gracia offline.",
        )

    usuario_id = int(payload["sub"])
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if usuario is None or not usuario.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario invalido.")
    return usuario


def require_roles(*roles):
    async def checker(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Rol sin permiso para esta accion.",
            )
        return usuario

    return checker
