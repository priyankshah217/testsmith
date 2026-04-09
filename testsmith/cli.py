"""testsmith CLI entrypoint."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .csv_writer import write_csv
from .generator import generate_test_cases
from .interview import run_interview
from .loaders import build_context
from .providers import get_provider

app = typer.Typer(
    add_completion=False, help="Generate QA test cases from text and documents."
)
console = Console()


@app.command()
def generate(
    prompt: Optional[str] = typer.Option(
        None, "--prompt", "-p", help="Plain text prompt / feature description."
    ),
    file: list[str] = typer.Option(
        [],
        "--file",
        "-f",
        help="Input source: local file (PDF/DOCX/MD/TXT) or URL. Repeatable.",
    ),
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Output CSV path. If omitted, a name is suggested by the LLM.",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help="LLM provider: 'anthropic' or 'gemini'. Auto-detected from env if omitted.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model name (e.g. 'claude-sonnet-4-6', 'gemini-2.5-flash'). Defaults per provider.",
    ),
    temperature: Optional[float] = typer.Option(
        None,
        "--temperature",
        "-t",
        help="Sampling temperature (0.0–2.0). Lower = more deterministic.",
    ),
    top_p: Optional[float] = typer.Option(
        None,
        "--top-p",
        help="Nucleus sampling top-p (0.0–1.0).",
    ),
    system_prompt: Optional[str] = typer.Option(
        None,
        "--system",
        "-s",
        help="Custom system prompt. Inline text or @path/to/file.txt. Replaces the default.",
    ),
    append_system: bool = typer.Option(
        False,
        "--append-system",
        help="Append --system to the default system prompt instead of replacing it.",
    ),
    user_template: Optional[str] = typer.Option(
        None,
        "--user-template",
        "-u",
        help="Custom user prompt template. Inline text or @path/to/file.txt. Use {context} as a placeholder.",
    ),
    fmt: str = typer.Option(
        "steps",
        "--format",
        help="Test step format: 'steps' (numbered steps) or 'bdd' (Given/When/Then, business-focused).",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Let the LLM ask clarifying questions before generating test cases.",
    ),
):
    """Generate test cases and write them to a CSV file."""
    if fmt not in ("steps", "bdd"):
        console.print(
            "[red]Error:[/red] --format must be 'steps' or 'bdd'."
        )
        raise typer.Exit(code=2)

    system_prompt = _resolve_text_arg(system_prompt)
    user_template = _resolve_text_arg(user_template)

    if not prompt and not file and sys.stdin.isatty() is False:
        prompt = sys.stdin.read().strip() or None

    if not prompt and not file:
        console.print(
            "[red]Error:[/red] provide --prompt and/or --file (or pipe text via stdin)."
        )
        raise typer.Exit(code=2)

    console.print(f"[cyan]Loading context[/cyan] ({len(file)} source(s))...")
    context = build_context(prompt, list(file))
    if not context.strip():
        console.print("[red]Error:[/red] context is empty after loading.")
        raise typer.Exit(code=2)

    try:
        llm = get_provider(provider, model=model, temperature=temperature, top_p=top_p)
    except Exception as e:
        console.print(f"[red]Provider error:[/red] {e}")
        raise typer.Exit(code=2)

    if interactive:
        if not sys.stdin.isatty():
            console.print(
                "[yellow]Stdin is piped — skipping interactive mode.[/yellow]"
            )
        else:
            context = run_interview(context, provider=llm, console=console)

    console.print(f"[cyan]Generating test cases via {llm.name} ({llm.model})...[/cyan]")
    try:
        rows, suggested = generate_test_cases(
            context,
            provider=llm,
            system_prompt=system_prompt,
            user_template=user_template,
            append_system=append_system,
            fmt=fmt,
        )
    except Exception as e:
        console.print(f"[red]Generation failed:[/red] {e}")
        raise typer.Exit(code=1)

    if out is None:
        out = _resolve_output_path(suggested)

    count = write_csv(rows, out)
    console.print(f"[green]Wrote {count} test case(s) to[/green] {out}")


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    return slug[:60] or "test-cases"


def _resolve_output_path(suggested: str | None) -> Path:
    base = _slugify(suggested) if suggested else "test-cases"
    path = Path(f"{base}.csv")
    n = 2
    while path.exists():
        path = Path(f"{base}_{n}.csv")
        n += 1
    return path


def _resolve_text_arg(value: Optional[str]) -> Optional[str]:
    """Allow '@path/to/file' to load text from a file."""
    if value and value.startswith("@"):
        return Path(value[1:]).expanduser().read_text(encoding="utf-8")
    return value


if __name__ == "__main__":
    app()
