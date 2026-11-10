"""Routes de réception et de consultation des alertes."""

import secrets

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.alerts.notifications import send_alert_notification
from app.alerts.storage import list_alerts, save_alert
from app.core.config import get_settings
from app.memory.redis_client import create_redis_client
from app.schemas.alert import (
    AlertRecord,
    AlertmanagerWebhook,
    AlertWebhookResponse,
)


router = APIRouter(prefix="/alerts", tags=["alerts"])


def validate_webhook_token(
    authorization: str | None,
    expected_token: str,
) -> None:
    """Valide le secret partagé sans comparaison temporelle naïve."""

    scheme, _, supplied_token = (authorization or "").partition(" ")

    if (
        scheme.lower() != "bearer"
        or not supplied_token
        or not secrets.compare_digest(supplied_token, expected_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton du webhook d’alertes invalide.",
        )


@router.post(
    "/webhook",
    response_model=AlertWebhookResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def receive_alerts(
    webhook: AlertmanagerWebhook,
    authorization: str | None = Header(default=None),
) -> AlertWebhookResponse:
    """Authentifie, normalise et persiste un lot Alertmanager."""

    settings = get_settings()
    configured_token = (
        settings.alert_webhook_token.get_secret_value().strip()
        if settings.alert_webhook_token is not None
        else ""
    )

    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook Alertmanager non configuré.",
        )

    validate_webhook_token(authorization, configured_token)
    redis_client = None

    try:
        redis_client = create_redis_client(settings)
        records = [
            save_alert(redis_client, settings, alert)
            for alert in webhook.alerts
        ]
    except Exception as error:
        print(f"Erreur Redis pendant l’alerting : {type(error).__name__}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le stockage des alertes est indisponible.",
        ) from None
    finally:
        if redis_client is not None:
            redis_client.close()

    notification_sent = False
    notification_error = None

    try:
        notification_sent = send_alert_notification(settings, records)
    except Exception as error:
        notification_error = type(error).__name__
        print(f"Erreur du webhook de notification : {notification_error}")

    return AlertWebhookResponse(
        accepted=len(records),
        notification_sent=notification_sent,
        notification_error=notification_error,
    )


@router.get("", response_model=list[AlertRecord])
def get_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    alert_status: str | None = Query(default=None, alias="status"),
) -> list[AlertRecord]:
    """Expose les alertes récentes au dashboard."""

    settings = get_settings()
    redis_client = None

    try:
        redis_client = create_redis_client(settings)
        return list_alerts(
            redis_client,
            settings,
            limit=limit,
            status=alert_status,
        )
    except Exception as error:
        print(f"Erreur Redis pendant la lecture des alertes : {type(error).__name__}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La mémoire des alertes est indisponible.",
        ) from None
    finally:
        if redis_client is not None:
            redis_client.close()
