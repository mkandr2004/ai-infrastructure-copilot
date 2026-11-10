"""Notification sortante optionnelle des alertes acceptées."""

import httpx

from app.core.config import Settings
from app.schemas.alert import AlertRecord


def send_alert_notification(
    settings: Settings,
    alerts: list[AlertRecord],
) -> bool:
    """Envoie un résumé vers le webhook explicitement configuré."""

    webhook_url = (
        settings.notification_webhook_url or ""
    ).strip()

    if not webhook_url or not alerts:
        return False

    payload = {
        "source": "ai-infrastructure-copilot",
        "alerts": [
            {
                "fingerprint": alert.fingerprint,
                "status": alert.status,
                "name": alert.labels.get("alertname", "Alerte"),
                "severity": alert.labels.get("severity", "unknown"),
                "summary": alert.annotations.get("summary", ""),
                "starts_at": alert.starts_at.isoformat(),
            }
            for alert in alerts
        ],
    }

    with httpx.Client(
        timeout=settings.notification_timeout_seconds,
    ) as client:
        response = client.post(webhook_url, json=payload)
        response.raise_for_status()

    return True
