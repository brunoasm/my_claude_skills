# International Transaction Fees Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the `accounting` skill to record the posted USD amount as an international charge's cost and to add a separate 1% cross-border fee row, driven from a SmartData XLSX report rather than from the user's recall.

**Architecture:** A parser script turns a J.P. Morgan SmartData "Account Statement (Version 2)" XLSX into normalized transactions, pairs each `INTERNATIONAL TRANSACTION` fee line with the purchase that incurred it, and cross-checks its own parse against the statement's summary totals. A second script reuses that parser to compare posted charges against the expenses sheet and flag ones that were never recorded. The skill's prose (`SKILL.md`) calls the parser during session start, consults its output while processing each receipt, and runs the missing-charge check during reconciliation. A reference file carries the format details so `SKILL.md` stays readable.

**Tech Stack:** Python 3 (`python3` resolves to the user's miniforge install), `openpyxl` 3.1.5 (already installed), `decimal` from the standard library. No pytest in this repo — tests are plain scripts run with `python3`.

## Global Constraints

- **No real financial data or PII in this repo.** Reports carry the cardholder's name, tax id, card number, street address, and balances. Tests must build synthetic fixtures; never commit a real report or copy values out of one.
- **Fee rate is exactly 1%** of the posted USD amount, **rounded half-up to the cent**. Use `Decimal` with `ROUND_HALF_UP`; float arithmetic does not reliably reproduce the observed cents.
- **A row is a transaction if and only if its first cell matches `^\d{2}/\d{2}/\d{4}$`.** Everything else is Level-3 addendum detail belonging to the transaction above it.
- **Never hard-code the header row number.** Find it by testing for a first cell that cleans to `Posting Date`.
- **Numeric cells are whitespace-padded strings**; summary figures also carry thousands separators.
- Match the repo's script house style: `#!/usr/bin/env python3`, a module docstring documenting the format and its traps, `argparse` CLI.
- Scripts live at `accounting/scripts/`, following `Emu_bulk_upload_FMNH/scripts/` and `document_ocr/scripts/`.
- **No absolute personal paths in the repo.** Verification commands use `$REPO` (this checkout) and `$WORKING_FOLDER` (the accounts and receipts folder); set them in your shell before running. The accounting skill itself runs *from* the working folder and stores its location nowhere.

---

### Task 1: Report parser core

**Files:**
- Create: `accounting/scripts/_smartdata_fixtures.py`
- Create: `accounting/scripts/parse_smartdata.py`
- Test: `accounting/scripts/test_parse_smartdata.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces, from `parse_smartdata.py`: `_clean(value) -> str`, `_number(value) -> Decimal`, `find_header_row(ws, first_header="Posting Date") -> int`, `parse_transactions(ws) -> list[dict]`, `statement_period(ws) -> str`, and module constants `FEE_DESCRIPTION`, `FEE_RATE`, `DATE_RE`, `DETAIL_SHEET`, `SUMMARY_SHEET`. Each transaction dict has keys `posting_date`, `transaction_date`, `description`, `location`, `country` (all `str`) and `original_amount`, `conversion_rate`, `amount` (all `Decimal`), plus `original_currency` (`str`).
- Produces, from `_smartdata_fixtures.py`: `pad(value) -> str`, `txn(posting, tdate, desc, loc, country, orig, cur, rate, usd) -> list`, `build_workbook(path, txn_rows=None, summary_row=None) -> Path`, and constants `DETAIL_HEADER`, `METADATA`, `ADDENDUM_ROWS`, `DEFAULT_TXNS`, `DEFAULT_SUMMARY`. Task 5's tests import these too — they live in their own module so that no test file imports another test file.

- [ ] **Step 1: Create the shared fixture builders**

Create `accounting/scripts/_smartdata_fixtures.py`:

```python
#!/usr/bin/env python3
"""
Synthetic SmartData report builders, shared by the scripts' self-tests.

These mirror the real export's structure -- metadata rows, a newline-laden
header, Level-3 addendum rows, whitespace-padded numbers -- so that tests never
need a real statement. Every value here is invented; no real financial data or
cardholder PII belongs in this repo.

This lives in its own module rather than in a test file so that no test file
has to import another test file.
"""

import openpyxl

DETAIL_HEADER = [
    "\nPosting Date", "Transaction\nDate", "\nDescription", "\nLocation",
    "\nCountry", "Original\nAmount", "Original\nCurrency Code",
    "Conversion\nRate", "\nAmount",
]

# Deliberately fake stand-ins for the cardholder block the real export carries.
METADATA = [
    " ", "Account Statement (Version 2) ", "Run Date: 03/05/2026",
    "Report Id: sd11080", "Posting Date: 01/26/2026 - 02/25/2026",
    " ", " ", " ", "TEST CARDHOLDER, TAX EX X0000-0000", "XX -00000000",
    "1 EXAMPLE ST", "EXAMPLE, IL 000000000 USA", None,
]


def pad(value):
    """Mimic the export's whitespace-padded numeric cells."""
    return f"          {value}"


def txn(posting, tdate, desc, loc, country, orig, cur, rate, usd):
    """Build one transaction row in the export's column order."""
    return [posting, tdate, desc, loc, country, pad(orig), cur, pad(rate), pad(usd)]


ADDENDUM_ROWS = [
    ["Description:", " ", "Example item", "Product Code:", " ", "X1"],
    ["Quantity:", " ", pad("1.00"), "Unit:", " ", "PCE", "Amount:", " ", pad("25.00")],
]

DEFAULT_TXNS = [
    txn("01/27/2026", "01/26/2026", "EXAMPLE US VENDOR", "CHICAGO, IL",
        "UNITED STATES", "25.00", "USD", "1.0000", "25.00"),
    *ADDENDUM_ROWS,
    txn("02/03/2026", "02/02/2026", "EXAMPLE CA VENDOR", "TORONTO, ON",
        "CANADA", "17.50", "CAD", "1.4000", "12.50"),
    txn("02/03/2026", "02/02/2026", "INTERNATIONAL TRANSACTION", " ", " ",
        "0.13", "USD", "1.0000", "0.13"),
    txn("02/10/2026", "02/09/2026", "EXAMPLE PH VENDOR", "MANILA, --",
        "PHILIPPINES", "1800.00", "PHP", "60.0200", "29.99"),
    txn("02/10/2026", "02/09/2026", "INTERNATIONAL TRANSACTION", " ", " ",
        "0.30", "USD", "1.0000", "0.30"),
]

# transaction_count, transaction_amount, payment_count, payment_amount,
# total_count, total_amount
DEFAULT_SUMMARY = [3, "67.49", 2, "0.43", 5, "67.92"]


def build_workbook(path, txn_rows=None, summary_row=None):
    """Write a synthetic report whose shape matches the real SmartData export."""
    txn_rows = DEFAULT_TXNS if txn_rows is None else txn_rows
    summary_row = DEFAULT_SUMMARY if summary_row is None else summary_row

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Detail Report"
    for text in METADATA:
        ws.append([text])
    ws.append(DETAIL_HEADER)
    for row in txn_rows:
        ws.append(row)

    s = wb.create_sheet("Summary Report")
    for text in METADATA:
        s.append([text])
    s.append(["Account Name", "Transaction\nCount", "Transaction\nAmount",
              "Payment\nCount", "Payment\nAmount", "Total\nCount", "Total\nAmount"])
    s.append(["TEST CARDHOLDER"] + list(summary_row))
    s.append(["Report Totals"] + list(summary_row))

    wb.save(path)
    return path
```

- [ ] **Step 2: Write the failing test**

Create `accounting/scripts/test_parse_smartdata.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 accounting/scripts/test_parse_smartdata.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'parse_smartdata'`

- [ ] **Step 4: Write minimal implementation**

Create `accounting/scripts/parse_smartdata.py`:

```python
#!/usr/bin/env python3
"""
Parses a J.P. Morgan SmartData "Account Statement (Version 2)" XLSX export.

Layout, verified against a real statement:

  Sheet "Detail Report"
    rows 1-12   report metadata, then the cardholder's name, tax id, card
                number and street address. This parser never emits those.
    row ~13     blank
    row ~14     table header. Cells contain embedded newlines, e.g.
                "Transaction\\nDate". Found by locating the row whose first
                cell cleans to "Posting Date" -- never hard-code the number.
    rows ~15+   Posting Date | Transaction Date | Description | Location |
                Country | Original Amount | Original Currency Code |
                Conversion Rate | Amount

Traps this module exists to absorb:

  * A row is a transaction only if its first cell looks like MM/DD/YYYY. Every
    other row is Level-3 addendum detail belonging to the transaction above it
    ("Description:", "Quantity:", "Guest Name:", "Total Room Nights:").
  * Numeric cells are whitespace-padded strings; summary figures also carry
    thousands separators.
  * Fee rows have Description == "INTERNATIONAL TRANSACTION" with blank
    Location and Country.
"""

import re
import warnings
from decimal import Decimal

import openpyxl

FEE_DESCRIPTION = "INTERNATIONAL TRANSACTION"
FEE_RATE = Decimal("0.01")
DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
DETAIL_SHEET = "Detail Report"
SUMMARY_SHEET = "Summary Report"

_COLUMN_COUNT = 9


def _clean(value):
    """Reduce a cell to comparable text: no newlines, collapsed whitespace."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def _number(value):
    """Parse a whitespace-padded, comma-separated numeric cell."""
    text = _clean(value).replace(",", "")
    if not text:
        return Decimal("0")
    return Decimal(text)


def find_header_row(ws, first_header="Posting Date"):
    """Return the 1-based row index of the table header."""
    for row in ws.iter_rows(min_row=1, max_row=40):
        if row and _clean(row[0].value) == first_header:
            return row[0].row
    raise ValueError(
        f'header row starting with "{first_header}" not found in sheet "{ws.title}"'
    )


def statement_period(ws):
    """Return the posting-date window from the metadata block, e.g. "A - B"."""
    for row in ws.iter_rows(min_row=1, max_row=13, values_only=True):
        text = _clean(row[0]) if row else ""
        if text.startswith("Posting Date:"):
            return text.split(":", 1)[1].strip()
    return ""


def parse_transactions(ws):
    """Return the transaction rows, skipping Level-3 addendum detail."""
    header_row = find_header_row(ws)
    transactions = []
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        if not row:
            continue
        cells = list(row) + [None] * (_COLUMN_COUNT - len(row))
        if not DATE_RE.match(_clean(cells[0])):
            continue
        transactions.append({
            "posting_date": _clean(cells[0]),
            "transaction_date": _clean(cells[1]),
            "description": _clean(cells[2]),
            "location": _clean(cells[3]),
            "country": _clean(cells[4]),
            "original_amount": _number(cells[5]),
            "original_currency": _clean(cells[6]),
            "conversion_rate": _number(cells[7]),
            "amount": _number(cells[8]),
        })
    return transactions


def load_workbook(path):
    """Open a report, silencing openpyxl's missing-default-style warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return openpyxl.load_workbook(path, data_only=True)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 accounting/scripts/test_parse_smartdata.py`
Expected: PASS — `7/7 passed`

- [ ] **Step 6: Commit**

```bash
git add accounting/scripts/_smartdata_fixtures.py accounting/scripts/parse_smartdata.py accounting/scripts/test_parse_smartdata.py
git commit -m "feat(accounting): parse SmartData statement XLSX detail rows"
```

---

### Task 2: Fee pairing, validation, and CLI

**Files:**
- Modify: `accounting/scripts/parse_smartdata.py`
- Modify: `accounting/scripts/test_parse_smartdata.py`

**Interfaces:**
- Consumes: from Task 1 — `_clean`, `_number`, `find_header_row`, `parse_transactions`, `statement_period`, `load_workbook`, `FEE_DESCRIPTION`, `FEE_RATE`, `DETAIL_SHEET`, `SUMMARY_SHEET`
- Produces: `fee_of(amount: Decimal) -> Decimal`, `is_international(txn: dict) -> bool`, `parse_summary(ws) -> dict | None`, `pair_fees(purchases, fees) -> tuple[list, list, list]`, `validate(purchases, fees, summary) -> dict`, `parse_report(path) -> dict`, `main() -> int`. `parse_report` returns keys `period`, `purchases`, `fees`, `pairs`, `problems`, `international_without_fee`, `validation`. Each entry of `pairs` is `{"fee": dict, "purchase": dict}`; each entry of `problems` is `{"fee": dict, "reason": "ambiguous" | "no_match", "candidates": list, "equivalent": bool}`. `validation` is `{"ok": bool, "checks": [{"name", "expected", "actual", "ok", "note"}]}`.

- [ ] **Step 1: Write the failing test**

Append to `accounting/scripts/test_parse_smartdata.py`, immediately **above** the `TESTS = [...]` line:

```python
def test_fee_of_rounds_half_up():
    # 12.50 * 1% == 0.125 exactly -- half-up gives 0.13, bankers' rounding 0.12
    assert fee_of(Decimal("12.50")) == Decimal("0.13")
    assert fee_of(Decimal("29.99")) == Decimal("0.30")
    assert fee_of(Decimal("3.00")) == Decimal("0.03")


def test_is_international_uses_country():
    assert is_international({"country": "CANADA"}) is True
    assert is_international({"country": "KOREA, REPUBLIC OF"}) is True
    assert is_international({"country": "UNITED STATES"}) is False
    assert is_international({"country": ""}) is False


def test_pairs_each_fee_with_its_purchase():
    with tempfile.TemporaryDirectory() as tmp:
        path, _ = load(tmp)
        result = parse_report(path)
        assert len(result["purchases"]) == 3
        assert len(result["fees"]) == 2
        assert len(result["pairs"]) == 2
        assert result["problems"] == []
        assert result["international_without_fee"] == []
        paired = {p["purchase"]["description"]: p["fee"]["amount"] for p in result["pairs"]}
        assert paired["EXAMPLE CA VENDOR"] == Decimal("0.13")
        assert paired["EXAMPLE PH VENDOR"] == Decimal("0.30")


def test_validation_passes_against_summary():
    with tempfile.TemporaryDirectory() as tmp:
        path, _ = load(tmp)
        validation = parse_report(path)["validation"]
        assert validation["ok"] is True
        assert all(c["ok"] for c in validation["checks"])


def test_validation_flags_summary_mismatch():
    with tempfile.TemporaryDirectory() as tmp:
        path = build_workbook(Path(tmp) / "report.xlsx",
                              summary_row=[99, "1.00", 99, "1.00", 198, "2.00"])
        validation = parse_report(path)["validation"]
        assert validation["ok"] is False
        failed = {c["name"] for c in validation["checks"] if not c["ok"]}
        assert failed == {"purchase_count", "purchase_total", "fee_count", "fee_total"}


def test_ambiguous_pairing_is_reported_not_guessed():
    rows = [
        txn("02/03/2026", "02/02/2026", "EXAMPLE CA VENDOR A", "TORONTO, ON",
            "CANADA", "17.50", "CAD", "1.4000", "12.50"),
        txn("02/03/2026", "02/02/2026", "EXAMPLE CA VENDOR B", "TORONTO, ON",
            "CANADA", "17.50", "CAD", "1.4000", "12.50"),
        txn("02/03/2026", "02/02/2026", "INTERNATIONAL TRANSACTION", " ", " ",
            "0.13", "USD", "1.0000", "0.13"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = build_workbook(Path(tmp) / "report.xlsx", txn_rows=rows,
                              summary_row=[2, "25.00", 1, "0.13", 3, "25.13"])
        result = parse_report(path)
        assert result["pairs"] == []
        assert len(result["problems"]) == 1
        problem = result["problems"][0]
        assert problem["reason"] == "ambiguous"
        assert len(problem["candidates"]) == 2
        # both candidates cost the same, so either assignment gives the same numbers
        assert problem["equivalent"] is True


def test_fee_with_no_candidate_is_reported():
    rows = [
        txn("02/03/2026", "02/02/2026", "EXAMPLE US VENDOR", "CHICAGO, IL",
            "UNITED STATES", "25.00", "USD", "1.0000", "25.00"),
        txn("02/03/2026", "02/02/2026", "INTERNATIONAL TRANSACTION", " ", " ",
            "0.99", "USD", "1.0000", "0.99"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = build_workbook(Path(tmp) / "report.xlsx", txn_rows=rows,
                              summary_row=[1, "25.00", 1, "0.99", 2, "25.99"])
        result = parse_report(path)
        assert [p["reason"] for p in result["problems"]] == ["no_match"]
        assert result["problems"][0]["candidates"] == []


def test_international_purchase_without_fee_is_reported():
    rows = [
        txn("02/03/2026", "02/02/2026", "EXAMPLE CA VENDOR", "TORONTO, ON",
            "CANADA", "17.50", "CAD", "1.4000", "12.50"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = build_workbook(Path(tmp) / "report.xlsx", txn_rows=rows,
                              summary_row=[1, "12.50", 0, "0.00", 1, "12.50"])
        result = parse_report(path)
        assert [p["description"] for p in result["international_without_fee"]] \
            == ["EXAMPLE CA VENDOR"]


def test_output_carries_no_cardholder_pii():
    import json
    with tempfile.TemporaryDirectory() as tmp:
        path, _ = load(tmp)
        dumped = json.dumps(parse_report(path), default=str)
        for secret in ("XX -00000000", "TAX EX", "EXAMPLE ST", "TEST CARDHOLDER"):
            assert secret not in dumped
```

Also extend the import block at the top of the file to:

```python
from parse_smartdata import (  # noqa: E402
    _clean,
    _number,
    fee_of,
    find_header_row,
    is_international,
    parse_report,
    parse_transactions,
    statement_period,
)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 accounting/scripts/test_parse_smartdata.py`
Expected: FAIL — `ImportError: cannot import name 'fee_of' from 'parse_smartdata'`

- [ ] **Step 3: Write minimal implementation**

Append to `accounting/scripts/parse_smartdata.py`:

```python
def fee_of(amount):
    """The international transaction fee on a posted USD amount: 1%, half-up."""
    return (amount * FEE_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def is_international(txn):
    """True when the report says the charge was processed outside the US.

    Fee rows carry a blank Country, so they are not themselves international
    purchases.
    """
    return txn["country"] not in ("", "UNITED STATES")


def parse_summary(ws):
    """Return the "Report Totals" figures, or None when absent."""
    header_row = find_header_row(ws, "Account Name")
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        if not row:
            continue
        if _clean(row[0]) == "Report Totals":
            cells = list(row) + [None] * (7 - len(row))
            return {
                "transaction_count": int(_number(cells[1])),
                "transaction_amount": _number(cells[2]),
                "payment_count": int(_number(cells[3])),
                "payment_amount": _number(cells[4]),
                "total_count": int(_number(cells[5])),
                "total_amount": _number(cells[6]),
            }
    return None


def pair_fees(purchases, fees):
    """Attribute each fee line to the purchase that incurred it.

    Fee rows carry no merchant name, so a fee pairs with a purchase when their
    transaction dates match, the purchase is international, and 1% of the
    purchase's USD amount equals the fee. Anything other than exactly one
    candidate is returned as a problem for a human to resolve -- never guessed.
    """
    unpaired = list(purchases)
    pairs, problems = [], []
    for fee in fees:
        candidates = [
            p for p in unpaired
            if p["transaction_date"] == fee["transaction_date"]
            and is_international(p)
            and fee_of(p["amount"]) == fee["amount"]
        ]
        if len(candidates) == 1:
            unpaired.remove(candidates[0])
            pairs.append({"fee": fee, "purchase": candidates[0]})
        else:
            problems.append({
                "fee": fee,
                "reason": "ambiguous" if candidates else "no_match",
                "candidates": candidates,
                "equivalent": bool(candidates)
                and len({c["amount"] for c in candidates}) == 1,
            })
    return pairs, problems, unpaired


def validate(purchases, fees, summary):
    """Cross-check the parse against the statement's own summary totals."""
    if summary is None:
        return {"ok": False, "checks": [{
            "name": "summary_present", "expected": "Report Totals row",
            "actual": "not found", "ok": False,
            "note": "counts and totals could not be cross-checked",
        }]}

    purchase_total = sum((p["amount"] for p in purchases), Decimal("0"))
    fee_total = sum((f["amount"] for f in fees), Decimal("0"))
    payment_note = (
        "real payments and refunds also land in the statement's Payment bucket, "
        "so a mismatch here means review, not a broken parse"
    )
    checks = [
        {"name": "purchase_count", "expected": summary["transaction_count"],
         "actual": len(purchases),
         "ok": len(purchases) == summary["transaction_count"],
         "note": "purchases parsed vs statement Transaction Count"},
        {"name": "purchase_total", "expected": str(summary["transaction_amount"]),
         "actual": str(purchase_total),
         "ok": purchase_total == summary["transaction_amount"],
         "note": "purchase sum vs statement Transaction Amount"},
        {"name": "fee_count", "expected": summary["payment_count"],
         "actual": len(fees), "ok": len(fees) == summary["payment_count"],
         "note": payment_note},
        {"name": "fee_total", "expected": str(summary["payment_amount"]),
         "actual": str(fee_total), "ok": fee_total == summary["payment_amount"],
         "note": payment_note},
    ]
    return {"ok": all(c["ok"] for c in checks), "checks": checks}


def parse_report(path):
    """Parse a report and pair its fees. Never returns cardholder PII."""
    wb = load_workbook(path)
    detail = wb[DETAIL_SHEET]
    transactions = parse_transactions(detail)
    summary = parse_summary(wb[SUMMARY_SHEET]) if SUMMARY_SHEET in wb.sheetnames else None

    fees = [t for t in transactions if t["description"] == FEE_DESCRIPTION]
    purchases = [t for t in transactions if t["description"] != FEE_DESCRIPTION]
    pairs, problems, unpaired = pair_fees(purchases, fees)

    # A purchase that is a candidate for an ambiguous fee is not "without a fee" --
    # reporting it in both buckets tells the reader a charge has no fee while
    # showing them its candidate fee.
    candidates = {id(c) for problem in problems for c in problem["candidates"]}

    return {
        "period": statement_period(detail),
        "purchases": purchases,
        "fees": fees,
        "pairs": pairs,
        "problems": problems,
        "international_without_fee": [
            p for p in unpaired if is_international(p) and id(p) not in candidates
        ],
        "validation": validate(purchases, fees, summary),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Parse a SmartData Account Statement XLSX and pair "
                    "international transaction fees with their purchases.")
    parser.add_argument("report", type=Path, help="path to a YYYY_MM.xlsx report")
    parser.add_argument("--json", action="store_true",
                        help="emit JSON instead of a human-readable summary")
    args = parser.parse_args()

    result = parse_report(args.report)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result["validation"]["ok"] else 1

    print(f"statement period: {result['period'] or 'unknown'}")
    print(f"purchases: {len(result['purchases'])}   fee lines: {len(result['fees'])}")
    print("validation:")
    for check in result["validation"]["checks"]:
        flag = "ok" if check["ok"] else "REVIEW"
        print(f"  [{flag}] {check['name']}: expected {check['expected']}, "
              f"got {check['actual']}")
    if result["pairs"]:
        print("paired fees:")
        for pair in result["pairs"]:
            p, f = pair["purchase"], pair["fee"]
            print(f"  {p['description']} ({p['country']}) "
                  f"{p['original_amount']} {p['original_currency']} "
                  f"-> ${p['amount']}  fee ${f['amount']}")
    for problem in result["problems"]:
        fee = problem["fee"]
        print(f"  ASK: fee ${fee['amount']} on {fee['transaction_date']} "
              f"-> {problem['reason']} ({len(problem['candidates'])} candidates"
              f"{', equivalent' if problem['equivalent'] else ''})")
    for purchase in result["international_without_fee"]:
        print(f"  ASK: international purchase with no fee line: "
              f"{purchase['description']} ${purchase['amount']}")
    return 0 if result["validation"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

Extend the import block at the top of `parse_smartdata.py` to:

```python
import argparse
import json
import re
import sys
import warnings
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import openpyxl
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 accounting/scripts/test_parse_smartdata.py`
Expected: PASS — `16/16 passed`

- [ ] **Step 5: Verify against the user's real report**

Run:

```bash
# set once: REPO=<this checkout>  WORKING_FOLDER=<accounts_and_receipts folder>
python3 accounting/scripts/parse_smartdata.py \
  "$WORKING_FOLDER/2026/reports/2026_07.xlsx"
```

Expected: every validation line reads `[ok]`, every fee appears under `paired fees:` with a plausible foreign amount and country, and **no** `ASK:` lines appear. Do not record the actual figures anywhere in the repo — this is a local check only. If any check reads `REVIEW`, stop and report it rather than adjusting the expected numbers to match.

- [ ] **Step 6: Commit**

```bash
git add accounting/scripts/parse_smartdata.py accounting/scripts/test_parse_smartdata.py
git commit -m "feat(accounting): pair international fees and self-validate parse"
```

---

### Task 3: Report reference file

**Files:**
- Create: `accounting/references/smartdata_reports.md`

**Interfaces:**
- Consumes: the script and behaviour from Tasks 1-2 (`parse_smartdata.py --json`, its output keys, the `ask` conditions)
- Produces: a reference `SKILL.md` links to in Task 4

- [ ] **Step 1: Write the reference file**

Create `accounting/references/smartdata_reports.md`:

```markdown
# SmartData reports

Reports exported from SmartData (J.P. Morgan) live in
`{working_folder}/{year}/reports/`. They are the authority on what was actually
charged to the p-card: which charges exist, their posted USD amount, and the
international transaction fees.

## Formats, in precedence order

| Source | Filename | Gives | Use |
|---|---|---|---|
| Account Statement, XLSX | `YYYY_MM.xlsx` | posting + transaction date, description, location, **country**, original amount + currency, conversion rate, USD amount, and a summary block of counts and totals | **Primary.** Parse with `scripts/parse_smartdata.py`. |
| Account Statement, PDF | e.g. `Account Statement (Version 2).pdf` | the same fields | Fallback. Read with `pdftotext -layout`; column alignment shifts between pages and long country names wrap, so treat results with suspicion. |
| Expense Inbox print, PDF | e.g. `Expense Management.pdf` | description, posting date, USD amount, **status** (Open/Rejected) | Supplement. No country, currency, or rate, but it reaches past the statement close date and is the only source of status. |

A statement covers a fixed posting-date window, printed in its header and
reported by the parser as `period`. Charges made after the close date are not in
it. The `YYYY_MM.xlsx` filename names the statement month.

## Parsing

Run the parser rather than reading the sheet by hand:

    python3 scripts/parse_smartdata.py {year}/reports/YYYY_MM.xlsx --json

It returns `period`, `purchases`, `fees`, `pairs`, `problems`,
`international_without_fee`, and `validation`. Amounts are strings in JSON;
compare them as decimals, not floats.

The script absorbs the traps in this export — a header row that moves and
contains embedded newlines, Level-3 addendum rows interleaved with
transactions, whitespace-padded numeric cells, and half-up cent rounding. Do
not re-derive that logic inline.

## The 1% fee

The international transaction fee is **1% of the posted USD amount, rounded
half-up to the cent**. It posts as its own transaction, described
`INTERNATIONAL TRANSACTION`, with blank location and country.

Read the actual fee from the report whenever one covers the charge. Only compute
1% when the charge has not posted yet, and mark that row as an estimate.

## International detection

A charge is international when its report **Country is present and not
`UNITED STATES`**. When no report covers the charge, fall back to the
heuristic: a non-USD receipt, **or** a vendor outside the US even if billed in
USD — card networks levy the fee on foreign vendors billing dollars too.

## Fee pairing

Fee rows carry no merchant name. A fee pairs with the purchase whose
transaction date matches, whose country is non-US, and whose USD amount times
1% equals the fee. The parser reports anything other than a unique match under
`problems` instead of guessing:

- `reason: "ambiguous"` — several candidates. When `equivalent` is `true` they
  all cost the same, so either assignment yields identical numbers; say so when
  asking.
- `reason: "no_match"` — no candidate. Usually the parent is on an adjacent
  statement.

`international_without_fee` lists non-US purchases with no fee line, excluding
any purchase already named as a candidate in `problems` (because a purchase
counted there is not also double-reported as missing a fee).

## Self-validation

The parser cross-checks its own counts and sums against the statement's
`Report Totals` row and reports each check under `validation`. The statement's
"Payment" bucket held exactly the fee lines in the verified month, but real
payments and refunds land there too — so a `fee_count` or `fee_total` mismatch
means *review this*, not *the parse is broken*. Report a `REVIEW` line to the
user rather than proceeding silently.

## Privacy

Reports carry the cardholder's name, tax id, **card number**, street address,
and account balances. They stay in the working folder. Never copy any of it into
the spreadsheet, into row notes, or anywhere in the skill repo. The parser is
written to exclude those fields from its output; keep it that way.
```

- [ ] **Step 2: Verify the documented command actually works**

Run:

```bash
# set once: REPO=<this checkout>  WORKING_FOLDER=<accounts_and_receipts folder>
cd "$WORKING_FOLDER"
python3 "$REPO/accounting/scripts/parse_smartdata.py" \
  2026/reports/2026_07.xlsx --json | head -20
```

Expected: valid JSON beginning with a `period` key. This confirms the reference file's documented invocation and output keys match the implementation.

- [ ] **Step 3: Commit**

```bash
git add accounting/references/smartdata_reports.md
git commit -m "docs(accounting): add SmartData report reference"
```

---

### Task 4: Wire the skill's workflow

**Files:**
- Modify: `accounting/SKILL.md`
- Modify: `accounting/CLAUDE.md`

**Interfaces:**
- Consumes: `scripts/parse_smartdata.py` and `references/smartdata_reports.md` from Tasks 1-3
- Produces: the user-facing workflow; nothing downstream depends on it

- [ ] **Step 1: Add the reference and script to "Available Resources"**

In `accounting/SKILL.md`, replace the `## Available Resources` list with:

```markdown
## Available Resources

- `references/gl_codes.md` — GL code reference table with entertainment flags
- `references/supplement_guide.md` — Supplement form layout and filing rules
- `references/smartdata_reports.md` — SmartData report formats, parsing, the 1% international fee, and pairing rules
- `scripts/parse_smartdata.py` — parses a SmartData Account Statement XLSX and pairs international fees
```

- [ ] **Step 2: Add session-start step 7 and renumber**

In `accounting/SKILL.md`, insert a new step **after** the existing step 6 ("Read all unnumbered files") and **before** "Report status". Inserting here keeps the "already read during session start (step 6)" cross-reference in Step 1.1 valid.

```markdown
7. **Load SmartData reports**: List `{working_folder}/{year}/reports/`. For each `YYYY_MM.xlsx`, run:
   ```bash
   python3 scripts/parse_smartdata.py "{working_folder}/{year}/reports/{file}" --json
   ```
   Keep the parsed purchases, fee lines, and pairings for use in Phase 1, and note which posting-date windows are covered. If `validation.ok` is false, report the failing checks to the user before processing anything. See `references/smartdata_reports.md` for the formats, the PDF fallbacks, and what each `problems` reason means.

   The folder is optional — if it is missing or empty, continue without it and ask per Step 1.3 when a receipt actually needs the information.
```

Then renumber the two steps that follow: "Report status" becomes **8** and the closing "Ask the user what they'd like to do" becomes **9**.

- [ ] **Step 3: Add report coverage to the status report**

In the (now) step 8 status block, add a line after `Existing expense records: {count}`:

```
   Reports loaded: {count} covering {posting-date windows}
```

- [ ] **Step 4: Insert Phase 1 Step 1.3 and renumber the rest**

In `accounting/SKILL.md`, insert this **before** the existing `### Step 1.3 — Propose expense record`, because the posted USD amount *is* the cost:

```markdown
### Step 1.3 — Cross-check against the SmartData report

Use the reports loaded during session start (step 7). See
`references/smartdata_reports.md` for details.

1. **Payment method**: match the receipt to a parsed purchase by description and
   amount. Descriptions are card descriptors (`AMAZON MKTPL*<id>`,
   `SQ *<merchant>`), so match fuzzily. A match confirms `p-card`. If there is no
   match, ask whether this is a p-card charge that has not posted yet, `finance`,
   or `reimbursement` — never silently default to `p-card`.

2. **Amount**: compare the receipt total to the posted USD amount. If they
   differ, show both and ask which to record. Differences are usually legitimate
   — tips, currency conversion, partial capture, hotel incidentals — so the
   posted amount normally wins, but do not assume it.

3. **International fee**: the charge is international when the report's Country
   is present and not `UNITED STATES`. If no report covers the receipt's period,
   fall back to the heuristic (non-USD receipt, or a vendor outside the US even
   if billed in USD).
   - If a paired fee line exists, use its **actual** amount.
   - If the charge is international but has not posted, compute **1% of the
     posted USD amount, rounded half-up to the cent** and mark it an estimate.
   - If the parser reported the fee under `problems`, show the candidates and
     ask. When `equivalent` is true, say that either assignment gives the same
     numbers.
   - If the report covers the charge but lists no paired fee and no `problems`
     entry for it — the parser reports it under `international_without_fee` —
     treat the fee as not yet posted: compute 1% rounded half-up to the cent,
     mark it an estimate, and say the report showed no fee line. The likely
     cause is the fee posting just after the statement close, and Phase 3's
     estimated-fee check will confirm or correct it against a later report.

These four branches must stay mutually exclusive and jointly cover every state
the parser can report: a paired fee, an unposted charge, a `problems` entry, and
`international_without_fee`.

For an international charge, `Cost` on the main row is the **posted USD amount**,
not the receipt's foreign total, and `notes` carries the original amount,
currency, and conversion rate.

**When a report is needed but missing**: if the receipt's period has no report at
all, ask the user to export that statement month from SmartData into
`{year}/reports/` as `YYYY_MM.xlsx`. Offer to continue meanwhile with a computed
1% estimate and a flagged payment method — a missing report must never block the
work. If a report covers the period but the charge is absent, it simply has not
posted; do not ask for another report.
```

Then renumber the following Phase 1 steps: `1.3 — Propose expense record` → **1.4**, `1.4 — Entertainment check` → **1.5**, `1.5 — Confirm with user` → **1.6**, `1.6 — Repeat` → **1.7**. The reference to "the `YYXXX` number assigned in Step 1.2" stays correct.

- [ ] **Step 5: Document the fee row in the expense-record step**

At the end of the (now) `### Step 1.4 — Propose expense record` section, after the field table, add:

```markdown
**International transaction fee row.** When Step 1.3 found or computed a fee, emit a
**second row** alongside the main one:

| Field | Value |
|-------|-------|
| Expense | `{vendor} — international transaction fee` |
| Vendor | same as the parent row |
| Cost | the actual fee from the report, else 1% of the parent's USD amount rounded half-up |
| date | the **parent row's** date, so the two rows stay adjacent |
| method | `p-card` |
| Fund | same as the parent row |
| GL code | same as the parent row |
| receipt_number | same as the parent row |
| notes | `Foreign transaction fee on {what} (see {receipt_number})` — append `; 1% estimate, verify against statement` when computed rather than read |

The fee inherits the parent's GL code, so no new GL code is needed. Sharing the
parent's `receipt_number` is expected: Phase 3 already treats one receipt number
covering multiple rows as normal. If the fee's own posting date differs from the
parent's, note it rather than splitting the rows apart.

For `finance` and `reimbursement`, add **no** fee row — the 1% is a card
assessment. Still record the posted USD amount and put the foreign amount in
`notes`.
```

- [ ] **Step 6: Add the Phase 3 reconciliation bullet**

In `accounting/SKILL.md`, in Phase 3, add a step after the existing "**Compare**" step:

```markdown
4. **Confirm estimated fees**: for rows whose notes carry `1% estimate`, check them
   against a report that now covers the period. Correct the cost if it differs and
   drop the estimate caveat once confirmed.
```

Renumber the existing "**Report** findings clearly" step to **5**.

- [ ] **Step 7: Update CLAUDE.md**

In `accounting/CLAUDE.md`, under "Working Folder", extend the per-year structure list to:

```markdown
Structure per year:
- `{year}/receipts/` — numbered receipt files
- `{year}/supplements/` — monthly entertainment supplement PDFs
- `{year}/reports/` — SmartData exports (`YYYY_MM.xlsx` preferred; statement and
  expense-inbox PDFs also appear). Parse with `scripts/parse_smartdata.py`; see
  `references/smartdata_reports.md`.
```

And extend the "Sensitive Data Policy" section with:

```markdown
SmartData reports in `{year}/reports/` carry the cardholder's name, tax id, card
number, street address, and account balances. They stay in the working folder.
Never copy any of it into the spreadsheet, into row notes, or into this
directory. `scripts/parse_smartdata.py` deliberately excludes those fields from
its output.
```

- [ ] **Step 8: Verify the skill's cross-references survived renumbering**

Run:

```bash
# set once: REPO=<this checkout>  WORKING_FOLDER=<accounts_and_receipts folder>
cd "$REPO"
grep -nE 'step [0-9]|Step 1\.[0-9]|Phase [0-9]' accounting/SKILL.md
```

Expected: session-start steps run 1-9 with no duplicates or gaps; Phase 1 steps run 1.1-1.7; Step 1.1's "session start (step 6)" still points at "Read all unnumbered files"; Step 1.4's table still cites "Step 1.2" for the receipt number; Phase 3 steps run 1-5. Fix any mismatch before committing.

- [ ] **Step 9: Commit**

```bash
git add accounting/SKILL.md accounting/CLAUDE.md
git commit -m "feat(accounting): record posted USD cost and 1% international fee row"
```

---

### Task 5: Missing-charge check

**Files:**
- Create: `accounting/scripts/check_missing_receipts.py`
- Test: `accounting/scripts/test_check_missing_receipts.py`

**Interfaces:**
- Consumes: from Task 2 — `parse_report(path) -> dict` and `FEE_DESCRIPTION`; from Task 1's `_smartdata_fixtures` module — `build_workbook`, `txn`
- Produces: `parse_money(text) -> Decimal | None`, `parse_sheet_date(text) -> date | None`, `parse_report_date(text) -> date | None`, `tokens(name) -> set[str]`, `load_expenses(path) -> list[dict]`, `check(report, expenses, window_days=5) -> dict`, `main() -> int`. `check` returns keys `period`, `charges_checked`, `matched`, `missing_from_sheet`, `possible_amount_mismatch`, `ambiguous`, `rows_without_receipt_number`. Expense dicts have keys `expense`, `vendor`, `cost` (`Decimal | None`), `date` (`date | None`), `method`, `receipt_number`.

- [ ] **Step 1: Write the failing test**

Create `accounting/scripts/test_check_missing_receipts.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 accounting/scripts/test_check_missing_receipts.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'check_missing_receipts'`

- [ ] **Step 3: Write minimal implementation**

Create `accounting/scripts/check_missing_receipts.py`:

```python
#!/usr/bin/env python3
"""
Flags p-card charges that posted to a SmartData report but are not recorded in
the expenses spreadsheet -- the mirror image of the orphaned-receipt check.

Matching is deliberately conservative. A charge claims a sheet row when the
amounts are equal and the sheet date falls within a few days of the charge's
transaction date (posting lags the transaction, and the sheet records the
purchase date). Where no exact match exists, a second pass looks for a row in
the same window whose vendor words overlap the card descriptor -- that surfaces
a row entered with the wrong amount rather than calling it absent.

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
    """Comparable words from a vendor name or card descriptor."""
    words = re.split(r"[^A-Za-z0-9]+", str(name or "").upper())
    return {w for w in words if len(w) >= 4 and not w.isdigit()}


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
    """Compare posted charges against recorded rows."""
    charges = [{
        "description": txn["description"],
        "transaction_date": txn["transaction_date"],
        "posting_date": txn["posting_date"],
        "amount": txn["amount"],
        "country": txn["country"],
        "is_fee": txn["description"] == FEE_DESCRIPTION,
    } for txn in report["purchases"] + report["fees"]]

    unclaimed = list(expenses)
    matched, ambiguous, no_receipt, deferred = [], [], [], []

    # Phase 1 -- exact amount within the date window, over EVERY charge, before
    # any fuzzy matching. Resolving all exact matches first is what stops a row
    # offered as a mismatch candidate from later being consumed as a different
    # charge's confirmed match.
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
        elif exact:
            ambiguous.append({"charge": charge, "candidates": exact})
        else:
            deferred.append((charge, when))

    # Phase 2 -- vendor-word overlap, only for charges with no exact match and
    # only over rows still unclaimed.
    mismatches, missing = [], []
    for charge, when in deferred:
        descriptor = tokens(charge["description"])
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
        costs = ", ".join(f"${c['cost']}" for c in item["candidates"])
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
```

- [ ] **Step 4: Run both test files to verify they pass**

Run:

```bash
python3 accounting/scripts/test_check_missing_receipts.py
python3 accounting/scripts/test_parse_smartdata.py
```

Expected: `9/9 passed` and `16/16 passed`. Running both confirms Task 5 did not disturb Task 2.

- [ ] **Step 5: Verify against the user's real data**

Run:

```bash
# set once: REPO=<this checkout>  WORKING_FOLDER=<accounts_and_receipts folder>
cd "$WORKING_FOLDER"
ID=$(python3 -c "import yaml;print(yaml.safe_load(open('spreadsheet_links.yaml'))[2026]['spreadsheet_id'])")
curl -sL -o /tmp/expenses.csv \
  "https://docs.google.com/spreadsheets/d/$ID/gviz/tq?tqx=out:csv&sheet=expenses"
python3 "$REPO/accounting/scripts/check_missing_receipts.py" \
  2026/reports/2026_07.xlsx --expenses /tmp/expenses.csv
rm -f /tmp/expenses.csv
```

Expected: it runs and classifies every charge into one of the buckets without raising. Sanity-check a couple of `MISSING` lines by hand against the sheet — they should be genuinely unrecorded, not matching rows the window or amount rule failed to reach. Record no figures in the repo. If matched rows are being reported as missing, fix the matching rule rather than widening the window until the output looks right.

- [ ] **Step 6: Commit**

```bash
git add accounting/scripts/check_missing_receipts.py accounting/scripts/test_check_missing_receipts.py
git commit -m "feat(accounting): flag posted charges missing from the expenses sheet"
```

---

### Task 6: Surface the missing-charge check in the skill

**Files:**
- Modify: `accounting/SKILL.md`
- Modify: `accounting/references/smartdata_reports.md`

**Interfaces:**
- Consumes: `scripts/check_missing_receipts.py` from Task 5
- Produces: the user-facing reconciliation behaviour; nothing downstream depends on it

- [ ] **Step 1: Add the script to "Available Resources"**

In `accounting/SKILL.md`, append to the `## Available Resources` list:

```markdown
- `scripts/check_missing_receipts.py` — flags posted charges missing from the expenses sheet
```

- [ ] **Step 2: Add the missing-charge check to Phase 3**

In `accounting/SKILL.md`, add to Phase 3 after the "Confirm estimated fees" step added in Task 4:

```markdown
5. **Check for unrecorded charges**: for each `YYYY_MM.xlsx` in `{year}/reports/`
   (the PDF formats are not parseable by this script), save the expenses tab as
   CSV and run:
   ```bash
   python3 scripts/check_missing_receipts.py "{year}/reports/{file}" --expenses {csv} --json
   ```
   Report each bucket separately — `missing_from_sheet` is the actionable list;
   `possible_amount_mismatch` means recorded with a different amount (often the
   receipt's foreign total instead of the posted USD); `ambiguous` needs the user to
   pick; `rows_without_receipt_number` cannot have a receipt file.

   State the limits alongside the results: charges not yet processed are expected to
   appear, another cardholder's spending never appears in this report, and
   aggregated monthly rows cannot match individual charges. Never create rows or
   invent receipt numbers from this output — report and ask.
```

Renumber the existing "**Report** findings clearly" step to **6**.

- [ ] **Step 3: Add report coverage of the check to the session-start status**

In `accounting/SKILL.md`, extend the (now) step 8 status block with:

```
   Posted charges not yet recorded: {count}
```

Populate it by running `check_missing_receipts.py` for each loaded report during
session start when the expenses CSV is already in hand. If the CSV could not be
fetched, print `unknown` rather than `0` — an unfetched sheet is not an empty one.

- [ ] **Step 4: Document the check in the reference file**

Append to `accounting/references/smartdata_reports.md`:

```markdown
## Missing-charge check

    python3 scripts/check_missing_receipts.py {year}/reports/YYYY_MM.xlsx \
        --expenses expenses.csv --json

A charge claims a sheet row when the amounts are equal and the sheet date is
within `--window-days` (default 5) of the charge's transaction date. Posting lags
the transaction, and the sheet records the purchase date, so some tolerance is
required. Where no exact match exists, a second pass matches on vendor word
overlap within the same window, which distinguishes *recorded with the wrong
amount* from *not recorded at all*.

Buckets:

| Key | Meaning |
|---|---|
| `missing_from_sheet` | Posted, not recorded. The actionable list. |
| `possible_amount_mismatch` | Recorded, but the amount disagrees — often the receipt's foreign total instead of the posted USD. |
| `ambiguous` | Several sheet rows could be the same charge; ask which. |
| `rows_without_receipt_number` | Matched, but the row has no receipt number, so no receipt file can exist. |

Always report these limits with the results:

- A charge not yet processed is a true positive. Early in a cycle the missing
  list is *expected* to be long.
- Only the cardholder's own charges appear in their report.
- Aggregated sheet rows (a month of spending as one total) cannot match
  individual charges and will surface as unmatched.

The check reports gaps only. It never writes rows and never invents receipt
numbers.
```

- [ ] **Step 5: Verify Phase 3 numbering and documented commands**

Run:

```bash
# set once: REPO=<this checkout>  WORKING_FOLDER=<accounts_and_receipts folder>
cd "$REPO"
grep -nE '^[0-9]+\. \*\*' accounting/SKILL.md
python3 accounting/scripts/check_missing_receipts.py --help
```

Expected: Phase 3 steps run 1-6 with no duplicates, and `--help` lists `report`,
`--expenses`, `--window-days`, and `--json` exactly as the reference documents them.

- [ ] **Step 6: Commit**

```bash
git add accounting/SKILL.md accounting/references/smartdata_reports.md
git commit -m "feat(accounting): surface unrecorded-charge check in reconciliation"
```

---

## Self-Review

**Spec coverage.** Every section of the spec maps to a task: data source precedence → Task 3 table and Task 4 step 2; the 1% rate → Task 2 `fee_of` plus Task 3; XLSX parsing contract → Tasks 1-2 (header detection, addendum filter, padded numbers, `Decimal`/half-up, summary self-validation); international detection → Task 2 `is_international` and Task 4 step 4; fee pairing → Task 2 `pair_fees` and Task 3; session-start step 7 → Task 4 step 2; Step 1.3 and renumbering → Task 4 steps 4-5; fee row shape → Task 4 step 5; non-p-card methods → Task 4 step 5; Phase 3 estimated-fee confirmation → Task 4 step 6; asking rules → Task 4 step 4; privacy → Task 2's PII test, Task 3, Task 4 step 7; missing-charge check (inputs, matching, all four buckets, known limits, report-only constraint) → Task 5 with Task 6 surfacing it in Phase 3, the status report, and the reference; files to change → Tasks 3, 4, 6.

**Phase 3 numbering across tasks.** Task 4 step 6 inserts "Confirm estimated fees" as Phase 3 step 4 and renumbers "Report findings" to 5; Task 6 step 2 inserts "Check for unrecorded charges" as step 5 and renumbers "Report findings" to 6. Executed in order these are consistent; executed out of order, Phase 3 numbering will need a manual fix, which Task 6 step 5's `grep` catches.

**Deviation from the spec's file list.** The spec named only `SKILL.md` and `CLAUDE.md`. This plan adds `scripts/parse_smartdata.py`, its test, and `references/smartdata_reports.md`. Rationale: the parsing contract is exactly the kind of detail that fails silently when re-derived by hand each session, and four sibling skills already ship `scripts/`. Flag this to the user before executing — dropping the script would mean moving its logic into prose, which the spec's own "silent wrong answers" concern argues against.

**Placeholder scan.** No TBD/TODO; every code step carries runnable code; the "verify against the real report" step states expected *shape* rather than figures, deliberately, so no real amounts enter the repo.

**Type consistency.** `_clean`/`_number` return `str`/`Decimal` and are used as such throughout. `parse_report` keys (`period`, `purchases`, `fees`, `pairs`, `problems`, `international_without_fee`, `validation`) are identical in Task 2's implementation, Task 2's tests, Task 3's reference, and Task 4's prose. `problems` entries use `reason`/`candidates`/`equivalent` consistently. `validation` uses `ok`/`checks` with `name`/`expected`/`actual`/`ok`/`note` consistently. `fee_of` takes and returns `Decimal` everywhere. Task 5's `check` returns `period`/`charges_checked`/`matched`/`missing_from_sheet`/`possible_amount_mismatch`/`ambiguous`/`rows_without_receipt_number`, used identically in its tests, its CLI, Task 6's Phase 3 prose, and Task 6's reference table; expense rows use `expense`/`vendor`/`cost`/`date`/`method`/`receipt_number` in both `load_expenses` and `check`. Task 5 imports `FEE_DESCRIPTION` and `parse_report` from Task 2 under those exact names, and reuses `build_workbook`/`txn` from Task 1's `_smartdata_fixtures` module — no test file imports another test file.

**Amount comparison.** `check` compares `Decimal` to `Decimal` (`row["cost"] == charge["amount"]`), so `$12.50` from the sheet equals `12.50` from the report. Trailing-zero differences are not an issue because `Decimal("12.50") == Decimal("12.5")` is true.
