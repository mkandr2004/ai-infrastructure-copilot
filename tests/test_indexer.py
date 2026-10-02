from types import SimpleNamespace
from unittest.mock import patch

import pytest
from qdrant_client import QdrantClient

from app.rag.documents import DocumentChunk
from app.rag.indexer import index_chunks


def test_index_chunks_upserts_document_points():
    settings = SimpleNamespace(
        qdrant_collection="knowledge_test",
        embedding_dimensions=3,
        gemini_embedding_model="modele-test",
    )
    client = QdrantClient(":memory:")

    chunks = [
        DocumentChunk(
            point_id=(
                "11111111-1111-1111-1111-111111111111"
            ),
            source="cpu.md",
            title="Diagnostic CPU",
            text="Vérifier les processus.",
            chunk_index=0,
        ),
        DocumentChunk(
            point_id=(
                "22222222-2222-2222-2222-222222222222"
            ),
            source="disk.md",
            title="Diagnostic disque",
            text="Vérifier l'espace disponible.",
            chunk_index=0,
        ),
    ]

    fake_vectors = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ]

    try:
        with patch(
            "app.rag.indexer.request_embedding",
            side_effect=fake_vectors,
        ) as mock_embedding:
            first_count = index_chunks(
                client,
                settings,
                chunks,
            )
            second_count = index_chunks(
                client,
                settings,
                chunks,
            )

        collection = client.get_collection(
            collection_name=(
                settings.qdrant_collection
            )
        )

        records, _ = client.scroll(
            collection_name=(
                settings.qdrant_collection
            ),
            limit=10,
            with_payload=True,
            with_vectors=True,
        )

        records_by_id = {
            str(record.id): record
            for record in records
        }

        cpu_record = records_by_id[
            chunks[0].point_id
        ]

        assert first_count == 2
        assert second_count == 2
        assert collection.points_count == 2
        assert mock_embedding.call_count == 4

        assert cpu_record.payload == {
            "source": "cpu.md",
            "title": "Diagnostic CPU",
            "text": "Vérifier les processus.",
            "chunk_index": 0,
            "embedding_model": "modele-test",
        }
        assert cpu_record.vector == [
            1.0,
            0.0,
            0.0,
        ]
    finally:
        client.close()


def test_index_chunks_rejects_empty_list():
    settings = SimpleNamespace(
        qdrant_collection="knowledge_test",
        embedding_dimensions=3,
        gemini_embedding_model="modele-test",
    )
    client = QdrantClient(":memory:")

    try:
        with pytest.raises(
            ValueError,
            match="Aucun passage",
        ):
            index_chunks(
                client,
                settings,
                [],
            )
    finally:
        client.close()


def test_index_chunks_removes_stale_points():
    settings = SimpleNamespace(
        qdrant_collection="knowledge_test",
        embedding_dimensions=3,
        gemini_embedding_model="modele-test",
    )
    client = QdrantClient(":memory:")

    cpu_chunk = DocumentChunk(
        point_id=(
            "11111111-1111-1111-1111-111111111111"
        ),
        source="cpu.md",
        title="Diagnostic CPU",
        text="Vérifier les processus CPU.",
        chunk_index=0,
    )

    disk_chunk = DocumentChunk(
        point_id=(
            "22222222-2222-2222-2222-222222222222"
        ),
        source="disk.md",
        title="Diagnostic disque",
        text="Vérifier l'espace disque.",
        chunk_index=0,
    )

    fake_vectors = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [1.0, 0.0, 0.0],
    ]

    try:
        with patch(
            "app.rag.indexer.request_embedding",
            side_effect=fake_vectors,
        ):
            index_chunks(
                client,
                settings,
                [cpu_chunk, disk_chunk],
            )

            index_chunks(
                client,
                settings,
                [cpu_chunk],
            )

        collection = client.get_collection(
            collection_name=(
                settings.qdrant_collection
            )
        )

        records, _ = client.scroll(
            collection_name=(
                settings.qdrant_collection
            ),
            limit=10,
            with_payload=True,
            with_vectors=False,
        )

        stored_ids = {
            str(record.id)
            for record in records
        }

        assert collection.points_count == 1
        assert stored_ids == {
            cpu_chunk.point_id,
        }
    finally:
        client.close()