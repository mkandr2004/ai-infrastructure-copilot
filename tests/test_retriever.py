from types import SimpleNamespace
from unittest.mock import patch

import pytest
from qdrant_client import QdrantClient, models

from app.rag.retriever import search_knowledge
from app.rag.vector_store import (
    ensure_knowledge_collection,
)


def create_test_settings():
    return SimpleNamespace(
        qdrant_collection="knowledge_test",
        embedding_dimensions=3,
        rag_score_threshold=0.68,
    )


def insert_test_points(
    client,
    settings,
):
    ensure_knowledge_collection(
        client,
        settings,
    )

    client.upsert(
        collection_name=settings.qdrant_collection,
        wait=True,
        points=[
            models.PointStruct(
                id=1,
                vector=[1.0, 0.0, 0.0],
                payload={
                    "source": "cpu.md",
                    "title": "Diagnostic CPU",
                    "text": "Vérifier les processus.",
                    "chunk_index": 0,
                },
            ),
            models.PointStruct(
                id=2,
                vector=[0.0, 1.0, 0.0],
                payload={
                    "source": "disk.md",
                    "title": "Diagnostic disque",
                    "text": "Vérifier l'espace.",
                    "chunk_index": 0,
                },
            ),
        ],
    )


def test_search_knowledge_returns_relevant_match():
    settings = create_test_settings()
    client = QdrantClient(":memory:")

    try:
        insert_test_points(
            client,
            settings,
        )

        with patch(
            "app.rag.retriever.request_embedding",
            side_effect=[
                [1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
        ) as mock_embedding:
            cpu_matches = search_knowledge(
                client,
                settings,
                "CPU saturé",
                limit=3,
            )
            unrelated_matches = search_knowledge(
                client,
                settings,
                "Question inconnue",
                limit=3,
            )

        assert len(cpu_matches) == 1

        match = cpu_matches[0]

        assert match.point_id == "1"
        assert match.score == pytest.approx(1.0)
        assert match.source == "cpu.md"
        assert match.title == "Diagnostic CPU"
        assert match.text == (
            "Vérifier les processus."
        )
        assert match.chunk_index == 0

        assert unrelated_matches == []

        assert mock_embedding.call_count == 2
        mock_embedding.assert_any_call(
            (
                "task: search result | "
                "query: CPU saturé"
            ),
            settings,
        )
    finally:
        client.close()


def test_search_knowledge_rejects_invalid_limit():
    settings = create_test_settings()
    client = QdrantClient(":memory:")

    try:
        with pytest.raises(
            ValueError,
            match="limite",
        ):
            search_knowledge(
                client,
                settings,
                "CPU saturé",
                limit=0,
            )
    finally:
        client.close()


def test_search_knowledge_requires_collection():
    settings = create_test_settings()
    client = QdrantClient(":memory:")

    try:
        with pytest.raises(
            ValueError,
            match="collection documentaire",
        ):
            search_knowledge(
                client,
                settings,
                "CPU saturé",
            )
    finally:
        client.close()
