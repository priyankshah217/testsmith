"""Source protocol and shared types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class SourceError(Exception):
    """Raised when a source fails to load a reference."""


@dataclass(frozen=True)
class LoadedDoc:
    """A document loaded from some source.

    Attributes:
        title: Short human-readable label (filename, page title, etc.).
        text: Extracted plain text / markdown content.
        origin: Where it came from (path or URL), for attribution in context.
    """

    title: str
    text: str
    origin: str


@runtime_checkable
class Source(Protocol):
    """Loads a `LoadedDoc` from a user-supplied reference string."""

    name: str

    def matches(self, ref: str) -> bool:
        """Return True if this source should handle `ref`."""
        ...

    def load(self, ref: str) -> LoadedDoc:
        """Load the reference. Raise `SourceError` on failure."""
        ...
