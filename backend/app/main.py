"""
PCE -- Puesto de Comando y Administracion de Emergencias (SSEI, AIJC).
Backend FastAPI, reconstruido a partir de Design.md, PRD_PCE_JorgeChavez.3 y
bitacora-de-desarrollo.md.

NOTA: este scaffold reconstruye el backend descrito en la bitacora (Pasos 4-14)
a partir de la documentacion, ya que el codigo original vive en un repo local
al que este entorno no tiene acceso. Antes de reemplazar el backend real,
compara contra TECH-DESIGN.md / los 8 ADRs / FRONTEND-SPEC.md si los tienes
a mano -- puede haber detalles de implementacion que no quedaron registrados
en la bitacora.
"""
from fastapi import FastAPI

from app.db.audit import register_audit_listeners
from app.routers import activaciones, auth, marcadores, pre_pai, relevos, unidades, usuarios

app = FastAPI(title="PCE - SSEI Jorge Chavez", version="0.1.0")

register_audit_listeners()

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(activaciones.router)
app.include_router(relevos.router)
app.include_router(marcadores.router)
app.include_router(pre_pai.router)
app.include_router(unidades.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
