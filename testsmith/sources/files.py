"""File-based sources: PDF, DOCX, and plain text."""

from __future__ import annotations

from pathlib import Path

from .base import LoadedDoc, SourceError

_TEXT_SUFFIXES = {".md", ".txt", ".rst", ""}
_PDF_SUFFIXES = {".pdf"}
_DOCX_SUFFIXES = {".docx", ".doc"}


def _as_path(ref: str) -> Path | None:
    """Return a Path if `ref` looks like a local filesystem reference."""
    if "://" in ref:
        return None
    return Path(ref).expanduser()


class _FileSourceBase:
    suffixes: set[str] = set()
    name: str = "file"

    def matches(self, ref: str) -> bool:
        path = _as_path(ref)
        if path is None:
            return False
        return path.suffix.lower() in self.suffixes

    def _read(self, path: Path) -> str:
        raise NotImplementedError

    def load(self, ref: str) -> LoadedDoc:
        path = _as_path(ref)
        if path is None or not path.exists():
            raise SourceError(f"File not found: {ref}")
        try:
            text = self._read(path)
        except Exception as e:
            raise SourceError(f"Failed to read {path.name}: {e}") from e
        return LoadedDoc(title=path.name, text=text, origin=str(path))


class PdfSource(_FileSourceBase):
    name = "pdf"
    suffixes = _PDF_SUFFIXES

    def _read(self, path: Path) -> str:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)


class DocxSource(_FileSourceBase):
    name = "docx"
    suffixes = _DOCX_SUFFIXES

    def _read(self, path: Path) -> str:
        from docx import Document

        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)


class TextSource(_FileSourceBase):
    name = "text"
    suffixes = _TEXT_SUFFIXES

    def _read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")
