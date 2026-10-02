"""Transformation des passages documentaires en points Qdrant."""

from qdrant_client import QdrantClient, models

from app.core.config import Settings
from app.rag.documents import DocumentChunk
from app.rag.embeddings import (
    prepare_document_for_embedding,
    request_embedding,
)
from app.rag.vector_store import (
    ensure_knowledge_collection,
)


def list_collection_point_ids(
    client: QdrantClient,
    collection_name: str,
) -> set[str]:
    """Retourne tous les identifiants présents dans une collection."""

    point_ids: set[str] = set()
    offset = None

    while True:
        records, next_offset = client.scroll(
            collection_name=collection_name,
            offset=offset,
            limit=100,
            with_payload=False,
            with_vectors=False,
        )

        point_ids.update(
            str(record.id)
            for record in records
        )

        if next_offset is None:
            return point_ids

        offset = next_offset


def index_chunks(
    client: QdrantClient,
    settings: Settings,
    chunks: list[DocumentChunk],
) -> int:
    """Génère, enregistre et synchronise les passages documentaires."""

    if not chunks:
        raise ValueError(
            "Aucun passage à indexer."
        )

    ensure_knowledge_collection(
        client,
        settings,
    )

    points: list[models.PointStruct] = []

    for chunk in chunks:
        embedding_input = (
            prepare_document_for_embedding(
                chunk.title,
                chunk.text,
            )
        )

        vector = request_embedding(
            embedding_input,
            settings,
        )

        points.append(
            models.PointStruct(
                id=chunk.point_id,
                vector=vector,
                payload={
                    "source": chunk.source,
                    "title": chunk.title,
                    "text": chunk.text,
                    "chunk_index": (
                        chunk.chunk_index
                    ),
                    "embedding_model": (
                        settings.gemini_embedding_model
                    ),
                },
            )
        )

    client.upsert(
        collection_name=(
            settings.qdrant_collection
        ),
        points=points,
        wait=True,
    )

    expected_point_ids = {
        chunk.point_id
        for chunk in chunks
    }

    stored_point_ids = list_collection_point_ids(
        client,
        settings.qdrant_collection,
    )

    stale_point_ids = sorted(
        stored_point_ids - expected_point_ids
    )

    if stale_point_ids:
        client.delete(
            collection_name=(
                settings.qdrant_collection
            ),
            points_selector=models.PointIdsList(
                points=stale_point_ids,
            ),
            wait=True,
        )

    return len(points)