"""
Flujo A (activacion) + evaluacion inicial del CI (informe al COE).

Reglas de negocio clave documentadas en la bitacora:
- Activacion es insert-only salvo /desactivar (Paso 14).
- /desactivar restringido a ROLES_DESACTIVACION (Coordinador del Plan de
  Emergencia y suplentes -- Gerente de Seguridad, Gerente de Operaciones,
  Duty Manager -- no el CI). PRD sec. 5.
- MATPEL: convocatoria fijada como "siempre activacion general"
  [Propuesto, pendiente de confirmar con el Jefe de Rescate] -- no tiene
  mapeo propio a nivel de activacion (Paso 8, Critico #4). Se fuerza
  nivel_alerta=I si no viene explicito.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.deps import get_current_user, require_roles
from app.models.models import (
    Activacion,
    CategoriaEmergencia,
    ConvocatoriaMiembro,
    EstadoActivacion,
    EvaluacionInicial,
    NivelAlerta,
    ROLES_DESACTIVACION,
    Usuario,
)
from app.schemas.schemas import (
    ActivacionCreate,
    ActivacionOut,
    ConvocatoriaConfirmar,
    ConvocatoriaMiembroOut,
    EvaluacionInicialCreate,
    EvaluacionInicialOut,
)

router = APIRouter(prefix="/activaciones", tags=["activaciones"])


@router.post("", response_model=ActivacionOut, status_code=status.HTTP_201_CREATED)
async def crear_activacion(
    body: ActivacionCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    nivel_alerta = body.nivel_alerta
    if body.categoria_emergencia == CategoriaEmergencia.MATPEL:
        # Criterio conservador (Paso 8): sin datos reales para una escala
        # diferenciada -- siempre activacion general.
        nivel_alerta = NivelAlerta.I

    activacion = Activacion(
        categoria_emergencia=body.categoria_emergencia,
        nivel_alerta=nivel_alerta,
        tipo_alerta=body.tipo_alerta if body.categoria_emergencia == CategoriaEmergencia.AERONAUTICA else None,
        clasificacion_origen=body.clasificacion_origen,
        tipo_incidente=body.tipo_incidente,
        hora_evento=body.hora_evento,
        creado_por_usuario_id=usuario.id,
    )
    db.add(activacion)
    await db.flush()

    for miembro in body.convocatoria:
        db.add(
            ConvocatoriaMiembro(
                activacion_id=activacion.id,
                instancia=miembro.instancia,
                usuario_id=miembro.usuario_id,
            )
        )

    await db.commit()
    await db.refresh(activacion)
    return activacion


@router.get("", response_model=list[ActivacionOut])
async def listar_activaciones(
    estado: EstadoActivacion | None = None,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = select(Activacion)
    if estado is not None:
        query = query.where(Activacion.estado == estado)
    result = await db.execute(query.order_by(Activacion.hora_evento.desc()))
    return result.scalars().all()


@router.get("/{activacion_id}", response_model=ActivacionOut)
async def obtener_activacion(
    activacion_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    activacion = await db.get(Activacion, activacion_id)
    if activacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activacion no encontrada.")
    return activacion


@router.post("/{activacion_id}/desactivar", response_model=ActivacionOut)
async def desactivar_activacion(
    activacion_id: int,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(require_roles(*ROLES_DESACTIVACION)),
):
    activacion = await db.get(Activacion, activacion_id)
    if activacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activacion no encontrada.")
    if activacion.estado == EstadoActivacion.CERRADA:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La activacion ya esta cerrada.")

    # Unico UPDATE permitido sobre Activacion -- el trigger de DB (migracion
    # 0003) verifica ademas que ningun otro campo cambie en este mismo UPDATE.
    activacion.estado = EstadoActivacion.CERRADA
    await db.commit()
    await db.refresh(activacion)
    return activacion


@router.get("/{activacion_id}/convocatoria", response_model=list[ConvocatoriaMiembroOut])
async def listar_convocatoria(
    activacion_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(ConvocatoriaMiembro).where(ConvocatoriaMiembro.activacion_id == activacion_id)
    )
    return result.scalars().all()


@router.post("/convocatoria/{miembro_id}/confirmar", response_model=ConvocatoriaMiembroOut)
async def confirmar_convocatoria(
    miembro_id: int,
    body: ConvocatoriaConfirmar,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    miembro = await db.get(ConvocatoriaMiembro, miembro_id)
    if miembro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado.")
    miembro.confirmado = True
    miembro.hora_confirmacion = body.hora_evento
    await db.commit()
    await db.refresh(miembro)
    return miembro


@router.post(
    "/{activacion_id}/evaluacion-inicial",
    response_model=EvaluacionInicialOut,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_evaluacion_inicial(
    activacion_id: int,
    body: EvaluacionInicialCreate,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    activacion = await db.get(Activacion, activacion_id)
    if activacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activacion no encontrada.")

    evaluacion = EvaluacionInicial(
        activacion_id=activacion_id,
        magnitud=body.magnitud,
        riesgos_secundarios=body.riesgos_secundarios,
        hora_evento=body.hora_evento,
        creado_por_usuario_id=usuario.id,
    )
    db.add(evaluacion)
    await db.commit()
    await db.refresh(evaluacion)
    return evaluacion


@router.get("/{activacion_id}/evaluacion-inicial", response_model=list[EvaluacionInicialOut])
async def listar_evaluaciones(
    activacion_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(EvaluacionInicial).where(EvaluacionInicial.activacion_id == activacion_id)
    )
    return result.scalars().all()
