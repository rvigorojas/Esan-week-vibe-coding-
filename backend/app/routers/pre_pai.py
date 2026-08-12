"""Biblioteca de Pre-PAI -- activables por tipo de escenario. Solo lectura
por API (las plantillas se cargan por seed/migracion, no por endpoint de
escritura en este scaffold)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.deps import get_current_user
from app.models.models import PrePAI, Usuario
from app.schemas.schemas import PrePAIOut

router = APIRouter(prefix="/pre-pai", tags=["pre-pai"])


@router.get("", response_model=list[PrePAIOut])
async def listar_pre_pai(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(PrePAI))
    return result.scalars().all()


@router.get("/{pre_pai_id}", response_model=PrePAIOut)
async def obtener_pre_pai(
    pre_pai_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    pre_pai = await db.get(PrePAI, pre_pai_id)
    if pre_pai is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pre-PAI no encontrado.")
    return pre_pai
