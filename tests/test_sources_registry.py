"""Tests for the source registry and dispatcher."""

from __future__ import annotations

import pytest

from testsmith.sources import REGISTRY, load
from testsmith.sources.base import LoadedDoc, SourceError


class TestRegistry:
    def test_all_sources_registered(self):
        names = [s.name for s in REGISTRY]
        assert "confluence" in names
        assert "figma" in names
        assert "pdf" in names
        assert "docx" in names
        assert "text" in names

    def test_url_sources_before_file_sources(self):
        names = [s.name for s in REGISTRY]
        # Confluence and Figma should come before any file source.
        first_url = min(names.index("confluence"), names.index("figma"))
        first_file = min(names.index("pdf"), names.index("docx"), names.index("text"))
        assert first_url < first_file

    def test_load_dispatches_to_text(self, fixtures_dir):
        doc = load(str(fixtures_dir / "sample.txt"))
        assert isinstance(doc, LoadedDoc)
        assert "Login screen" in doc.text

    def test_load_unknown_ref_raises(self):
        with pytest.raises(SourceError, match="No source handles"):
            load("ftp://nowhere/something.xyz")
