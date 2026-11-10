"""Transitions contrôlées des workflows."""

from datetime import UTC, datetime

from app.schemas.workflow import (
    InvestigationWorkflowRecord,
    WorkflowStatus,
    WorkflowStepName,
    WorkflowStepRecord,
    WorkflowStepStatus,
)


def update_workflow_step(
    workflow: InvestigationWorkflowRecord,
    step_name: WorkflowStepName,
    **updates,
) -> InvestigationWorkflowRecord:
    """Met à jour une étape sans modifier l'objet initial."""

    updated_steps: list[WorkflowStepRecord] = []
    step_found = False

    for step in workflow.steps:
        if step.name == step_name:
            updated_steps.append(
                step.model_copy(
                    update=updates,
                )
            )
            step_found = True
        else:
            updated_steps.append(step)

    if not step_found:
        raise ValueError(
            f"Étape absente du workflow : {step_name}."
        )

    return workflow.model_copy(
        update={
            "steps": updated_steps,
            "updated_at": datetime.now(UTC),
        },
    )


def get_workflow_step(
    workflow: InvestigationWorkflowRecord,
    step_name: WorkflowStepName,
) -> WorkflowStepRecord:
    """Retourne une étape précise."""

    for step in workflow.steps:
        if step.name == step_name:
            return step

    raise ValueError(
        f"Étape absente du workflow : {step_name}."
    )


def queue_workflow(
    workflow: InvestigationWorkflowRecord,
) -> InvestigationWorkflowRecord:
    """Place un workflow en attente dans la file Redis."""

    if workflow.status != WorkflowStatus.PENDING:
        raise ValueError(
            "Seul un workflow en attente peut être mis en file."
        )

    return workflow.model_copy(
        update={
            "status": WorkflowStatus.QUEUED,
            "updated_at": datetime.now(UTC),
            "error": None,
        },
    )


def start_workflow(
    workflow: InvestigationWorkflowRecord,
) -> InvestigationWorkflowRecord:
    """Démarre un workflow en attente ou en file."""

    if workflow.status not in {
        WorkflowStatus.PENDING,
        WorkflowStatus.QUEUED,
    }:
        raise ValueError(
            "Seul un workflow en attente ou en file peut démarrer."
        )

    return workflow.model_copy(
        update={
            "status": WorkflowStatus.RUNNING,
            "updated_at": datetime.now(UTC),
            "error": None,
        },
    )


def start_step(
    workflow: InvestigationWorkflowRecord,
    step_name: WorkflowStepName,
) -> InvestigationWorkflowRecord:
    """Démarre une étape en attente."""

    if workflow.status != WorkflowStatus.RUNNING:
        raise ValueError(
            "Le workflow doit être en cours."
        )

    step = get_workflow_step(
        workflow,
        step_name,
    )

    if step.status != WorkflowStepStatus.PENDING:
        raise ValueError(
            "Seule une étape en attente peut démarrer."
        )

    return update_workflow_step(
        workflow,
        step_name,
        status=WorkflowStepStatus.RUNNING,
        started_at=datetime.now(UTC),
        completed_at=None,
        summary=None,
        error=None,
    )


def complete_step(
    workflow: InvestigationWorkflowRecord,
    step_name: WorkflowStepName,
    summary: str,
) -> InvestigationWorkflowRecord:
    """Termine avec succès une étape en cours."""

    clean_summary = summary.strip()

    if not clean_summary:
        raise ValueError(
            "Le résumé de l'étape est vide."
        )

    step = get_workflow_step(
        workflow,
        step_name,
    )

    if step.status != WorkflowStepStatus.RUNNING:
        raise ValueError(
            "Seule une étape en cours peut réussir."
        )

    return update_workflow_step(
        workflow,
        step_name,
        status=WorkflowStepStatus.COMPLETED,
        completed_at=datetime.now(UTC),
        summary=clean_summary,
        error=None,
    )


def skip_step(
    workflow: InvestigationWorkflowRecord,
    step_name: WorkflowStepName,
    reason: str,
) -> InvestigationWorkflowRecord:
    """Ignore explicitement une étape en attente."""

    clean_reason = reason.strip()

    if not clean_reason:
        raise ValueError(
            "La raison de l'ignorance est vide."
        )

    step = get_workflow_step(
        workflow,
        step_name,
    )

    if step.status != WorkflowStepStatus.PENDING:
        raise ValueError(
            "Seule une étape en attente peut être ignorée."
        )

    now = datetime.now(UTC)

    return update_workflow_step(
        workflow,
        step_name,
        status=WorkflowStepStatus.SKIPPED,
        started_at=now,
        completed_at=now,
        summary=clean_reason,
        error=None,
    )


def fail_step(
    workflow: InvestigationWorkflowRecord,
    step_name: WorkflowStepName,
    error: str,
) -> InvestigationWorkflowRecord:
    """Marque une étape comme échouée."""

    clean_error = error.strip()

    if not clean_error:
        raise ValueError(
            "Le message d'erreur est vide."
        )

    step = get_workflow_step(
        workflow,
        step_name,
    )

    if step.status not in {
        WorkflowStepStatus.PENDING,
        WorkflowStepStatus.RUNNING,
    }:
        raise ValueError(
            "Cette étape ne peut plus échouer."
        )

    now = datetime.now(UTC)

    return update_workflow_step(
        workflow,
        step_name,
        status=WorkflowStepStatus.FAILED,
        started_at=step.started_at or now,
        completed_at=now,
        summary=None,
        error=clean_error,
    )


def complete_workflow(
    workflow: InvestigationWorkflowRecord,
) -> InvestigationWorkflowRecord:
    """Termine un workflow dont toutes les étapes sont closes."""

    allowed_statuses = {
        WorkflowStepStatus.COMPLETED,
        WorkflowStepStatus.SKIPPED,
    }

    if any(
        step.status not in allowed_statuses
        for step in workflow.steps
    ):
        raise ValueError(
            "Toutes les étapes doivent être terminées "
            "ou ignorées."
        )

    return workflow.model_copy(
        update={
            "status": WorkflowStatus.COMPLETED,
            "updated_at": datetime.now(UTC),
            "error": None,
        },
    )


def fail_workflow(
    workflow: InvestigationWorkflowRecord,
    error: str,
) -> InvestigationWorkflowRecord:
    """Termine un workflow en échec."""

    clean_error = error.strip()

    if not clean_error:
        raise ValueError(
            "Le message d'erreur est vide."
        )

    return workflow.model_copy(
        update={
            "status": WorkflowStatus.FAILED,
            "updated_at": datetime.now(UTC),
            "error": clean_error,
        },
    )
