"""Load context from local files (PDF, DOCX, MD, TXT)."""
from __future__ import annotations

from pathlib import Path


def load_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix in {".docx", ".doc"}:
        return _load_docx(path)
    if suffix in {".md", ".txt", ".rst", ""}:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {suffix} ({path})")


def _load_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def _load_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def build_context(prompt: str | None, files: list[Path]) -> str:
    parts: list[str] = []
    if prompt:
        parts.append(f"## User Prompt\n{prompt}")
    for f in files:
        try:
            content = load_file(f)
        except Exception as e:
            parts.append(f"## File: {f.name}\n[ERROR loading file: {e}]")
            continue
        parts.append(f"## File: {f.name}\n{content}")
    return "\n\n---\n\n".join(parts)
