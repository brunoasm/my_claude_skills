#!/usr/bin/env python3
"""
Flags p-card charges that posted to a SmartData report but are not recorded in
the expenses spreadsheet -- the mirror image of the orphaned-receipt check.

Matching is deliberately conservative. A charge claims a sheet row when the
amounts are equal and the sheet date falls within a few days of the charge's
transaction date (posting lags the transaction, and the sheet records the
purchase date). Where no exact match exists, a second pass looks for a row in
the same window whose vendor words overlap the card descriptor -- that surfaces
a row entered with the wrong amount rather than calling it absent. Fee lines
carry no vendor words of their own, so that pass cannot speak to them and they
go straight to the missing list.

Results are split into explicit buckets so that "not recorded" is never
conflated with "recorded differently":

  missing_from_sheet            posted, not recorded -- the actionable list
  possible_amount_mismatch      recorded, but the amount disagrees
  ambiguous                     several rows could be the same charge
  rows_without_receipt_number   matched, but the row carries no receipt number

Known limits, which belong in any report of these results:

  * A charge not yet processed is a true positive. Early in a statement cycle the
    missing list is expected to be long.
  * Only the cardholder's own charges appear in their report; another
    cardholder's spending is out of scope.
  * Aggregated sheet rows (a month of spending recorded as one total) cannot
    match individual charges and will surface as unmatched.

Usage:
    python3 check_missing_receipts.py REPORT.xlsx --expenses expenses.csv [--json]
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parse_smartdata import FEE_DESCRIPTION, parse_report  # noqa: E402

DEFAULT_WINDOW_DAYS = 5
_SHEET_DATE_FORMATS = ("%d-%b-%Y", "%d-%B-%Y", "%m/%d/%Y", "%Y-%m-%d")

# Words that appear in every fee line and in every fee row, so they identify
# nothing. Every fee charge is described "INTERNATIONAL TRANSACTION" and every
# fee row is named "{vendor} - international transaction fee", so leaving them
# in makes token overlap between any fee and any other fee automatic.
GENERIC_TOKENS = frozenset({"INTERNATIONAL", "TRANSACTION"})


def parse_money(text):
    """Parse a spreadsheet Cost cell into a Decimal, or None if unparseable."""
    cleaned = str(text or "").strip().replace("$", "").replace(",", "")
    if not cleaned:
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return -value if negative else value


def parse_sheet_date(text):
    """Parse a spreadsheet date cell, e.g. "15-Mar-2026"."""
    cleaned = str(text or "").strip()
    for fmt in _SHEET_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def parse_report_date(text):
    """Parse a report date cell, e.g. "03/15/2026"."""
    try:
        return datetime.strptime(str(text).strip(), "%m/%d/%Y").date()
    except ValueError:
        return None


def tokens(name):
    """Discriminating words from a vendor name or card descriptor.

    Words shared by every fee line and every fee row are dropped: they would
    make any fee overlap any other fee, which is no evidence at all.
    """
    words = re.split(r"[^A-Za-z0-9]+", str(name or "").upper())
    return {w for w in words
            if len(w) >= 4 and not w.isdigit() and w not in GENERIC_TOKENS}


def load_expenses(path):
    """Read the expenses CSV export into comparable rows."""
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for raw in csv.DictReader(handle):
            cost = parse_money(raw.get("Cost"))
            when = parse_sheet_date(raw.get("date"))
            if cost is None and when is None:
                continue
            rows.append({
                "expense": (raw.get("Expense") or "").strip(),
                "vendor": (raw.get("Vendor") or "").strip(),
                "cost": cost,
                "date": when,
                "method": (raw.get("method") or "").strip(),
                "receipt_number": (raw.get("receipt_number") or "").strip(),
            })
    return rows


def _within(left, right, days):
    return left is not None and right is not None and abs((left - right).days) <= days


def check(report, expenses, window_days=DEFAULT_WINDOW_DAYS):
    """Compare posted charges against recorded rows.

    Two-phase matching:
    - Phase 1: Exact matches only. A row is claimed (removed from unclaimed) only
      when exactly one row matches both amount and date. Multiple exact matches
      go to ambiguous bucket; no exact matches proceed to phase 2.
    - Phase 2: Vendor-overlap matching for charges with no exact match. Rows
      already claimed in phase 1 are unavailable, preventing a row from being
      reported as a mismatch candidate for one charge and then claimed as the
      exact match for another.
    """
    charges = [{
        "description": txn["description"],
        "transaction_date": txn["transaction_date"],
        "posting_date": txn["posting_date"],
        "amount": txn["amount"],
        "country": txn["country"],
        "is_fee": txn["description"] == FEE_DESCRIPTION,
    } for txn in report["purchases"] + report["fees"]]

    unclaimed = list(expenses)
    matched, mismatches, ambiguous, no_receipt = [], [], [], []
    unmatched_exact = []  # charges with no exact match, for phase 2

    # Phase 1: Exact matching
    for charge in charges:
        when = parse_report_date(charge["transaction_date"])

        exact = [r for r in unclaimed
                 if r["cost"] == charge["amount"] and _within(r["date"], when, window_days)]
        if len(exact) == 1:
            row = exact[0]
            unclaimed.remove(row)
            matched.append({"charge": charge, "row": row})
            if not row["receipt_number"]:
                no_receipt.append({"charge": charge, "row": row})
        elif len(exact) > 1:
            ambiguous.append({"charge": charge, "candidates": exact})
        else:
            # No exact match; defer to phase 2 for vendor-overlap matching
            unmatched_exact.append(charge)

    # Phase 2: Vendor-overlap matching for charges with no exact match
    missing = []
    for charge in unmatched_exact:
        descriptor = tokens(charge["description"])
        if not descriptor:
            # Nothing discriminating survives -- a fee line's whole descriptor is
            # generic. Overlap would match it against any fee row in the window,
            # including one that correctly records a different charge (a fee from
            # the previous statement, say). Report it as unrecorded, which is the
            # honest answer, rather than pointing the user at a correct row.
            missing.append(charge)
            continue
        when = parse_report_date(charge["transaction_date"])
        near = [r for r in unclaimed
                if _within(r["date"], when, window_days)
                and (tokens(r["vendor"]) & descriptor or tokens(r["expense"]) & descriptor)]
        if near:
            mismatches.append({"charge": charge, "candidates": near})
        else:
            missing.append(charge)

    return {
        "period": report["period"],
        "charges_checked": len(charges),
        "matched": len(matched),
        "missing_from_sheet": missing,
        "possible_amount_mismatch": mismatches,
        "ambiguous": ambiguous,
        "rows_without_receipt_number": no_receipt,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Flag posted p-card charges missing from the expenses sheet.")
    parser.add_argument("report", type=Path, help="path to a YYYY_MM.xlsx report")
    parser.add_argument("--expenses", type=Path, required=True,
                        help="expenses tab exported as CSV")
    parser.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS,
                        help=f"date tolerance when matching (default {DEFAULT_WINDOW_DAYS})")
    parser.add_argument("--json", action="store_true",
                        help="emit JSON instead of a human-readable summary")
    args = parser.parse_args()

    result = check(parse_report(args.report), load_expenses(args.expenses),
                   window_days=args.window_days)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0

    print(f"statement period: {result['period'] or 'unknown'}")
    print(f"charges checked: {result['charges_checked']}   matched: {result['matched']}")
    for charge in result["missing_from_sheet"]:
        label = "fee" if charge["is_fee"] else charge["country"] or "US"
        print(f"  MISSING  {charge['transaction_date']}  ${charge['amount']}  "
              f"{charge['description']} [{label}]")
    for item in result["possible_amount_mismatch"]:
        charge = item["charge"]
        costs = ", ".join("unparseable" if c["cost"] is None else f"${c['cost']}"
                          for c in item["candidates"])
        print(f"  AMOUNT?  {charge['transaction_date']}  posted ${charge['amount']}  "
              f"{charge['description']}  sheet has {costs}")
    for item in result["ambiguous"]:
        charge = item["charge"]
        print(f"  AMBIGUOUS {charge['transaction_date']}  ${charge['amount']}  "
              f"{charge['description']}  {len(item['candidates'])} candidate rows")
    for item in result["rows_without_receipt_number"]:
        print(f"  NO RECEIPT NUMBER  ${item['row']['cost']}  {item['row']['expense']}")
    if not any((result["missing_from_sheet"], result["possible_amount_mismatch"],
                result["ambiguous"], result["rows_without_receipt_number"])):
        print("  every posted charge is recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
