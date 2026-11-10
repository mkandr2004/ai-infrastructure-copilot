from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.schemas.workflow import (
    InvestigationWorkflowRecord,
    WorkflowStatus,
)
from app.workflows.worker import process_workflow


def make_workflow(
    status: WorkflowStatus = WorkflowStatus.QUEUED,
) -> InvestigationWorkflowRecord:
    now = datetime.now(UTC)
    return InvestigationWorkflowRecord(
        id="workflow-1",
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=1),
        status=status,
        problem_description="CPU élevé",
    )


def test_worker_processes_queued_workflow():
    settings = SimpleNamespace()
    redis_client = MagicMock()
    session = MagicMock()
    session_context = MagicMock()
    session_context.__enter__.return_value = session

    with (
        patch(
            "app.workflows.worker.get_settings",
            return_value=settings,
        ),
        patch(
            "app.workflows.worker.create_redis_client",
            return_value=redis_client,
        ),
        patch(
            "app.workflows.worker.get_workflow",
            return_value=make_workflow(),
        ),
        patch(
            "app.workflows.worker.SessionLocal",
            return_value=session_context,
        ),
        patch(
            "app.workflows.worker.run_investigation_workflow",
        ) as mock_run,
    ):
        processed = process_workflow("workflow-1")

    assert processed is True
    mock_run.assert_called_once()
    assert mock_run.call_args.args[:3] == (
        redis_client,
        session,
        settings,
    )
    redis_client.close.assert_called_once_with()


def test_worker_ignores_missing_workflow():
    redis_client = MagicMock()

    with (
        patch(
            "app.workflows.worker.get_settings",
            return_value=SimpleNamespace(),
        ),
        patch(
            "app.workflows.worker.create_redis_client",
            return_value=redis_client,
        ),
        patch(
            "app.workflows.worker.get_workflow",
            return_value=None,
        ),
        patch(
            "app.workflows.worker.run_investigation_workflow",
        ) as mock_run,
    ):
        processed = process_workflow("missing")

    assert processed is False
    mock_run.assert_not_called()
    redis_client.close.assert_called_once_with()


def test_worker_does_not_reprocess_completed_workflow():
    redis_client = MagicMock()

    with (
        patch(
            "app.workflows.worker.get_settings",
            return_value=SimpleNamespace(),
        ),
        patch(
            "app.workflows.worker.create_redis_client",
            return_value=redis_client,
        ),
        patch(
            "app.workflows.worker.get_workflow",
            return_value=make_workflow(WorkflowStatus.COMPLETED),
        ),
        patch(
            "app.workflows.worker.run_investigation_workflow",
        ) as mock_run,
    ):
        processed = process_workflow("workflow-1")

    assert processed is False
    mock_run.assert_not_called()
    redis_client.close.assert_called_once_with()
