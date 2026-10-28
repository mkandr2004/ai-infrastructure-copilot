"""Enregistrement et lecture des incidents dans Redis."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from redis import Redis

from app.core.config import Settings
from app.schemas.incident import (
    IncidentMetrics,
    IncidentRecord,
)


def incident_key(
    settings: Settings,
    incident_id: str,
) -> str:
    """Construit la clé Redis d'un incident."""

    return (
        f"{settings.redis_key_prefix}:"
        f"incident:{incident_id}"
    )


def incident_index_key(
    settings: Settings,
) -> str:
    """Construit la clé Redis de l'index des incidents."""

    return (
        f"{settings.redis_key_prefix}:"
        "incidents:index"
    )


def save_incident(
    client: Redis,
    settings: Settings,
    *,
    system_data: dict,
    problem_description: str,
    diagnostic_model: str,
    diagnosis: str,
    knowledge_sources: list[str],
    logs_included: bool,
) -> IncidentRecord:
    """Enregistre un incident avec expiration automatique."""

    clean_description = problem_description.strip()
    clean_diagnosis = diagnosis.strip()

    if not clean_description:
        raise ValueError(
            "La description de l'incident est vide."
        )

    if not clean_diagnosis:
        raise ValueError(
            "Le diagnostic de l'incident est vide."
        )

    if settings.incident_ttl_seconds < 1:
        raise ValueError(
            "La durée de conservation doit être positive."
        )

    created_at = datetime.now(UTC)
    expires_at = created_at + timedelta(
        seconds=settings.incident_ttl_seconds,
    )

    incident = IncidentRecord(
        id=str(uuid4()),
        created_at=created_at,
        expires_at=expires_at,
        collected_at=datetime.fromisoformat(
            system_data["timestamp"],
        ),
        problem_description=clean_description,
        metrics=IncidentMetrics(
            cpu_percent=system_data["cpu"]["percent"],
            memory_percent=(
                system_data["memory"]["percent"]
            ),
            disk_percent=system_data["disk"]["percent"],
        ),
        diagnostic_model=diagnostic_model,
        diagnosis=clean_diagnosis,
        knowledge_sources=list(
            dict.fromkeys(knowledge_sources)
        ),
        logs_included=logs_included,
    )

    key = incident_key(
        settings,
        incident.id,
    )
    index_key = incident_index_key(settings)

    with client.pipeline(
        transaction=True,
    ) as pipeline:
        pipeline.set(
            key,
            incident.model_dump_json(),
            ex=settings.incident_ttl_seconds,
        )
        pipeline.zadd(
            index_key,
            {
                incident.id: (
                    incident.created_at.timestamp()
                ),
            },
        )
        pipeline.expire(
            index_key,
            settings.incident_ttl_seconds,
        )
        pipeline.execute()

    return incident


def get_incident(
    client: Redis,
    settings: Settings,
    incident_id: str,
) -> IncidentRecord | None:
    """Retourne un incident ou None s'il a expiré."""

    raw_incident = client.get(
        incident_key(
            settings,
            incident_id,
        )
    )

    if raw_incident is None:
        client.zrem(
            incident_index_key(settings),
            incident_id,
        )
        return None

    return IncidentRecord.model_validate_json(
        raw_incident
    )


def list_incidents(
    client: Redis,
    settings: Settings,
    limit: int = 20,
) -> list[IncidentRecord]:
    """Retourne les incidents les plus récents."""

    if limit < 1:
        raise ValueError(
            "La limite doit être d'au moins un incident."
        )

    index_key = incident_index_key(settings)

    incident_ids = client.zrevrange(
        index_key,
        0,
        -1,
    )

    incidents: list[IncidentRecord] = []
    expired_ids: list[str] = []

    for incident_id in incident_ids:
        raw_incident = client.get(
            incident_key(
                settings,
                incident_id,
            )
        )

        if raw_incident is None:
            expired_ids.append(incident_id)
            continue

        incidents.append(
            IncidentRecord.model_validate_json(
                raw_incident
            )
        )

        if len(incidents) >= limit:
            break

    if expired_ids:
        client.zrem(
            index_key,
            *expired_ids,
        )

    return incidents
