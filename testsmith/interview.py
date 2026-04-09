"""Interactive interview: LLM asks clarifying questions, user answers."""
from __future__ import annotations

import json
import re

from rich.console import Console
from rich.prompt import Prompt

from .providers import LLMProvider

INTERVIEW_SYSTEM_PROMPT = """You are a senior QA engineer preparing to write test cases.
Given the product context below, identify the most important gaps and ambiguities
that would meaningfully improve test coverage if clarified.

Return ONLY a JSON array of 3 to 5 concise clarifying questions (strings, no prose,
no markdown fences). Ask only about things NOT already clear from the context.
Prefer questions about: user roles, platforms, acceptance criteria, edge cases,
out-of-scope items, and non-functional concerns (a11y, perf, security).

Example output:
["Which user roles should I cover?", "What platforms are in scope?"]
"""


def run_interview(
    context: str,
    provider: LLMProvider,
    console: Console,
    max_questions: int = 5,
) -> str:
    """Ask the LLM for clarifying questions, prompt the user, return enriched context."""
    console.print("[cyan]Analyzing context for clarifying questions...[/cyan]")
    try:
        raw = provider.complete(
            system=INTERVIEW_SYSTEM_PROMPT,
            user=f"Product context:\n\n{context}\n\nReturn the JSON array of questions now.",
            max_tokens=1024,
        )
        questions = _parse_questions(raw)[:max_questions]
    except Exception as e:
        console.print(f"[yellow]Could not generate questions ({e}); skipping interview.[/yellow]")
        return context

    if not questions:
        console.print("[yellow]No clarifying questions — proceeding with existing context.[/yellow]")
        return context

    console.print(
        f"\n[bold]I have {len(questions)} question(s) to improve coverage.[/bold] "
        "Press Enter or type [cyan]skip[/cyan] to skip a question, "
        "type [cyan]done[/cyan] to stop early.\n"
    )

    answers: list[tuple[str, str]] = []
    for i, q in enumerate(questions, start=1):
        try:
            ans = Prompt.ask(f"[green]{i}.[/green] {q}", default="", show_default=False)
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Interview aborted — generating with current answers.[/yellow]")
            break
        ans = ans.strip()
        if ans.lower() == "done":
            break
        if not ans or ans.lower() == "skip":
            continue
        answers.append((q, ans))

    if not answers:
        console.print("[yellow]No answers provided — proceeding with original context.[/yellow]")
        return context

    addendum = "\n\n".join(f"Q: {q}\nA: {a}" for q, a in answers)
    return f"{context}\n\n---\nClarifications from the user:\n\n{addendum}"


def _parse_questions(text: str) -> list[str]:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("["):
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            text = match.group(0)
    data = json.loads(text)
    if not isinstance(data, list):
        return []
    return [str(q).strip() for q in data if str(q).strip()]
