"""Tests for file-based sources (TextSource, PdfSource, DocxSource)."""

from __future__ import annotations

from pathlib import Path

import pytest

from testsmith.sources.base import SourceError
from testsmith.sources.files import DocxSource, PdfSource, TextSource


class TestTextSource:
    def test_matches_txt(self, tmp_path: Path):
        assert TextSource().matches(str(tmp_path / "file.txt"))

    def test_matches_md(self, tmp_path: Path):
        assert TextSource().matches(str(tmp_path / "file.md"))

    def test_matches_rst(self, tmp_path: Path):
        assert TextSource().matches(str(tmp_path / "file.rst"))

    def test_no_match_pdf(self, tmp_path: Path):
        assert not TextSource().matches(str(tmp_path / "file.pdf"))

    def test_no_match_url(self):
        assert not TextSource().matches("https://example.com/file.txt")

    def test_load_txt(self, fixtures_dir: Path):
        doc = TextSource().load(str(fixtures_dir / "sample.txt"))
        assert doc.title == "sample.txt"
        assert "Login screen" in doc.text
        assert "Social login" in doc.text

    def test_load_md(self, fixtures_dir: Path):
        doc = TextSource().load(str(fixtures_dir / "sample.md"))
        assert doc.title == "sample.md"
        assert "Checkout Flow" in doc.text
        assert "Guest checkout" in doc.text

    def test_load_missing_file(self, tmp_path: Path):
        with pytest.raises(SourceError, match="File not found"):
            TextSource().load(str(tmp_path / "nonexistent.txt"))


class TestPdfSource:
    def test_matches_pdf(self, tmp_path: Path):
        assert PdfSource().matches(str(tmp_path / "doc.pdf"))

    def test_no_match_txt(self, tmp_path: Path):
        assert not PdfSource().matches(str(tmp_path / "doc.txt"))

    def test_no_match_url(self):
        assert not PdfSource().matches("https://example.com/doc.pdf")


class TestDocxSource:
    def test_matches_docx(self, tmp_path: Path):
        assert DocxSource().matches(str(tmp_path / "doc.docx"))

    def test_matches_doc(self, tmp_path: Path):
        assert DocxSource().matches(str(tmp_path / "doc.doc"))

    def test_no_match_txt(self, tmp_path: Path):
        assert not DocxSource().matches(str(tmp_path / "doc.txt"))
