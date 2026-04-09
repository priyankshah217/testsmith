"""Tests for provider selection, model inference, and mismatch detection."""

from __future__ import annotations

import pytest

from testsmith.providers import _infer_provider_from_model, get_provider


class TestInferProviderFromModel:
    def test_claude_model(self):
        assert _infer_provider_from_model("claude-sonnet-4-6") == "anthropic"

    def test_claude_uppercase(self):
        assert _infer_provider_from_model("Claude-3-haiku") == "anthropic"

    def test_gemini_model(self):
        assert _infer_provider_from_model("gemini-2.5-pro") == "gemini"

    def test_gemini_flash(self):
        assert _infer_provider_from_model("gemini-2.5-flash") == "gemini"

    def test_unknown_model(self):
        assert _infer_provider_from_model("gpt-4o") is None

    def test_empty_string(self):
        assert _infer_provider_from_model("") is None


class TestProviderModelMismatch:
    def test_gemini_provider_claude_model_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="does not match provider"):
            get_provider(preferred="gemini", model="claude-sonnet-4-6")

    def test_anthropic_provider_gemini_model_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="does not match provider"):
            get_provider(preferred="anthropic", model="gemini-2.5-pro")

    def test_matching_provider_and_model_ok(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Should not raise — provider and model match.
        provider = get_provider(preferred="gemini", model="gemini-2.5-flash")
        assert provider.name == "gemini"
        assert provider.model == "gemini-2.5-flash"

    def test_model_infers_provider(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        # No --provider, but model is gemini → should pick gemini.
        provider = get_provider(model="gemini-2.5-flash")
        assert provider.name == "gemini"

    def test_no_keys_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="No LLM API key"):
            get_provider()


class TestProviderEnvFallbacks:
    def test_model_from_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("TESTSMITH_MODEL", "gemini-2.5-flash")
        provider = get_provider()
        assert provider.model == "gemini-2.5-flash"

    def test_temperature_from_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("TESTSMITH_TEMPERATURE", "0.5")
        provider = get_provider()
        assert provider.temperature == 0.5

    def test_invalid_temperature_env_ignored(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("TESTSMITH_TEMPERATURE", "not-a-number")
        provider = get_provider()
        assert provider.temperature is None
