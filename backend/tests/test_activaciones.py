from datetime import datetime, timezone

import pytest

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_crear_activacion_aeronautica(client, jefe_rescate, duty_manager):
    headers = await auth_headers(client, "jrescate")
    payload = {
        "categoria_emergencia": "AERONAUTICA",
        "nivel_alerta": "II",
        "tipo_alerta": 4,
        "tipo_incidente": "Advertencia de aeronave",
        "hora_evento": datetime.now(timezone.utc).isoformat(),
        "convocatoria": [{"instancia": "PMM", "usuario_id": jefe_rescate.id}],
    }
    resp = await client.post("/activaciones", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["estado"] == "ACTIVA"
    assert data["nivel_alerta"] == "II"
    assert data["tipo_alerta"] == 4


@pytest.mark.asyncio
async def test_matpel_fuerza_nivel_general(client, jefe_rescate):
    headers = await auth_headers(client, "jrescate")
    payload = {
        "categoria_emergencia": "MATPEL",
        "nivel_alerta": "III",  # deberia ser ignorado -- MATPEL siempre I
        "clasificacion_origen": "Clase 3 - Liquidos inflamables",
        "tipo_incidente": "Derrame de combustible",
        "hora_evento": datetime.now(timezone.utc).isoformat(),
    }
    resp = await client.post("/activaciones", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["nivel_alerta"] == "I"
