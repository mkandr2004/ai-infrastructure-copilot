"""Routes HTTP des workflows d'investigation."""

from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.memory.redis_client import create_redis_client
from app.schemas.workflow import (
    InvestigationWorkflowRecord,
    InvestigationWorkflowRequest,
)
from app.workflows.queue import enqueue_workflow
from app.workflows.storage import (
    create_workflow,
    get_workflow,
    list_workflows,
)


router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
)


@router.post(
    "",
    response_model=InvestigationWorkflowRecord,
    status_code=202,
)
def create_investigation_workflow(
    request: InvestigationWorkflowRequest,
) -> InvestigationWorkflowRecord:
    """Crée et place une investigation dans la file Redis."""

    if not request.confirm_external_send:
        raise HTTPException(
            status_code=400,
            detail=(
                "Confirme explicitement l'envoi à Gemini."
            ),
        )

    settings = get_settings()
    redis_client = None

    try:
        redis_client = create_redis_client(settings)
        workflow = create_workflow(
            redis_client,
            settings,
            request,
        )

        return enqueue_workflow(
            redis_client,
            settings,
            workflow,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from None
    except Exception as error:
        print(
            "Erreur de mise en file du workflow : "
            f"{type(error).__name__}"
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "La file des workflows est indisponible."
            ),
        ) from None
    finally:
        if redis_client is not None:
            redis_client.close()


@router.get(
    "",
    response_model=list[InvestigationWorkflowRecord],
)
def get_workflows(
    limit: int = Query(default=20, ge=1, le=100),
) -> list[InvestigationWorkflowRecord]:
    """Liste les workflows les plus récents."""

    settings = get_settings()
    redis_client = None

    try:
        redis_client = create_redis_client(settings)

        return list_workflows(
            redis_client,
            settings,
            limit=limit,
        )
    except Exception as error:
        print(
            "Erreur Redis pendant la lecture des workflows : "
            f"{type(error).__name__}"
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "La mémoire des workflows est indisponible."
            ),
        ) from None
    finally:
        if redis_client is not None:
            redis_client.close()


@router.get(
    "/{workflow_id}",
    response_model=InvestigationWorkflowRecord,
)
def get_workflow_by_id(
    workflow_id: str,
) -> InvestigationWorkflowRecord:
    """Lit un workflow par son identifiant."""

    settings = get_settings()
    redis_client = None

    try:
        redis_client = create_redis_client(settings)
        workflow = get_workflow(
            redis_client,
            settings,
            workflow_id,
        )
    except Exception as error:
        print(
            "Erreur Redis pendant la lecture du workflow : "
            f"{type(error).__name__}"
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "La mémoire des workflows est indisponible."
            ),
        ) from None
    finally:
        if redis_client is not None:
            redis_client.close()

    if workflow is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow introuvable ou expiré.",
        )

    return workflow
