"""Tests for the generator module — prompt building and response parsing."""

from __future__ import annotations

import json

import pytest

from testsmith.generator import (
    _parse_response,
    build_system_prompt,
    build_user_prompt,
    DEFAULT_SYSTEM_PROMPT,
    _build_output_contract,
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

    def test_bdd_format(self):
        result = build_system_prompt(None, fmt="bdd")
        assert "Given" in result
        assert "When" in result
        assert "Then" in result
        assert "Business-focused language" in result

    def test_bdd_format_with_custom_append(self):
        result = build_system_prompt("Extra", append=True, fmt="bdd")
        assert "Given" in result
        assert "Extra" in result

    def test_bdd_format_with_custom_replace(self):
        result = build_system_prompt("My custom prompt", fmt="bdd")
        assert "My custom prompt" in result
        assert "Given" in result
        assert "senior QA engineer" not in result


class TestOutputContract:
    def test_default_has_numbered_steps(self):
        contract = _build_output_contract("steps")
        assert "numbered steps" in contract
        assert "Given" not in contract

    def test_bdd_has_given_when_then(self):
        contract = _build_output_contract("bdd")
        assert "Given" in contract
        assert "When" in contract
        assert "Then" in contract
        assert "NEVER use UI-action words" in contract
        assert "numbered steps" not in contract


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
