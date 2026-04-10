"""Generic quality checks for generated test cases.

Validates test case fields against common quality issues:
- Vague or hedging language in Expected Results
- Non-specific actions in Steps and Preconditions
- Steps that duplicate Preconditions
- Duplicate (Preconditions + Steps) pairs
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Phrases that signal vague or non-deterministic expected results.
_HEDGING_PATTERNS: list[str] = [
    r"\blikely\b",
    r"\bmay\b",
    r"\bmight\b",
    r"\bpossibly\b",
    r"\bshould\b",
    r"\bprobably\b",
    r"\bcould\b",
    r"e\.g\.",
    r"\bfor example\b",
    r"\bfor instance\b",
    r"\bsuch as\b",
    r"\bas per the design\b",
    r"\bas per the UX\b",
    r"\bmatches the design\b",
    r"\baccurately describes\b",
    r"\bcorrectly reflects\b",
    r"\bcorrectly describes\b",
]

# Phrases that signal non-specific actions in Steps or Preconditions.
_EXEMPLIFICATION_PATTERNS: list[str] = [
    r"e\.g\.",
    r"\bfor example\b",
    r"\bfor instance\b",
    r"\bsuch as\b",
]

_HEDGING_RE = re.compile("|".join(_HEDGING_PATTERNS), re.IGNORECASE)
_EXEMPLIFICATION_RE = re.compile(
    "|".join(_EXEMPLIFICATION_PATTERNS), re.IGNORECASE
)


@dataclass
class QualityWarning:
    """A single quality issue found in a test case."""

    tc_id: str
    field: str
    issue: str
    matched_text: str


@dataclass
class QualityReport:
    """Summary of quality checks across all test cases."""

    warnings: list[QualityWarning] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return len(self.warnings) == 0

    @property
    def count(self) -> int:
        return len(self.warnings)

    def summary_lines(self) -> list[str]:
        """Return human-readable warning lines for CLI output."""
        lines: list[str] = []
        for w in self.warnings:
            lines.append(f"  {w.tc_id} [{w.field}]: {w.issue} (found: \"{w.matched_text}\")")
        return lines


def check_quality(rows: list[dict]) -> QualityReport:
    """Run all quality checks on a list of test case dicts.

    Each dict is expected to have at minimum:
    ID, Title, Preconditions, Steps, Expected Result
    """
    report = QualityReport()

    for row in rows:
        tc_id = str(row.get("ID", "?"))
        _check_hedging(tc_id, row, report)
        _check_exemplification(tc_id, row, report)
        _check_precondition_step_overlap(tc_id, row, report)

    _check_duplicates(rows, report)
    return report


def _check_hedging(tc_id: str, row: dict, report: QualityReport) -> None:
    """Flag hedging/vague language in Expected Result."""
    expected = str(row.get("Expected Result", ""))
    if not expected:
        return
    match = _HEDGING_RE.search(expected)
    if match:
        report.warnings.append(
            QualityWarning(
                tc_id=tc_id,
                field="Expected Result",
                issue="vague or hedging language",
                matched_text=match.group(),
            )
        )


def _check_exemplification(
    tc_id: str, row: dict, report: QualityReport
) -> None:
    """Flag 'e.g.' / 'for example' etc. in Steps and Preconditions."""
    for field_name in ("Steps", "Preconditions"):
        text = str(row.get(field_name, ""))
        if not text:
            continue
        match = _EXEMPLIFICATION_RE.search(text)
        if match:
            report.warnings.append(
                QualityWarning(
                    tc_id=tc_id,
                    field=field_name,
                    issue="non-specific language",
                    matched_text=match.group(),
                )
            )


def _check_precondition_step_overlap(
    tc_id: str, row: dict, report: QualityReport
) -> None:
    """Flag when Steps restate Preconditions."""
    preconditions = str(row.get("Preconditions", "")).lower().strip()
    steps = str(row.get("Steps", "")).lower().strip()
    if not preconditions or not steps:
        return

    # Extract meaningful phrases from preconditions (ignore short/generic ones)
    # Split on common delimiters and check if any precondition phrase
    # appears verbatim in the steps.
    for phrase in re.split(r"[.\n;]+", preconditions):
        phrase = phrase.strip()
        # Skip short phrases that would produce false positives
        if len(phrase) < 20:
            continue
        if phrase in steps:
            report.warnings.append(
                QualityWarning(
                    tc_id=tc_id,
                    field="Steps",
                    issue="restates Preconditions",
                    matched_text=phrase[:60],
                )
            )
            break  # One warning per test case is enough


def _check_duplicates(rows: list[dict], report: QualityReport) -> None:
    """Flag test cases with identical (Preconditions + Steps) pairs."""
    seen: dict[str, str] = {}
    for row in rows:
        tc_id = str(row.get("ID", "?"))
        key = (
            str(row.get("Preconditions", "")).strip().lower()
            + "|||"
            + str(row.get("Steps", "")).strip().lower()
        )
        if key in seen:
            report.warnings.append(
                QualityWarning(
                    tc_id=tc_id,
                    field="Preconditions+Steps",
                    issue=f"duplicate of {seen[key]}",
                    matched_text="same preconditions and steps",
                )
            )
        else:
            seen[key] = tc_id
