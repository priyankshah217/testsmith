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

_STEPS_GUIDANCE_DEFAULT = (
    '- Steps: numbered steps separated by " | " (e.g. "1. Open app | 2. Click login").'
)

_STEPS_GUIDANCE_BDD = """\
- Steps: write in BDD format using Given / When / Then keywords, separated by " | ".
  Each step MUST start with one of: "Given", "When", "Then", "And", "But".
  Example: "Given user has an active subscription | When the subscription renewal date arrives | Then the subscription is renewed automatically | And the user receives a confirmation email"

  CRITICAL — Business-focused language rules for BDD steps:
  • Steps MUST describe business intent, outcomes, and domain actions — NOT UI interactions.
  • NEVER use UI-action words: click, tap, press, scroll, hover, swipe, drag, select (dropdown),
    type, enter (into field), navigate, open, close, toggle, check (checkbox), uncheck,
    fill in, submit (button), expand, collapse.
  • INSTEAD of "When user clicks the checkout button" → "When user initiates checkout"
  • INSTEAD of "Given user navigates to profile page" → "Given user is viewing their profile"
  • INSTEAD of "When user types email in the login field" → "When user provides login credentials"
  • INSTEAD of "Then user scrolls to the bottom" → "Then user reviews the full content"
  • "Given" sets up the business state or context (not the UI state).
  • "When" describes the business action or event (not the UI gesture).
  • "Then" asserts the business outcome or side-effect (not what appears on screen).
  • If a verification is about data, say what the DATA should be — not what the SCREEN shows."""


def _build_output_contract(fmt: str = "steps") -> str:
    steps_guidance = _STEPS_GUIDANCE_BDD if fmt == "bdd" else _STEPS_GUIDANCE_DEFAULT
    return f"""Return ONLY a JSON object (no prose, no markdown fences) with EXACTLY these keys:
- "suggested_filename": a short, descriptive, kebab-case filename (no extension, no path,
  max 60 chars) reflecting the feature under test. Examples: "login-social-auth",
  "checkout-guest-flow", "password-reset-email".
- "test_cases": a JSON array where each element is an object with AT LEAST these keys:
{json.dumps(CSV_COLUMNS)}
(Additional keys are allowed and will be preserved in the JSON but omitted from the CSV.)

Field guidance for each test case:
- ID: "TC-001", "TC-002", ... sequential.
- Title: short imperative summary.
- Preconditions: setup/state required; use "None" if not applicable.
{steps_guidance}
- Expected Result: the observable outcome.
- Priority: one of P0, P1, P2, P3.
- Type: one of Functional, Negative, Edge, UI, Integration, Performance, Security, Accessibility."""


# Default contract for backward compatibility
OUTPUT_CONTRACT = _build_output_contract("steps")

DEFAULT_SYSTEM_PROMPT = f"""You are a senior QA engineer. Given product context (requirements, design docs,
user prompts), produce a comprehensive set of test cases covering happy paths,
edge cases, negative tests, and non-functional concerns where relevant.

{OUTPUT_CONTRACT}
"""


def _build_default_system_prompt(fmt: str = "steps") -> str:
    contract = _build_output_contract(fmt)
    return (
        "You are a senior QA engineer. Given product context (requirements, design docs,\n"
        "user prompts), produce a comprehensive set of test cases covering happy paths,\n"
        "edge cases, negative tests, and non-functional concerns where relevant.\n\n"
        f"{contract}\n"
    )


DEFAULT_USER_TEMPLATE = (
    "Product context:\n\n{context}\n\nGenerate the test cases now as a JSON array."
)


def build_system_prompt(
    custom: str | None,
    append: bool = False,
    fmt: str = "steps",
) -> str:
    contract = _build_output_contract(fmt)
    default = _build_default_system_prompt(fmt)
    if not custom:
        return default
    if append:
        return f"{default}\n\nAdditional instructions:\n{custom}"
    # Custom replaces default, but we always enforce the output contract
    # so the CSV stays parseable.
    return f"{custom}\n\n{contract}"


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
    fmt: str = "steps",
    max_tokens: int = 16384,
) -> tuple[list[dict], str | None]:
    provider = provider or get_provider()
    system = build_system_prompt(system_prompt, append=append_system, fmt=fmt)
    user = build_user_prompt(context, user_template)
    text = provider.complete(system=system, user=user, max_tokens=max_tokens)
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
