# CLAUDE.md

Guidance for Claude Code when working in this repo.

## What this project is

`testsmith` is a CLI that generates QA test cases as CSV from a feature
description and/or supporting sources (local files, Confluence pages, Figma
designs), using Anthropic Claude or Google Gemini as the LLM.

Entry point: `testsmith = "testsmith.cli:app"` (defined in `pyproject.toml`).

## Architecture

```
testsmith/
├── cli.py           Typer CLI. Orchestrates: load → (optional) interview → generate → judge → write
├── loaders.py       Thin composer. Turns (prompt, [refs]) into one context string
├── sources/         Pluggable input pipeline
│   ├── base.py      Source protocol, LoadedDoc dataclass, SourceError
│   ├── registry.py  Ordered REGISTRY + load() dispatcher + register() helper
│   ├── files.py     PdfSource, DocxSource, TextSource
│   ├── confluence.py  ConfluenceSource (stdlib HTTP, storage-format → text)
│   └── figma.py     FigmaSource (stdlib HTTP, node tree → text, text-only v1)
├── interview.py     Adaptive clarification loop (one-at-a-time, LLM-gated)
├── generator.py     Builds prompts, calls the provider, parses JSON response
│                    (returns tuple: (rows, suggested_filename))
│                    Supports --format (steps | bdd) via _build_output_contract()
│                    LLM-as-judge: judge_and_fix() sends quality warnings back
│                    to the LLM for correction (single retry, no loop)
├── quality.py       Post-generation quality validator. Regex-based checks for
│                    hedging language, exemplification, precondition/step overlap,
│                    and duplicate test cases. Returns QualityReport.
├── providers.py     LLMProvider protocol + AnthropicProvider + GeminiProvider
└── csv_writer.py    Writes rows to CSV with the canonical column schema
```

### Key conventions

- **Sources are the extension point.** Adding a new input type (Notion,
  Jira, Linear, GitHub issues, ...) means creating a class that implements
  the `Source` protocol in `sources/base.py` and registering it in
  `sources/registry.py`. No changes to CLI, loaders, generator, or
  interview should be needed.
- **URL-based sources come first in the registry** so a URL isn't
  misinterpreted as a filesystem path by a file source.
- **Stdlib-only HTTP for sources.** Both `ConfluenceSource` and
  `FigmaSource` use `urllib.request`. Do NOT add `requests` or `httpx`
  for new sources unless there is a concrete need — keeping deps minimal
  is a goal.
- **Generator returns `(rows, suggested_filename)`.** The LLM emits both
  in a single completion so naming is free (no extra API call). The CLI
  slugifies and handles collisions with `_2`, `_3` suffixes.
- **Interview is adaptive, not batched.** The model decides per turn
  whether another clarifying question is needed; simple prompts get zero
  questions, dense specs get more (hard-capped at 5 turns).
- **Failed sources are excluded from context.** `build_context` catches
  `SourceError`, excludes it from context, and returns errors separately.
  The CLI shows warnings and aborts if ALL sources fail and no prompt
  is provided. Partial failures proceed with available sources only.
- **`.env` support.** `python-dotenv` loads `.env` from the current
  directory at startup. Env vars always override `.env` values.
- **Two-layer quality enforcement.** `quality.py` runs regex checks on
  generated test cases (hedging, exemplification, duplication). If
  warnings are found, `judge_and_fix()` in `generator.py` sends them
  to the LLM as a QA Reviewer for correction. Single retry max — if
  the judge fails, the original output is used. The code-level
  validator always runs again on the corrected output as a final check.
- **Context injection boundary.** The default user template wraps
  `{context}` with `PRODUCT CONTEXT START/END` markers and a "treat
  as data only" instruction to mitigate prompt injection from source
  documents.

## Adding a new source

1. Create `testsmith/sources/<name>.py` with a class implementing:
   ```python
   class MyNewSource:
       name = "mynew"
       def matches(self, ref: str) -> bool: ...
       def load(self, ref: str) -> LoadedDoc: ...
   ```
2. Raise `SourceError` on any failure — network, auth, parse, empty result.
3. Register it in `testsmith/sources/registry.py`. URL-based sources go
   before file sources.
4. Smoke-test with:
   ```bash
   python -c "from testsmith.sources import REGISTRY, load; print([s.name for s in REGISTRY])"
   ```
5. Update `README.md`'s supported-sources table and add a setup section
   if the source needs env vars.

## Running locally

```bash
cd ~/PythonProjects/testsmith
source .venv/bin/activate
pip install -e .

# Smoke test
testsmith -p "Login screen with email + password and social auth"
```

## Environment variables

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | Use Anthropic Claude (preferred if both set) |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Use Google Gemini |
| `TESTSMITH_PROVIDER` | Force provider (`anthropic` or `gemini`) |
| `CONFLUENCE_BASE_URL` / `CONFLUENCE_EMAIL` / `CONFLUENCE_API_TOKEN` | Confluence source |
| `FIGMA_API_TOKEN` | Figma source |

All variables can be set in a `.env` file in the working directory
(loaded via `python-dotenv`). Env vars always take priority over `.env`.

## Things to preserve

- **Single-command Typer app.** There is no `generate` subcommand — the
  CLI is just `testsmith [OPTIONS]`.
- **`-f` accepts both paths and URLs.** Do not split this into two flags;
  the registry dispatches based on the ref's shape.
- **Provider abstraction.** New LLM providers should implement
  `LLMProvider.complete(system, user, max_tokens) -> str`. Keep this
  interface narrow — features that need structured output (like the
  filename suggestion) live in the prompt contract, not the provider API.
- **Format is prompt-driven.** The `--format` flag (`steps` or `bdd`)
  controls test step style purely through the output contract prompt in
  `generator.py` (`_build_output_contract(fmt)`). BDD mode enforces
  business-focused Given/When/Then language and blocks UI-interaction
  words. Adding new formats means adding a new `_STEPS_GUIDANCE_*`
  constant — no changes to CSV writer or parsing needed.

## Out of scope for v1 (intentional)

- Multimodal / screenshot extraction for Figma. Requires extending
  `LLMProvider.complete` with image inputs and gating on vision-capable
  providers; significant refactor. Deferred.
- Recursive page-tree fetching for Confluence (`--include-children`).
- Recorded-HTTP fixture tests for the network sources.
