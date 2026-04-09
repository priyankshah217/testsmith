"""Tests for Figma source — URL parsing and node-tree rendering."""

from __future__ import annotations

import pytest

from testsmith.sources.base import SourceError
from testsmith.sources.figma import (
    FigmaSource,
    _parse_figma_url,
    _render_node,
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
            "name": "Button",
            "description": "Primary CTA button",
            "children": [],
        }
        text = _render_node(node, depth=2)
        assert "## Button" in text
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


class TestFigmaSourceLoadRequiresEnv:
    def test_load_fails_without_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("FIGMA_API_TOKEN", raising=False)
        with pytest.raises(SourceError, match="FIGMA_API_TOKEN is not set"):
            FigmaSource().load("https://figma.com/design/abc/Name?node-id=1-2")
