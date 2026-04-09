"""Tests for CSV writer."""

from __future__ import annotations

import csv
from pathlib import Path

from testsmith.csv_writer import write_csv


class TestWriteCsv:
    def test_writes_rows(self, tmp_path: Path):
        rows = [
            {"ID": "TC-001", "Title": "Login", "Priority": "P0", "Type": "Functional"},
            {"ID": "TC-002", "Title": "Logout", "Priority": "P1", "Type": "Functional"},
        ]
        out = tmp_path / "out.csv"
        count = write_csv(rows, out)
        assert count == 2
        assert out.exists()

        with out.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            read_rows = list(reader)
        assert len(read_rows) == 2
        assert read_rows[0]["ID"] == "TC-001"
        assert read_rows[1]["Title"] == "Logout"

    def test_creates_parent_dirs(self, tmp_path: Path):
        out = tmp_path / "sub" / "dir" / "out.csv"
        write_csv([{"ID": "TC-001", "Title": "T"}], out)
        assert out.exists()

    def test_stringifies_lists(self, tmp_path: Path):
        rows = [{"ID": "TC-001", "Steps": ["step1", "step2"]}]
        out = tmp_path / "out.csv"
        write_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["Steps"] == "step1\nstep2"

    def test_handles_none_values(self, tmp_path: Path):
        rows = [{"ID": "TC-001", "Title": None}]
        out = tmp_path / "out.csv"
        write_csv(rows, out)
        with out.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["Title"] == ""

    def test_empty_rows(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        count = write_csv([], out)
        assert count == 0
        assert out.exists()
