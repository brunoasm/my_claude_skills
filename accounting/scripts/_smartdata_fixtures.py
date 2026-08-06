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
