# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Open-source release metadata: `LICENSE` (MIT), `CHANGELOG.md`, expanded
  `pyproject.toml` metadata, README badges.

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
