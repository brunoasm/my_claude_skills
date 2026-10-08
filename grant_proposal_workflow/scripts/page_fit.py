#!/usr/bin/env python3
"""Report how a document fits its page limit.

Renders a .docx (or reads a .pdf) and reports the page count, the page and
vertical position where the body ends (the last line before a stop heading such
as "References"), and the space left on that page.

For .docx input, tracked changes are accepted in a temporary copy before
rendering, so the result reflects the document as it would look once accepted.
The original file is never modified.

Requires LibreOffice (soffice) for .docx and poppler's pdftotext.

Usage:
  page_fit.py FILE.docx [--stop "References|Works Cited|Literature Cited|Bibliography"]
                        [--limit 15] [--keep-pdf OUT.pdf]

Word and LibreOffice paginate slightly differently; confirm close calls in Word.
"""
import argparse
import html
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import zipfile

DEL_RE = [
    re.compile(r"<w:(del|moveFrom)\b[^>]*/>"),
    re.compile(r"<w:(del|moveFrom)\b[^>]*>.*?</w:\1>", re.S),
    re.compile(r"<w:(rPrChange|pPrChange|sectPrChange|tblPrChange|trPrChange|tcPrChange)\b[^>]*>.*?</w:\1>", re.S),
    re.compile(r"<w:(rPrChange|pPrChange|sectPrChange|tblPrChange|trPrChange|tcPrChange)\b[^>]*/>"),
    re.compile(r"<w:(ins|moveTo)\b[^>]*/>"),
    re.compile(r"<w:(moveFromRangeStart|moveFromRangeEnd|moveToRangeStart|moveToRangeEnd)\b[^>]*/>"),
]
UNWRAP_RE = re.compile(r"</?w:(ins|moveTo)\b[^>]*>")


def accept_changes(src, dst):
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
        for item in zi.infolist():
            data = zi.read(item.filename)
            if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", item.filename):
                s = data.decode("utf8")
                for rx in DEL_RE:
                    s = rx.sub("", s)
                s = UNWRAP_RE.sub("", s)
                data = s.encode("utf8")
            zo.writestr(item, data)


def to_pdf(docx, workdir):
    accepted = os.path.join(workdir, "accepted.docx")
    accept_changes(docx, accepted)
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        sys.exit("LibreOffice (soffice) not found")
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", workdir, accepted],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return os.path.join(workdir, "accepted.pdf")


def read_lines(pdf, workdir):
    out = os.path.join(workdir, "bbox.html")
    subprocess.run(["pdftotext", "-bbox-layout", pdf, out], check=True)
    text = open(out, encoding="utf8").read()
    pages = []
    for pm in re.finditer(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', text, re.S):
        lines = []
        for lm in re.finditer(r'<line xMin="[\d.]+" yMin="([\d.]+)" xMax="[\d.]+" yMax="([\d.]+)">(.*?)</line>', pm.group(3), re.S):
            words = [html.unescape(w) for w in re.findall(r"<word[^>]*>(.*?)</word>", lm.group(3), re.S)]
            lines.append((float(lm.group(1)), float(lm.group(2)), " ".join(words)))
        lines.sort()
        pages.append({"h": float(pm.group(2)), "lines": lines})
    return pages


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--stop", default=r"References( Cited)?|Works Cited|Literature Cited|Bibliography",
                    help="regex for the heading that ends the counted body (matched against whole lines)")
    ap.add_argument("--limit", type=int, default=None, help="page limit for the body")
    ap.add_argument("--keep-pdf", default=None)
    ap.add_argument("--bottom-margin-pt", type=float, default=None,
                    help="bottom margin in points; default guesses from the fullest page")
    a = ap.parse_args()

    work = tempfile.mkdtemp()
    try:
        pdf = a.file if a.file.lower().endswith(".pdf") else to_pdf(a.file, work)
        if a.keep_pdf:
            shutil.copy(pdf, a.keep_pdf)
        pages = read_lines(pdf, work)
        stop = re.compile(r"^\s*(%s)\s*:?\s*$" % a.stop, re.I)

        # Ignore page numbers and running footers: lines that are only digits.
        def content(lines):
            return [l for l in lines if not re.fullmatch(r"\s*(Page\s*)?\d+(\s*of\s*\d+)?\s*", l[2], re.I)]

        body_end = None
        for i, p in enumerate(pages):
            for j, l in enumerate(content(p["lines"])):
                if stop.match(l[2]):
                    prev = content(p["lines"])[:j]
                    if prev:
                        body_end = (i, prev[-1])
                    elif i > 0:
                        body_end = (i - 1, content(pages[i - 1]["lines"])[-1])
                    break
            if body_end:
                break
        if body_end is None:
            last = len(pages) - 1
            body_end = (last, content(pages[last]["lines"])[-1])
            print("Stop heading not found; treating the whole document as body.")

        heights = [l[1] - l[0] for p in pages for l in content(p["lines"]) if 4 < l[1] - l[0] < 30]
        lh = statistics.median(heights) * 1.15 if heights else 14
        full_bottom = max(content(p["lines"])[-1][1] for p in pages if content(p["lines"]))
        bottom = pages[body_end[0]]["h"] - a.bottom_margin_pt if a.bottom_margin_pt else full_bottom
        page_no, line = body_end
        slack = bottom - line[1]

        print("File: %s" % a.file)
        print("Pages in rendered file: %d" % len(pages))
        print("Body ends on page %d at y = %.0f pt (page height %.0f pt)" % (page_no + 1, line[1], pages[page_no]["h"]))
        print("Last body line: %s" % line[2][:100])
        print("Space left on that page: %.0f pt (about %.1f lines of body text)" % (slack, max(slack, 0) / lh))
        if a.limit:
            ok = page_no + 1 <= a.limit
            print("Page limit %d: %s" % (a.limit, "OK" if ok else "OVER by %d page(s)" % (page_no + 1 - a.limit)))
            sys.exit(0 if ok else 1)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
