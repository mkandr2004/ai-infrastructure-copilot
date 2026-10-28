from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from app.rag.context import build_knowledge_context
from app.rag.retriever import KnowledgeMatch
from app.services.diagnosis import (
    build_diagnostic_prompt,
    request_diagnostic,
)


def test_build_diagnostic_prompt_without_knowledge_context():
    system_data = {
        "timestamp": "2026-10-02T10:00:00",
        "cpu": {"percent": 15.0},
        "memory": {"percent": 40.0},
        "disk": {"percent": 30.0},
        "logs": [],
    }

    prompt = build_diagnostic_prompt(system_data)

    assert '"percent": 15.0' in prompt
    assert "<system_data>" in prompt
    assert "<knowledge_context>" not in prompt


def test_build_diagnostic_prompt_with_knowledge_context():
    system_data = {
        "timestamp": "2026-10-02T10:00:00",
        "cpu": {"percent": 95.0},
        "memory": {"percent": 40.0},
        "disk": {"percent": 30.0},
        "logs": [],
    }

    matches = [
    KnowledgeMatch(
        point_id="cpu-1",
        score=0.82,
        source="cpu.md",
        title="Diagnostic CPU — Vérifications",
        text="Utiliser top pour identifier les processus actifs.",
        chunk_index=0,
    )
]

    knowledge_context = build_knowledge_context(matches)

    prompt = build_diagnostic_prompt(
        system_data,
        knowledge_context,
    )

    assert "<knowledge_context>" in prompt
    assert "CONTEXTE DOCUMENTAIRE LOCAL" in prompt
    assert "cpu.md" in prompt
    assert "Utiliser top" in prompt
    assert "Les données système observées restent prioritaires" in prompt
    assert '"percent": 95.0' in prompt


def test_request_diagnostic_configures_timeout():
    settings = SimpleNamespace(
        gemini_api_key=SecretStr("cle-fictive"),
        gemini_model="modele-test",
        gemini_timeout_ms=30000,
        gemini_retry_attempts=1,
    )

    fake_response = SimpleNamespace(
        output_text="Diagnostic simulé",
    )

    fake_client = MagicMock()
    fake_client.interactions.create.return_value = (
        fake_response
    )

    fake_context = MagicMock()
    fake_context.__enter__.return_value = (
        fake_client
    )

    with patch(
        "app.services.diagnosis.genai.Client",
        return_value=fake_context,
    ) as mock_client_factory:
        result = request_diagnostic(
            "Prompt de test",
            settings,
        )

    assert result == "Diagnostic simulé"

    client_options = (
        mock_client_factory.call_args.kwargs
    )

    assert client_options["api_key"] == (
        "cle-fictive"
    )
    assert (
        client_options["http_options"].timeout
        == 30000
    )
    assert (
        client_options[
            "http_options"
        ].retry_options.attempts
        == 1
    )

    fake_client.interactions.create.assert_called_once_with(
        model="modele-test",
        input="Prompt de test",
        store=False,
    )
    fake_context.__exit__.assert_called_once()
