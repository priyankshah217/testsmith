# testsmith

Forge QA test cases from text and documents using LLMs.

`testsmith` is a CLI that takes a feature description and/or supporting documents (PDF, DOCX, MD, TXT), sends them to an LLM (Anthropic Claude or Google Gemini), and writes the generated test cases to a CSV file.

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
testsmith generate [OPTIONS]
```

You must provide at least one of `--prompt`, `--file`, or piped stdin.

### Options

| Option | Description |
| --- | --- |
| `-p`, `--prompt TEXT` | Plain text prompt / feature description. |
| `-f`, `--file PATH` | Local file to include as context (PDF, DOCX, MD, TXT). Repeatable. |
| `-o`, `--out PATH` | Output CSV path. Default: `test_cases.csv`. |
| `--provider TEXT` | LLM provider: `anthropic` or `gemini`. Auto-detected from env if omitted. |
| `-s`, `--system TEXT` | Custom system prompt. Inline text or `@path/to/file.txt`. Replaces the default. |
| `--append-system` | Append `--system` to the default system prompt instead of replacing it. |
| `-u`, `--user-template TEXT` | Custom user prompt template. Inline text or `@path/to/file.txt`. Use `{context}` as a placeholder. |

### Examples

Generate from an inline prompt:

```bash
testsmith generate -p "Login screen with email + password, forgot password link, and social login"
```

Generate from one or more documents:

```bash
testsmith generate -f specs/checkout.pdf -f specs/payment.docx -o checkout_cases.csv
```

Mix a prompt with supporting files:

```bash
testsmith generate -p "Focus on edge cases" -f specs/checkout.pdf
```

Pipe text via stdin:

```bash
cat feature.md | testsmith generate
```

Pick a provider explicitly:

```bash
testsmith generate -p "Signup flow" --provider anthropic
```

Use a custom system prompt from a file:

```bash
testsmith generate -f spec.pdf --system @prompts/qa_system.txt
```

Append to the default system prompt instead of replacing it:

```bash
testsmith generate -f spec.pdf --system "Focus on accessibility test cases." --append-system
```

Use a custom user template with a `{context}` placeholder:

```bash
testsmith generate -f spec.pdf --user-template @prompts/user_template.txt
```

## Output

Test cases are written to a CSV file (default `test_cases.csv`) in the current directory.
