"""Commande de recherche dans la documentation Qdrant."""

import argparse

from app.core.config import get_settings
from app.rag.retriever import search_knowledge
from app.rag.vector_store import (
    create_qdrant_client,
)


def main() -> int:
    """Recherche des passages documentaires pertinents."""

    parser = argparse.ArgumentParser(
        description=(
            "Recherche dans la documentation indexée."
        )
    )
    parser.add_argument(
        "query",
        help="Question ou problème à rechercher.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Nombre maximal de résultats.",
    )
    parser.add_argument(
        "--confirm-external-send",
        action="store_true",
        help=(
            "Confirme l'envoi de la question "
            "à Gemini pour créer son embedding."
        ),
    )
    arguments = parser.parse_args()

    print("Recherche :", arguments.query)
    print("Limite :", arguments.limit)

    if not arguments.confirm_external_send:
        print()
        print("La recherche n'a pas été envoyée.")
        print(
            "Relance avec --confirm-external-send "
            "pour créer l'embedding."
        )
        return 0

    settings = get_settings()
    client = create_qdrant_client(
        settings
    )

    try:
        matches = search_knowledge(
            client,
            settings,
            arguments.query,
            limit=arguments.limit,
        )

    except Exception as error:
        print(
            "Échec de la recherche :",
            type(error).__name__,
        )
        return 1

    finally:
        client.close()

    if not matches:
        print()
        print(
            "Aucun passage suffisamment pertinent."
        )
        return 0

    print()
    print("Passages trouvés :", len(matches))

    for position, match in enumerate(
        matches,
        start=1,
    ):
        print()
        print(
            f"{position}. {match.title}"
        )
        print("Source :", match.source)
        print(
            "Score :",
            round(match.score, 4),
        )
        print(match.text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
