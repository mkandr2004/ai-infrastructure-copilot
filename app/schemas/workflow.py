"""Schémas des workflows d'investigation."""

from datetime import datetime
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.incident import IncidentMetrics


class WorkflowStatus(StrEnum):
    """États possibles d'un workflow complet."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStepStatus(StrEnum):
    """États possibles d'une étape du workflow."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class WorkflowStepName(StrEnum):
    """Étapes contrôlées d'une investigation."""

    COLLECT_METRICS = "collect_metrics"
    ANALYZE_HISTORY = "analyze_history"
    FIND_SIMILAR_INCIDENTS = "find_similar_incidents"
    SEARCH_KNOWLEDGE = "search_knowledge"
    BUILD_FINDINGS = "build_findings"
    PRODUCE_DIAGNOSIS = "produce_diagnosis"


class InvestigationTarget(StrEnum):
    """Ressource concernée par un constat."""

    GENERAL = "general"
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"


class FindingSeverity(StrEnum):
    """Niveau d'importance d'un constat."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class InvestigationWorkflowRequest(BaseModel):
    """Paramètres demandés pour démarrer une investigation."""

    model_config = ConfigDict(extra="forbid")

    confirm_external_send: bool = False
    include_logs: bool = False
    use_knowledge: bool = True
    problem_description: str = Field(
        min_length=1,
        max_length=2000,
    )

    @field_validator("problem_description")
    @classmethod
    def clean_problem_description(
        cls,
        value: str,
    ) -> str:
        """Nettoie et refuse une description vide."""

        clean_value = value.strip()

        if not clean_value:
            raise ValueError(
                "La description du problème est vide."
            )

        return clean_value


class WorkflowStepRecord(BaseModel):
    """Résultat d'une étape du workflow."""

    model_config = ConfigDict(extra="forbid")

    name: WorkflowStepName
    status: WorkflowStepStatus = (
        WorkflowStepStatus.PENDING
    )
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: str | None = None
    error: str | None = None


class InvestigationFinding(BaseModel):
    """Constat produit pendant l'investigation."""

    model_config = ConfigDict(extra="forbid")

    target: InvestigationTarget
    severity: FindingSeverity
    title: str
    details: str
    evidence: list[str] = Field(
        default_factory=list,
    )


class InvestigationWorkflowRecord(BaseModel):
    """Workflow complet conservé temporairement."""

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    status: WorkflowStatus
    problem_description: str
    logs_included_in_diagnosis: bool = False
    knowledge_requested: bool = True
    steps: list[WorkflowStepRecord] = Field(
        default_factory=list,
    )
    metrics: IncidentMetrics | None = None
    history_points_analyzed: int = Field(
        default=0,
        ge=0,
    )
    similar_incident_ids: list[str] = Field(
        default_factory=list,
    )
    knowledge_sources: list[str] = Field(
        default_factory=list,
    )
    findings: list[InvestigationFinding] = Field(
        default_factory=list,
    )
    diagnostic_model: str | None = None
    diagnosis: str | None = None
    error: str | None = None
