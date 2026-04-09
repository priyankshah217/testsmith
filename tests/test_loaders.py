"""Tests for the context builder in loaders.py."""

from __future__ import annotations

from testsmith.loaders import build_context


class TestBuildContext:
    def test_prompt_only(self):
        ctx = build_context("do something", [])
        assert "## User Prompt" in ctx
        assert "do something" in ctx

    def test_file_only(self, fixtures_dir):
        ref = str(fixtures_dir / "sample.txt")
        ctx = build_context(None, [ref])
        assert "## sample.txt" in ctx
        assert "Login screen" in ctx

    def test_prompt_and_file(self, fixtures_dir):
        ref = str(fixtures_dir / "sample.md")
        ctx = build_context("focus on payments", [ref])
        assert "focus on payments" in ctx
        assert "Checkout Flow" in ctx

    def test_multiple_files(self, fixtures_dir):
        refs = [
            str(fixtures_dir / "sample.txt"),
            str(fixtures_dir / "sample.md"),
        ]
        ctx = build_context(None, refs)
        assert "Login screen" in ctx
        assert "Checkout Flow" in ctx
        assert "---" in ctx  # separator between parts

    def test_bad_ref_produces_error_marker(self):
        ctx = build_context(None, ["/nonexistent/file.txt"])
        assert "[ERROR loading source" in ctx

    def test_empty_prompt_and_no_files(self):
        ctx = build_context(None, [])
        assert ctx == ""
