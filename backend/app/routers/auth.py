"""Login unico para COE y PMM -- el rol define permisos, no la pantalla
(Tablet_app_structures.pptx, Opcion 1F). Funciona offline si ya se inicio
sesion antes (el token queda en el cliente; ver token blando en core/security.py)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.db.base import get_db
from app.models.models import Usuario
from app.schemas.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.username == body.username))
    usuario = result.scalar_one_or_none()
    if usuario is None or not usuario.activo or not verify_password(body.password, usuario.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas.")

    token = create_access_token(usuario.id, usuario.rol.value)
    return TokenResponse(access_token=token, rol=usuario.rol, usuario_id=usuario.id)
