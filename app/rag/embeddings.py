"""Préparation des textes et génération des embeddings Gemini."""

from google import genai
from google.genai import types

from app.core.config import Settings


def prepare_document_for_embedding(
    title: str,
    text: str,
) -> str:
    """Prépare un passage documentaire pour l'indexation."""

    clean_title = title.strip()
    clean_text = text.strip()

    if not clean_title:
        raise ValueError("Le titre du document est vide.")

    if not clean_text:
        raise ValueError("Le texte du document est vide.")

    return (
        f"title: {clean_title} | "
        f"text: {clean_text}"
    )


def prepare_query_for_embedding(query: str) -> str:
    """Prépare une recherche destinée à retrouver des documents."""

    clean_query = query.strip()

    if not clean_query:
        raise ValueError("La recherche est vide.")

    return (
        "task: search result | "
        f"query: {clean_query}"
    )


def request_embedding(
    content: str,
    settings: Settings,
) -> list[float]:
    """Demande à Gemini un vecteur pour le contenu fourni."""

    if settings.gemini_api_key is None:
        raise ValueError(
            "Clé Gemini non configurée pour les embeddings."
        )

    if not content.strip():
        raise ValueError(
            "Le contenu à transformer est vide."
        )

    with genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
    ) as client:
        result = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=content,
            config=types.EmbedContentConfig(
                output_dimensionality=(
                    settings.embedding_dimensions
                ),
            ),
        )

    if (
        not result.embeddings
        or result.embeddings[0].values is None
    ):
        raise ValueError(
            "Gemini n'a retourné aucun embedding."
        )

    vector = list(result.embeddings[0].values)

    if len(vector) != settings.embedding_dimensions:
        raise ValueError(
            "La dimension reçue ne correspond pas "
            "à la configuration."
        )

    return vector
