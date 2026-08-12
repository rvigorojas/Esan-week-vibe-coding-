from datetime import datetime, timezone

import pytest

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_relevo_filtra_por_activacion(client, jefe_rescate, duty_manager):
    headers = await auth_headers(client, "jrescate")
    act_resp = await client.post(
        "/activaciones",
        json={
            "categoria_emergencia": "AERONAUTICA",
            "nivel_alerta": "II",
            "tipo_alerta": 4,
            "tipo_incidente": "Advertencia de aeronave",
            "hora_evento": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    activacion_id = act_resp.json()["id"]

    relevo_resp = await client.post(
        "/relevos-mando",
        json={
            "activacion_id": activacion_id,
            "instancia": "PMM",
            "sale_usuario_id": None,
            "entra_usuario_id": jefe_rescate.id,
            "hora_evento": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    assert relevo_resp.status_code == 201, relevo_resp.text
    assert relevo_resp.json()["activacion_id"] == activacion_id

    listado = await client.get(f"/relevos-mando?activacion_id={activacion_id}", headers=headers)
    assert listado.status_code == 200
    assert len(listado.json()) == 1
