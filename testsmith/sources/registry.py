"""Source registry and dispatcher."""

from __future__ import annotations

from .base import LoadedDoc, Source, SourceError
from .confluence import ConfluenceSource
from .figma import FigmaSource
from .files import DocxSource, PdfSource, TextSource

# Order matters: URL-based sources are checked before file-based ones so that
# a Confluence/Figma URL isn't misinterpreted as a filesystem path.
REGISTRY: list[Source] = [
    ConfluenceSource(),
    FigmaSource(),
    PdfSource(),
    DocxSource(),
    TextSource(),
]


def register(source: Source) -> None:
    """Add a source to the registry. Order matters: first match wins."""
    REGISTRY.append(source)


def load(ref: str) -> LoadedDoc:
    """Dispatch `ref` to the first matching source."""
    for source in REGISTRY:
        if source.matches(ref):
            return source.load(ref)
    raise SourceError(f"No source handles reference: {ref}")
