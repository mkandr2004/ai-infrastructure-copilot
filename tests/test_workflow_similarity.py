from datetime import UTC, datetime

import pytest

from app.schemas.incident import (
    IncidentMetrics,
    IncidentRecord,
)
from app.workflows.similarity import (
    description_similarity,
    find_similar_incidents,
    tokenize_description,
)


def make_incident(
    incident_id: str,
    description: str,
) -> IncidentRecord:
    created_at = datetime(
        2026,
        11,
        10,
        12,
        0,
        tzinfo=UTC,
    )

    return IncidentRecord(
        id=incident_id,
        created_at=created_at,
        expires_at=created_at,
        collected_at=created_at,
        problem_description=description,
        metrics=IncidentMetrics(
            cpu_percent=20.0,
            memory_percent=30.0,
            disk_percent=40.0,
        ),
        diagnostic_model="modele-test",
        diagnosis="Diagnostic simulé.",
    )


def test_tokenize_description_removes_common_words():
    tokens = tokenize_description(
        "Le processeur est à 95 pour cent"
    )

    assert "le" not in tokens
    assert "est" not in tokens
    assert "processeur" in tokens
    assert "95" in tokens


def test_description_similarity_detects_shared_terms():
    score = description_similarity(
        "CPU élevé avec processus Python",
        "Processus Python avec CPU élevé",
    )

    assert score == 1.0


def test_description_similarity_rejects_unrelated_text():
    score = description_similarity(
        "CPU élevé",
        "Disque complètement saturé",
    )

    assert score == 0.0


def test_find_similar_incidents_filters_unrelated_entries():
    incidents = [
        make_incident(
            "cpu-1",
            "CPU élevé avec processus Python",
        ),
        make_incident(
            "memory-1",
            "Mémoire RAM complètement saturée",
        ),
        make_incident(
            "cpu-2",
            "Charge CPU élevée",
        ),
    ]

    results = find_similar_incidents(
        "CPU élevé avec processus Python",
        incidents,
    )

    assert [
        incident.id
        for incident in results
    ] == [
        "cpu-1",
        "cpu-2",
    ]


def test_find_similar_incidents_respects_limit():
    incidents = [
        make_incident(
            "cpu-1",
            "CPU élevé",
        ),
        make_incident(
            "cpu-2",
            "CPU élevé",
        ),
    ]

    results = find_similar_incidents(
        "CPU élevé",
        incidents,
        limit=1,
    )

    assert len(results) == 1


def test_find_similar_incidents_validates_options():
    incident = make_incident(
        "cpu-1",
        "CPU élevé",
    )

    with pytest.raises(
        ValueError,
        match="limite",
    ):
        find_similar_incidents(
            "CPU élevé",
            [incident],
            limit=0,
        )

    with pytest.raises(
        ValueError,
        match="score",
    ):
        find_similar_incidents(
            "CPU élevé",
            [incident],
            minimum_score=2.0,
        )
