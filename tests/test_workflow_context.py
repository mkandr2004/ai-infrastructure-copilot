from datetime import UTC, datetime

from app.schemas.incident import (
    IncidentMetrics,
    IncidentRecord,
)
from app.schemas.workflow import (
    FindingSeverity,
    InvestigationFinding,
    InvestigationTarget,
)
from app.workflows.context import (
    build_investigation_context,
)


def make_finding() -> InvestigationFinding:
    return InvestigationFinding(
        target=InvestigationTarget.CPU,
        severity=FindingSeverity.CRITICAL,
        title="CPU à un niveau critique",
        details="Le CPU dépasse le seuil critique.",
        evidence=[
            "Valeur actuelle : 95.0 %",
            "Moyenne historique : 92.0 %",
        ],
    )


def make_incident() -> IncidentRecord:
    created_at = datetime(
        2026,
        11,
        10,
        12,
        0,
        tzinfo=UTC,
    )

    return IncidentRecord(
        id="incident-cpu",
        created_at=created_at,
        expires_at=created_at,
        collected_at=created_at,
        problem_description="CPU élevé",
        metrics=IncidentMetrics(
            cpu_percent=95.0,
            memory_percent=30.0,
            disk_percent=20.0,
        ),
        diagnostic_model="modele-test",
        diagnosis="ANCIEN_DIAGNOSTIC_SECRET",
    )


def test_empty_investigation_context_returns_empty_string():
    context = build_investigation_context(
        [],
        [],
        history_points_analyzed=0,
    )

    assert context == ""


def test_investigation_context_contains_findings():
    context = build_investigation_context(
        [make_finding()],
        [],
        history_points_analyzed=10,
    )

    assert "CONSTATS DÉTERMINISTES" in context
    assert "Ressource : cpu" in context
    assert "Gravité : critical" in context
    assert "Valeur actuelle : 95.0 %" in context
    assert (
        "Nombre de mesures historiques analysées : 10"
        in context
    )


def test_context_includes_incident_facts_without_old_diagnosis():
    context = build_investigation_context(
        [],
        [make_incident()],
        history_points_analyzed=0,
    )

    assert "incident-cpu" in context
    assert "Description signalée : CPU élevé" in context
    assert "CPU 95.0 %" in context
    assert "ANCIEN_DIAGNOSTIC_SECRET" not in context
