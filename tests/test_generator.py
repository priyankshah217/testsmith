"""Tests for the generator module — prompt building and response parsing."""

from __future__ import annotations

import json

import pytest

from testsmith.generator import (
    _parse_response,
    build_system_prompt,
    build_user_prompt,
    DEFAULT_SYSTEM_PROMPT,
)


class TestBuildSystemPrompt:
    def test_default(self):
        result = build_system_prompt(None)
        assert result == DEFAULT_SYSTEM_PROMPT

    def test_custom_replaces_default(self):
        result = build_system_prompt("My custom prompt")
        assert "My custom prompt" in result
        assert "senior QA engineer" not in result

    def test_append_mode(self):
        result = build_system_prompt("Extra instructions", append=True)
        assert "senior QA engineer" in result
        assert "Extra instructions" in result


class TestBuildUserPrompt:
    def test_default_template(self):
        result = build_user_prompt("some context", None)
        assert "some context" in result
        assert "Generate the test cases" in result

    def test_custom_template_with_placeholder(self):
        result = build_user_prompt("ctx", "Here: {context} — done")
        assert result == "Here: ctx — done"

    def test_custom_template_without_placeholder(self):
        result = build_user_prompt("ctx", "My template")
        assert "My template" in result
        assert "ctx" in result


class TestParseResponse:
    def test_object_form(self):
        response = json.dumps(
            {
                "suggested_filename": "login-auth",
                "test_cases": [
                    {"ID": "TC-001", "Title": "Test login"},
                ],
            }
        )
        rows, name = _parse_response(response)
        assert len(rows) == 1
        assert rows[0]["ID"] == "TC-001"
        assert name == "login-auth"

    def test_object_form_empty_filename(self):
        response = json.dumps(
            {
                "suggested_filename": "",
                "test_cases": [{"ID": "TC-001", "Title": "T"}],
            }
        )
        rows, name = _parse_response(response)
        assert len(rows) == 1
        assert name is None

    def test_bare_array_compat(self):
        response = json.dumps([{"ID": "TC-001", "Title": "T"}])
        rows, name = _parse_response(response)
        assert len(rows) == 1
        assert name is None

    def test_strips_code_fences(self):
        response = '```json\n[{"ID": "TC-001", "Title": "T"}]\n```'
        rows, name = _parse_response(response)
        assert len(rows) == 1

    def test_extracts_array_from_prose(self):
        response = 'Here are the cases:\n[{"ID": "TC-001", "Title": "T"}]\nDone.'
        rows, name = _parse_response(response)
        assert len(rows) == 1

    def test_invalid_json_raises(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            _parse_response("not json at all")

    def test_object_missing_test_cases_raises(self):
        response = json.dumps({"suggested_filename": "f", "wrong_key": []})
        with pytest.raises(ValueError, match="test_cases"):
            _parse_response(response)
