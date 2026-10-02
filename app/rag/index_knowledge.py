"""Commande d'indexation de la documentation dans Qdrant."""

import argparse

from app.core.config import get_settings
from app.rag.documents import load_markdown_chunks
from app.rag.indexer import index_chunks
from app.rag.vector_store import (
    create_qdrant_client,
)


def main() -> int:
    """Affiche ou indexe les documents locaux."""

    parser = argparse.ArgumentParser(
        description=(
            "Indexe la documentation locale dans Qdrant."
        )
    )
    parser.add_argument(
        "--confirm-external-send",
        action="store_true",
        help=(
            "Confirme l'envoi des passages "
            "documentaires à Gemini."
        ),
    )
    arguments = parser.parse_args()

    settings = get_settings()

    chunks = load_markdown_chunks(
        settings.knowledge_path
    )

    print(
        "Passages documentaires trouvés :",
        len(chunks),
    )

    for chunk in chunks:
        print(
            f"- {chunk.source} : {chunk.title}"
        )

    if not arguments.confirm_external_send:
        print()
        print("Aucun document n'a été envoyé.")
        print(
            "Relance avec --confirm-external-send "
            "pour créer les embeddings."
        )
        return 0

    print()
    print(
        "Envoi confirmé. Création des embeddings..."
    )

    client = create_qdrant_client(
        settings
    )

    try:
        indexed_count = index_chunks(
            client,
            settings,
            chunks,
        )

        collection = client.get_collection(
            collection_name=(
                settings.qdrant_collection
            )
        )
        points_count = collection.points_count

    except Exception as error:
        print(
            "Échec de l'indexation :",
            type(error).__name__,
        )
        return 1

    finally:
        client.close()

    print("Indexation terminée.")
    print(
        "Passages traités :",
        indexed_count,
    )
    print(
        "Points présents dans Qdrant :",
        points_count,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
