"""Tests for Figma source — URL parsing and node-tree rendering."""

from __future__ import annotations

import pytest

from testsmith.sources.base import SourceError
from testsmith.sources.figma import (
    FigmaSource,
    _is_auto_generated_name,
    _is_qa_relevant_text,
    _is_relevant_name,
    _parse_figma_url,
    _render_node,
    _truncate,
)


class TestFigmaSourceMatches:
    def test_matches_design_url(self):
        url = "https://www.figma.com/design/abc123/My-File?node-id=1-23"
        assert FigmaSource().matches(url)

    def test_matches_file_url(self):
        url = "https://figma.com/file/xyz/My-File"
        assert FigmaSource().matches(url)

    def test_matches_proto_url(self):
        url = "https://www.figma.com/proto/abc/My-File"
        assert FigmaSource().matches(url)

    def test_no_match_other_domain(self):
        assert not FigmaSource().matches("https://example.com/design/abc/foo")

    def test_no_match_local_file(self):
        assert not FigmaSource().matches("./design.pdf")


class TestParseFigmaUrl:
    def test_design_with_node_id(self):
        fk, nid = _parse_figma_url(
            "https://www.figma.com/design/abc123/Name?node-id=1-23"
        )
        assert fk == "abc123"
        assert nid == "1:23"

    def test_design_without_node_id(self):
        fk, nid = _parse_figma_url("https://figma.com/design/xyz/Name")
        assert fk == "xyz"
        assert nid is None

    def test_file_url(self):
        fk, nid = _parse_figma_url("https://figma.com/file/key123/Title")
        assert fk == "key123"
        assert nid is None

    def test_proto_url(self):
        fk, nid = _parse_figma_url("https://figma.com/proto/ppp/Proto?node-id=10-20")
        assert fk == "ppp"
        assert nid == "10:20"

    def test_no_file_key(self):
        fk, nid = _parse_figma_url("https://figma.com/about")
        assert fk is None
        assert nid is None

    def test_multiple_dashes_in_node_id(self):
        fk, nid = _parse_figma_url("https://figma.com/design/abc/N?node-id=100-200")
        assert nid == "100:200"


class TestRenderNode:
    def test_text_node(self):
        node = {"type": "TEXT", "name": "Label", "characters": "Hello"}
        assert _render_node(node, depth=1).strip() == "Hello"

    def test_empty_text_node(self):
        node = {"type": "TEXT", "name": "Label", "characters": ""}
        assert _render_node(node, depth=1) == ""

    def test_frame_heading(self):
        node = {"type": "FRAME", "name": "Login", "children": []}
        text = _render_node(node, depth=1)
        assert text.strip() == "# Login"

    def test_component_with_description(self):
        node = {
            "type": "COMPONENT",
            "name": "SubmitButton",
            "description": "Primary CTA button",
            "children": [],
        }
        text = _render_node(node, depth=2)
        assert "## SubmitButton" in text
        assert "[interactive]" in text
        assert "Primary CTA button" in text

    def test_skips_visual_nodes(self):
        node = {"type": "RECTANGLE", "name": "bg-fill"}
        assert _render_node(node, depth=1) == ""

    def test_skips_vector(self):
        assert _render_node({"type": "VECTOR", "name": "icon"}, depth=1) == ""

    def test_nested_tree(self):
        tree = {
            "type": "DOCUMENT",
            "name": "Doc",
            "children": [
                {
                    "type": "CANVAS",
                    "name": "Page 1",
                    "children": [
                        {
                            "type": "FRAME",
                            "name": "Header",
                            "children": [
                                {"type": "TEXT", "name": "t", "characters": "Welcome"},
                            ],
                        },
                        {"type": "RECTANGLE", "name": "bg"},
                    ],
                }
            ],
        }
        text = _render_node(tree, depth=1)
        assert "Page 1" in text
        assert "Header" in text
        assert "Welcome" in text
        assert "bg" not in text

    def test_heading_depth_cap(self):
        # depth=10 should still produce at most ####
        node = {"type": "FRAME", "name": "Deep", "children": []}
        text = _render_node(node, depth=10)
        assert text.strip() == "#### Deep"

    def test_document_no_heading(self):
        node = {"type": "DOCUMENT", "name": "MyDoc", "children": []}
        text = _render_node(node, depth=1)
        assert text.strip() == ""

    def test_group_renders_as_bullet(self):
        node = {"type": "GROUP", "name": "Controls", "children": []}
        text = _render_node(node, depth=1)
        assert text.strip() == "- Controls"

    def test_auto_generated_name_skipped(self):
        node = {
            "type": "FRAME",
            "name": "Frame 123",
            "children": [
                {"type": "TEXT", "name": "t", "characters": "Hello"},
            ],
        }
        text = _render_node(node, depth=1)
        assert "Frame 123" not in text
        assert "Hello" in text

    def test_interactive_control_tagged(self):
        node = {"type": "FRAME", "name": "EmailInput", "children": []}
        text = _render_node(node, depth=1)
        assert "[interactive]" in text
        assert "EmailInput" in text

    def test_qa_text_bolded(self):
        node = {"type": "TEXT", "name": "err", "characters": "Invalid email address"}
        text = _render_node(node, depth=1)
        assert "**Invalid email address**" in text

    def test_normal_text_not_bolded(self):
        node = {"type": "TEXT", "name": "t", "characters": "Welcome back"}
        text = _render_node(node, depth=1)
        assert text.strip() == "Welcome back"
        assert "**" not in text

    def test_interactive_group_tagged(self):
        node = {"type": "GROUP", "name": "Dropdown Menu", "children": []}
        text = _render_node(node, depth=1)
        assert "[interactive]" in text


class TestSmartFiltering:
    def test_auto_generated_names_detected(self):
        assert _is_auto_generated_name("Frame 123")
        assert _is_auto_generated_name("Group 45")
        assert _is_auto_generated_name("Rectangle 7")
        assert not _is_auto_generated_name("Login Form")
        assert not _is_auto_generated_name("Header")

    def test_interactive_patterns(self):
        assert _is_relevant_name("SubmitButton")
        assert _is_relevant_name("email-input")
        assert _is_relevant_name("Dropdown Menu")
        assert _is_relevant_name("Toggle Switch")
        assert not _is_relevant_name("Background")
        assert not _is_relevant_name("Spacer")

    def test_qa_text_patterns(self):
        assert _is_qa_relevant_text("Error: invalid email")
        assert _is_qa_relevant_text("Please wait, loading...")
        assert _is_qa_relevant_text("No results found")
        assert _is_qa_relevant_text("Sign in to continue")
        assert not _is_qa_relevant_text("Welcome to our app")
        assert not _is_qa_relevant_text("Hello world")

    def test_truncate_short_text(self):
        text = "short"
        assert _truncate(text) == text

    def test_truncate_long_text(self):
        text = "x" * 40_000
        result = _truncate(text)
        assert len(result) < 40_000
        assert "truncated" in result


class TestFigmaSourceLoadRequiresEnv:
    def test_load_fails_without_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("FIGMA_API_TOKEN", raising=False)
        with pytest.raises(SourceError, match="FIGMA_API_TOKEN is not set"):
            FigmaSource().load("https://figma.com/design/abc/Name?node-id=1-2")
