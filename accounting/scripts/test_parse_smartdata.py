#!/usr/bin/env python3
"""
Self-tests for parse_smartdata.py.

There is no pytest in this repo, so run this file directly:

    python3 accounting/scripts/test_parse_smartdata.py

Fixtures come from _smartdata_fixtures.py and are entirely synthetic, so no
real financial data or cardholder PII is ever committed.
"""

import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _smartdata_fixtures import build_workbook, pad, txn  # noqa: E402
from parse_smartdata import (  # noqa: E402
    _clean,
    _number,
    find_header_row,
    parse_transactions,
    statement_period,
)


def load(tmpdir, **kwargs):
    path = build_workbook(Path(tmpdir) / "report.xlsx", **kwargs)
    wb = openpyxl.load_workbook(path)
    return path, wb


def test_clean_collapses_newlines_and_blanks():
    assert _clean("\nPosting Date") == "Posting Date"
    assert _clean("Transaction\nDate") == "Transaction Date"
    assert _clean(" ") == ""
    assert _clean(None) == ""


def test_number_strips_padding_and_separators():
    assert _number(pad("31.99")) == Decimal("31.99")
    assert _number("1,234.56") == Decimal("1234.56")
    assert _number(" ") == Decimal("0")


def test_header_row_found_below_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        _, wb = load(tmp)
        assert find_header_row(wb["Detail Report"]) == 14


def test_addendum_rows_are_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        _, wb = load(tmp)
        txns = parse_transactions(wb["Detail Report"])
        # 3 purchases + 2 fee lines; the 2 addendum rows must not appear
        assert len(txns) == 5
        assert all(t["description"] != "Quantity:" for t in txns)


def test_padded_numbers_become_decimals():
    with tempfile.TemporaryDirectory() as tmp:
        _, wb = load(tmp)
        first = parse_transactions(wb["Detail Report"])[0]
        assert first["amount"] == Decimal("25.00")
        assert first["original_currency"] == "USD"
        assert first["country"] == "UNITED STATES"


def test_fee_rows_have_blank_country():
    with tempfile.TemporaryDirectory() as tmp:
        _, wb = load(tmp)
        fees = [t for t in parse_transactions(wb["Detail Report"])
                if t["description"] == "INTERNATIONAL TRANSACTION"]
        assert len(fees) == 2
        assert all(f["country"] == "" for f in fees)


def test_statement_period_read_from_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        _, wb = load(tmp)
        assert statement_period(wb["Detail Report"]) == "01/26/2026 - 02/25/2026"


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
