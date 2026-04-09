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

_STEPS_GUIDANCE_DEFAULT = '- Steps: numbered steps, each on its own line (use "\\n" inside the JSON string). Example: "1. Open app\\n2. Click login\\n3. Enter credentials".'

_STEPS_GUIDANCE_BDD = """\
- Steps: write in BDD format using Given / When / Then keywords, each on its own line (use "\\n" inside the JSON string).
  Each step MUST start with one of: "Given", "When", "Then", "And", "But".
  Example: "Given user has an active subscription\\nWhen the subscription renewal date arrives\\nThen the subscription is renewed automatically\\nAnd the user receives a confirmation email"

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


def _build_output_contract(fmt: str = "steps", trace: bool = False) -> str:
    steps_guidance = _STEPS_GUIDANCE_BDD if fmt == "bdd" else _STEPS_GUIDANCE_DEFAULT
    trace_guidance = _TRACE_GUIDANCE_TEXT if trace else ""
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
- Type: one of Functional, Negative, Edge, UI, Integration, Performance, Security, Accessibility.
{trace_guidance}"""


_TRACE_GUIDANCE_TEXT = """
IMPORTANT — Source traceability (required):
Each test case MUST also include a "source" object with these keys:
- "document": which source document or design file the test was derived from
- "section": specific section, heading, rule ID, or component/screen name
- "quote": verbatim excerpt (≤ 50 words) from the source that justifies this test.
  For design sources (e.g. Figma) where no text is quotable, describe the visual element
  or interaction pattern instead (e.g. "Toggle switch for Delivery option in Deal Method section").
- "derivation": one sentence explaining how the test was derived (e.g. boundary test, negative case, happy path)"""


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
    trace: bool = False,
) -> str:
    contract = _build_output_contract(fmt, trace=trace)
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
    trace: bool = False,
) -> tuple[list[dict], str | None]:
    provider = provider or get_provider()
    system = build_system_prompt(
        system_prompt, append=append_system, fmt=fmt, trace=trace
    )
    user = build_user_prompt(context, user_template)
    text = provider.complete(system=system, user=user, max_tokens=max_tokens)
    return _parse_response(text)


def _parse_response(text: str) -> tuple[list[dict], str | None]:
    text = text.strip()
    # Strip accidental code fences.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    # Strip trailing commas before } or ] (common LLM mistake)
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Try to find JSON object or array in the response
    if not text.startswith(("{", "[")):
        # Model may have added prose before/after the JSON
        # Prefer array match (bare array) over object match (single object inside array)
        arr_match = re.search(r"\[.*\]", text, re.DOTALL)
        obj_match = re.search(r"\{.*\}", text, re.DOTALL)
        if arr_match:
            text = arr_match.group(0)
        elif obj_match:
            text = obj_match.group(0)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        # Show a useful snippet around the error position
        pos = e.pos or 0
        snippet = text[max(0, pos - 40) : pos + 40]
        raise ValueError(
            f"Failed to parse model response as JSON at position {pos}: {e.msg}\n"
            f"  ...{snippet}..."
        ) from e

    # Object form: {"suggested_filename": ..., "test_cases": [...]}
    if isinstance(data, dict):
        rows = data.get("test_cases")
        if not isinstance(rows, list):
            raise ValueError("Model response missing 'test_cases' array")
        name = data.get("suggested_filename")
        return rows, name if isinstance(name, str) and name.strip() else None

    # Bare array
    if isinstance(data, list):
        return data, None

    raise ValueError("Model did not return a JSON array or object")
