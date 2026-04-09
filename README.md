# testsmith

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Forge QA test cases from text, documents, Confluence pages, and Figma designs using LLMs.

`testsmith` is a CLI that takes a feature description and/or supporting sources (local files or URLs), sends them to an LLM (Anthropic Claude or Google Gemini), and writes the generated test cases to a CSV file.

## Requirements

- Python >= 3.11
- An API key for one of the supported providers:
  - `ANTHROPIC_API_KEY` for Anthropic Claude
  - `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) for Google Gemini

## Installation

### Via pipx (recommended)

[pipx](https://pipx.pypa.io/) installs CLI tools in isolated environments so they don't conflict with your system Python:

```bash
# Install pipx (pick your platform)
# macOS:   brew install pipx
# Linux:   python3 -m pip install --user pipx
# Windows: python -m pip install --user pipx

pipx install git+https://github.com/priyankshah217/testsmith.git
```

To upgrade later:

```bash
pipx upgrade testsmith
```

### Via pip (in a virtualenv)

```bash
# macOS / Linux
python3 -m venv .venv && source .venv/bin/activate

# Windows
python -m venv .venv && .venv\Scripts\activate

pip install git+https://github.com/priyankshah217/testsmith.git
```

### From source (for development)

```bash
git clone https://github.com/priyankshah217/testsmith.git
cd testsmith

# macOS / Linux
python3 -m venv .venv && source .venv/bin/activate

# Windows
python -m venv .venv && .venv\Scripts\activate

pip install -e ".[dev]"
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
| `-m`, `--model TEXT` | LLM model name (e.g. `claude-sonnet-4-6`, `gemini-2.5-flash`). Defaults per provider. |
| `-t`, `--temperature FLOAT` | Sampling temperature (0.0–2.0). Lower = more deterministic. |
| `--top-p FLOAT` | Nucleus sampling top-p (0.0–1.0). |
| `--format TEXT` | Test step format: `steps` (default, numbered) or `bdd` (Given/When/Then, business-focused). |
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
| Figma design (text-only) | `-f "https://www.figma.com/design/<fileKey>/<name>?node-id=1-23"` |

Adding new sources (Notion, Jira, Linear, ...) is a single file in `testsmith/sources/` — see `testsmith/sources/base.py` for the `Source` protocol.

### Confluence setup

Set these environment variables to fetch Confluence pages:

```bash
export CONFLUENCE_BASE_URL=https://<your-site>.atlassian.net
export CONFLUENCE_EMAIL=you@example.com
export CONFLUENCE_API_TOKEN=<token from id.atlassian.com/manage-profile/security/api-tokens>
```

### Figma setup

Set a personal access token to fetch Figma designs:

```bash
export FIGMA_API_TOKEN=<token from figma.com/settings>
```

Figma support is **text-only** in v1: frame/component names become headings, text layers become body text, and component descriptions are preserved. Purely visual nodes (vectors, rectangles, etc.) are skipped. If the URL contains a `node-id`, only that subtree is fetched; otherwise the whole file is loaded. **Tip:** right-click a frame in Figma → Copy link to get a URL with the right `node-id`.

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

Generate from a Figma design (quote the URL — the `?` will be interpreted by your shell otherwise):

```bash
testsmith -f "https://www.figma.com/design/ABC123/Checkout?node-id=42-1337"
```

Mix a prompt with supporting files, Confluence pages, and Figma designs:

```bash
testsmith -p "Focus on edge cases" \
  -f "https://www.figma.com/design/ABC123/Checkout?node-id=42-1337" \
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

Generate BDD-style test cases (Given/When/Then, business-focused):

```bash
testsmith -p "Subscription renewal flow" --format bdd
```

Use a specific model with custom temperature:

```bash
testsmith -p "Signup flow" -m claude-sonnet-4-6 -t 0.3
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

### Step formats

| `--format` | Steps column example |
| --- | --- |
| `steps` (default) | `1. Open app \| 2. Enter credentials \| 3. Submit form` |
| `bdd` | `Given user has an active account \| When user provides valid credentials \| Then user is authenticated` |

BDD mode enforces **business-focused language** — steps describe domain intent and outcomes, not UI interactions (no "click", "tap", "navigate", etc.).

## Claude Code skill

Testsmith ships with a [Claude Code skill](https://docs.anthropic.com/en/docs/claude-code/skills) so Claude can run testsmith for you when you ask for test cases.

### Install the skill

Copy the bundled skill to your Claude Code skills directory:

```bash
# macOS / Linux
cp -r skills/testsmith ~/.claude/skills/

# Windows (PowerShell)
Copy-Item -Recurse skills\testsmith $env:USERPROFILE\.claude\skills\
```

Or create a symlink so it stays in sync with the repo:

```bash
ln -s "$(pwd)/skills/testsmith" ~/.claude/skills/testsmith
```

Once installed, just ask Claude Code: *"generate test cases for the login screen"* — it will invoke testsmith automatically.

## Contributing

```bash
git clone https://github.com/priyankshah217/testsmith.git
cd testsmith
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```
