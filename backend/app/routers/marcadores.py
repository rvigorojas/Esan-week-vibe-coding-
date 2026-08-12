"""Flujo C -- Mapa geoespacial (marcador de incidente). Coordenadas de
cuadricula, sin georreferenciar (v1, PRD sec. 8). El campo `sincronizado`
respalda el badge de estado offline junto al marcador."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.deps import get_current_user
from app.models.models import MarcadorIncidente, Usuario
from app.schemas.schemas import MarcadorIncidenteCreate, MarcadorIncidenteOut

router = APIRouter(prefix="/marcadores-incidente", tags=["marcadores-incidente"])


@router.post("", response_model=MarcadorIncidenteOut, status_code=201)
async def crear_marcador(
    body: MarcadorIncidenteCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    marcador = MarcadorIncidente(
        activacion_id=body.activacion_id,
        capa=body.capa,
        coordenada_x=body.coordenada_x,
        coordenada_y=body.coordenada_y,
        tipo=body.tipo,
        riesgo=body.riesgo,
        sincronizado=body.sincronizado,
        hora_evento=body.hora_evento,
        creado_por_usuario_id=usuario.id,
    )
    db.add(marcador)
    await db.commit()
    await db.refresh(marcador)
    return marcador


@router.get("", response_model=list[MarcadorIncidenteOut])
async def listar_marcadores(
    activacion_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = select(MarcadorIncidente)
    if activacion_id is not None:
        query = query.where(MarcadorIncidente.activacion_id == activacion_id)
    result = await db.execute(query)
    return result.scalars().all()
