"""Tests for Confluence source — URL parsing and HTML-to-text conversion."""

from __future__ import annotations

import pytest

from testsmith.sources.base import SourceError
from testsmith.sources.confluence import (
    ConfluenceSource,
    _html_to_text,
    _PAGE_ID_RE,
)


class TestConfluenceSourceMatches:
    def test_matches_standard_url(self):
        url = "https://acme.atlassian.net/wiki/spaces/ENG/pages/12345/My-Page"
        assert ConfluenceSource().matches(url)

    def test_matches_tinyurl(self):
        url = "https://acme.atlassian.net/wiki/x/abc123"
        assert ConfluenceSource().matches(url)

    def test_no_match_non_atlassian(self):
        assert not ConfluenceSource().matches("https://example.com/wiki/page")

    def test_no_match_no_wiki_path(self):
        assert not ConfluenceSource().matches(
            "https://acme.atlassian.net/jira/browse/PROJ-1"
        )

    def test_no_match_local_file(self):
        assert not ConfluenceSource().matches("./spec.pdf")

    def test_no_match_bare_path(self):
        assert not ConfluenceSource().matches("/tmp/file.txt")


class TestPageIdParsing:
    def test_extracts_page_id(self):
        url = "https://acme.atlassian.net/wiki/spaces/ENG/pages/12345/Title"
        match = _PAGE_ID_RE.search(url)
        assert match and match.group(1) == "12345"

    def test_extracts_page_id_no_slug(self):
        url = "https://acme.atlassian.net/wiki/spaces/ENG/pages/99999"
        match = _PAGE_ID_RE.search(url)
        assert match and match.group(1) == "99999"

    def test_no_match_tinyurl(self):
        url = "https://acme.atlassian.net/wiki/x/abc"
        assert _PAGE_ID_RE.search(url) is None


class TestHtmlToText:
    def test_strips_tags(self):
        assert _html_to_text("<p>Hello <b>world</b></p>").strip() == "Hello world"

    def test_preserves_headings(self):
        text = _html_to_text("<h1>Title</h1><p>Body</p>")
        assert "Title" in text
        assert "Body" in text

    def test_renders_unordered_list(self):
        html = "<ul><li>one</li><li>two</li></ul>"
        text = _html_to_text(html)
        assert "- one" in text
        assert "- two" in text

    def test_renders_ordered_list(self):
        html = "<ol><li>first</li><li>second</li></ol>"
        text = _html_to_text(html)
        assert "1. first" in text
        assert "1. second" in text

    def test_skips_ac_macros(self):
        html = (
            "<p>visible</p>"
            '<ac:structured-macro ac:name="info">'
            "<ac:rich-text-body><p>hidden</p></ac:rich-text-body>"
            "</ac:structured-macro>"
        )
        text = _html_to_text(html)
        assert "visible" in text
        assert "hidden" not in text

    def test_skips_script_and_style(self):
        html = "<p>ok</p><script>alert(1)</script><style>.x{}</style>"
        text = _html_to_text(html)
        assert "ok" in text
        assert "alert" not in text
        assert ".x" not in text

    def test_collapses_blank_lines(self):
        html = "<p>a</p><p></p><p></p><p></p><p>b</p>"
        text = _html_to_text(html)
        # Should not have 3+ consecutive newlines.
        assert "\n\n\n" not in text
        assert "a" in text and "b" in text

    def test_empty_input(self):
        assert _html_to_text("") == ""

    def test_nested_lists(self):
        html = "<ul><li>outer<ul><li>inner</li></ul></li></ul>"
        text = _html_to_text(html)
        assert "outer" in text
        assert "inner" in text


class TestConfluenceSourceLoadRequiresEnv:
    def test_load_fails_without_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("CONFLUENCE_BASE_URL", raising=False)
        monkeypatch.delenv("CONFLUENCE_EMAIL", raising=False)
        monkeypatch.delenv("CONFLUENCE_API_TOKEN", raising=False)
        with pytest.raises(SourceError, match="Confluence credentials missing"):
            ConfluenceSource().load(
                "https://acme.atlassian.net/wiki/spaces/ENG/pages/1/Title"
            )
