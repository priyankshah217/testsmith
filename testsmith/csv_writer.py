"""Write test cases to CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from .generator import CSV_COLUMNS


def write_csv(rows: list[dict], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: _stringify(row.get(col, "")) for col in CSV_COLUMNS})
    return len(rows)


def _stringify(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(v) for v in value)
    return str(value)
