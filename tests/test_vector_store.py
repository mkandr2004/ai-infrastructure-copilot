from types import SimpleNamespace

from qdrant_client import QdrantClient, models

from app.rag.vector_store import (
    create_qdrant_client,
    ensure_knowledge_collection,
)


def test_create_qdrant_client_uses_local_path(tmp_path):
    settings = SimpleNamespace(
        qdrant_path=tmp_path / "qdrant",
    )

    client = create_qdrant_client(settings)

    try:
        assert settings.qdrant_path.exists()
    finally:
        client.close()


def test_ensure_knowledge_collection_is_idempotent():
    settings = SimpleNamespace(
        qdrant_collection="infrastructure_knowledge_test",
        embedding_dimensions=768,
    )
    client = QdrantClient(":memory:")

    try:
        created_first = ensure_knowledge_collection(
            client,
            settings,
        )
        created_second = ensure_knowledge_collection(
            client,
            settings,
        )

        collection = client.get_collection(
            collection_name=settings.qdrant_collection,
        )
        vector_config = collection.config.params.vectors

        assert created_first is True
        assert created_second is False
        assert vector_config.size == 768
        assert vector_config.distance == models.Distance.COSINE
        assert collection.points_count == 0
    finally:
        client.close()
