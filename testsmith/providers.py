"""LLM provider abstraction. Supports Anthropic Claude and Google Gemini."""
from __future__ import annotations

import os
from typing import Protocol


class LLMProvider(Protocol):
    name: str

    def complete(self, system: str, user: str, max_tokens: int = 8192) -> str: ...


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 8192) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            b.text for b in msg.content if getattr(b, "type", "") == "text"
        )


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-pro"):
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 8192) -> str:
        from google.genai import types

        resp = self.client.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
            ),
        )
        return resp.text or ""


def get_provider(preferred: str | None = None) -> LLMProvider:
    """Pick a provider. Explicit > ANTHROPIC_API_KEY > GEMINI_API_KEY."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    choice = (preferred or os.environ.get("TESTSMITH_PROVIDER") or "").lower().strip()

    if choice == "anthropic":
        if not anthropic_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        return AnthropicProvider(anthropic_key)
    if choice == "gemini":
        if not gemini_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        return GeminiProvider(gemini_key)

    if anthropic_key:
        return AnthropicProvider(anthropic_key)
    if gemini_key:
        return GeminiProvider(gemini_key)

    raise RuntimeError(
        "No LLM API key found. Set ANTHROPIC_API_KEY or GEMINI_API_KEY."
    )
