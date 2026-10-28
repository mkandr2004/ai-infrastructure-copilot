from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from app.rag.retriever import KnowledgeMatch

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.db.database import get_db
from app.main import app

from app.schemas.incident import (
    IncidentMetrics,
    IncidentRecord,
)

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


def test_metrics_history_returns_saved_snapshots():
    fake_session = object()

    fake_snapshot = SimpleNamespace(
        id=42,
        collected_at=datetime(
            2026,
            9,
            23,
            12,
            0,
            tzinfo=UTC,
        ),
        cpu_percent=10.0,
        memory_total_gb=16.0,
        memory_used_gb=4.0,
        memory_available_gb=12.0,
        memory_percent=25.0,
        disk_total_gb=100.0,
        disk_used_gb=20.0,
        disk_free_gb=80.0,
        disk_percent=20.0,
        created_at=datetime(
            2026,
            9,
            23,
            12,
            0,
            1,
            tzinfo=UTC,
        ),
    )

    def override_get_db():
        yield fake_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch(
            "app.main.list_metric_snapshots",
            return_value=[fake_snapshot],
        ) as mock_list:
            response = client.get(
                "/metrics/history",
                params={"limit": 1},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 1
    assert history[0]["id"] == 42
    assert history[0]["cpu_percent"] == 10.0
    assert history[0]["memory_percent"] == 25.0
    assert history[0]["disk_percent"] == 20.0

    mock_list.assert_called_once_with(
        fake_session,
        1,
    )

def test_diagnose_requires_description_for_knowledge_search():
    with (
        patch("app.main.create_qdrant_client") as mock_create_client,
        patch("app.main.request_diagnostic") as mock_gemini,
    ):
        response = client.post(
            "/diagnose",
            json={
                "confirm_external_send": True,
                "include_logs": False,
                "use_knowledge": True,
            },
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == (
            "Une description du problème est nécessaire "
            "pour rechercher dans la documentation."
        )
    )

    mock_create_client.assert_not_called()
    mock_gemini.assert_not_called()


def test_diagnose_uses_retrieved_knowledge():
    fake_data = {
        "timestamp": "2026-10-02T10:00:00",
        "cpu": {"percent": 95.0},
        "memory": {"percent": 40.0},
        "disk": {"percent": 30.0},
        "logs": [],
    }

    fake_settings = SimpleNamespace(
        gemini_api_key=SecretStr("cle-fictive-pour-test"),
        gemini_model="modele-de-test",
    )

    fake_client = MagicMock()

    fake_matches = [
        KnowledgeMatch(
            point_id="cpu-1",
            score=0.82,
            source="cpu.md",
            title="Diagnostic CPU — Vérifications",
            text="Utiliser top pour identifier les processus actifs.",
            chunk_index=0,
        )
    ]

    with (
        patch("app.main.get_settings", return_value=fake_settings),
        patch("app.main.collect_system_metrics", return_value=fake_data),
        patch(
            "app.main.create_qdrant_client",
            return_value=fake_client,
        ),
        patch(
            "app.main.search_knowledge",
            return_value=fake_matches,
        ) as mock_search,
        patch(
            "app.main.request_diagnostic",
            return_value="Diagnostic enrichi",
        ) as mock_gemini,
    ):
        response = client.post(
            "/diagnose",
            json={
                "confirm_external_send": True,
                "include_logs": False,
                "use_knowledge": True,
                "problem_description": (
                    "Le processeur reste à 95 %."
                ),
            },
        )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["diagnosis"] == "Diagnostic enrichi"
    assert response_data["knowledge_used"] is True
    assert response_data["knowledge_sources"] == ["cpu.md"]

    mock_search.assert_called_once_with(
        fake_client,
        fake_settings,
        "Le processeur reste à 95 %.",
    )

    fake_client.close.assert_called_once_with()

    prompt_sent = mock_gemini.call_args.args[0]

    assert "Le processeur reste à 95 %." in prompt_sent
    assert "cpu.md" in prompt_sent
    assert "Utiliser top" in prompt_sent

def test_diagnose_continues_without_relevant_knowledge():
    fake_data = {
        "timestamp": "2026-10-02T10:00:00+00:00",
        "cpu": {"percent": 5.0},
        "memory": {"percent": 30.0},
        "disk": {"percent": 20.0},
        "logs": [],
    }

    fake_settings = SimpleNamespace(
        gemini_api_key=SecretStr("cle-fictive-pour-test"),
        gemini_model="modele-de-test",
    )

    fake_client = MagicMock()

    with (
        patch("app.main.get_settings", return_value=fake_settings),
        patch("app.main.collect_system_metrics", return_value=fake_data),
        patch(
            "app.main.create_qdrant_client",
            return_value=fake_client,
        ),
        patch(
            "app.main.search_knowledge",
            return_value=[],
        ),
        patch(
            "app.main.request_diagnostic",
            return_value="Diagnostic sans contexte",
        ) as mock_gemini,
    ):
        response = client.post(
            "/diagnose",
            json={
                "confirm_external_send": True,
                "include_logs": False,
                "use_knowledge": True,
                "problem_description": (
                    "Comment renouveler un certificat TLS ?"
                ),
            },
        )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["knowledge_used"] is False
    assert response_data["knowledge_sources"] == []
    assert response_data["diagnosis"] == "Diagnostic sans contexte"

    fake_client.close.assert_called_once_with()

    prompt_sent = mock_gemini.call_args.args[0]

    assert "Comment renouveler un certificat TLS ?" in prompt_sent
    assert "<knowledge_context>" not in prompt_sent


def test_diagnose_returns_error_when_knowledge_search_fails():
    fake_data = {
        "timestamp": "2026-10-02T10:00:00+00:00",
        "cpu": {"percent": 5.0},
        "memory": {"percent": 30.0},
        "disk": {"percent": 20.0},
        "logs": [],
    }

    fake_settings = SimpleNamespace(
        gemini_api_key=SecretStr("cle-fictive-pour-test"),
        gemini_model="modele-de-test",
    )

    fake_client = MagicMock()

    with (
        patch("app.main.get_settings", return_value=fake_settings),
        patch("app.main.collect_system_metrics", return_value=fake_data),
        patch(
            "app.main.create_qdrant_client",
            return_value=fake_client,
        ),
        patch(
            "app.main.search_knowledge",
            side_effect=RuntimeError("Qdrant indisponible"),
        ),
        patch("app.main.request_diagnostic") as mock_gemini,
    ):
        response = client.post(
            "/diagnose",
            json={
                "confirm_external_send": True,
                "include_logs": False,
                "use_knowledge": True,
                "problem_description": (
                    "Le processeur reste à 95 %."
                ),
            },
        )

    assert response.status_code == 502
    assert (
        response.json()["detail"]
        == "La recherche documentaire a échoué."
    )

    fake_client.close.assert_called_once_with()
    mock_gemini.assert_not_called()

def make_api_incident(
    incident_id: str = "incident-123",
) -> IncidentRecord:
    timestamp = datetime(
        2026,
        10,
        28,
        12,
        0,
        tzinfo=UTC,
    )

    return IncidentRecord(
        id=incident_id,
        created_at=timestamp,
        expires_at=timestamp,
        collected_at=timestamp,
        problem_description="CPU élevé",
        metrics=IncidentMetrics(
            cpu_percent=95.0,
            memory_percent=40.0,
            disk_percent=30.0,
        ),
        diagnostic_model="modele-test",
        diagnosis="Diagnostic enregistré",
        knowledge_sources=["cpu.md"],
        logs_included=False,
    )


def test_diagnose_requires_description_to_save_incident():
    with (
        patch("app.main.request_diagnostic") as mock_gemini,
        patch(
            "app.main.create_redis_client"
        ) as mock_redis,
    ):
        response = client.post(
            "/diagnose",
            json={
                "confirm_external_send": True,
                "save_incident": True,
            },
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == (
            "Une description du problème est nécessaire "
            "pour enregistrer un incident."
        )
    )

    mock_gemini.assert_not_called()
    mock_redis.assert_not_called()


def test_diagnose_saves_incident():
    fake_data = {
        "timestamp": "2026-10-28T12:00:00+00:00",
        "cpu": {"percent": 95.0},
        "memory": {"percent": 40.0},
        "disk": {"percent": 30.0},
        "logs": [],
    }

    fake_settings = SimpleNamespace(
        gemini_api_key=SecretStr(
            "cle-fictive-pour-test"
        ),
        gemini_model="modele-test",
    )

    fake_redis = MagicMock()
    saved_incident = SimpleNamespace(
        id="incident-123",
    )

    with (
        patch(
            "app.main.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "app.main.collect_system_metrics",
            return_value=fake_data,
        ),
        patch(
            "app.main.request_diagnostic",
            return_value="Diagnostic enregistré",
        ),
        patch(
            "app.main.create_redis_client",
            return_value=fake_redis,
        ),
        patch(
            "app.main.save_incident",
            return_value=saved_incident,
        ) as mock_save,
    ):
        response = client.post(
            "/diagnose",
            json={
                "confirm_external_send": True,
                "include_logs": False,
                "use_knowledge": False,
                "save_incident": True,
                "problem_description": "CPU élevé",
            },
        )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["incident_saved"] is True
    assert response_data["incident_id"] == (
        "incident-123"
    )

    mock_save.assert_called_once_with(
        fake_redis,
        fake_settings,
        system_data=fake_data,
        problem_description="CPU élevé",
        diagnostic_model="modele-test",
        diagnosis="Diagnostic enregistré",
        knowledge_sources=[],
        logs_included=False,
    )

    fake_redis.close.assert_called_once_with()


def test_diagnose_continues_when_redis_fails():
    fake_data = {
        "timestamp": "2026-10-28T12:00:00+00:00",
        "cpu": {"percent": 5.0},
        "memory": {"percent": 30.0},
        "disk": {"percent": 20.0},
        "logs": [],
    }

    fake_settings = SimpleNamespace(
        gemini_api_key=SecretStr(
            "cle-fictive-pour-test"
        ),
        gemini_model="modele-test",
    )

    fake_redis = MagicMock()

    with (
        patch(
            "app.main.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "app.main.collect_system_metrics",
            return_value=fake_data,
        ),
        patch(
            "app.main.request_diagnostic",
            return_value="Diagnostic disponible",
        ),
        patch(
            "app.main.create_redis_client",
            return_value=fake_redis,
        ),
        patch(
            "app.main.save_incident",
            side_effect=RuntimeError(
                "Redis indisponible"
            ),
        ),
    ):
        response = client.post(
            "/diagnose",
            json={
                "confirm_external_send": True,
                "save_incident": True,
                "problem_description": "Serveur lent",
            },
        )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["diagnosis"] == (
        "Diagnostic disponible"
    )
    assert response_data["incident_saved"] is False
    assert response_data["incident_id"] is None

    fake_redis.close.assert_called_once_with()


def test_incidents_returns_saved_incidents():
    fake_settings = SimpleNamespace()
    fake_redis = MagicMock()
    incident = make_api_incident()

    with (
        patch(
            "app.main.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "app.main.create_redis_client",
            return_value=fake_redis,
        ),
        patch(
            "app.main.list_incidents",
            return_value=[incident],
        ) as mock_list,
    ):
        response = client.get(
            "/incidents",
            params={"limit": 5},
        )

    assert response.status_code == 200
    assert response.json()[0]["id"] == (
        "incident-123"
    )

    mock_list.assert_called_once_with(
        fake_redis,
        fake_settings,
        limit=5,
    )
    fake_redis.close.assert_called_once_with()


def test_incident_by_id_returns_saved_incident():
    fake_settings = SimpleNamespace()
    fake_redis = MagicMock()
    incident = make_api_incident()

    with (
        patch(
            "app.main.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "app.main.create_redis_client",
            return_value=fake_redis,
        ),
        patch(
            "app.main.get_incident",
            return_value=incident,
        ) as mock_get,
    ):
        response = client.get(
            "/incidents/incident-123"
        )

    assert response.status_code == 200
    assert response.json()["id"] == (
        "incident-123"
    )

    mock_get.assert_called_once_with(
        fake_redis,
        fake_settings,
        "incident-123",
    )
    fake_redis.close.assert_called_once_with()


def test_incident_by_id_returns_404_when_missing():
    fake_settings = SimpleNamespace()
    fake_redis = MagicMock()

    with (
        patch(
            "app.main.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "app.main.create_redis_client",
            return_value=fake_redis,
        ),
        patch(
            "app.main.get_incident",
            return_value=None,
        ),
    ):
        response = client.get(
            "/incidents/missing"
        )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Incident introuvable ou expiré."
    )

    fake_redis.close.assert_called_once_with()


def test_diagnose_returns_429_when_search_hits_quota():
    fake_data = {
        "timestamp": "2026-10-28T12:00:00+00:00",
        "cpu": {"percent": 5.0},
        "memory": {"percent": 30.0},
        "disk": {"percent": 20.0},
        "logs": [],
    }

    fake_settings = SimpleNamespace(
        gemini_api_key=SecretStr(
            "cle-fictive-pour-test"
        ),
        gemini_model="modele-test",
    )

    fake_client = MagicMock()
    quota_error = RuntimeError("quota dépassé")
    quota_error.status_code = 429

    with (
        patch(
            "app.main.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "app.main.collect_system_metrics",
            return_value=fake_data,
        ),
        patch(
            "app.main.create_qdrant_client",
            return_value=fake_client,
        ),
        patch(
            "app.main.search_knowledge",
            side_effect=quota_error,
        ),
        patch(
            "app.main.request_diagnostic"
        ) as mock_gemini,
    ):
        response = client.post(
            "/diagnose",
            json={
                "confirm_external_send": True,
                "use_knowledge": True,
                "problem_description": "CPU élevé",
            },
        )

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Quota Gemini dépassé. Réessaie plus tard."
    )

    fake_client.close.assert_called_once_with()
    mock_gemini.assert_not_called()


def test_diagnose_returns_429_when_diagnosis_hits_quota():
    fake_data = {
        "timestamp": "2026-10-28T12:00:00+00:00",
        "cpu": {"percent": 5.0},
        "memory": {"percent": 30.0},
        "disk": {"percent": 20.0},
        "logs": [],
    }

    fake_settings = SimpleNamespace(
        gemini_api_key=SecretStr(
            "cle-fictive-pour-test"
        ),
        gemini_model="modele-test",
    )

    quota_error = RuntimeError("quota dépassé")
    quota_error.status_code = 429

    with (
        patch(
            "app.main.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "app.main.collect_system_metrics",
            return_value=fake_data,
        ),
        patch(
            "app.main.request_diagnostic",
            side_effect=quota_error,
        ),
    ):
        response = client.post(
            "/diagnose",
            json={
                "confirm_external_send": True,
                "problem_description": "Serveur lent",
            },
        )

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Quota Gemini dépassé. Réessaie plus tard."
    )
