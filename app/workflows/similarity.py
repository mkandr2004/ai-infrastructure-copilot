"""Recherche déterministe d'incidents similaires."""

import re
from collections.abc import Sequence

from app.schemas.incident import IncidentRecord


TOKEN_PATTERN = re.compile(
    r"[a-zÀ-ÿ0-9]+",
    flags=re.IGNORECASE,
)

STOP_WORDS = {
    "a",
    "au",
    "aux",
    "avec",
    "ce",
    "ces",
    "dans",
    "de",
    "des",
    "du",
    "en",
    "est",
    "et",
    "la",
    "le",
    "les",
    "pour",
    "que",
    "qui",
    "sur",
    "un",
    "une",
}


def tokenize_description(
    description: str,
) -> set[str]:
    """Transforme une description en mots comparables."""

    return {
        token.casefold()
        for token in TOKEN_PATTERN.findall(description)
        if token.casefold() not in STOP_WORDS
    }


def description_similarity(
    first_description: str,
    second_description: str,
) -> float:
    """Calcule une similarité de Jaccard entre deux textes."""

    first_tokens = tokenize_description(
        first_description
    )
    second_tokens = tokenize_description(
        second_description
    )

    if not first_tokens or not second_tokens:
        return 0.0

    common_tokens = (
        first_tokens & second_tokens
    )
    all_tokens = (
        first_tokens | second_tokens
    )

    return len(common_tokens) / len(all_tokens)


def find_similar_incidents(
    problem_description: str,
    incidents: Sequence[IncidentRecord],
    *,
    limit: int = 5,
    minimum_score: float = 0.15,
) -> list[IncidentRecord]:
    """Retourne les incidents textuellement similaires."""

    if limit < 1:
        raise ValueError(
            "La limite doit être d'au moins un incident."
        )

    if not 0.0 <= minimum_score <= 1.0:
        raise ValueError(
            "Le score minimal doit être compris entre 0 et 1."
        )

    scored_incidents: list[
        tuple[float, IncidentRecord]
    ] = []

    for incident in incidents:
        score = description_similarity(
            problem_description,
            incident.problem_description,
        )

        if score >= minimum_score:
            scored_incidents.append(
                (
                    score,
                    incident,
                )
            )

    scored_incidents.sort(
        key=lambda item: (
            item[0],
            item[1].created_at.timestamp(),
        ),
        reverse=True,
    )

    return [
        incident
        for _, incident in scored_incidents[:limit]
    ]
