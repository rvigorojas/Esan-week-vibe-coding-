"""Estado de unidades SSEI (R1, R2, R8-R13, CR9). PATCH aplica last-write-wins
por hora_evento (ADR-6): una actualizacion con hora_evento anterior a la ya
registrada se ignora en vez de sobrescribir."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.deps import get_current_user
from app.models.models import Unidad, Usuario
from app.schemas.schemas import UnidadOut, UnidadUpdate

router = APIRouter(prefix="/unidades", tags=["unidades"])


@router.get("", response_model=list[UnidadOut])
async def listar_unidades(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Unidad).order_by(Unidad.codigo))
    return result.scalars().all()


@router.patch("/{unidad_id}", response_model=UnidadOut)
async def actualizar_unidad(
    unidad_id: int,
    body: UnidadUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    unidad = await db.get(Unidad, unidad_id)
    if unidad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada.")

    # Last-write-wins por hora_evento (ADR-6): se ignora si llega una
    # actualizacion mas vieja que el estado ya guardado.
    if body.hora_evento < unidad.hora_evento:
        return unidad

    unidad.estado = body.estado
    unidad.hora_evento = body.hora_evento
    await db.commit()
    await db.refresh(unidad)
    return unidad
