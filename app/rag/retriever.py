"""Recherche sémantique dans la documentation indexée."""

from dataclasses import dataclass

from qdrant_client import QdrantClient

from app.core.config import Settings
from app.rag.embeddings import (
    prepare_query_for_embedding,
    request_embedding,
)


@dataclass(frozen=True, slots=True)
class KnowledgeMatch:
    """Passage documentaire retourné par Qdrant."""

    point_id: str
    score: float
    source: str
    title: str
    text: str
    chunk_index: int


def search_knowledge(
    client: QdrantClient,
    settings: Settings,
    query: str,
    limit: int = 3,
) -> list[KnowledgeMatch]:
    """Retourne les passages les plus proches de la recherche."""

    if limit < 1:
        raise ValueError(
            "La limite doit être d'au moins un résultat."
        )

    if not client.collection_exists(
        collection_name=settings.qdrant_collection,
    ):
        raise ValueError(
            "La collection documentaire est absente."
        )

    embedding_input = prepare_query_for_embedding(
        query
    )
    query_vector = request_embedding(
        embedding_input,
        settings,
    )

    response = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=limit,
        score_threshold=settings.rag_score_threshold,
        with_payload=True,
        with_vectors=False,
    )

    matches: list[KnowledgeMatch] = []

    for point in response.points:
        payload = point.payload or {}

        required_fields = {
            "source",
            "title",
            "text",
            "chunk_index",
        }

        if not required_fields.issubset(payload):
            raise ValueError(
                f"Point Qdrant incomplet : {point.id}"
            )

        matches.append(
            KnowledgeMatch(
                point_id=str(point.id),
                score=float(point.score),
                source=str(payload["source"]),
                title=str(payload["title"]),
                text=str(payload["text"]),
                chunk_index=int(
                    payload["chunk_index"]
                ),
            )
        )

    return matches
