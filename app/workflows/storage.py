"""Stockage temporaire des workflows dans Redis."""

from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import uuid4

from redis import Redis

from app.core.config import Settings
from app.schemas.workflow import (
    InvestigationWorkflowRecord,
    InvestigationWorkflowRequest,
    WorkflowStatus,
    WorkflowStepName,
    WorkflowStepRecord,
)


def workflow_key(
    settings: Settings,
    workflow_id: str,
) -> str:
    """Construit la clé Redis d'un workflow."""

    return (
        f"{settings.redis_key_prefix}:"
        f"workflow:{workflow_id}"
    )


def workflow_index_key(
    settings: Settings,
) -> str:
    """Construit la clé Redis de l'index des workflows."""

    return (
        f"{settings.redis_key_prefix}:"
        "workflows:index"
    )


def store_workflow(
    client: Redis,
    settings: Settings,
    workflow: InvestigationWorkflowRecord,
    ttl_seconds: int,
) -> None:
    """Écrit un workflow et actualise son index."""

    key = workflow_key(
        settings,
        workflow.id,
    )
    index_key = workflow_index_key(settings)

    with client.pipeline(
        transaction=True,
    ) as pipeline:
        pipeline.set(
            key,
            workflow.model_dump_json(),
            ex=ttl_seconds,
        )
        pipeline.zadd(
            index_key,
            {
                workflow.id: (
                    workflow.created_at.timestamp()
                ),
            },
        )
        pipeline.expire(
            index_key,
            settings.workflow_ttl_seconds,
        )
        pipeline.execute()


def create_workflow(
    client: Redis,
    settings: Settings,
    request: InvestigationWorkflowRequest,
) -> InvestigationWorkflowRecord:
    """Crée un workflow en attente."""

    if settings.workflow_ttl_seconds < 1:
        raise ValueError(
            "La durée de conservation doit être positive."
        )

    created_at = datetime.now(UTC)
    expires_at = created_at + timedelta(
        seconds=settings.workflow_ttl_seconds,
    )

    workflow = InvestigationWorkflowRecord(
        id=str(uuid4()),
        created_at=created_at,
        updated_at=created_at,
        expires_at=expires_at,
        status=WorkflowStatus.PENDING,
        problem_description=(
            request.problem_description
        ),
        logs_included_in_diagnosis=(
            request.include_logs
        ),
        knowledge_requested=request.use_knowledge,
        steps=[
            WorkflowStepRecord(name=step_name)
            for step_name in WorkflowStepName
        ],
    )

    store_workflow(
        client,
        settings,
        workflow,
        settings.workflow_ttl_seconds,
    )

    return workflow


def save_workflow(
    client: Redis,
    settings: Settings,
    workflow: InvestigationWorkflowRecord,
) -> InvestigationWorkflowRecord:
    """Met à jour un workflow sans dépasser son expiration."""

    updated_at = datetime.now(UTC)

    remaining_seconds = ceil(
        (
            workflow.expires_at - updated_at
        ).total_seconds()
    )

    if remaining_seconds < 1:
        raise ValueError(
            "Le workflow a déjà expiré."
        )

    updated_workflow = workflow.model_copy(
        update={
            "updated_at": updated_at,
        },
    )

    store_workflow(
        client,
        settings,
        updated_workflow,
        remaining_seconds,
    )

    return updated_workflow


def get_workflow(
    client: Redis,
    settings: Settings,
    workflow_id: str,
) -> InvestigationWorkflowRecord | None:
    """Retourne un workflow ou None s'il a expiré."""

    raw_workflow = client.get(
        workflow_key(
            settings,
            workflow_id,
        )
    )

    if raw_workflow is None:
        client.zrem(
            workflow_index_key(settings),
            workflow_id,
        )
        return None

    return InvestigationWorkflowRecord.model_validate_json(
        raw_workflow
    )


def list_workflows(
    client: Redis,
    settings: Settings,
    limit: int = 20,
) -> list[InvestigationWorkflowRecord]:
    """Retourne les workflows les plus récents."""

    if limit < 1:
        raise ValueError(
            "La limite doit être d'au moins un workflow."
        )

    index_key = workflow_index_key(settings)

    workflow_ids = client.zrevrange(
        index_key,
        0,
        -1,
    )

    workflows: list[InvestigationWorkflowRecord] = []
    expired_ids: list[str] = []

    for workflow_id in workflow_ids:
        raw_workflow = client.get(
            workflow_key(
                settings,
                workflow_id,
            )
        )

        if raw_workflow is None:
            expired_ids.append(workflow_id)
            continue

        workflows.append(
            InvestigationWorkflowRecord.model_validate_json(
                raw_workflow
            )
        )

        if len(workflows) >= limit:
            break

    if expired_ids:
        client.zrem(
            index_key,
            *expired_ids,
        )

    return workflows
