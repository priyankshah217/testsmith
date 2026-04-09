"""LLM provider abstraction. Supports Anthropic Claude and Google Gemini."""

from __future__ import annotations

import os
from typing import Protocol


DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-2.5-pro",
}


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(self, system: str, user: str, max_tokens: int = 8192) -> str: ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ):
        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key)
        self.model = model or DEFAULT_MODELS["anthropic"]
        self.temperature = temperature
        self.top_p = top_p

    def complete(self, system: str, user: str, max_tokens: int = 8192) -> str:
        kwargs: dict = dict(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.top_p is not None:
            kwargs["top_p"] = self.top_p
        msg = self.client.messages.create(**kwargs)
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ):
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model or DEFAULT_MODELS["gemini"]
        self.temperature = temperature
        self.top_p = top_p

    def complete(self, system: str, user: str, max_tokens: int = 8192) -> str:
        from google.genai import types

        config_kwargs: dict = dict(
            system_instruction=system,
            max_output_tokens=max_tokens,
        )
        if self.temperature is not None:
            config_kwargs["temperature"] = self.temperature
        if self.top_p is not None:
            config_kwargs["top_p"] = self.top_p
        resp = self.client.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return resp.text or ""


def _infer_provider_from_model(model: str) -> str | None:
    """Infer provider name from a model string, or None if ambiguous."""
    m = model.lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith("gemini"):
        return "gemini"
    return None


def get_provider(
    preferred: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
) -> LLMProvider:
    """Pick a provider and configure it.

    Resolution order:
      Provider: explicit arg > inferred from model > env TESTSMITH_PROVIDER > first available key.
      Model: explicit arg > env TESTSMITH_MODEL > provider default.
      Temperature: explicit arg > env TESTSMITH_TEMPERATURE > provider default.
      Top-p: explicit arg > env TESTSMITH_TOP_P > provider default.
    """
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    model = model or os.environ.get("TESTSMITH_MODEL") or None
    temperature = (
        temperature if temperature is not None else _env_float("TESTSMITH_TEMPERATURE")
    )
    top_p = top_p if top_p is not None else _env_float("TESTSMITH_TOP_P")

    # Resolve provider: explicit > inferred from model > env > auto-detect from keys.
    explicit = (preferred or os.environ.get("TESTSMITH_PROVIDER") or "").lower().strip()
    inferred = _infer_provider_from_model(model) if model else None

    if explicit and inferred and explicit != inferred:
        raise RuntimeError(
            f"Model '{model}' does not match provider '{explicit}'. "
            f"Either drop --provider (it will be inferred as '{inferred}') "
            f"or use a {explicit} model."
        )

    choice = explicit or inferred or ""

    def _build_anthropic() -> AnthropicProvider:
        if not anthropic_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        return AnthropicProvider(
            anthropic_key, model=model, temperature=temperature, top_p=top_p
        )

    def _build_gemini() -> GeminiProvider:
        if not gemini_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        return GeminiProvider(
            gemini_key, model=model, temperature=temperature, top_p=top_p
        )

    if choice == "anthropic":
        return _build_anthropic()
    if choice == "gemini":
        return _build_gemini()
    if anthropic_key:
        return _build_anthropic()
    if gemini_key:
        return _build_gemini()

    raise RuntimeError("No LLM API key found. Set ANTHROPIC_API_KEY or GEMINI_API_KEY.")


def _env_float(name: str) -> float | None:
    val = os.environ.get(name)
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None
