# testsmith

Forge QA test cases from text, documents, and Confluence pages using LLMs.

`testsmith` is a CLI that takes a feature description and/or supporting sources (local files or URLs), sends them to an LLM (Anthropic Claude or Google Gemini), and writes the generated test cases to a CSV file.

## Requirements

- Python >= 3.11
- An API key for one of the supported providers:
  - `ANTHROPIC_API_KEY` for Anthropic Claude
  - `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) for Google Gemini

## Installation

```bash
cd ~/PythonProjects/testsmith
pip install -e .
```

This installs the `testsmith` command on your PATH.

## Usage

```bash
testsmith [OPTIONS]
```

You must provide at least one of `--prompt`, `--file`, or piped stdin.

### Options

| Option | Description |
| --- | --- |
| `-p`, `--prompt TEXT` | Plain text prompt / feature description. |
| `-f`, `--file REF` | Input source: local file (PDF, DOCX, MD, TXT) **or** URL (e.g. Confluence page). Repeatable. |
| `-o`, `--out PATH` | Output CSV path. If omitted, the LLM suggests a kebab-case filename based on the feature (e.g. `login-social-auth.csv`). Collisions get `_2`, `_3`, ... |
| `--provider TEXT` | LLM provider: `anthropic` or `gemini`. Auto-detected from env if omitted. |
| `-s`, `--system TEXT` | Custom system prompt. Inline text or `@path/to/file.txt`. Replaces the default. |
| `--append-system` | Append `--system` to the default system prompt instead of replacing it. |
| `-u`, `--user-template TEXT` | Custom user prompt template. Inline text or `@path/to/file.txt`. Use `{context}` as a placeholder. |
| `-i`, `--interactive` | Let the LLM ask clarifying questions adaptively before generating. It asks one question at a time and stops as soon as it has enough context (0–5 questions). Type `skip` to skip a question or `done` to stop early. |

### Supported input sources

| Source | Example |
| --- | --- |
| Plain text | `-p "Login screen with social auth"` |
| PDF | `-f ./specs/checkout.pdf` |
| DOCX | `-f ./specs/payment.docx` |
| Markdown / text | `-f ./notes.md` |
| Confluence page | `-f https://acme.atlassian.net/wiki/spaces/ENG/pages/12345/Checkout-PRD` |

Adding new sources (Figma, Notion, Jira, ...) is a single file in `testsmith/sources/` — see `testsmith/sources/base.py` for the `Source` protocol.

### Confluence setup

Set these environment variables to fetch Confluence pages:

```bash
export CONFLUENCE_BASE_URL=https://<your-site>.atlassian.net
export CONFLUENCE_EMAIL=you@example.com
export CONFLUENCE_API_TOKEN=<token from id.atlassian.com/manage-profile/security/api-tokens>
```

### Examples

Generate from an inline prompt (LLM picks the filename):

```bash
testsmith -p "Login screen with email + password, forgot password link, and social login"
```

Generate from documents:

```bash
testsmith -f specs/checkout.pdf -f specs/payment.docx
```

Generate from a Confluence page:

```bash
testsmith -f https://acme.atlassian.net/wiki/spaces/ENG/pages/12345/Checkout-PRD
```

Mix a prompt with supporting files and Confluence pages:

```bash
testsmith -p "Focus on edge cases" \
  -f https://acme.atlassian.net/wiki/spaces/ENG/pages/12345/PRD \
  -f specs/wireframes.pdf
```

Pipe text via stdin:

```bash
cat feature.md | testsmith
```

Pick a provider explicitly:

```bash
testsmith -p "Signup flow" --provider anthropic
```

Interactive mode (LLM asks clarifying questions only when genuinely ambiguous):

```bash
testsmith -i -p "Checkout flow with guest and returning users"
```

Use a custom system prompt from a file:

```bash
testsmith -f spec.pdf --system @prompts/qa_system.txt
```

Append to the default system prompt instead of replacing it:

```bash
testsmith -f spec.pdf --system "Focus on accessibility test cases." --append-system
```

Force an explicit output filename:

```bash
testsmith -p "Password reset flow" -o reset.csv
```

## Output

Test cases are written to a CSV with columns:
`ID, Title, Preconditions, Steps, Expected Result, Priority, Type`

By default the filename is suggested by the LLM based on the feature context; pass `-o` to override.
