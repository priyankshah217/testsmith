"""Tests for the generator module — prompt building and response parsing."""

from __future__ import annotations

import json

import pytest

from testsmith.generator import (
    _build_judge_prompt,
    _build_output_contract,
    _parse_response,
    build_system_prompt,
    build_user_prompt,
    judge_and_fix,
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


class TestJudgeAndFix:
    """Tests for the LLM-as-judge correction flow."""

    def test_build_judge_prompt_contains_warnings(self):
        rows = [{"ID": "TC-001", "Steps": "1. Select item (e.g., shoes)"}]
        warnings = [
            {
                "tc_id": "TC-001",
                "field": "Steps",
                "issue": "non-specific language",
                "matched_text": "e.g.",
            }
        ]
        prompt = _build_judge_prompt(rows, warnings, "test-file")
        assert "TC-001" in prompt
        assert "non-specific language" in prompt
        assert "e.g." in prompt
        assert "test-file" in prompt

    def test_judge_and_fix_returns_corrected_rows(self):
        """Mock provider returns corrected JSON."""
        corrected = {
            "suggested_filename": "test-file",
            "test_cases": [{"ID": "TC-001", "Steps": "1. Select running shoes"}],
        }

        class MockProvider:
            name = "mock"
            model = "mock-1"

            def complete(self, system, user, max_tokens=8192):
                return json.dumps(corrected)

        rows = [{"ID": "TC-001", "Steps": "1. Select item (e.g., shoes)"}]
        warnings = [
            {
                "tc_id": "TC-001",
                "field": "Steps",
                "issue": "non-specific language",
                "matched_text": "e.g.",
            }
        ]
        result_rows, name = judge_and_fix(rows, "test-file", warnings, MockProvider())
        assert result_rows[0]["Steps"] == "1. Select running shoes"
        assert name == "test-file"

    def test_judge_and_fix_handles_parse_error(self):
        """If judge returns invalid JSON, raise ValueError."""

        class BadProvider:
            name = "mock"
            model = "mock-1"

            def complete(self, system, user, max_tokens=8192):
                return "not json"

        with pytest.raises(ValueError):
            judge_and_fix(
                [{"ID": "TC-001"}],
                "test-file",
                [
                    {
                        "tc_id": "TC-001",
                        "field": "Steps",
                        "issue": "x",
                        "matched_text": "y",
                    }
                ],
                BadProvider(),
            )
