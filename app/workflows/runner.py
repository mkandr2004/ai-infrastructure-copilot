"""Orchestration contrôlée des investigations."""

from redis import Redis
from sqlalchemy.orm import Session

from app.collectors.system import collect_system_metrics
from app.core.config import Settings
from app.memory.incidents import list_incidents
from app.rag.context import build_knowledge_context
from app.rag.retriever import search_knowledge
from app.rag.vector_store import create_qdrant_client
from app.schemas.incident import IncidentMetrics
from app.schemas.workflow import (
    InvestigationWorkflowRecord,
    WorkflowStepName,
)
from app.services.diagnosis import (
    build_diagnostic_prompt,
    request_diagnostic,
)
from app.services.metrics import list_metric_snapshots
from app.workflows.analyzers import analyze_system_metrics
from app.workflows.context import build_investigation_context
from app.workflows.lifecycle import (
    complete_step,
    complete_workflow,
    fail_step,
    fail_workflow,
    skip_step,
    start_step,
    start_workflow,
)
from app.workflows.similarity import find_similar_incidents
from app.workflows.storage import save_workflow


HISTORY_LIMIT = 100
INCIDENT_LIMIT = 50
SIMILAR_INCIDENT_LIMIT = 5


def persist_workflow(
    client: Redis,
    settings: Settings,
    workflow: InvestigationWorkflowRecord,
) -> InvestigationWorkflowRecord:
    """Persiste une transition du workflow."""

    return save_workflow(
        client,
        settings,
        workflow,
    )


def run_investigation_workflow(
    redis_client: Redis,
    session: Session,
    settings: Settings,
    workflow: InvestigationWorkflowRecord,
) -> InvestigationWorkflowRecord:
    """Exécute toutes les étapes d'une investigation."""

    current_step: WorkflowStepName | None = None
    system_data: dict = {}
    history = []
    similar_incidents = []
    knowledge_context = ""

    try:
        workflow = start_workflow(workflow)
        workflow = persist_workflow(
            redis_client,
            settings,
            workflow,
        )

        current_step = WorkflowStepName.COLLECT_METRICS
        workflow = start_step(workflow, current_step)
        workflow = persist_workflow(
            redis_client,
            settings,
            workflow,
        )

        system_data = collect_system_metrics()

        if not workflow.logs_included_in_diagnosis:
            system_data["logs"] = []

        workflow = workflow.model_copy(
            update={
                "metrics": IncidentMetrics(
                    cpu_percent=system_data["cpu"]["percent"],
                    memory_percent=(
                        system_data["memory"]["percent"]
                    ),
                    disk_percent=(
                        system_data["disk"]["percent"]
                    ),
                ),
            },
        )
        workflow = complete_step(
            workflow,
            current_step,
            "Métriques système collectées.",
        )
        workflow = persist_workflow(
            redis_client,
            settings,
            workflow,
        )
        current_step = None

        current_step = WorkflowStepName.ANALYZE_HISTORY
        workflow = start_step(workflow, current_step)
        workflow = persist_workflow(
            redis_client,
            settings,
            workflow,
        )

        history = list_metric_snapshots(
            session,
            limit=HISTORY_LIMIT,
        )
        workflow = workflow.model_copy(
            update={
                "history_points_analyzed": len(history),
            },
        )
        workflow = complete_step(
            workflow,
            current_step,
            f"{len(history)} mesure(s) historique(s) analysée(s).",
        )
        workflow = persist_workflow(
            redis_client,
            settings,
            workflow,
        )
        current_step = None

        current_step = WorkflowStepName.FIND_SIMILAR_INCIDENTS
        workflow = start_step(workflow, current_step)
        workflow = persist_workflow(
            redis_client,
            settings,
            workflow,
        )

        incidents = list_incidents(
            redis_client,
            settings,
            limit=INCIDENT_LIMIT,
        )
        similar_incidents = find_similar_incidents(
            workflow.problem_description,
            incidents,
            limit=SIMILAR_INCIDENT_LIMIT,
        )
        workflow = workflow.model_copy(
            update={
                "similar_incident_ids": [
                    incident.id
                    for incident in similar_incidents
                ],
            },
        )
        workflow = complete_step(
            workflow,
            current_step,
            (
                f"{len(similar_incidents)} incident(s) "
                "similaire(s) trouvé(s)."
            ),
        )
        workflow = persist_workflow(
            redis_client,
            settings,
            workflow,
        )
        current_step = None

        current_step = WorkflowStepName.SEARCH_KNOWLEDGE

        if workflow.knowledge_requested:
            workflow = start_step(workflow, current_step)
            workflow = persist_workflow(
                redis_client,
                settings,
                workflow,
            )

            qdrant_client = create_qdrant_client(settings)

            try:
                matches = search_knowledge(
                    qdrant_client,
                    settings,
                    workflow.problem_description,
                )
            finally:
                qdrant_client.close()

            knowledge_context = build_knowledge_context(
                matches
            )
            workflow = workflow.model_copy(
                update={
                    "knowledge_sources": list(
                        dict.fromkeys(
                            match.source
                            for match in matches
                        )
                    ),
                },
            )
            workflow = complete_step(
                workflow,
                current_step,
                f"{len(matches)} passage(s) documentaire(s) retenu(s).",
            )
        else:
            workflow = skip_step(
                workflow,
                current_step,
                "Recherche documentaire non demandée.",
            )

        workflow = persist_workflow(
            redis_client,
            settings,
            workflow,
        )
        current_step = None

        current_step = WorkflowStepName.BUILD_FINDINGS
        workflow = start_step(workflow, current_step)
        workflow = persist_workflow(
            redis_client,
            settings,
            workflow,
        )

        findings = analyze_system_metrics(
            system_data,
            history,
        )
        workflow = workflow.model_copy(
            update={
                "findings": findings,
            },
        )
        investigation_context = build_investigation_context(
            findings,
            similar_incidents,
            history_points_analyzed=len(history),
        )
        workflow = complete_step(
            workflow,
            current_step,
            f"{len(findings)} constat(s) déterministe(s) produit(s).",
        )
        workflow = persist_workflow(
            redis_client,
            settings,
            workflow,
        )
        current_step = None

        current_step = WorkflowStepName.PRODUCE_DIAGNOSIS
        workflow = start_step(workflow, current_step)
        workflow = persist_workflow(
            redis_client,
            settings,
            workflow,
        )

        prompt = build_diagnostic_prompt(
            system_data,
            knowledge_context=knowledge_context,
            problem_description=workflow.problem_description,
            investigation_context=investigation_context,
        )
        diagnosis = request_diagnostic(
            prompt,
            settings,
        )
        workflow = workflow.model_copy(
            update={
                "diagnostic_model": settings.gemini_model,
                "diagnosis": diagnosis,
            },
        )
        workflow = complete_step(
            workflow,
            current_step,
            "Diagnostic Gemini produit.",
        )
        current_step = None

        workflow = complete_workflow(workflow)
        return persist_workflow(
            redis_client,
            settings,
            workflow,
        )

    except Exception:
        if current_step is not None:
            try:
                workflow = fail_step(
                    workflow,
                    current_step,
                    f"Échec de l'étape {current_step.value}.",
                )
            except ValueError:
                pass

        workflow = fail_workflow(
            workflow,
            "Le workflow d'investigation a échoué.",
        )

        try:
            persist_workflow(
                redis_client,
                settings,
                workflow,
            )
        except Exception:
            pass

        raise
