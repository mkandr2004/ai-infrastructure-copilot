from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.memory.incidents import (
    get_incident,
    incident_index_key,
    incident_key,
    list_incidents,
    save_incident,
)
from app.schemas.incident import (
    IncidentMetrics,
    IncidentRecord,
)


def make_settings():
    return SimpleNamespace(
        redis_key_prefix="test_copilot",
        incident_ttl_seconds=3600,
    )


def make_incident(
    incident_id: str,
) -> IncidentRecord:
    created_at = datetime(
        2026,
        10,
        28,
        12,
        0,
        tzinfo=UTC,
    )

    return IncidentRecord(
        id=incident_id,
        created_at=created_at,
        expires_at=created_at,
        collected_at=created_at,
        problem_description="CPU élevé",
        metrics=IncidentMetrics(
            cpu_percent=95.0,
            memory_percent=40.0,
            disk_percent=30.0,
        ),
        diagnostic_model="modele-test",
        diagnosis="Diagnostic simulé",
        knowledge_sources=["cpu.md"],
        logs_included=False,
    )


def test_save_incident_uses_ttl_and_index():
    settings = make_settings()
    client = MagicMock()
    pipeline = MagicMock()

    client.pipeline.return_value.__enter__.return_value = (
        pipeline
    )

    system_data = {
        "timestamp": "2026-10-28T12:00:00+00:00",
        "cpu": {"percent": 95.0},
        "memory": {"percent": 40.0},
        "disk": {"percent": 30.0},
    }

    incident = save_incident(
        client,
        settings,
        system_data=system_data,
        problem_description=" CPU élevé ",
        diagnostic_model="modele-test",
        diagnosis=" Diagnostic simulé ",
        knowledge_sources=[
            "cpu.md",
            "cpu.md",
        ],
        logs_included=False,
    )

    stored_key = incident_key(
        settings,
        incident.id,
    )
    index_key = incident_index_key(settings)

    pipeline.set.assert_called_once()

    set_call = pipeline.set.call_args

    assert set_call.args[0] == stored_key
    assert set_call.kwargs["ex"] == 3600

    stored_incident = (
        IncidentRecord.model_validate_json(
            set_call.args[1]
        )
    )

    assert stored_incident.problem_description == (
        "CPU élevé"
    )
    assert stored_incident.diagnosis == (
        "Diagnostic simulé"
    )
    assert stored_incident.knowledge_sources == [
        "cpu.md"
    ]

    pipeline.zadd.assert_called_once_with(
        index_key,
        {
            incident.id: (
                incident.created_at.timestamp()
            ),
        },
    )
    pipeline.expire.assert_called_once_with(
        index_key,
        3600,
    )
    pipeline.execute.assert_called_once_with()


def test_get_incident_returns_stored_incident():
    settings = make_settings()
    client = MagicMock()
    expected = make_incident("incident-1")

    client.get.return_value = (
        expected.model_dump_json()
    )

    result = get_incident(
        client,
        settings,
        "incident-1",
    )

    assert result == expected
    client.zrem.assert_not_called()


def test_get_incident_removes_expired_id():
    settings = make_settings()
    client = MagicMock()
    client.get.return_value = None

    result = get_incident(
        client,
        settings,
        "expired-1",
    )

    assert result is None
    client.zrem.assert_called_once_with(
        incident_index_key(settings),
        "expired-1",
    )


def test_list_incidents_skips_expired_entries():
    settings = make_settings()
    client = MagicMock()

    newest = make_incident("newest")
    oldest = make_incident("oldest")

    client.zrevrange.return_value = [
        "newest",
        "expired",
        "oldest",
    ]

    client.get.side_effect = [
        newest.model_dump_json(),
        None,
        oldest.model_dump_json(),
    ]

    result = list_incidents(
        client,
        settings,
        limit=2,
    )

    assert [
        incident.id
        for incident in result
    ] == [
        "newest",
        "oldest",
    ]

    client.zrem.assert_called_once_with(
        incident_index_key(settings),
        "expired",
    )


def test_list_incidents_rejects_invalid_limit():
    settings = make_settings()
    client = MagicMock()

    with pytest.raises(
        ValueError,
        match="limite",
    ):
        list_incidents(
            client,
            settings,
            limit=0,
        )
