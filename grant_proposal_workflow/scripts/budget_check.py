#!/usr/bin/env python3
"""Check the arithmetic and cross-document agreement of a budget justification.

Summary tables inside a justification drift from the line items when someone
edits a number in one place and not the others. This script catches that.

Reads a .docx (tracked changes accepted by default) and, optionally, one or more
.xlsx budget workbooks. Reports:
  1. Table arithmetic: rows labelled Total/Subtotal against the sum of the rows
     above them, and a "Total" column against the year columns in the same row.
  2. Table totals that are not stated anywhere in the prose (e.g. a section
     header says "E. Travel ($48,000)" but the travel table totals $42,500).
  3. With --xlsx: dollar amounts in the document that do not appear among the
     workbook's stored cell values, and formula cells with no stored value
     (the workbook was written by a script and never recalculated).

Standard library only. Matching is by exact whole-dollar value, so a "not found"
item is a lead to check, not proof of an error (it may be a legitimate sum or a
number quoted from another source).

Usage:
  budget_check.py JUSTIFICATION.docx [--xlsx BUDGET.xlsx ...] [--original]
                  [--min-amount 100]
"""
import argparse
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
MONEY = re.compile(r"[-−]?\$\s?\d[\d,]*(?:\.\d+)?")
TOTAL_ROW = re.compile(r"\b(sub)?totals?\b", re.I)
YEAR_COL = re.compile(r"^\s*(Y(ea)?r?\s*\d+|FY\s*\d+|\d{4}(\s*[-–]\s*\d{2,4})?)\s*$", re.I)


def w(tag):
    return "{%s}%s" % (W, tag)


def load_body(path, original):
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8")
    if original:  # state before tracked changes: drop insertions, keep deletions
        xml = re.sub(r"<w:(?:ins|moveTo)\b[^>]*/>", "", xml)
        xml = re.sub(r"<w:(ins|moveTo)\b[^>]*>.*?</w:\1>", "", xml, flags=re.S)
        xml = xml.replace("<w:delText", "<w:t").replace("</w:delText>", "</w:t>")
    else:  # accepted state
        xml = re.sub(r"<w:(?:del|moveFrom)\b[^>]*/>", "", xml)
        xml = re.sub(r"<w:(del|moveFrom)\b[^>]*>.*?</w:\1>", "", xml, flags=re.S)
    return ET.fromstring(xml).find(w("body"))


def text_of(el):
    return "".join(t.text or "" for t in el.iter(w("t")))


def money(s):
    m = MONEY.search(s or "")
    if not m:
        return None
    raw = m.group(0)
    v = float(re.sub(r"[^\d.]", "", raw))
    return -v if raw[0] in "-−" else v


def table_rows(tbl):
    rows = []
    for tr in tbl.findall(w("tr")):
        rows.append([text_of(tc).strip() for tc in tr.findall(w("tc"))])
    return rows


def fmt(v):
    return "${:,.0f}".format(v)


def xlsx_values(path):
    z = zipfile.ZipFile(path)
    vals, missing = set(), []
    for name in z.namelist():
        if not re.match(r"xl/worksheets/sheet\d+\.xml$", name):
            continue
        root = ET.fromstring(z.read(name))
        for c in root.iter("{%s}c" % S):
            f = c.find("{%s}f" % S)
            v = c.find("{%s}v" % S)
            if f is not None and (v is None or v.text in (None, "")):
                missing.append("%s!%s" % (name.split("/")[-1], c.get("r")))
                continue
            if v is not None and c.get("t") not in ("s", "str", "inlineStr", "b", "e"):
                try:
                    x = float(v.text)
                except (TypeError, ValueError):
                    continue
                vals.update({round(x), int(x), int(x) + 1})
    return vals, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx")
    ap.add_argument("--xlsx", nargs="*", default=[])
    ap.add_argument("--original", action="store_true", help="check the state before tracked changes")
    ap.add_argument("--min-amount", type=float, default=100, help="ignore smaller amounts in the workbook check")
    a = ap.parse_args()

    body = load_body(a.docx, a.original)
    prose_amounts, all_amounts, tables = set(), [], []
    for el in body:
        if el.tag == w("p"):
            t = text_of(el)
            for m in MONEY.finditer(t):
                v = money(m.group(0))
                prose_amounts.add(round(v))
                all_amounts.append((round(v), "text: " + t.strip()[:70]))
        elif el.tag == w("tbl"):
            tables.append(table_rows(el))

    problems = 0
    print("File: %s (%s)" % (a.docx, "original, before tracked changes" if a.original else "tracked changes accepted"))
    print("Tables found: %d" % len(tables))

    print("\n1. Table arithmetic")
    table_totals = []
    for ti, rows in enumerate(tables, 1):
        if not rows:
            continue
        header = rows[0]
        ncol = max(len(r) for r in rows)
        year_cols = [j for j, h in enumerate(header) if YEAR_COL.match(h)]
        total_col = next((j for j, h in enumerate(header) if TOTAL_ROW.search(h)), None)
        # A total row may close a section (items since the last total), the whole
        # table (all items, across subtotals), or extend the previous total
        # ("Total direct" + indirect = "Total project"). Accept any of the three.
        section = [0.0] * ncol
        counted = [0] * ncol
        all_items = [0.0] * ncol
        all_counted = [0] * ncol
        prev_total = [None] * ncol
        after_prev = [0.0] * ncol
        for ri, r in enumerate(rows[1:], 2):
            label = r[0] if r else ""
            for j, cell in enumerate(r):
                for m in MONEY.finditer(cell):
                    all_amounts.append((round(money(m.group(0))), "table %d row %d: %s" % (ti, ri, label[:40])))
            nums = [money(c) if MONEY.fullmatch(c.strip() or "x") else None for c in r]
            if total_col is not None and year_cols and total_col < len(nums) and nums[total_col] is not None:
                parts = [nums[j] for j in year_cols if j < len(nums) and nums[j] is not None]
                if parts:
                    s = sum(parts)
                    if round(s) != round(nums[total_col]):
                        problems += 1
                        print("  FAIL table %d row %d '%s': Total column %s, years sum to %s (diff %s)"
                              % (ti, ri, label[:40], fmt(nums[total_col]), fmt(s), fmt(nums[total_col] - s)))
            if TOTAL_ROW.search(label):
                for j, v in enumerate(nums):
                    if v is None or j == 0:
                        continue
                    table_totals.append((round(v), ti, ri, label, header[j] if j < len(header) else ""))
                    sums = [section[j], all_items[j]]
                    if prev_total[j] is not None:
                        sums.append(prev_total[j] + after_prev[j])
                    if all_counted[j] >= 2 and not any(round(s) == round(v) for s in sums):
                        problems += 1
                        diff = v - section[j]
                        note = " (rounding?)" if abs(diff) <= max(counted[j], 1) else ""
                        found = ("rows since the previous total sum to %s, all line items to %s" % (fmt(section[j]), fmt(all_items[j]))
                                 if counted[j] else "all line items sum to %s" % fmt(all_items[j]))
                        print("  FAIL table %d '%s' column '%s': stated %s, but %s%s"
                              % (ti, label[:30], header[j] if j < len(header) else j, fmt(v), found, note))
                    prev_total[j], after_prev[j] = v, 0.0
                section = [0.0] * ncol
                counted = [0] * ncol
            else:
                for j, v in enumerate(nums):
                    if v is not None and j < ncol:
                        section[j] += v
                        counted[j] += 1
                        all_items[j] += v
                        all_counted[j] += 1
                        after_prev[j] += v
            if total_col is not None and total_col < len(nums) and nums[total_col] is not None and not TOTAL_ROW.search(label):
                table_totals.append((round(nums[total_col]), ti, ri, label, header[total_col]))
    if not problems:
        print("  OK   every Total row/column equals the sum of its parts")

    print("\n2. Table totals not stated anywhere in the prose")
    unstated = [t for t in table_totals if t[0] not in prose_amounts]
    seen = set()
    for v, ti, ri, label, col in unstated:
        if (v, ti) in seen:
            continue
        seen.add((v, ti))
        print("  CHECK table %d row %d '%s' / '%s' = %s" % (ti, ri, label[:40], col[:15], fmt(v)))
    if not unstated:
        print("  OK   every table total also appears in the text")
    print("  (Expected for some line items. Look for totals that should match a section header.)")

    if a.xlsx:
        print("\n3. Agreement with the budget workbook")
        wb_vals, no_cache = set(), []
        for x in a.xlsx:
            v, m = xlsx_values(x)
            wb_vals |= v
            no_cache += ["%s %s" % (x.split("/")[-1], c) for c in m]
        if no_cache:
            problems += 1
            print("  FAIL formula cells with no stored value (%d), open and save in Excel/LibreOffice first: %s"
                  % (len(no_cache), ", ".join(no_cache[:8])))
        missing = {}
        for v, where in all_amounts:
            if abs(v) >= a.min_amount and v not in wb_vals:
                missing.setdefault(v, where)
        for v, where in sorted(missing.items()):
            print("  CHECK %s not in workbook  [%s]" % (fmt(v), where))
        if not missing:
            print("  OK   every amount >= %s appears in the workbook" % fmt(a.min_amount))
        print("  (A missing amount may be a legitimate sum or a quoted rate; a stale summary number shows up here.)")

    print("\n%s" % ("Problems found." if problems else "No arithmetic problems found; review the CHECK items."))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
