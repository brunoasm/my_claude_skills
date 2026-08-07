#!/usr/bin/env python3
"""
Self-tests for check_missing_receipts.py. Run directly:

    python3 accounting/scripts/test_check_missing_receipts.py

Fixtures are synthetic: a report built by the parser's own test helpers and a
CSV written inline. No real financial data or cardholder PII.
"""

import sys
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _smartdata_fixtures import build_workbook, txn  # noqa: E402
from check_missing_receipts import (  # noqa: E402
    check,
    load_expenses,
    parse_money,
    parse_report_date,
    parse_sheet_date,
    tokens,
)
from parse_smartdata import parse_report  # noqa: E402

CSV_HEADER = ('"Expense","Vendor","Cost","date","method","Fund","GL code",'
              '"receipt_number","notes","request reimbursement"')

REPORT_ROWS = [
    txn("02/03/2026", "02/02/2026", "EXAMPLE CA VENDOR", "TORONTO, ON",
        "CANADA", "17.50", "CAD", "1.4000", "12.50"),
    txn("02/03/2026", "02/02/2026", "INTERNATIONAL TRANSACTION", " ", " ",
        "0.13", "USD", "1.0000", "0.13"),
]
REPORT_SUMMARY = [1, "12.50", 1, "0.13", 2, "12.63"]


def write_csv(path, rows):
    path.write_text("\n".join([CSV_HEADER] + list(rows)) + "\n", encoding="utf-8")
    return path


def row(expense, vendor, cost, when, receipt="26001"):
    return (f'"{expense}","{vendor}","{cost}","{when}","p-card","startup",'
            f'"6405","{receipt}","",""')


def run(tmp, csv_rows, window_days=5):
    report_path = build_workbook(Path(tmp) / "report.xlsx",
                                 txn_rows=REPORT_ROWS, summary_row=REPORT_SUMMARY)
    csv_path = write_csv(Path(tmp) / "expenses.csv", csv_rows)
    return check(parse_report(report_path), load_expenses(csv_path),
                 window_days=window_days)


def test_parse_money_handles_sheet_formats():
    assert parse_money("$1,234.56") == Decimal("1234.56")
    assert parse_money("$4.12") == Decimal("4.12")
    assert parse_money("-$4.12") == Decimal("-4.12")
    assert parse_money("($4.12)") == Decimal("-4.12")
    assert parse_money("") is None
    assert parse_money("n/a") is None


def test_parse_sheet_date_handles_sheet_format():
    assert parse_sheet_date("15-Mar-2026") == date(2026, 3, 15)
    assert parse_sheet_date("2-Feb-2026") == date(2026, 2, 2)
    assert parse_sheet_date("") is None


def test_tokens_drops_short_and_numeric_words():
    assert "VENDOR" in tokens("EXAMPLE CA VENDOR")
    assert "CA" not in tokens("EXAMPLE CA VENDOR")
    assert tokens("AMAZON MKTPL*UB37Z09Y3") >= {"AMAZON", "MKTPL"}


def test_recorded_charge_is_matched_not_missing():
    with tempfile.TemporaryDirectory() as tmp:
        result = run(tmp, [
            row("Example purchase", "Example CA Vendor", "$12.50", "2-Feb-2026"),
            row("Example CA Vendor — international transaction fee",
                "Example CA Vendor", "$0.13", "2-Feb-2026"),
        ])
        assert result["charges_checked"] == 2
        assert result["matched"] == 2
        assert result["missing_from_sheet"] == []
        assert result["possible_amount_mismatch"] == []
        assert result["ambiguous"] == []


def test_unrecorded_charge_is_reported_missing():
    with tempfile.TemporaryDirectory() as tmp:
        result = run(tmp, [
            row("Example purchase", "Example CA Vendor", "$12.50", "2-Feb-2026"),
        ])
        missing = result["missing_from_sheet"]
        assert [m["amount"] for m in missing] == [Decimal("0.13")]
        assert missing[0]["is_fee"] is True


def test_wrong_amount_becomes_mismatch_not_missing():
    with tempfile.TemporaryDirectory() as tmp:
        result = run(tmp, [
            # recorded at the receipt's foreign total instead of the posted USD
            row("Example purchase", "Example CA Vendor", "$17.50", "2-Feb-2026"),
            row("Example CA Vendor — international transaction fee",
                "Example CA Vendor", "$0.13", "2-Feb-2026"),
        ])
        assert result["missing_from_sheet"] == []
        assert len(result["possible_amount_mismatch"]) == 1
        flagged = result["possible_amount_mismatch"][0]
        assert flagged["charge"]["amount"] == Decimal("12.50")
        assert flagged["candidates"][0]["cost"] == Decimal("17.50")


def test_date_outside_window_is_missing():
    with tempfile.TemporaryDirectory() as tmp:
        result = run(tmp, [
            row("Example purchase", "Unrelated Name", "$12.50", "1-Jan-2026"),
            row("Unrelated fee", "Unrelated Name", "$0.13", "1-Jan-2026"),
        ])
        assert len(result["missing_from_sheet"]) == 2


def test_blank_receipt_number_is_flagged():
    with tempfile.TemporaryDirectory() as tmp:
        result = run(tmp, [
            row("Example purchase", "Example CA Vendor", "$12.50", "2-Feb-2026",
                receipt=""),
            row("Example CA Vendor — international transaction fee",
                "Example CA Vendor", "$0.13", "2-Feb-2026", receipt=""),
        ])
        assert result["matched"] == 2
        assert len(result["rows_without_receipt_number"]) == 2


def test_duplicate_sheet_rows_are_ambiguous():
    with tempfile.TemporaryDirectory() as tmp:
        result = run(tmp, [
            row("Example purchase", "Example CA Vendor", "$12.50", "2-Feb-2026"),
            row("Example purchase again", "Example CA Vendor", "$12.50",
                "2-Feb-2026", receipt="26002"),
            row("Example CA Vendor — international transaction fee",
                "Example CA Vendor", "$0.13", "2-Feb-2026"),
        ])
        assert len(result["ambiguous"]) == 1
        assert len(result["ambiguous"][0]["candidates"]) == 2


def test_parse_report_date_handles_report_format():
    assert parse_report_date("02/02/2026") == date(2026, 2, 2)
    assert parse_report_date("invalid") is None


def test_row_cannot_be_claimed_by_multiple_charges():
    """A sheet row exactly matching one charge cannot be a mismatch candidate for another."""
    with tempfile.TemporaryDirectory() as tmp:
        # Report with two charges from same vendor:
        # First: 12.00 (no exact match exists)
        # Second: 12.50 (exact match exists in sheet)
        # The sheet row should match the second charge, not be offered as candidate for first
        report_rows = [
            txn("02/03/2026", "02/02/2026", "EXAMPLE CA VENDOR", "TORONTO, ON",
                "CANADA", "16.67", "CAD", "1.4000", "12.00"),
            txn("02/03/2026", "02/02/2026", "EXAMPLE CA VENDOR", "TORONTO, ON",
                "CANADA", "17.50", "CAD", "1.4000", "12.50"),
        ]
        report_summary = [2, "24.50", 0, "0.00", 2, "24.50"]

        report_path = build_workbook(Path(tmp) / "report.xlsx",
                                     txn_rows=report_rows, summary_row=report_summary)
        csv_path = write_csv(Path(tmp) / "expenses.csv", [
            row("Example purchase", "Example CA Vendor", "$12.50", "2-Feb-2026"),
        ])

        result = check(parse_report(report_path), load_expenses(csv_path))

        # The 12.50 charge should get an exact match
        assert result["matched"] == 1, f"Expected 1 matched, got {result['matched']}"
        # The 12.00 charge should be missing, not offered as a mismatch candidate
        assert len(result["missing_from_sheet"]) == 1, \
            f"Expected 1 missing, got {len(result['missing_from_sheet'])}"
        assert result["missing_from_sheet"][0]["amount"] == Decimal("12.00")
        assert len(result["possible_amount_mismatch"]) == 0, \
            f"Expected 0 mismatches, got {len(result['possible_amount_mismatch'])}"


def test_generic_fee_words_are_not_tokens():
    """"INTERNATIONAL" and "TRANSACTION" identify nothing -- every fee has them."""
    assert tokens("INTERNATIONAL TRANSACTION") == set()
    assert tokens("Example CA Vendor — international transaction fee") \
        == {"EXAMPLE", "VENDOR"}


def test_unrecorded_fee_is_missing_not_matched_to_an_unrelated_fee_row():
    """An unrecorded fee must not be absorbed by another charge's fee row.

    Every fee line reads "INTERNATIONAL TRANSACTION" and every fee row is named
    "{vendor} — international transaction fee", so word overlap between any fee
    and any fee row is automatic. A statement boundary routinely leaves a
    correctly recorded fee from the previous cycle inside the date window; the
    unrecorded fee must still be reported as missing, not offered as an amount
    mismatch against that correct row.
    """
    report_rows = [
        txn("02/10/2026", "02/09/2026", "EXAMPLE PH VENDOR", "MANILA, --",
            "PHILIPPINES", "1800.00", "PHP", "60.0200", "29.99"),
        txn("02/10/2026", "02/09/2026", "INTERNATIONAL TRANSACTION", " ", " ",
            "0.30", "USD", "1.0000", "0.30"),
    ]
    report_summary = [1, "29.99", 1, "0.30", 2, "30.29"]
    with tempfile.TemporaryDirectory() as tmp:
        report_path = build_workbook(Path(tmp) / "report.xlsx",
                                     txn_rows=report_rows,
                                     summary_row=report_summary)
        csv_path = write_csv(Path(tmp) / "expenses.csv", [
            # the purchase is recorded correctly
            row("Example purchase", "Example PH Vendor", "$29.99", "9-Feb-2026"),
            # an unrelated fee, correctly recorded, from the previous statement
            row("Example CA Vendor — international transaction fee",
                "Example CA Vendor", "$0.13", "7-Feb-2026", receipt="26000"),
        ])
        result = check(parse_report(report_path), load_expenses(csv_path))

        assert [m["amount"] for m in result["missing_from_sheet"]] \
            == [Decimal("0.30")]
        assert result["missing_from_sheet"][0]["is_fee"] is True
        assert result["possible_amount_mismatch"] == []


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


def main():
    failures = []
    for test in TESTS:
        try:
            test()
            print(f"  ok    {test.__name__}")
        except AssertionError as exc:
            failures.append(test.__name__)
            print(f"  FAIL  {test.__name__}: {exc or 'assertion failed'}")
        except Exception as exc:  # noqa: BLE001
            failures.append(test.__name__)
            print(f"  ERROR {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(TESTS) - len(failures)}/{len(TESTS)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
