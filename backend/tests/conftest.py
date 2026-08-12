"""
Fixtures compartidas. Usa la misma DATABASE_URL de settings -- corre contra
un Postgres real (como en el Paso 14 de la bitacora: "14/14 tests ... contra
PostgreSQL 16 real"), no sqlite. Levanta `docker compose up db` antes de
correr pytest.

Simplificacion de este scaffold: el reset de esquema usa
Base.metadata.create_all() directamente, no `alembic upgrade head` -- por lo
tanto los triggers de Postgres (0002/0003) NO estan activos durante los
tests, solo las restricciones a nivel API. Para probar tambien la capa de
DB (ej. que un UPDATE directo por SQL a activacion falle salvo el cierre),
cambia este fixture para correr las migraciones reales contra una base de
pruebas.
"""
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db.base import AsyncSessionLocal, Base, engine
from app.main import app
from app.models.models import Rol, Usuario


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _reset_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def jefe_rescate(db_session) -> Usuario:
    usuario = Usuario(
        username="jrescate",
        password_hash=hash_password("clave123"),
        nombre_completo="Jorge Atarama",
        rol=Rol.JEFE_RESCATE,
        activo=True,
    )
    db_session.add(usuario)
    await db_session.commit()
    await db_session.refresh(usuario)
    return usuario


@pytest_asyncio.fixture
async def duty_manager(db_session) -> Usuario:
    usuario = Usuario(
        username="dmanager",
        password_hash=hash_password("clave123"),
        nombre_completo="Duty Manager Turno A",
        rol=Rol.DUTY_MANAGER,
        activo=True,
    )
    db_session.add(usuario)
    await db_session.commit()
    await db_session.refresh(usuario)
    return usuario


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def auth_headers(client: AsyncClient, username: str, password: str = "clave123") -> dict:
    resp = await client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
