"""Flujo D -- Relevo de mando (tarjeta rapida de 1 accion, variante 1l /
Opcion 1D). GET soporta ?activacion_id= para la pestana "Cadena de mando"
del Flujo B (corregido en el Paso 14: RelevoMando ahora tiene activacion_id)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.deps import get_current_user
from app.models.models import Activacion, RelevoMando, Usuario
from app.schemas.schemas import RelevoMandoCreate, RelevoMandoOut

router = APIRouter(prefix="/relevos-mando", tags=["relevos-mando"])


@router.post("", response_model=RelevoMandoOut, status_code=status.HTTP_201_CREATED)
async def crear_relevo(
    body: RelevoMandoCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    activacion = await db.get(Activacion, body.activacion_id)
    if activacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activacion no encontrada.")

    relevo = RelevoMando(
        activacion_id=body.activacion_id,
        instancia=body.instancia,
        sale_usuario_id=body.sale_usuario_id,
        entra_usuario_id=body.entra_usuario_id,
        hora_evento=body.hora_evento,
        creado_por_usuario_id=usuario.id,
    )
    db.add(relevo)
    await db.commit()
    await db.refresh(relevo)
    return relevo


@router.get("", response_model=list[RelevoMandoOut])
async def listar_relevos(
    activacion_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = select(RelevoMando)
    if activacion_id is not None:
        query = query.where(RelevoMando.activacion_id == activacion_id)
    result = await db.execute(query.order_by(RelevoMando.hora_evento.asc()))
    return result.scalars().all()
