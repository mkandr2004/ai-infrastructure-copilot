"""Connexion à Qdrant et gestion de la collection documentaire."""

from qdrant_client import QdrantClient, models

from app.core.config import Settings


def create_qdrant_client(settings: Settings) -> QdrantClient:
    """Ouvre le stockage Qdrant local."""

    settings.qdrant_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return QdrantClient(
        path=str(settings.qdrant_path),
    )


def ensure_knowledge_collection(
    client: QdrantClient,
    settings: Settings,
) -> bool:
    """Crée la collection documentaire si elle n'existe pas."""

    if client.collection_exists(
        collection_name=settings.qdrant_collection,
    ):
        return False

    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=models.VectorParams(
            size=settings.embedding_dimensions,
            distance=models.Distance.COSINE,
        ),
    )

    return True
