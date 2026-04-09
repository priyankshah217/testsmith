"""Write test cases to CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from .generator import CSV_COLUMNS


def _flatten(row: dict, parent_key: str = "") -> dict:
    """Flatten nested dicts into dot-separated keys.

    Example: {"source": {"document": "PRD"}} → {"source.document": "PRD"}
    """
    items: dict = {}
    for key, value in row.items():
        full_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(_flatten(value, full_key))
        else:
            items[full_key] = value
    return items


def write_csv(rows: list[dict], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Flatten nested objects (e.g. source.document, source.section)
    flat_rows = [_flatten(row) for row in rows]

    # Discover extra columns beyond the standard set, preserving order of first appearance
    extra: list[str] = []
    seen = set(CSV_COLUMNS)
    for row in flat_rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                extra.append(key)

    fieldnames = CSV_COLUMNS + extra

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in flat_rows:
            writer.writerow({col: _stringify(row.get(col, "")) for col in fieldnames})
    return len(rows)


def _stringify(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " | ".join(str(v) for v in value)
    return str(value)
