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
