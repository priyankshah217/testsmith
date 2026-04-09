---
name: testsmith
description: Use this skill when the user asks to generate, draft, or update QA test cases from a PRD, RFC, design doc, Figma link, Confluence page, feature description, or any local spec file (PDF/DOCX/MD/TXT). Knows the testsmith CLI flags, prompt conventions, and output format.
---

# Testsmith helper

Testsmith is a CLI that generates QA test cases (CSV) from plain text, document inputs, Confluence pages, and Figma designs using an LLM (Anthropic or Gemini, auto-detected from env).

- **Repo:** https://github.com/priyankshah217/testsmith
- **Install:** `pipx install git+https://github.com/priyankshah217/testsmith.git`
- **Providers:** auto-detects `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`. Override with `--provider anthropic|gemini` or env var `TESTSMITH_PROVIDER`.

## CLI surface

```
testsmith [OPTIONS]

  -p, --prompt TEXT          Inline feature description
  -f, --file REF             Local file (PDF/DOCX/MD/TXT) OR URL
                             (Confluence page, Figma design). Repeatable.
  -o, --out PATH             Output CSV path. If omitted, the LLM suggests a
                             kebab-case filename based on the feature (e.g.
                             login-social-auth.csv). Collisions get _2, _3, ...
  -i, --interactive          Let the LLM ask clarifying questions first
      --provider TEXT        anthropic | gemini
  -m, --model TEXT           LLM model name (e.g. claude-sonnet-4-6, gemini-2.5-flash)
  -t, --temperature FLOAT    Sampling temperature (0.0–2.0)
      --top-p FLOAT          Nucleus sampling top-p (0.0–1.0)
      --format TEXT           Step format: steps (default) or bdd (Given/When/Then)
  -s, --system TEXT          Custom system prompt. Inline or @path/to/file
      --append-system        Append --system to default instead of replacing
  -u, --user-template TEXT   Custom user prompt. Inline or @path. Use {context}
```

Inputs can be combined freely: `-p "..." -f spec.pdf -f https://acme.atlassian.net/wiki/spaces/ENG/pages/12345/PRD`.

## Supported sources

| Source | How to pass it |
| --- | --- |
| Plain text | `-p "feature description"` |
| Local file | `-f path/to/file.pdf` (PDF, DOCX, MD, TXT) |
| Confluence page | `-f https://<site>.atlassian.net/wiki/spaces/<SPACE>/pages/<ID>/<slug>` |
| Figma design | `-f "https://www.figma.com/design/<fileKey>/<name>?node-id=<id>"` (quote it!) |

**Confluence env vars** (required before passing a Confluence URL):
- `CONFLUENCE_BASE_URL` — e.g. `https://acme.atlassian.net`
- `CONFLUENCE_EMAIL` — Atlassian account email
- `CONFLUENCE_API_TOKEN` — from `id.atlassian.com/manage-profile/security/api-tokens`

**Figma env var** (required before passing a Figma URL):
- `FIGMA_API_TOKEN` — from `figma.com/settings`

Figma extraction is **text-only** in v1: frame/component names become headings, text layers become body text, component descriptions are preserved. Purely visual nodes are skipped. Prefer passing a URL with `node-id` (right-click a frame → Copy link) so testsmith fetches just that subtree instead of the whole file.

## Output CSV schema

Columns: `ID, Title, Preconditions, Steps, Expected Result, Priority, Type`

- `ID`: `TC-001`, `TC-002`, ...
- `Steps`: one step per line (newline-separated within the CSV cell). Numbered by default, or Given/When/Then with `--format bdd`
- `Priority`: `P0`–`P3`
- `Type`: `Functional`, `Negative`, `Edge`, `UI`, `Integration`, `Performance`, `Security`, `Accessibility`

## How to use this skill

When the user asks for test cases:

1. **Collect context.** Gather plain-text description, file paths, or URLs. Testsmith natively accepts plain text (`-p`), local files, Confluence URLs, and Figma URLs (all via `-f`).

2. **Pick invocation style.** `-o` is optional — omit it to let the LLM name the file.
   - Quick one-liner: `testsmith -p "<feature description>"`
   - From a doc: `testsmith -f <path>`
   - Mixed: `testsmith -p "<context>" -f <path1> -f <path2>`
   - Force a filename: add `-o <out>.csv` when the user specifies one.

3. **Step format.** If the user asks for BDD, Gherkin, or Given/When/Then style test cases, add `--format bdd`. BDD mode produces business-focused steps (no UI-interaction words like click, tap, navigate). Default is `--format steps` (numbered).

4. **Custom prompting.** Prefer `--append-system` over `--system` so the built-in JSON/CSV output contract stays intact. Use full `--system` replacement only when the user explicitly wants to rewrite the QA persona.

5. **Run it.** Execute the command via Bash from the user's shell (ANTHROPIC_API_KEY / GEMINI_API_KEY are expected to be set in the environment).

6. **Report.** After the command succeeds, tell the user the CSV path and how many rows were generated (testsmith prints this). Offer to open/preview the first few rows.

## Examples

```bash
# Simple prompt (LLM picks the filename)
testsmith -p "Login page with email+password, forgot password link, rate limiting"

# From a PRD (LLM picks the filename)
testsmith -f ~/docs/checkout-prd.pdf

# Focused negative cases
testsmith -f spec.pdf --append-system "Focus heavily on payment failure paths and idempotency."

# Explicit filename
testsmith -p "Password reset flow" -o reset.csv

# Force provider
testsmith --provider gemini -p "Password reset flow"

# BDD format (business-focused Given/When/Then steps)
testsmith -p "Subscription renewal flow" --format bdd

# Specific model and temperature
testsmith -p "Signup flow" -m claude-sonnet-4-6 -t 0.3
```

## Gotchas

- If both API keys are set, Anthropic wins by default. Pass `--provider gemini` to override.
- Large PDFs can blow past the model's context window. If that happens, split the file or pre-summarize before passing it to testsmith.
- If `testsmith` is not on PATH, install with `pipx install git+https://github.com/priyankshah217/testsmith.git` or run `pipx ensurepath`.
