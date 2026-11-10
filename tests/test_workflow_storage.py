from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.schemas.workflow import (
    InvestigationWorkflowRecord,
    InvestigationWorkflowRequest,
    WorkflowStatus,
)
from app.workflows.storage import (
    create_workflow,
    get_workflow,
    list_workflows,
    save_workflow,
    workflow_index_key,
    workflow_key,
)


def make_settings(
    ttl_seconds: int = 3600,
):
    return SimpleNamespace(
        redis_key_prefix="test_copilot",
        workflow_ttl_seconds=ttl_seconds,
    )


def make_workflow(
    workflow_id: str,
) -> InvestigationWorkflowRecord:
    created_at = datetime.now(UTC)

    return InvestigationWorkflowRecord(
        id=workflow_id,
        created_at=created_at,
        updated_at=created_at,
        expires_at=(
            created_at + timedelta(hours=1)
        ),
        status=WorkflowStatus.PENDING,
        problem_description="CPU élevé",
    )


def make_pipeline_client():
    client = MagicMock()
    pipeline = MagicMock()

    client.pipeline.return_value.__enter__.return_value = (
        pipeline
    )

    return client, pipeline


def test_create_workflow_uses_ttl_and_index():
    settings = make_settings()
    client, pipeline = make_pipeline_client()

    request = InvestigationWorkflowRequest(
        problem_description="  CPU élevé  ",
    )

    workflow = create_workflow(
        client,
        settings,
        request,
    )

    assert workflow.status == WorkflowStatus.PENDING
    assert workflow.problem_description == "CPU élevé"
    assert len(workflow.steps) == 6

    set_call = pipeline.set.call_args

    assert set_call.args[0] == workflow_key(
        settings,
        workflow.id,
    )
    assert set_call.kwargs["ex"] == 3600

    stored_workflow = (
        InvestigationWorkflowRecord.model_validate_json(
            set_call.args[1]
        )
    )

    assert stored_workflow == workflow

    pipeline.zadd.assert_called_once_with(
        workflow_index_key(settings),
        {
            workflow.id: (
                workflow.created_at.timestamp()
            ),
        },
    )
    pipeline.expire.assert_called_once_with(
        workflow_index_key(settings),
        3600,
    )
    pipeline.execute.assert_called_once_with()


def test_create_workflow_rejects_invalid_ttl():
    settings = make_settings(ttl_seconds=0)
    client = MagicMock()

    request = InvestigationWorkflowRequest(
        problem_description="CPU élevé",
    )

    with pytest.raises(
        ValueError,
        match="conservation",
    ):
        create_workflow(
            client,
            settings,
            request,
        )

    client.pipeline.assert_not_called()


def test_save_workflow_updates_timestamp():
    settings = make_settings()
    client, pipeline = make_pipeline_client()
    workflow = make_workflow("workflow-1")

    updated_workflow = save_workflow(
        client,
        settings,
        workflow,
    )

    assert (
        updated_workflow.updated_at
        >= workflow.updated_at
    )

    set_call = pipeline.set.call_args

    assert set_call.args[0] == workflow_key(
        settings,
        workflow.id,
    )
    assert 1 <= set_call.kwargs["ex"] <= 3600

    stored_workflow = (
        InvestigationWorkflowRecord.model_validate_json(
            set_call.args[1]
        )
    )

    assert stored_workflow == updated_workflow


def test_get_workflow_returns_stored_workflow():
    settings = make_settings()
    client = MagicMock()
    expected = make_workflow("workflow-1")

    client.get.return_value = (
        expected.model_dump_json()
    )

    result = get_workflow(
        client,
        settings,
        "workflow-1",
    )

    assert result == expected
    client.zrem.assert_not_called()


def test_get_workflow_removes_expired_id():
    settings = make_settings()
    client = MagicMock()
    client.get.return_value = None

    result = get_workflow(
        client,
        settings,
        "expired-workflow",
    )

    assert result is None
    client.zrem.assert_called_once_with(
        workflow_index_key(settings),
        "expired-workflow",
    )


def test_list_workflows_skips_expired_entries():
    settings = make_settings()
    client = MagicMock()

    newest = make_workflow("newest")
    oldest = make_workflow("oldest")

    client.zrevrange.return_value = [
        "newest",
        "expired",
        "oldest",
    ]

    client.get.side_effect = [
        newest.model_dump_json(),
        None,
        oldest.model_dump_json(),
    ]

    result = list_workflows(
        client,
        settings,
        limit=2,
    )

    assert [
        workflow.id
        for workflow in result
    ] == [
        "newest",
        "oldest",
    ]

    client.zrem.assert_called_once_with(
        workflow_index_key(settings),
        "expired",
    )


def test_list_workflows_rejects_invalid_limit():
    settings = make_settings()
    client = MagicMock()

    with pytest.raises(
        ValueError,
        match="limite",
    ):
        list_workflows(
            client,
            settings,
            limit=0,
        )
