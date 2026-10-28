from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.collectors.system import collect_system_metrics
from app.core.config import get_settings
from app.db.database import get_db
from app.memory.incidents import (
    get_incident,
    list_incidents,
    save_incident,
)
from app.memory.redis_client import create_redis_client
from app.models.metric import MetricSnapshot
from app.rag.context import build_knowledge_context
from app.rag.retriever import search_knowledge
from app.rag.vector_store import create_qdrant_client
from app.schemas.incident import IncidentRecord
from app.schemas.metric import MetricSnapshotResponse
from app.services.diagnosis import (
    build_diagnostic_prompt,
    request_diagnostic,
)
from app.services.metrics import list_metric_snapshots


app = FastAPI(title="AI Infrastructure Copilot")


def is_gemini_rate_limit_error(
    error: Exception,
) -> bool:
    """Indique si Gemini refuse l'appel pour quota."""

    return getattr(error, "status_code", None) == 429


class DiagnoseRequest(BaseModel):
    confirm_external_send: bool = False
    include_logs: bool = False
    use_knowledge: bool = False
    save_incident: bool = False
    problem_description: str | None = Field(
        default=None,
        max_length=2000,
    )


class DiagnoseResponse(BaseModel):
    timestamp: str
    model: str
    diagnosis: str
    logs_sent: bool
    knowledge_used: bool
    knowledge_sources: list[str]
    incident_saved: bool
    incident_id: str | None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def get_metrics() -> dict:
    return collect_system_metrics()


@app.get(
    "/metrics/history",
    response_model=list[MetricSnapshotResponse],
)
def get_metrics_history(
    limit: int = Query(default=100, ge=1, le=1000),
    session: Session = Depends(get_db),
) -> list[MetricSnapshot]:
    return list_metric_snapshots(session, limit)


@app.get(
    "/incidents",
    response_model=list[IncidentRecord],
)
def get_incidents(
    limit: int = Query(default=20, ge=1, le=100),
) -> list[IncidentRecord]:
    settings = get_settings()
    redis_client = None

    try:
        redis_client = create_redis_client(settings)

        return list_incidents(
            redis_client,
            settings,
            limit=limit,
        )

    except Exception as error:
        print(
            "Erreur Redis pendant la lecture : "
            f"{type(error).__name__}"
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "La mémoire des incidents est indisponible."
            ),
        ) from None

    finally:
        if redis_client is not None:
            redis_client.close()


@app.get(
    "/incidents/{incident_id}",
    response_model=IncidentRecord,
)
def get_incident_by_id(
    incident_id: str,
) -> IncidentRecord:
    settings = get_settings()
    redis_client = None

    try:
        redis_client = create_redis_client(settings)

        incident = get_incident(
            redis_client,
            settings,
            incident_id,
        )

    except Exception as error:
        print(
            "Erreur Redis pendant la lecture : "
            f"{type(error).__name__}"
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "La mémoire des incidents est indisponible."
            ),
        ) from None

    finally:
        if redis_client is not None:
            redis_client.close()

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident introuvable ou expiré.",
        )

    return incident


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(request: DiagnoseRequest) -> DiagnoseResponse:
    if not request.confirm_external_send:
        raise HTTPException(
            status_code=400,
            detail="Confirme explicitement l'envoi à Gemini.",
        )

    problem_description = (
        request.problem_description or ""
    ).strip()

    if request.use_knowledge and not problem_description:
        raise HTTPException(
            status_code=400,
            detail=(
                "Une description du problème est nécessaire "
                "pour rechercher dans la documentation."
            ),
        )

    if request.save_incident and not problem_description:
        raise HTTPException(
            status_code=400,
            detail=(
                "Une description du problème est nécessaire "
                "pour enregistrer un incident."
            ),
        )

    settings = get_settings()

    if settings.gemini_api_key is None:
        raise HTTPException(
            status_code=503,
            detail="Clé Gemini non configurée.",
        )

    system_data = collect_system_metrics()

    # Par défaut, les logs ne quittent pas la machine.
    if not request.include_logs:
        system_data["logs"] = []

    knowledge_context = ""
    knowledge_sources: list[str] = []

    if request.use_knowledge:
        try:
            qdrant_client = create_qdrant_client(settings)

            try:
                matches = search_knowledge(
                    qdrant_client,
                    settings,
                    problem_description,
                )
            finally:
                qdrant_client.close()

        except ValueError as error:
            raise HTTPException(
                status_code=503,
                detail=str(error),
            ) from None
        except Exception as error:
            if is_gemini_rate_limit_error(error):
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Quota Gemini dépassé. "
                        "Réessaie plus tard."
                    ),
                ) from None

            print(
                "Erreur de recherche documentaire : "
                f"{type(error).__name__}"
            )
            raise HTTPException(
                status_code=502,
                detail="La recherche documentaire a échoué.",
            ) from None

        knowledge_context = build_knowledge_context(
            matches
        )

        knowledge_sources = list(
            dict.fromkeys(
                match.source
                for match in matches
            )
        )

    prompt = build_diagnostic_prompt(
        system_data,
        knowledge_context=knowledge_context,
        problem_description=problem_description,
    )

    try:
        diagnosis = request_diagnostic(
            prompt,
            settings,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from None
    except Exception as error:
        if is_gemini_rate_limit_error(error):
            raise HTTPException(
                status_code=429,
                detail=(
                    "Quota Gemini dépassé. "
                    "Réessaie plus tard."
                ),
            ) from None

        # N'affiche ni la clé ni le contenu du prompt.
        print(f"Erreur Gemini : {type(error).__name__}")
        raise HTTPException(
            status_code=502,
            detail=(
                "Le service Gemini n'a pas pu "
                "produire de diagnostic."
            ),
        ) from None

    incident_saved = False
    incident_id = None

    if request.save_incident:
        redis_client = None

        try:
            redis_client = create_redis_client(
                settings
            )

            incident = save_incident(
                redis_client,
                settings,
                system_data=system_data,
                problem_description=(
                    problem_description
                ),
                diagnostic_model=(
                    settings.gemini_model
                ),
                diagnosis=diagnosis,
                knowledge_sources=(
                    knowledge_sources
                ),
                logs_included=request.include_logs,
            )

            incident_saved = True
            incident_id = incident.id

        except Exception as error:
            # Le diagnostic reste disponible si Redis échoue.
            print(
                "Erreur Redis pendant l'enregistrement : "
                f"{type(error).__name__}"
            )

        finally:
            if redis_client is not None:
                redis_client.close()

    return DiagnoseResponse(
        timestamp=system_data["timestamp"],
        model=settings.gemini_model,
        diagnosis=diagnosis,
        logs_sent=request.include_logs,
        knowledge_used=bool(knowledge_context),
        knowledge_sources=knowledge_sources,
        incident_saved=incident_saved,
        incident_id=incident_id,
    )