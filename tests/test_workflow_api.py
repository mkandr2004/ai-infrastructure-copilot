from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.workflow import (
    InvestigationWorkflowRecord,
    WorkflowStatus,
)


client = TestClient(app)


def make_workflow(
    workflow_id: str = "workflow-1",
) -> InvestigationWorkflowRecord:
    now = datetime.now(UTC)

    return InvestigationWorkflowRecord(
        id=workflow_id,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=1),
        status=WorkflowStatus.COMPLETED,
        problem_description="CPU élevé",
        diagnostic_model="modele-test",
        diagnosis="Diagnostic final.",
    )


def test_create_workflow_requires_confirmation():
    with patch(
        "app.workflows.router.create_redis_client"
    ) as mock_redis:
        response = client.post(
            "/workflows",
            json={
                "problem_description": "CPU élevé",
                "confirm_external_send": False,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Confirme explicitement l'envoi à Gemini."
    )
    mock_redis.assert_not_called()


def test_create_workflow_queues_investigation():
    fake_settings = SimpleNamespace()
    fake_redis = MagicMock()
    pending_workflow = make_workflow("pending-1").model_copy(
        update={"status": WorkflowStatus.PENDING}
    )
    queued_workflow = pending_workflow.model_copy(
        update={"status": WorkflowStatus.QUEUED}
    )

    with (
        patch(
            "app.workflows.router.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "app.workflows.router.create_redis_client",
            return_value=fake_redis,
        ),
        patch(
            "app.workflows.router.create_workflow",
            return_value=pending_workflow,
        ) as mock_create,
        patch(
            "app.workflows.router.enqueue_workflow",
            return_value=queued_workflow,
        ) as mock_enqueue,
    ):
        response = client.post(
            "/workflows",
            json={
                "problem_description": "CPU élevé",
                "confirm_external_send": True,
                "use_knowledge": False,
            },
        )

    assert response.status_code == 202
    assert response.json()["id"] == "pending-1"
    assert response.json()["status"] == "queued"
    mock_create.assert_called_once()
    mock_enqueue.assert_called_once_with(
        fake_redis,
        fake_settings,
        pending_workflow,
    )
    fake_redis.close.assert_called_once_with()


def test_list_workflows_returns_records():
    fake_redis = MagicMock()
    workflow = make_workflow()

    with (
        patch(
            "app.workflows.router.create_redis_client",
            return_value=fake_redis,
        ),
        patch(
            "app.workflows.router.list_workflows",
            return_value=[workflow],
        ) as mock_list,
    ):
        response = client.get(
            "/workflows",
            params={"limit": 5},
        )

    assert response.status_code == 200
    assert response.json()[0]["id"] == workflow.id
    mock_list.assert_called_once()
    assert mock_list.call_args.kwargs["limit"] == 5
    fake_redis.close.assert_called_once_with()


def test_get_workflow_returns_record():
    fake_redis = MagicMock()
    workflow = make_workflow()

    with (
        patch(
            "app.workflows.router.create_redis_client",
            return_value=fake_redis,
        ),
        patch(
            "app.workflows.router.get_workflow",
            return_value=workflow,
        ),
    ):
        response = client.get(
            f"/workflows/{workflow.id}"
        )

    assert response.status_code == 200
    assert response.json()["id"] == workflow.id
    fake_redis.close.assert_called_once_with()


def test_get_workflow_returns_404_when_missing():
    fake_redis = MagicMock()

    with (
        patch(
            "app.workflows.router.create_redis_client",
            return_value=fake_redis,
        ),
        patch(
            "app.workflows.router.get_workflow",
            return_value=None,
        ),
    ):
        response = client.get(
            "/workflows/missing"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Workflow introuvable ou expiré."
    )
    fake_redis.close.assert_called_once_with()


def test_create_workflow_returns_503_when_queue_fails():
    fake_redis = MagicMock()
    pending_workflow = make_workflow().model_copy(
        update={"status": WorkflowStatus.PENDING}
    )
    with (
        patch(
            "app.workflows.router.create_redis_client",
            return_value=fake_redis,
        ),
        patch(
            "app.workflows.router.create_workflow",
            return_value=pending_workflow,
        ),
        patch(
            "app.workflows.router.enqueue_workflow",
            side_effect=RuntimeError("Redis indisponible"),
        ),
    ):
        response = client.post(
            "/workflows",
            json={
                "problem_description": "CPU élevé",
                "confirm_external_send": True,
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "La file des workflows est indisponible."
    )
    fake_redis.close.assert_called_once_with()


def test_list_workflows_returns_503_when_redis_fails():
    fake_redis = MagicMock()

    with (
        patch(
            "app.workflows.router.create_redis_client",
            return_value=fake_redis,
        ),
        patch(
            "app.workflows.router.list_workflows",
            side_effect=RuntimeError("Redis indisponible"),
        ),
    ):
        response = client.get("/workflows")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "La mémoire des workflows est indisponible."
    )
    fake_redis.close.assert_called_once_with()
