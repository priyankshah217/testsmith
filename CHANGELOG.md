# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-04-12

### Added
- **OpenAI-compatible provider**: supports OpenAI, LiteLLM gateway, Azure
  OpenAI, Ollama, vLLM, and any OpenAI-compatible API. Install with
  `pip install testsmith-ai[openai]`. Configure via `OPENAI_API_KEY` and
  optional `OPENAI_BASE_URL` for custom endpoints.
- Auto-detection of provider from model name (gpt-*, o1-*, o3-*, o4-*).

## [0.3.2] - 2026-04-12

### Added
- **LLM-as-judge** quality correction: when the code-level validator detects
  quality warnings (hedging, "e.g.", duplication), the output is automatically
  sent to a second LLM call with a QA Reviewer persona for correction. Single
  retry max; graceful fallback to original output on failure.

### Fixed
- Synced SELF-CHECK banned word list in prompt with `quality.py` validator
  (7 strings were missing: "for instance", "possibly", "probably", "could",
  "as per the UX", "matches the design", "correctly describes").
- Default user template now wraps `{context}` with injection boundary markers.
- `user_with_checklist.md` no longer references undefined Phase 1/2/3.
- `system_mobile_app.md` trigger conditions tightened to prevent over-generation.

## [0.3.1] - 2026-04-12

### Fixed
- Synced SELF-CHECK banned word list (7 missing strings).
- Added context injection boundary to default user template.
- Tightened sample prompt trigger conditions.

## [0.3.0] - 2026-04-11

### Added
- Post-generation quality validator (`quality.py`) with regex-based checks
  for hedging language, exemplification, precondition/step overlap, and
  duplicate test cases. Warnings displayed before CSV write.
- Sample prompts in `prompts/` directory: `system_advanced.md`,
  `system_mobile_app.md`, `user_with_checklist.md`.
- Upgraded default system prompt with coverage guidance, field quality rules,
  and SELF-CHECK lint directive.

## [0.2.2] - 2026-04-10

### Added
- `.env` file support via `python-dotenv`. Place a `.env` in the working
  directory; environment variables always take priority.
- `.env.example` with all configurable variables.
- `--debug` flag to dump raw LLM response and system prompt for
  troubleshooting parse failures.

### Fixed
- User prompt templates with JSON examples (curly braces) no longer
  crash with `KeyError`. Switched from `str.format()` to `str.replace()`.
- JSON parse resilience: strip trailing commas, extract JSON from
  prose-wrapped responses, better error messages with position context.
- Updated README, CLAUDE.md, and SKILL.md for all v0.2.x features
  including `--trace`, `--debug`, `--max-tokens`, and PyPI package name.

## [0.2.1] - 2026-04-09

### Fixed
- Failed sources no longer inject error markers into LLM context,
  preventing the LLM from generating test cases about the errors.
- CLI aborts with a clear message when all sources fail to load.

## [0.2.0] - 2026-04-09

### Added
- `--model`, `--temperature`, `--top-p` flags with automatic provider
  inference from model name and mismatch detection.
- `--format bdd` flag for business-focused Given/When/Then test steps.
- `--trace` flag for on-demand source traceability columns (document,
  section, quote, derivation). Design sources like Figma describe visual
  elements instead of verbatim quotes.
- `--max-tokens` flag to control LLM output budget (default 16384).
- Dynamic CSV columns: extra fields from LLM responses (e.g. source
  traceability) are included when `--trace` is enabled.
- BDD steps now render on separate lines in CSV cells.
- GitHub Actions publish workflow for automated PyPI releases.

### Fixed
- Confluence pages using `ac:` macros (layouts, structured macros)
  returned empty content. Now preserves text from content-bearing tags.
- Source loading errors now shown as visible warnings instead of being
  silently embedded in context.
- Custom system prompts with extra fields (e.g. source traceability)
  no longer conflict with the output contract.
- `CONFLUENCE_BASE_URL` with trailing `/wiki` no longer causes double
  path in API requests.
- Figma API timeout increased from 30s to 60s; `TimeoutError` now
  caught gracefully instead of crashing.
- Gemini thinking models no longer exhaust token budget on large prompts.

## [0.1.0] - 2026-04-09

### Added
- Initial CLI: generate QA test cases as CSV from a feature prompt and/or
  supporting inputs.
- Provider abstraction with Anthropic Claude and Google Gemini backends,
  auto-detected from environment variables.
- Pluggable source pipeline (`testsmith/sources/`) with a `Source` protocol
  and ordered registry.
- Built-in sources:
  - `PdfSource`, `DocxSource`, `TextSource` for local files.
  - `ConfluenceSource` for Atlassian Cloud pages (stdlib HTTP, storage-format
    XHTML to text).
  - `FigmaSource` for Figma designs (text-only node-tree extraction).
- Adaptive clarification interview (`-i`): LLM asks one question at a time
  and stops as soon as it has enough context.
- LLM-suggested output filenames (kebab-case, collision-safe) with `-o`
  override.
- Custom system and user prompt templates via `-s` / `-u` (inline or
  `@path/to/file`), with `--append-system` to extend the default.
