from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.collectors.system import collect_system_metrics
from app.core.config import get_settings
from app.db.database import get_db
from app.models.metric import MetricSnapshot
from app.schemas.metric import MetricSnapshotResponse
from app.services.diagnosis import (
    build_diagnostic_prompt,
    request_diagnostic,
)
from app.services.metrics import list_metric_snapshots


app = FastAPI(title="AI Infrastructure Copilot")


class DiagnoseRequest(BaseModel):
    confirm_external_send: bool = False
    include_logs: bool = False


class DiagnoseResponse(BaseModel):
    timestamp: str
    model: str
    diagnosis: str
    logs_sent: bool


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


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(request: DiagnoseRequest) -> DiagnoseResponse:
    if not request.confirm_external_send:
        raise HTTPException(
            status_code=400,
            detail="Confirme explicitement l'envoi à Gemini.",
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

    prompt = build_diagnostic_prompt(system_data)

    try:
        diagnosis = request_diagnostic(prompt, settings)
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from None
    except Exception as error:
        # N'affiche ni la clé ni le contenu du prompt.
        print(f"Erreur Gemini : {type(error).__name__}")
        raise HTTPException(
            status_code=502,
            detail="Le service Gemini n'a pas pu produire de diagnostic.",
        ) from None

    return DiagnoseResponse(
        timestamp=system_data["timestamp"],
        model=settings.gemini_model,
        diagnosis=diagnosis,
        logs_sent=request.include_logs,
    )