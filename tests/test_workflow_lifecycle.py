from datetime import UTC, datetime, timedelta

import pytest

from app.schemas.workflow import (
    InvestigationWorkflowRecord,
    WorkflowStatus,
    WorkflowStepName,
    WorkflowStepRecord,
    WorkflowStepStatus,
)
from app.workflows.lifecycle import (
    complete_step,
    complete_workflow,
    fail_step,
    fail_workflow,
    get_workflow_step,
    skip_step,
    start_step,
    start_workflow,
)


def make_workflow() -> InvestigationWorkflowRecord:
    now = datetime.now(UTC)

    return InvestigationWorkflowRecord(
        id="workflow-test",
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=1),
        status=WorkflowStatus.PENDING,
        problem_description="CPU élevé",
        steps=[
            WorkflowStepRecord(name=step_name)
            for step_name in WorkflowStepName
        ],
    )


def test_start_workflow_changes_status():
    workflow = start_workflow(
        make_workflow()
    )

    assert workflow.status == WorkflowStatus.RUNNING


def test_step_can_start_and_complete():
    workflow = start_workflow(make_workflow())

    workflow = start_step(
        workflow,
        WorkflowStepName.COLLECT_METRICS,
    )
    workflow = complete_step(
        workflow,
        WorkflowStepName.COLLECT_METRICS,
        " Métriques collectées. ",
    )

    step = get_workflow_step(
        workflow,
        WorkflowStepName.COLLECT_METRICS,
    )

    assert step.status == WorkflowStepStatus.COMPLETED
    assert step.started_at is not None
    assert step.completed_at is not None
    assert step.summary == "Métriques collectées."


def test_pending_step_can_be_skipped():
    workflow = start_workflow(make_workflow())

    workflow = skip_step(
        workflow,
        WorkflowStepName.SEARCH_KNOWLEDGE,
        "Documentation non demandée.",
    )

    step = get_workflow_step(
        workflow,
        WorkflowStepName.SEARCH_KNOWLEDGE,
    )

    assert step.status == WorkflowStepStatus.SKIPPED
    assert step.started_at is not None
    assert step.completed_at is not None


def test_running_step_and_workflow_can_fail():
    workflow = start_workflow(make_workflow())
    workflow = start_step(
        workflow,
        WorkflowStepName.COLLECT_METRICS,
    )
    workflow = fail_step(
        workflow,
        WorkflowStepName.COLLECT_METRICS,
        "Collecte indisponible.",
    )
    workflow = fail_workflow(
        workflow,
        "Investigation interrompue.",
    )

    step = get_workflow_step(
        workflow,
        WorkflowStepName.COLLECT_METRICS,
    )

    assert step.status == WorkflowStepStatus.FAILED
    assert workflow.status == WorkflowStatus.FAILED
    assert workflow.error == "Investigation interrompue."


def test_workflow_cannot_finish_with_pending_steps():
    workflow = start_workflow(make_workflow())

    with pytest.raises(
        ValueError,
        match="Toutes les étapes",
    ):
        complete_workflow(workflow)


def test_workflow_completes_when_steps_are_closed():
    workflow = start_workflow(make_workflow())

    for step_name in WorkflowStepName:
        workflow = skip_step(
            workflow,
            step_name,
            "Étape ignorée pour ce test.",
        )

    workflow = complete_workflow(workflow)

    assert workflow.status == WorkflowStatus.COMPLETED


def test_completed_step_cannot_restart():
    workflow = start_workflow(make_workflow())
    step_name = WorkflowStepName.COLLECT_METRICS

    workflow = start_step(
        workflow,
        step_name,
    )
    workflow = complete_step(
        workflow,
        step_name,
        "Étape terminée.",
    )

    with pytest.raises(
        ValueError,
        match="en attente",
    ):
        start_step(
            workflow,
            step_name,
        )
