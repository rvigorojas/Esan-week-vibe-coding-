from datetime import datetime, timezone

import pytest

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_ci_no_puede_desactivar(client, jefe_rescate):
    """El CI (Jefe de Rescate) no esta en ROLES_DESACTIVACION -- PRD sec. 5."""
    headers = await auth_headers(client, "jrescate")
    act_resp = await client.post(
        "/activaciones",
        json={
            "categoria_emergencia": "AERONAUTICA",
            "nivel_alerta": "I",
            "tipo_alerta": 1,
            "tipo_incidente": "Prueba",
            "hora_evento": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    activacion_id = act_resp.json()["id"]

    resp = await client.post(f"/activaciones/{activacion_id}/desactivar", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_duty_manager_puede_desactivar(client, jefe_rescate, duty_manager):
    headers_ci = await auth_headers(client, "jrescate")
    act_resp = await client.post(
        "/activaciones",
        json={
            "categoria_emergencia": "AERONAUTICA",
            "nivel_alerta": "I",
            "tipo_alerta": 1,
            "tipo_incidente": "Prueba",
            "hora_evento": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers_ci,
    )
    activacion_id = act_resp.json()["id"]

    headers_dm = await auth_headers(client, "dmanager")
    resp = await client.post(f"/activaciones/{activacion_id}/desactivar", headers=headers_dm)
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "CERRADA"

    # Segunda desactivacion debe fallar (409) -- ya esta cerrada.
    resp2 = await client.post(f"/activaciones/{activacion_id}/desactivar", headers=headers_dm)
    assert resp2.status_code == 409
