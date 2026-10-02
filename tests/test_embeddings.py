from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from app.rag.embeddings import (
    prepare_document_for_embedding,
    prepare_query_for_embedding,
    request_embedding,
)


def test_prepare_embedding_inputs():
    document = prepare_document_for_embedding(
        "  CPU élevé  ",
        "  Vérifier les processus actifs.  ",
    )
    query = prepare_query_for_embedding(
        "  Pourquoi le processeur est-il saturé ?  "
    )

    assert document == (
        "title: CPU élevé | "
        "text: Vérifier les processus actifs."
    )
    assert query == (
        "task: search result | "
        "query: Pourquoi le processeur est-il saturé ?"
    )


def test_prepare_embedding_inputs_reject_empty_values():
    with pytest.raises(ValueError, match="titre"):
        prepare_document_for_embedding(
            " ",
            "Texte valide",
        )

    with pytest.raises(ValueError, match="texte"):
        prepare_document_for_embedding(
            "Titre valide",
            " ",
        )

    with pytest.raises(ValueError, match="recherche"):
        prepare_query_for_embedding(" ")


def test_request_embedding_returns_expected_vector():
    settings = SimpleNamespace(
        gemini_api_key=SecretStr("cle-fictive"),
        gemini_embedding_model="modele-fictif",
        embedding_dimensions=3,
    )

    fake_result = SimpleNamespace(
        embeddings=[
            SimpleNamespace(
                values=[0.1, 0.2, 0.3],
            )
        ],
    )

    fake_client = MagicMock()
    fake_client.models.embed_content.return_value = fake_result

    fake_context = MagicMock()
    fake_context.__enter__.return_value = fake_client

    with patch(
        "app.rag.embeddings.genai.Client",
        return_value=fake_context,
    ) as mock_client_factory:
        vector = request_embedding(
            "contenu de test",
            settings,
        )

    assert vector == [0.1, 0.2, 0.3]

    mock_client_factory.assert_called_once_with(
        api_key="cle-fictive",
    )
    fake_context.__exit__.assert_called_once()

    call_arguments = (
        fake_client.models.embed_content.call_args.kwargs
    )

    assert call_arguments["model"] == "modele-fictif"
    assert call_arguments["contents"] == "contenu de test"
    assert (
        call_arguments["config"].output_dimensionality
        == 3
    )


def test_request_embedding_rejects_wrong_dimension():
    settings = SimpleNamespace(
        gemini_api_key=SecretStr("cle-fictive"),
        gemini_embedding_model="modele-fictif",
        embedding_dimensions=3,
    )

    fake_result = SimpleNamespace(
        embeddings=[
            SimpleNamespace(
                values=[0.1, 0.2],
            )
        ],
    )

    fake_client = MagicMock()
    fake_client.models.embed_content.return_value = fake_result

    fake_context = MagicMock()
    fake_context.__enter__.return_value = fake_client

    with (
        patch(
            "app.rag.embeddings.genai.Client",
            return_value=fake_context,
        ),
        pytest.raises(
            ValueError,
            match="dimension",
        ),
    ):
        request_embedding(
            "contenu de test",
            settings,
        )


def test_request_embedding_requires_api_key():
    settings = SimpleNamespace(
        gemini_api_key=None,
        gemini_embedding_model="modele-fictif",
        embedding_dimensions=3,
    )

    with pytest.raises(
        ValueError,
        match="Clé Gemini",
    ):
        request_embedding(
            "contenu de test",
            settings,
        )
