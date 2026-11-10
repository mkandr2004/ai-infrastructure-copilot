"""Stockage temporaire des alertes Alertmanager dans Redis."""

from datetime import UTC, datetime

from redis import Redis

from app.core.config import Settings
from app.schemas.alert import AlertRecord, AlertmanagerAlert


def alert_key(settings: Settings, fingerprint: str) -> str:
    """Construit la clé Redis d’une alerte."""

    return f"{settings.redis_key_prefix}:alert:{fingerprint}"


def alert_index_key(settings: Settings) -> str:
    """Construit la clé Redis de l’index des alertes."""

    return f"{settings.redis_key_prefix}:alerts:index"


def save_alert(
    client: Redis,
    settings: Settings,
    alert: AlertmanagerAlert,
) -> AlertRecord:
    """Normalise et conserve une alerte avec une durée limitée."""

    if settings.alert_ttl_seconds < 1:
        raise ValueError("La durée de conservation des alertes doit être positive.")

    received_at = datetime.now(UTC)
    record = AlertRecord(
        fingerprint=alert.fingerprint,
        status=alert.status,
        labels=alert.labels,
        annotations=alert.annotations,
        starts_at=alert.startsAt,
        ends_at=alert.endsAt,
        received_at=received_at,
        generator_url=alert.generatorURL,
    )

    with client.pipeline(transaction=True) as pipeline:
        pipeline.set(
            alert_key(settings, record.fingerprint),
            record.model_dump_json(),
            ex=settings.alert_ttl_seconds,
        )
        pipeline.zadd(
            alert_index_key(settings),
            {record.fingerprint: received_at.timestamp()},
        )
        pipeline.expire(
            alert_index_key(settings),
            settings.alert_ttl_seconds,
        )
        pipeline.execute()

    return record


def list_alerts(
    client: Redis,
    settings: Settings,
    limit: int = 50,
    status: str | None = None,
) -> list[AlertRecord]:
    """Retourne les alertes les plus récentes, avec filtre optionnel."""

    if limit < 1:
        raise ValueError("La limite doit être positive.")

    index_key = alert_index_key(settings)
    fingerprints = client.zrevrange(index_key, 0, -1)
    records: list[AlertRecord] = []
    expired: list[str] = []

    for fingerprint in fingerprints:
        raw_record = client.get(alert_key(settings, fingerprint))

        if raw_record is None:
            expired.append(fingerprint)
            continue

        record = AlertRecord.model_validate_json(raw_record)

        if status is not None and record.status != status:
            continue

        records.append(record)

        if len(records) >= limit:
            break

    if expired:
        client.zrem(index_key, *expired)

    return records
