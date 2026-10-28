"""Schémas des incidents conservés temporairement."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IncidentMetrics(BaseModel):
    """Résumé des métriques associées à un incident."""

    model_config = ConfigDict(extra="forbid")

    cpu_percent: float
    memory_percent: float
    disk_percent: float


class IncidentRecord(BaseModel):
    """Incident complet conservé dans Redis."""

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime
    expires_at: datetime
    collected_at: datetime
    problem_description: str
    metrics: IncidentMetrics
    diagnostic_model: str
    diagnosis: str
    knowledge_sources: list[str] = Field(
        default_factory=list,
    )
    logs_included: bool = False
