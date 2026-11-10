"""File Redis des workflows d'investigation."""

from redis import Redis

from app.core.config import Settings
from app.schemas.workflow import InvestigationWorkflowRecord
from app.workflows.lifecycle import queue_workflow
from app.workflows.storage import save_workflow


def workflow_queue_key(
    settings: Settings,
) -> str:
    """Construit la clé Redis de la file d'attente."""

    queue_name = settings.workflow_queue_name.strip()

    if not queue_name:
        raise ValueError(
            "Le nom de la file des workflows est vide."
        )

    return (
        f"{settings.redis_key_prefix}:"
        f"queue:{queue_name}"
    )


def enqueue_workflow(
    client: Redis,
    settings: Settings,
    workflow: InvestigationWorkflowRecord,
) -> InvestigationWorkflowRecord:
    """Persiste puis ajoute un workflow à la file."""

    queued_workflow = queue_workflow(workflow)
    queued_workflow = save_workflow(
        client,
        settings,
        queued_workflow,
    )

    client.rpush(
        workflow_queue_key(settings),
        queued_workflow.id,
    )

    return queued_workflow


def dequeue_workflow(
    client: Redis,
    settings: Settings,
) -> str | None:
    """Retire le prochain identifiant de la file."""

    workflow_id = client.lpop(
        workflow_queue_key(settings)
    )

    if workflow_id is None:
        return None

    return str(workflow_id)
