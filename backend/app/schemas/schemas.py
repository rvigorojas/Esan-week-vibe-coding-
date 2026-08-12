"""Schemas Pydantic para request/response. Un archivo por simplicidad de
scaffold; en un repo real conviene separarlos por dominio."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.models import (
    CapaMapa,
    CategoriaEmergencia,
    EstadoActivacion,
    EstadoUnidad,
    Instancia,
    NivelAlerta,
    Rol,
)


# --- Auth --------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: Rol
    usuario_id: int


# --- Usuario -------------------------------------------------------------

class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    nombre_completo: str
    rol: Rol
    activo: bool


# --- Activacion ------------------------------------------------------------

class ConvocatoriaMiembroIn(BaseModel):
    instancia: Instancia
    usuario_id: int


class ActivacionCreate(BaseModel):
    categoria_emergencia: CategoriaEmergencia
    nivel_alerta: NivelAlerta
    tipo_alerta: int | None = None
    clasificacion_origen: str | None = None
    tipo_incidente: str
    hora_evento: datetime
    convocatoria: list[ConvocatoriaMiembroIn] = []


class ConvocatoriaMiembroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    instancia: Instancia
    usuario_id: int
    confirmado: bool
    hora_confirmacion: datetime | None


class ActivacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    categoria_emergencia: CategoriaEmergencia
    nivel_alerta: NivelAlerta
    tipo_alerta: int | None
    clasificacion_origen: str | None
    tipo_incidente: str
    estado: EstadoActivacion
    hora_evento: datetime
    hora_recepcion: datetime
    creado_por_usuario_id: int


class ConvocatoriaConfirmar(BaseModel):
    hora_evento: datetime


# --- Evaluacion inicial ----------------------------------------------------

class EvaluacionInicialCreate(BaseModel):
    magnitud: str
    riesgos_secundarios: str | None = None
    hora_evento: datetime


class EvaluacionInicialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    activacion_id: int
    magnitud: str
    riesgos_secundarios: str | None
    hora_evento: datetime
    hora_recepcion: datetime


# --- Relevo de mando ---------------------------------------------------

class RelevoMandoCreate(BaseModel):
    activacion_id: int
    instancia: Instancia
    sale_usuario_id: int | None = None
    entra_usuario_id: int
    hora_evento: datetime


class RelevoMandoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    activacion_id: int
    instancia: Instancia
    sale_usuario_id: int | None
    entra_usuario_id: int
    hora_evento: datetime
    hora_recepcion: datetime


# --- Marcador de incidente (mapa) ---------------------------------------

class MarcadorIncidenteCreate(BaseModel):
    activacion_id: int
    capa: CapaMapa
    coordenada_x: float
    coordenada_y: float
    tipo: str
    riesgo: str | None = None
    sincronizado: bool = True
    hora_evento: datetime


class MarcadorIncidenteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    activacion_id: int
    capa: CapaMapa
    coordenada_x: float
    coordenada_y: float
    tipo: str
    riesgo: str | None
    sincronizado: bool
    hora_evento: datetime
    hora_recepcion: datetime


# --- Pre-PAI -------------------------------------------------------------

class PrePAIOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tipo_emergencia: str
    nombre_escenario: str
    caracterizacion: str | None
    dimensiones_escenario: str | None
    riesgos: str | None
    recursos: str | None
    contactos: str | None
    estrategias_control: str | None
    version: int


# --- Unidad --------------------------------------------------------------

class UnidadUpdate(BaseModel):
    estado: EstadoUnidad
    hora_evento: datetime


class UnidadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codigo: str
    estado: EstadoUnidad
    hora_evento: datetime
    hora_recepcion: datetime
