"""Chargement et découpage des documents Markdown."""

from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """Passage documentaire prêt à être indexé."""

    point_id: str
    source: str
    title: str
    text: str
    chunk_index: int


def split_markdown_document(
    path: Path,
) -> list[DocumentChunk]:
    """Transforme les sections d'un fichier Markdown en passages."""

    content = path.read_text(
        encoding="utf-8",
    ).strip()

    if not content:
        raise ValueError(
            f"Le document {path.name} est vide."
        )

    lines = content.splitlines()

    document_title = path.stem.replace(
        "_",
        " ",
    )

    for line in lines:
        stripped_line = line.strip()

        if stripped_line.startswith("# "):
            document_title = stripped_line[2:].strip()
            break

    raw_sections: list[tuple[str, str]] = []
    current_title = document_title
    current_lines: list[str] = []

    def save_current_section() -> None:
        text = "\n".join(current_lines).strip()

        if text:
            raw_sections.append(
                (current_title, text)
            )

    for line in lines:
        stripped_line = line.strip()

        if stripped_line.startswith("# "):
            continue

        if stripped_line.startswith("## "):
            save_current_section()

            section_name = stripped_line[3:].strip()
            current_title = (
                f"{document_title} — {section_name}"
            )
            current_lines = []
            continue

        current_lines.append(line)

    save_current_section()

    chunks: list[DocumentChunk] = []

    for chunk_index, (title, text) in enumerate(
        raw_sections
    ):
        point_id = str(
            uuid5(
                NAMESPACE_URL,
                (
                    f"{path.name}:"
                    f"{chunk_index}:"
                    f"{title}"
                ),
            )
        )

        chunks.append(
            DocumentChunk(
                point_id=point_id,
                source=path.name,
                title=title,
                text=text,
                chunk_index=chunk_index,
            )
        )

    return chunks


def load_markdown_chunks(
    directory: Path,
) -> list[DocumentChunk]:
    """Charge tous les documents Markdown d'un dossier."""

    if not directory.is_dir():
        raise ValueError(
            f"Dossier documentaire introuvable : {directory}"
        )

    paths = sorted(
        directory.glob("*.md")
    )

    if not paths:
        raise ValueError(
            f"Aucun document Markdown dans : {directory}"
        )

    chunks: list[DocumentChunk] = []

    for path in paths:
        chunks.extend(
            split_markdown_document(path)
        )

    return chunks
