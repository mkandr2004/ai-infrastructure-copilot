from pathlib import Path

import pytest

from app.rag.documents import (
    load_markdown_chunks,
    split_markdown_document,
)


def test_split_markdown_document_by_sections(
    tmp_path: Path,
):
    document_path = tmp_path / "cpu.md"
    document_path.write_text(
        (
            "# Diagnostic CPU\n\n"
            "## Symptômes\n\n"
            "Le système répond lentement.\n\n"
            "## Vérifications\n\n"
            "Utiliser top et ps.\n"
        ),
        encoding="utf-8",
    )

    chunks = split_markdown_document(
        document_path
    )

    assert len(chunks) == 2

    assert chunks[0].source == "cpu.md"
    assert chunks[0].chunk_index == 0
    assert chunks[0].title == (
        "Diagnostic CPU — Symptômes"
    )
    assert chunks[0].text == (
        "Le système répond lentement."
    )

    assert chunks[1].chunk_index == 1
    assert chunks[1].title == (
        "Diagnostic CPU — Vérifications"
    )
    assert chunks[1].text == (
        "Utiliser top et ps."
    )

    second_read = split_markdown_document(
        document_path
    )

    assert (
        second_read[0].point_id
        == chunks[0].point_id
    )
    assert (
        second_read[1].point_id
        == chunks[1].point_id
    )


def test_load_markdown_chunks_uses_sorted_files(
    tmp_path: Path,
):
    (tmp_path / "disk.md").write_text(
        "# Disque\n\nContenu disque.",
        encoding="utf-8",
    )
    (tmp_path / "cpu.md").write_text(
        "# CPU\n\nContenu CPU.",
        encoding="utf-8",
    )
    (tmp_path / "ignore.txt").write_text(
        "Ce fichier ne doit pas être chargé.",
        encoding="utf-8",
    )

    chunks = load_markdown_chunks(
        tmp_path
    )

    assert len(chunks) == 2
    assert chunks[0].source == "cpu.md"
    assert chunks[1].source == "disk.md"


def test_load_markdown_chunks_rejects_invalid_sources(
    tmp_path: Path,
):
    missing_directory = (
        tmp_path / "absent"
    )

    with pytest.raises(
        ValueError,
        match="introuvable",
    ):
        load_markdown_chunks(
            missing_directory
        )

    with pytest.raises(
        ValueError,
        match="Aucun document",
    ):
        load_markdown_chunks(
            tmp_path
        )

    empty_document = tmp_path / "empty.md"
    empty_document.write_text(
        "",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="est vide",
    ):
        load_markdown_chunks(
            tmp_path
        )
