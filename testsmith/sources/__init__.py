"""Input sources for testsmith.

Each source knows how to recognize a reference (file path, URL, etc.) and
load it into a `LoadedDoc`. New inputs (Confluence, Figma, Notion, ...) are
added by implementing `Source` and registering it in `REGISTRY`.
"""
from __future__ import annotations

from .base import LoadedDoc, Source, SourceError
from .registry import load, register, REGISTRY

__all__ = ["LoadedDoc", "Source", "SourceError", "load", "register", "REGISTRY"]
