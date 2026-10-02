from app.rag.context import build_knowledge_context
from app.rag.retriever import KnowledgeMatch
from app.services.diagnosis import build_diagnostic_prompt


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
