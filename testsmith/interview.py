"""Adaptive interview: LLM asks clarifying questions one at a time, only when needed."""

from __future__ import annotations

import json
import re

from rich.console import Console
from rich.prompt import Prompt

from .providers import LLMProvider

INTERVIEW_SYSTEM_PROMPT = """You are a senior QA engineer preparing to write test cases.
You will review product context and decide whether you need a clarification from the
user before you can write high-quality test cases.

Rules:
- Ask a clarifying question ONLY if the answer would MEANINGFULLY change the test cases.
  Do NOT ask about things you can reasonably assume or that are already clear.
- Ask about things like: user roles, platforms, acceptance criteria, edge cases,
  out-of-scope items, non-functional concerns (a11y, perf, security), integrations.
- Ask ONE focused question at a time. Do not batch multiple questions.
- Stop asking as soon as you have enough to write solid test cases. It is perfectly
  fine — and often correct — to ask zero questions.

Return ONLY a JSON object (no prose, no markdown fences) with EXACTLY these keys:
- "need_clarification": boolean
- "question": string (the next question to ask, or "" if need_clarification is false)
- "reason": string (short rationale; why you need this, or why you are ready to proceed)
"""


def run_interview(
    context: str,
    provider: LLMProvider,
    console: Console,
    max_turns: int = 5,
) -> str:
    """Adaptively ask clarifying questions one at a time until the LLM is confident."""
    console.print(
        "[cyan]Checking context for ambiguity...[/cyan] "
        "[dim](type [cyan]done[/cyan] at any prompt to stop early)[/dim]"
    )

    answers: list[tuple[str, str]] = []
    asked: set[str] = set()

    for turn in range(1, max_turns + 1):
        enriched = _build_context_with_answers(context, answers)
        try:
            raw = provider.complete(
                system=INTERVIEW_SYSTEM_PROMPT,
                user=(
                    f"Product context:\n\n{enriched}\n\n"
                    "Decide if you need one more clarifying question. "
                    "Return the JSON object now."
                ),
                max_tokens=4096,
            )
            if not raw or not raw.strip():
                raise ValueError("empty response from model")
            decision = _parse_decision(raw)
        except Exception as e:
            console.print(
                f"[yellow]Clarification check failed ({e}); proceeding.[/yellow]"
            )
            break

        if not decision.get("need_clarification"):
            if turn == 1:
                console.print(
                    "[green]Context looks clear — no questions needed.[/green]"
                )
            else:
                console.print(
                    "[green]Enough context gathered — generating now.[/green]"
                )
            break

        question = (decision.get("question") or "").strip()
        if not question or question in asked:
            break
        asked.add(question)

        try:
            ans = Prompt.ask(
                f"[green]?[/green] {question}", default="", show_default=False
            )
        except (EOFError, KeyboardInterrupt):
            console.print(
                "\n[yellow]Interview aborted — generating with current answers.[/yellow]"
            )
            break

        ans = ans.strip()
        if ans.lower() == "done":
            break
        if not ans or ans.lower() == "skip":
            # Record the skip so the model doesn't re-ask the same thing.
            answers.append((question, "(user skipped)"))
            continue
        answers.append((question, ans))
    else:
        console.print(
            f"[yellow]Reached max {max_turns} questions — proceeding.[/yellow]"
        )

    return _build_context_with_answers(context, answers)


def _build_context_with_answers(context: str, answers: list[tuple[str, str]]) -> str:
    if not answers:
        return context
    addendum = "\n\n".join(f"Q: {q}\nA: {a}" for q, a in answers)
    return f"{context}\n\n---\nClarifications from the user:\n\n{addendum}"


def _parse_decision(text: str) -> dict:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    return data
