"""
Modelo de datos del PCE. Entidades derivadas de Design.md + PRD_PCE_JorgeChavez.3 +
bitacora-de-desarrollo.md (Pasos 4-14).

Convenciones clave documentadas en la bitacora:
- Doble timestamp (ADR-2, Paso 9): `hora_evento` es la hora del dispositivo (para
  mostrar), `hora_recepcion` es server_default=now() (para auditoria y para el
  last-write-wins de Unidad, ADR-6). Un reloj de tablet desincronizado no puede
  alterar el orden de la auditoria.
- Insert-only (ADR-2 + ADR-6, Paso 8-9): Activacion, EvaluacionInicial,
  RelevoMando y MarcadorIncidente no admiten UPDATE/DELETE por API. La unica
  excepcion es la transicion Activacion.estado 'ACTIVA' -> 'CERRADA' (Paso 14),
  reforzada con un trigger de base de datos dedicado (ver alembic
  0003_relevo_activacion_y_cierre) que verifica que ningun otro campo cambie
  en el mismo UPDATE. Esto se aplica en el nivel API (routers) y se refuerza a
  nivel DB (triggers, "sin edicion retroactiva no auditada" con dos capas).
- Enums: SQLAlchemy guarda el NOMBRE del enum de Python en mayusculas
  ('ACTIVA', 'CERRADA'), no su .value en minusculas -- bug real detectado y
  corregido en el Paso 14 al comparar contra Postgres real.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# --- Enums -------------------------------------------------------------

class Rol(str, enum.Enum):
    GERENTE_SEGURIDAD = "GERENTE_SEGURIDAD"
    GERENTE_OPERACIONES = "GERENTE_OPERACIONES"
    DUTY_MANAGER = "DUTY_MANAGER"
    JEFE_RESCATE = "JEFE_RESCATE"  # Comandante de Incidente (CI)
    SUP_GRAL_RESCATE = "SUP_GRAL_RESCATE"
    SUPERVISOR_RESCATE = "SUPERVISOR_RESCATE"


# Roles habilitados para cerrar una activacion (PRD sec. 5: Coordinador del
# Plan de Emergencia y sus suplentes -- no el CI). Ver Paso 14.
ROLES_DESACTIVACION = {Rol.GERENTE_SEGURIDAD, Rol.GERENTE_OPERACIONES, Rol.DUTY_MANAGER}


class CategoriaEmergencia(str, enum.Enum):
    AERONAUTICA = "AERONAUTICA"
    EPIDEMIOLOGICA = "EPIDEMIOLOGICA"
    ESTRUCTURAL_INCIDENTE = "ESTRUCTURAL_INCIDENTE"
    MATPEL = "MATPEL"


class NivelAlerta(str, enum.Enum):
    """Nivel de activacion general, comun a las 4 categorias tras mapear su
    escala propia (PRD sec. 8). Coexiste con TipoAlerta 1-10 solo para
    Aeronautica -- no son alternativos (corregido en Paso 8)."""
    I = "I"
    II = "II"
    III = "III"


class EstadoActivacion(str, enum.Enum):
    ACTIVA = "ACTIVA"
    CERRADA = "CERRADA"


class Instancia(str, enum.Enum):
    COE = "COE"
    PMM = "PMM"


class EstadoUnidad(str, enum.Enum):
    OK = "OK"
    FUERA_SERVICIO = "FUERA_SERVICIO"
    NO_APLICA = "NO_APLICA"


class CapaMapa(str, enum.Enum):
    CUADRICULA = "CUADRICULA"
    INCIDENTE = "INCIDENTE"
    ACCESOS = "ACCESOS"
    UNIDADES = "UNIDADES"  # fase 2


# --- Usuario -------------------------------------------------------------

class Usuario(Base):
    """Roster de usuarios. Agregado en el Paso 8 (Critico #2 de la revision
    adversarial: no habia entidad de Usuario pese a que login (ADR-7) y la
    convocatoria automatica de Flujo A la necesitaban)."""
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[Rol] = mapped_column(Enum(Rol, name="rol"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# --- Activacion ------------------------------------------------------------

class Activacion(Base):
    """Insert-only salvo la transicion ACTIVA -> CERRADA (Paso 14)."""
    __tablename__ = "activacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    categoria_emergencia: Mapped[CategoriaEmergencia] = mapped_column(
        Enum(CategoriaEmergencia, name="categoria_emergencia"), nullable=False
    )
    # Escala oficial I/II/III, resultado de mapear la escala propia de cada
    # categoria (PRD sec. 8). Para MATPEL, siempre 'I' (activacion general) --
    # [Propuesto, pendiente de confirmar con el Jefe de Rescate], Paso 8.
    nivel_alerta: Mapped[NivelAlerta] = mapped_column(
        Enum(NivelAlerta, name="nivel_alerta"), nullable=False
    )
    # Solo Aeronautica: escala numerica 1-10 (`Tipo de Alerta` de los Excel
    # historicos). Coexiste con nivel_alerta, no lo reemplaza (Paso 8, Critico #3).
    tipo_alerta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Clasificacion de origen tal cual se registra hoy por categoria:
    # Epidemiologica -> EMERGENCIA/URGENCIA/CONSULTA
    # Estructural/Incidente -> ESTRUCTURAL/INCIDENTE
    # MATPEL -> una de las 9 clases UN (se guarda tal cual, sin mapeo a nivel)
    clasificacion_origen: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tipo_incidente: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[EstadoActivacion] = mapped_column(
        Enum(EstadoActivacion, name="estado_activacion"),
        nullable=False,
        default=EstadoActivacion.ACTIVA,
    )
    hora_evento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hora_recepcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    creado_por_usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)

    convocatoria: Mapped[list["ConvocatoriaMiembro"]] = relationship(back_populates="activacion")
    evaluaciones: Mapped[list["EvaluacionInicial"]] = relationship(back_populates="activacion")
    relevos: Mapped[list["RelevoMando"]] = relationship(back_populates="activacion")
    marcadores: Mapped[list["MarcadorIncidente"]] = relationship(back_populates="activacion")


class ConvocatoriaMiembro(Base):
    """Mutable (no insert-only): 'confirmado' se actualiza cuando el miembro
    confirma asistencia. No esta en la lista de registros offline insert-only
    de la bitacora."""
    __tablename__ = "convocatoria_miembro"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activacion_id: Mapped[int] = mapped_column(ForeignKey("activacion.id"), nullable=False)
    instancia: Mapped[Instancia] = mapped_column(Enum(Instancia, name="instancia"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    confirmado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hora_confirmacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    activacion: Mapped["Activacion"] = relationship(back_populates="convocatoria")
    usuario: Mapped["Usuario"] = relationship()


class EvaluacionInicial(Base):
    """Insert-only. El campo 'tipo' vive en Activacion, no aca (movido en el
    Paso 3 -- ver nota en la revision de PRD.3 seccion 4, fila desactualizada)."""
    __tablename__ = "evaluacion_inicial"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activacion_id: Mapped[int] = mapped_column(ForeignKey("activacion.id"), nullable=False)
    magnitud: Mapped[str] = mapped_column(String(64), nullable=False)
    riesgos_secundarios: Mapped[str | None] = mapped_column(Text, nullable=True)
    hora_evento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hora_recepcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    creado_por_usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)

    activacion: Mapped["Activacion"] = relationship(back_populates="evaluaciones")


class RelevoMando(Base):
    """Insert-only. `activacion_id` agregado en el Paso 14 (hueco detectado en
    FRONTEND-SPEC.md: Cadena de mando no podia filtrar por incidente sin el)."""
    __tablename__ = "relevo_mando"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activacion_id: Mapped[int] = mapped_column(ForeignKey("activacion.id"), nullable=False)
    instancia: Mapped[Instancia] = mapped_column(Enum(Instancia, name="instancia_relevo"), nullable=False)
    sale_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    entra_usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    hora_evento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hora_recepcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    creado_por_usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)

    activacion: Mapped["Activacion"] = relationship(back_populates="relevos")


class MarcadorIncidente(Base):
    """Insert-only. Coordenadas de cuadricula (mapa sin georreferenciar, v1 --
    PRD sec. 8). `sincronizado` respalda el badge de estado offline (Flujo C,
    hueco resuelto en Design.md: badge junto al marcador, no banner)."""
    __tablename__ = "marcador_incidente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activacion_id: Mapped[int] = mapped_column(ForeignKey("activacion.id"), nullable=False)
    capa: Mapped[CapaMapa] = mapped_column(Enum(CapaMapa, name="capa_mapa"), nullable=False)
    coordenada_x: Mapped[float] = mapped_column(Float, nullable=False)
    coordenada_y: Mapped[float] = mapped_column(Float, nullable=False)
    tipo: Mapped[str] = mapped_column(String(255), nullable=False)
    riesgo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sincronizado: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hora_evento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hora_recepcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    creado_por_usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)

    activacion: Mapped["Activacion"] = relationship(back_populates="marcadores")


class PrePAI(Base):
    """Plantillas de Pre-PAI (Paso 9: completada con los campos que el PRD ya
    documentaba). Versionada (`version`) segun ADR-4 (retrocompatibilidad de
    payloads offline al actualizar el PWA)."""
    __tablename__ = "pre_pai"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo_emergencia: Mapped[str] = mapped_column(String(64), nullable=False)
    nombre_escenario: Mapped[str] = mapped_column(String(255), nullable=False)
    caracterizacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimensiones_escenario: Mapped[str | None] = mapped_column(Text, nullable=True)
    riesgos: Mapped[str | None] = mapped_column(Text, nullable=True)
    recursos: Mapped[str | None] = mapped_column(Text, nullable=True)
    contactos: Mapped[str | None] = mapped_column(Text, nullable=True)
    estrategias_control: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Unidad(Base):
    """Estado de unidades SSEI (R1, R2, R8-R13, CR9). Mutable con last-write-wins
    por hora_evento (ADR-6): un reloj de tablet desincronizado no puede
    revertir una actualizacion mas reciente."""
    __tablename__ = "unidad"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    estado: Mapped[EstadoUnidad] = mapped_column(Enum(EstadoUnidad, name="estado_unidad"), nullable=False)
    hora_evento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hora_recepcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class LogAuditoria(Base):
    """Sin endpoint propio (decision de diseno, Paso 13): se alimenta via
    listeners de SQLAlchemy (app/db/audit.py), no se expone por API."""
    __tablename__ = "log_auditoria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tabla: Mapped[str] = mapped_column(String(64), nullable=False)
    registro_id: Mapped[int] = mapped_column(Integer, nullable=False)
    accion: Mapped[str] = mapped_column(String(16), nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    datos_anteriores: Mapped[str | None] = mapped_column(Text, nullable=True)
    datos_nuevos: Mapped[str | None] = mapped_column(Text, nullable=True)
