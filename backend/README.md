# PCE — Backend (SSEI, Jorge Chávez)

Backend FastAPI + PostgreSQL async para el Puesto de Comando y Administración
de Emergencias (SSEI, AIJC).

**⚠️ Nota de origen:** este código fue reconstruido a partir de la
documentación del proyecto (`Design.md`, `PRD_PCE_JorgeChavez.3`,
`bitacora-de-desarrollo.md`) en una conversación sin acceso al repo local
donde el backend ya se había implementado y verificado end-to-end (commits
`53126bc`, `f3ba454`, `9698419` según la bitácora). No es un `git pull` de
ese repo — es una reconstrucción fiel a lo documentado, pero puede diferir
en detalles de implementación que la bitácora no registró (nombres exactos
de columnas, validaciones adicionales, el contenido completo de los 8 ADRs
que no estaban disponibles). Antes de reemplazar el backend real con esto,
compáralos.

## Stack

- FastAPI + SQLAlchemy 2.0 (async) + asyncpg
- PostgreSQL 16
- Alembic para migraciones
- JWT con mecanismo de "token blando" (ADR-7) para offline prolongado
- Triggers de Postgres para insert-only (ADR-2, refuerzo de doble capa)

## Levantar en local

```bash
cp .env.example .env      # ajustar si hace falta
docker compose up -d db   # o tu Postgres local
alembic upgrade head
uvicorn app.main:app --reload
```

(`docker-compose.yml` está un nivel arriba de `backend/`, junto a este README.)

## Correr tests

Requiere Postgres real corriendo (no usa sqlite):

```bash
docker compose up -d db
pytest
```

## Estructura

```
app/
  core/       # config y seguridad (JWT + token blando)
  db/         # engine async, sesión, listeners de auditoría
  models/     # entidades SQLAlchemy (ver docstring de models.py)
  schemas/    # Pydantic (request/response)
  routers/    # endpoints agrupados por dominio
  deps.py     # auth, control de acceso por rol
  main.py
alembic/
  versions/
    0001_initial.py                    # create_all — espejo vivo de los modelos
    0002_insert_only_triggers.py       # triggers insert-only (todas las tablas)
    0003_relevo_activacion_y_cierre.py # trigger dedicado: ACTIVA -> CERRADA
tests/
```

## Decisiones de diseño relevantes (ver docstrings del código para el detalle)

- **Insert-only en dos capas** (ADR-2): API sin UPDATE/DELETE + trigger de
  Postgres como respaldo, en `activacion`, `evaluacion_inicial`,
  `relevo_mando`, `marcador_incidente`. La única excepción es
  `activacion.estado`: `ACTIVA → CERRADA`, sin tocar ningún otro campo.
- **Doble timestamp** (ADR-2): `hora_evento` (reloj del dispositivo, para
  mostrar) + `hora_recepcion` (`server_default=now()`, para auditoría y
  last-write-wins).
- **Token blando** (ADR-7): el JWT vencido se sigue aceptando durante
  `JWT_SOFT_TOKEN_GRACE_HOURS` (12h por defecto) si el cliente estuvo
  offline. Pendiente de decidir con Renzo: qué pasa si el token ya había
  vencido *antes* de perder conexión (hueco 6.4, aún abierto).
- **MATPEL**: convocatoria fijada como "siempre activación general"
  — `[Propuesto, pendiente de confirmar con el Jefe de Rescate]`.
- **Auditoría sin endpoint propio**: el feed de "últimos eventos" del
  Resumen COE se arma combinando los endpoints de dominio ya consumidos,
  no leyendo `log_auditoria` directamente (decisión de diseño, no un hueco).

## Pendientes que la bitácora deja abiertos

- Hueco 6.2 y 6.4 de `FRONTEND-SPEC.md` (mecanismo de sync con token
  vencido) — sigue pendiente de decidir con Renzo.
- Confirmación del Jefe de Rescate sobre el criterio real de convocatoria
  MATPEL.
- Confirmación de Renzo sobre la ventana de 12h del token blando.
