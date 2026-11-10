from app.services.diagnosis import build_diagnostic_prompt


def test_prompt_keeps_investigation_context_separate():
    system_data = {
        "timestamp": "2026-11-10T12:00:00+00:00",
        "cpu": {"percent": 95.0},
        "memory": {"percent": 40.0},
        "disk": {"percent": 30.0},
        "logs": [],
    }

    investigation_context = """
    CONTEXTE D'INVESTIGATION LOCAL :
    Ressource : cpu
    Gravité : critical
    Valeur actuelle : 95.0 %
    """.strip()

    prompt = build_diagnostic_prompt(
        system_data,
        problem_description="CPU élevé",
        investigation_context=investigation_context,
    )

    assert "<investigation_context>" in prompt
    assert "</investigation_context>" in prompt
    assert "Ressource : cpu" in prompt
    assert "Gravité : critical" in prompt
    assert "Valeur actuelle : 95.0 %" in prompt
    assert (
        "Un incident historique similaire ne prouve pas"
        in prompt
    )
    assert "<knowledge_context>" not in prompt
