from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.workflow import (
    InvestigationWorkflowRecord,
    WorkflowStatus,
)
from app.workflows.queue import (
    dequeue_workflow,
    enqueue_workflow,
    workflow_queue_key,
)


def make_settings(queue_name: str = "investigations"):
    return SimpleNamespace(
        redis_key_prefix="test",
        workflow_queue_name=queue_name,
    )


def make_workflow() -> InvestigationWorkflowRecord:
    now = datetime.now(UTC)
    return InvestigationWorkflowRecord(
        id="workflow-1",
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=1),
        status=WorkflowStatus.PENDING,
        problem_description="CPU élevé",
    )


def test_workflow_queue_key_is_namespaced():
    assert workflow_queue_key(make_settings()) == (
        "test:queue:investigations"
    )


def test_empty_workflow_queue_name_is_rejected():
    with pytest.raises(ValueError, match="nom de la file"):
        workflow_queue_key(make_settings("  "))


def test_enqueue_workflow_persists_before_push():
    client = MagicMock()
    settings = make_settings()
    workflow = make_workflow()

    with patch(
        "app.workflows.queue.save_workflow",
        side_effect=lambda client, settings, workflow: workflow,
    ) as mock_save:
        queued = enqueue_workflow(client, settings, workflow)

    assert queued.status == WorkflowStatus.QUEUED
    mock_save.assert_called_once()
    client.rpush.assert_called_once_with(
        "test:queue:investigations",
        "workflow-1",
    )


def test_dequeue_workflow_returns_identifier():
    client = MagicMock()
    client.lpop.return_value = "workflow-1"

    assert dequeue_workflow(client, make_settings()) == "workflow-1"


def test_dequeue_workflow_returns_none_when_empty():
    client = MagicMock()
    client.lpop.return_value = None

    assert dequeue_workflow(client, make_settings()) is None
