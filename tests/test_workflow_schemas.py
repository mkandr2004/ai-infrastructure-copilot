from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.incident import IncidentMetrics
from app.schemas.workflow import (
    FindingSeverity,
    InvestigationFinding,
    InvestigationTarget,
    InvestigationWorkflowRecord,
    InvestigationWorkflowRequest,
    WorkflowStatus,
    WorkflowStepName,
    WorkflowStepRecord,
    WorkflowStepStatus,
)


def test_workflow_request_uses_safe_defaults():
    request = InvestigationWorkflowRequest(
        problem_description="  CPU élevé  ",
    )

    assert request.problem_description == "CPU élevé"
    assert request.confirm_external_send is False
    assert request.include_logs is False
    assert request.use_knowledge is True


def test_workflow_request_rejects_blank_description():
    with pytest.raises(ValidationError):
        InvestigationWorkflowRequest(
            problem_description="   ",
        )


def test_workflow_request_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        InvestigationWorkflowRequest(
            problem_description="CPU élevé",
            unknown_option=True,
        )


def test_workflow_record_contains_structured_results():
    created_at = datetime.now(UTC)

    workflow = InvestigationWorkflowRecord(
        id="workflow-test",
        created_at=created_at,
        updated_at=created_at,
        expires_at=created_at + timedelta(days=1),
        status=WorkflowStatus.COMPLETED,
        problem_description="CPU élevé",
        steps=[
            WorkflowStepRecord(
                name=WorkflowStepName.COLLECT_METRICS,
                status=WorkflowStepStatus.COMPLETED,
                started_at=created_at,
                completed_at=created_at,
                summary="Métriques collectées.",
            ),
        ],
        metrics=IncidentMetrics(
            cpu_percent=95.0,
            memory_percent=40.0,
            disk_percent=20.0,
        ),
        history_points_analyzed=10,
        findings=[
            InvestigationFinding(
                target=InvestigationTarget.CPU,
                severity=FindingSeverity.CRITICAL,
                title="CPU très élevé",
                details=(
                    "Le processeur dépasse le seuil critique."
                ),
                evidence=[
                    "CPU observé : 95.0 %",
                ],
            ),
        ],
        diagnostic_model="modele-test",
        diagnosis="Diagnostic simulé.",
    )

    assert workflow.status == WorkflowStatus.COMPLETED
    assert workflow.metrics is not None
    assert workflow.metrics.cpu_percent == 95.0
    assert workflow.history_points_analyzed == 10
    assert len(workflow.steps) == 1
    assert len(workflow.findings) == 1
