"""Call Claude to generate test cases as structured JSON."""
from __future__ import annotations

import json
import re

from .providers import LLMProvider, get_provider

CSV_COLUMNS = [
    "ID",
    "Title",
    "Preconditions",
    "Steps",
    "Expected Result",
    "Priority",
    "Type",
]

OUTPUT_CONTRACT = f"""Return ONLY a JSON object (no prose, no markdown fences) with EXACTLY these keys:
- "suggested_filename": a short, descriptive, kebab-case filename (no extension, no path,
  max 60 chars) reflecting the feature under test. Examples: "login-social-auth",
  "checkout-guest-flow", "password-reset-email".
- "test_cases": a JSON array where each element is an object with EXACTLY these keys:
{json.dumps(CSV_COLUMNS)}

Field guidance for each test case:
- ID: "TC-001", "TC-002", ... sequential.
- Title: short imperative summary.
- Preconditions: setup/state required; use "None" if not applicable.
- Steps: numbered steps separated by " | " (e.g. "1. Open app | 2. Click login").
- Expected Result: the observable outcome.
- Priority: one of P0, P1, P2, P3.
- Type: one of Functional, Negative, Edge, UI, Integration, Performance, Security, Accessibility."""

DEFAULT_SYSTEM_PROMPT = f"""You are a senior QA engineer. Given product context (requirements, design docs,
user prompts), produce a comprehensive set of test cases covering happy paths,
edge cases, negative tests, and non-functional concerns where relevant.

{OUTPUT_CONTRACT}
"""

DEFAULT_USER_TEMPLATE = (
    "Product context:\n\n{context}\n\n"
    "Generate the test cases now as a JSON array."
)


def build_system_prompt(custom: str | None, append: bool = False) -> str:
    if not custom:
        return DEFAULT_SYSTEM_PROMPT
    if append:
        return f"{DEFAULT_SYSTEM_PROMPT}\n\nAdditional instructions:\n{custom}"
    # Custom replaces default, but we always enforce the output contract
    # so the CSV stays parseable.
    return f"{custom}\n\n{OUTPUT_CONTRACT}"


def build_user_prompt(context: str, template: str | None) -> str:
    tmpl = template or DEFAULT_USER_TEMPLATE
    if "{context}" in tmpl:
        return tmpl.format(context=context)
    return f"{tmpl}\n\nProduct context:\n\n{context}"


def generate_test_cases(
    context: str,
    provider: LLMProvider | None = None,
    system_prompt: str | None = None,
    user_template: str | None = None,
    append_system: bool = False,
) -> tuple[list[dict], str | None]:
    provider = provider or get_provider()
    system = build_system_prompt(system_prompt, append=append_system)
    user = build_user_prompt(context, user_template)
    text = provider.complete(system=system, user=user, max_tokens=8192)
    return _parse_response(text)


def _parse_response(text: str) -> tuple[list[dict], str | None]:
    text = text.strip()
    # Strip accidental code fences.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    # Try object form first ({"suggested_filename": ..., "test_cases": [...]})
    if text.startswith("{"):
        data = json.loads(text)
        rows = data.get("test_cases")
        if not isinstance(rows, list):
            raise ValueError("Model response missing 'test_cases' array")
        name = data.get("suggested_filename")
        return rows, name if isinstance(name, str) and name.strip() else None

    # Back-compat: bare array
    if not text.startswith("["):
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            text = match.group(0)
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Model did not return a JSON array or object")
    return data, None
