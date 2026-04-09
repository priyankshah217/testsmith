"""Tests for the context builder in loaders.py."""

from __future__ import annotations

from testsmith.loaders import build_context


class TestBuildContext:
    def test_prompt_only(self):
        ctx, errors = build_context("do something", [])
        assert "## User Prompt" in ctx
        assert "do something" in ctx
        assert errors == []

    def test_file_only(self, fixtures_dir):
        ref = str(fixtures_dir / "sample.txt")
        ctx, errors = build_context(None, [ref])
        assert "## sample.txt" in ctx
        assert "Login screen" in ctx
        assert errors == []

    def test_prompt_and_file(self, fixtures_dir):
        ref = str(fixtures_dir / "sample.md")
        ctx, errors = build_context("focus on payments", [ref])
        assert "focus on payments" in ctx
        assert "Checkout Flow" in ctx
        assert errors == []

    def test_multiple_files(self, fixtures_dir):
        refs = [
            str(fixtures_dir / "sample.txt"),
            str(fixtures_dir / "sample.md"),
        ]
        ctx, errors = build_context(None, refs)
        assert "Login screen" in ctx
        assert "Checkout Flow" in ctx
        assert "---" in ctx  # separator between parts
        assert errors == []

    def test_bad_ref_produces_error_marker(self):
        ctx, errors = build_context(None, ["/nonexistent/file.txt"])
        assert "[ERROR loading source" in ctx
        assert len(errors) == 1
        assert "/nonexistent/file.txt" in errors[0]

    def test_empty_prompt_and_no_files(self):
        ctx, errors = build_context(None, [])
        assert ctx == ""
        assert errors == []
