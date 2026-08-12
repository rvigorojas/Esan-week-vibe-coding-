"""Roster de usuarios -- alimenta los selectores de convocatoria y relevo
(Flujo A y Flujo D)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.deps import get_current_user
from app.models.models import Usuario
from app.schemas.schemas import UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UsuarioOut])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Usuario).where(Usuario.activo.is_(True)))
    return result.scalars().all()
