"""Build the combined context string from a prompt and a list of references.

Loading logic lives in `testsmith.sources`. This module only composes
`LoadedDoc`s into the final context passed to the LLM.
"""

from __future__ import annotations

from .sources import SourceError, load

_SEPARATOR = "\n\n---\n\n"


def build_context(
    prompt: str | None, refs: list[str]
) -> tuple[str, list[str]]:
    """Build context and return (context_string, list_of_error_messages)."""
    parts: list[str] = []
    errors: list[str] = []
    if prompt:
        parts.append(f"## User Prompt\n{prompt}")
    for ref in refs:
        try:
            doc = load(ref)
            parts.append(f"## {doc.title}\n{doc.text}")
        except SourceError as e:
            parts.append(f"## {ref}\n[ERROR loading source: {e}]")
            errors.append(f"{ref}: {e}")
    return _SEPARATOR.join(parts), errors
