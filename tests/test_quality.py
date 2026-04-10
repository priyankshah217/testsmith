"""Tests for quality checker."""

from __future__ import annotations

from testsmith.quality import check_quality


def _row(**overrides) -> dict:
    """Build a test case row with sensible defaults."""
    base = {
        "ID": "TC-001",
        "Title": "Test case",
        "Preconditions": "User is logged in",
        "Steps": "1. Open the dashboard",
        "Expected Result": "Dashboard is displayed",
        "Priority": "P0",
        "Type": "Functional",
    }
    base.update(overrides)
    return base


class TestHedgingLanguage:
    """5A — Expected Result must be deterministic."""

    def test_clean_expected_result(self):
        qr = check_quality([_row()])
        assert qr.clean

    def test_flags_may(self):
        qr = check_quality([_row(**{"Expected Result": "The toggle may change state"})])
        assert qr.count == 1
        assert qr.warnings[0].field == "Expected Result"
        assert qr.warnings[0].matched_text == "may"

    def test_flags_likely(self):
        qr = check_quality(
            [_row(**{"Expected Result": "User is likely navigated away"})]
        )
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "likely"

    def test_flags_might(self):
        qr = check_quality(
            [_row(**{"Expected Result": "The button might be disabled"})]
        )
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "might"

    def test_flags_should(self):
        qr = check_quality([_row(**{"Expected Result": "The page should reload"})])
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "should"

    def test_flags_probably(self):
        qr = check_quality([_row(**{"Expected Result": "User probably sees an error"})])
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "probably"

    def test_flags_could(self):
        qr = check_quality([_row(**{"Expected Result": "The state could change"})])
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "could"

    def test_flags_possibly(self):
        qr = check_quality([_row(**{"Expected Result": "User is possibly redirected"})])
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "possibly"

    def test_flags_accurately_describes(self):
        qr = check_quality(
            [
                _row(
                    **{
                        "Expected Result": "Bottom sheet accurately describes the feature"
                    }
                )
            ]
        )
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "accurately describes"

    def test_flags_correctly_reflects(self):
        qr = check_quality(
            [_row(**{"Expected Result": "Content correctly reflects the state"})]
        )
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "correctly reflects"

    def test_flags_matches_the_design(self):
        qr = check_quality(
            [_row(**{"Expected Result": "Widget matches the design spec"})]
        )
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "matches the design"

    def test_flags_as_per_the_design(self):
        qr = check_quality(
            [_row(**{"Expected Result": "Widget is displayed as per the design"})]
        )
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "as per the design"

    def test_flags_as_per_the_ux(self):
        qr = check_quality(
            [_row(**{"Expected Result": "Widget renders as per the UX"})]
        )
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "as per the UX"

    def test_flags_eg_in_expected_result(self):
        qr = check_quality(
            [_row(**{"Expected Result": "An icon (e.g., info) is visible"})]
        )
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "e.g."

    def test_flags_such_as_in_expected_result(self):
        qr = check_quality(
            [_row(**{"Expected Result": "An element such as an info icon appears"})]
        )
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "such as"

    def test_flags_for_example_in_expected_result(self):
        qr = check_quality(
            [_row(**{"Expected Result": "A screen for example the dashboard is shown"})]
        )
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "for example"

    def test_no_false_positive_on_normal_text(self):
        """Words like 'display' or 'shown' should not trigger."""
        qr = check_quality(
            [_row(**{"Expected Result": "The Delivery toggle switches to ON"})]
        )
        assert qr.clean


class TestExemplification:
    """5B — Steps and Preconditions must use specific actions."""

    def test_flags_eg_in_steps(self):
        qr = check_quality([_row(Steps="Toggle a method (e.g., from OFF to ON)")])
        assert qr.count == 1
        assert qr.warnings[0].field == "Steps"
        assert qr.warnings[0].matched_text == "e.g."

    def test_flags_eg_in_preconditions(self):
        qr = check_quality(
            [_row(Preconditions="A deal method (e.g., Delivery) is disabled")]
        )
        assert qr.count == 1
        assert qr.warnings[0].field == "Preconditions"
        assert qr.warnings[0].matched_text == "e.g."

    def test_flags_for_example_in_steps(self):
        qr = check_quality([_row(Steps="Select a method, for example Meet-up")])
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "for example"

    def test_flags_for_instance_in_steps(self):
        qr = check_quality([_row(Steps="Pick a category, for instance Fashion")])
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "for instance"

    def test_flags_such_as_in_preconditions(self):
        qr = check_quality(
            [_row(Preconditions="User is in a category such as Fashion")]
        )
        assert qr.count == 1
        assert qr.warnings[0].matched_text == "such as"

    def test_clean_steps(self):
        qr = check_quality([_row(Steps="Toggle the Delivery option from OFF to ON")])
        assert qr.clean

    def test_clean_preconditions(self):
        qr = check_quality([_row(Preconditions="The Delivery toggle is set to OFF")])
        assert qr.clean

    def test_does_not_flag_expected_result_for_exemplification(self):
        """Exemplification check only applies to Steps and Preconditions."""
        qr = check_quality(
            [
                _row(
                    Steps="Tap the toggle",
                    Preconditions="User is logged in",
                    **{"Expected Result": "Toggle switches to ON"},
                )
            ]
        )
        assert qr.clean


class TestPreconditionStepOverlap:
    """5C — Steps must not restate Preconditions."""

    def test_flags_overlap(self):
        qr = check_quality(
            [
                _row(
                    Preconditions="The Delivery option is currently toggled off in the settings panel",
                    Steps="Ensure the Delivery option is currently toggled off in the settings panel",
                )
            ]
        )
        assert qr.count == 1
        assert qr.warnings[0].issue == "restates Preconditions"

    def test_no_false_positive_on_short_phrases(self):
        """Short preconditions should not trigger overlap."""
        qr = check_quality(
            [_row(Preconditions="User is logged in", Steps="Open the dashboard")]
        )
        assert qr.clean

    def test_no_false_positive_on_different_text(self):
        qr = check_quality(
            [
                _row(
                    Preconditions="Meet-up is enabled with one location saved",
                    Steps="Tap the Edit button on the location card",
                )
            ]
        )
        assert qr.clean


class TestDuplicateDetection:
    """5D — No two test cases may share the same (Preconditions + Steps)."""

    def test_flags_duplicates(self):
        rows = [
            _row(
                ID="TC-001",
                Preconditions="User is on listing screen",
                Steps="Tap toggle",
            ),
            _row(
                ID="TC-002",
                Preconditions="User is on listing screen",
                Steps="Tap toggle",
            ),
        ]
        qr = check_quality(rows)
        assert qr.count == 1
        assert "duplicate of TC-001" in qr.warnings[0].issue

    def test_no_false_positive_on_different_steps(self):
        rows = [
            _row(
                ID="TC-001",
                Preconditions="User is on listing screen",
                Steps="Tap toggle A",
            ),
            _row(
                ID="TC-002",
                Preconditions="User is on listing screen",
                Steps="Tap toggle B",
            ),
        ]
        qr = check_quality(rows)
        assert qr.clean

    def test_no_false_positive_on_different_preconditions(self):
        rows = [
            _row(ID="TC-001", Preconditions="First-time user", Steps="Tap toggle"),
            _row(ID="TC-002", Preconditions="Returning user", Steps="Tap toggle"),
        ]
        qr = check_quality(rows)
        assert qr.clean

    def test_case_insensitive(self):
        rows = [
            _row(
                ID="TC-001", Preconditions="User is Logged In", Steps="Open Dashboard"
            ),
            _row(
                ID="TC-002", Preconditions="user is logged in", Steps="open dashboard"
            ),
        ]
        qr = check_quality(rows)
        assert qr.count == 1


class TestMultipleWarnings:
    """Multiple issues in a single test case should all be reported."""

    def test_hedging_and_exemplification(self):
        qr = check_quality(
            [
                _row(
                    Steps="Toggle a method (e.g., Delivery)",
                    **{"Expected Result": "The toggle may change"},
                )
            ]
        )
        assert qr.count == 2
        fields = {w.field for w in qr.warnings}
        assert "Steps" in fields
        assert "Expected Result" in fields

    def test_multiple_rows(self):
        rows = [
            _row(
                ID="TC-001",
                Steps="Step A",
                **{"Expected Result": "User should see the page"},
            ),
            _row(
                ID="TC-002",
                Steps="Step B",
                **{"Expected Result": "The button might be hidden"},
            ),
            _row(
                ID="TC-003",
                Steps="Step C",
                **{"Expected Result": "Dashboard is displayed"},
            ),
        ]
        qr = check_quality(rows)
        assert qr.count == 2
        ids = {w.tc_id for w in qr.warnings}
        assert ids == {"TC-001", "TC-002"}


class TestQualityReport:
    """Report helper methods."""

    def test_clean_report(self):
        qr = check_quality([_row()])
        assert qr.clean
        assert qr.count == 0
        assert qr.summary_lines() == []

    def test_summary_lines_format(self):
        qr = check_quality([_row(**{"Expected Result": "User may see an error"})])
        lines = qr.summary_lines()
        assert len(lines) == 1
        assert "TC-001" in lines[0]
        assert "Expected Result" in lines[0]
        assert "may" in lines[0]

    def test_empty_rows(self):
        qr = check_quality([])
        assert qr.clean

    def test_missing_fields(self):
        """Rows with missing fields should not crash."""
        qr = check_quality([{"ID": "TC-001"}])
        assert qr.clean
