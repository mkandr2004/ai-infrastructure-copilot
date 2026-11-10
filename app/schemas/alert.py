"""Schémas des alertes reçues depuis Alertmanager."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AlertmanagerAlert(BaseModel):
    """Alerte individuelle au format webhook Alertmanager."""

    model_config = ConfigDict(extra="ignore")

    status: str
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: datetime
    endsAt: datetime | None = None
    generatorURL: str = ""
    fingerprint: str


class AlertmanagerWebhook(BaseModel):
    """Lot d’alertes envoyé par Alertmanager."""

    model_config = ConfigDict(extra="ignore")

    status: str
    receiver: str = ""
    alerts: list[AlertmanagerAlert]
    groupLabels: dict[str, str] = Field(default_factory=dict)
    commonLabels: dict[str, str] = Field(default_factory=dict)
    commonAnnotations: dict[str, str] = Field(default_factory=dict)
    externalURL: str = ""
    version: str = "4"
    groupKey: str = ""
    truncatedAlerts: int = 0


class AlertRecord(BaseModel):
    """Alerte normalisée et conservée temporairement dans Redis."""

    model_config = ConfigDict(extra="forbid")

    fingerprint: str
    status: str
    labels: dict[str, str]
    annotations: dict[str, str]
    starts_at: datetime
    ends_at: datetime | None = None
    received_at: datetime
    generator_url: str = ""


class AlertWebhookResponse(BaseModel):
    """Accusé de réception retourné à Alertmanager."""

    accepted: int = Field(ge=0)
    notification_sent: bool = False
    notification_error: str | None = None
