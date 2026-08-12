"""
Log de auditoria (LogAuditoria). No hay endpoint que lo exponga (decision de
diseno, Paso 13 de la bitacora): el feed de "ultimos eventos" del Resumen COE
se arma combinando los endpoints de dominio ya consumidos, no leyendo esta
tabla directamente.

Este modulo escucha 'after_insert' en las tablas offline insert-only y
'after_update' en Activacion (transicion activa -> cerrada) y Unidad
(cambios de estado), y escribe una fila en log_auditoria por cada evento.
Se engancha en app/main.py al arrancar la app.
"""
import json
from datetime import datetime, timezone

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.models import (
    Activacion,
    EvaluacionInicial,
    LogAuditoria,
    MarcadorIncidente,
    RelevoMando,
    Unidad,
)

_AUDITED_INSERT_MODELS = (Activacion, EvaluacionInicial, RelevoMando, MarcadorIncidente)


def _to_jsonable(obj) -> dict:
    data = {}
    for col in obj.__table__.columns:
        value = getattr(obj, col.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        data[col.name] = value
    return data


def _record(session: Session, tabla: str, registro_id, accion: str, usuario_id, anterior, nuevo):
    entry = LogAuditoria(
        tabla=tabla,
        registro_id=registro_id,
        accion=accion,
        usuario_id=usuario_id,
        hora=datetime.now(timezone.utc),
        datos_anteriores=json.dumps(anterior) if anterior is not None else None,
        datos_nuevos=json.dumps(nuevo) if nuevo is not None else None,
    )
    session.add(entry)


def register_audit_listeners():
    for model in _AUDITED_INSERT_MODELS:

        def after_insert(mapper, connection, target, _model=model):
            session = Session.object_session(target)
            if session is None:
                return
            _record(
                session,
                tabla=_model.__tablename__,
                registro_id=target.id,
                accion="insert",
                usuario_id=getattr(target, "creado_por_usuario_id", None),
                anterior=None,
                nuevo=_to_jsonable(target),
            )

        event.listen(model, "after_insert", after_insert)

    def activacion_after_update(mapper, connection, target: Activacion):
        session = Session.object_session(target)
        if session is None:
            return
        _record(
            session,
            tabla="activacion",
            registro_id=target.id,
            accion="update",
            usuario_id=None,
            anterior=None,
            nuevo=_to_jsonable(target),
        )

    event.listen(Activacion, "after_update", activacion_after_update)

    def unidad_after_update(mapper, connection, target: Unidad):
        session = Session.object_session(target)
        if session is None:
            return
        _record(
            session,
            tabla="unidad",
            registro_id=target.id,
            accion="update",
            usuario_id=None,
            anterior=None,
            nuevo=_to_jsonable(target),
        )

    event.listen(Unidad, "after_update", unidad_after_update)
