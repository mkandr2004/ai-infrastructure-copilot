from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_diagnose_refuses_without_confirmation():
    with patch("app.main.request_diagnostic") as mock_gemini:
        response = client.post(
            "/diagnose",
            json={
                "confirm_external_send": False,
                "include_logs": False,
            },
        )

    assert response.status_code == 400
    mock_gemini.assert_not_called()


def test_diagnose_sends_metrics_without_logs():
    fake_data = {
        "timestamp": "2026-09-22T12:00:00",
        "cpu": {"percent": 2.0},
        "memory": {"percent": 20.0},
        "disk": {"percent": 1.0},
        "logs": ["LOG_CONFIDENTIEL_DE_TEST"],
    }

    fake_settings = SimpleNamespace(
        gemini_api_key=SecretStr("cle-fictive-pour-test"),
        gemini_model="modele-de-test",
    )

    with (
        patch("app.main.get_settings", return_value=fake_settings),
        patch("app.main.collect_system_metrics", return_value=fake_data),
        patch(
            "app.main.request_diagnostic",
            return_value="Diagnostic simulé",
        ) as mock_gemini,
    ):
        response = client.post(
            "/diagnose",
            json={
                "confirm_external_send": True,
                "include_logs": False,
            },
        )

    assert response.status_code == 200
    assert response.json()["diagnosis"] == "Diagnostic simulé"
    assert response.json()["logs_sent"] is False

    prompt_envoye = mock_gemini.call_args.args[0]
    assert "LOG_CONFIDENTIEL_DE_TEST" not in prompt_envoye
    mock_gemini.assert_called_once()
