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

If no stop heading is found, the body is taken to end before a trailing
numbered reference list ("1. Author ...", "2. ..."), as produced by a
reference-manager bibliography with no heading.

For .docx input the script also compares the fonts the document asks for with
the fonts actually embedded in the rendered PDF (poppler's pdffonts). When a font
is missing here, LibreOffice substitutes a look-alike with different metrics, so
the page count and line breaks are approximate and the PDF must not be uploaded:
export the upload PDF on a machine that has the fonts.

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


NUM_RE = re.compile(r"^\s*\[?(\d{1,3})[.\]]\s+\S")
MAX_WRAP = 8  # lines a single reference entry may wrap over
METRIC_COMPATIBLE = {"calibri": "Carlito", "cambria": "Caladea", "arial": "Liberation Sans",
                     "helvetica": "Liberation Sans", "times new roman": "Liberation Serif",
                     "courier new": "Liberation Mono"}


def trailing_numbered_list(flat):
    """
    Index in flat of the "1." line that starts a numbered list running
    consecutively (1, 2, 3, ...) to the end of the document, or None.
    A numbered list elsewhere (aims, steps) is not a reference list.
    """
    nums = []
    for k, (_, _, l) in enumerate(flat):
        m = NUM_RE.match(l[2])
        if m:
            nums.append((k, int(m.group(1))))
    for s, (k, n) in enumerate(nums):
        if n != 1:
            continue
        expected, last = 2, k
        for k2, n2 in nums[s + 1:]:
            if k2 - last > MAX_WRAP:
                break
            if n2 == expected:
                expected, last = expected + 1, k2
        if expected > 2 and len(flat) - 1 - last <= MAX_WRAP:
            return k
    return None


def norm_font(name):
    return re.sub(r"[^a-z]", "", name.split("+")[-1].split("-")[0].lower())


def used_fonts(docx):
    """Fonts the document actually uses: direct run fonts, styles in use, defaults, theme."""
    with zipfile.ZipFile(docx) as zf:
        names = zf.namelist()
        read = lambda n: zf.read(n).decode("utf8", "replace") if n in names else ""
        parts = "".join(read(n) for n in names if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", n))
        styles, theme = read("word/styles.xml"), read("word/theme/theme1.xml")
    themes = {}
    for kind in ("major", "minor"):
        m = re.search(r"<a:%sFont>.*?<a:latin typeface=\"([^\"]*)\"" % kind, theme, re.S)
        if m and m.group(1):
            themes[kind] = m.group(1)

    def font_in(xml):
        m = re.search(r"<w:rFonts\b[^>]*>", xml or "")
        if not m:
            return None
        a = re.search(r'\bw:ascii="([^"]+)"', m.group(0))
        if a:
            return a.group(1)
        t = re.search(r'\bw:asciiTheme="([^"]+)"', m.group(0))
        return themes.get(t.group(1)[:5]) if t else None

    by_id = dict(re.findall(r'<w:style\b[^>]*w:styleId="([^"]+)"[^>]*>(.*?)</w:style>', styles, re.S))

    def style_font(sid):
        seen = set()
        while sid and sid not in seen and sid in by_id:
            seen.add(sid)
            f = font_in(re.search(r"<w:rPr>.*?</w:rPr>", by_id[sid], re.S).group(0)) if "<w:rPr>" in by_id[sid] else None
            if f:
                return f
            b = re.search(r'<w:basedOn w:val="([^"]+)"', by_id[sid])
            sid = b.group(1) if b else None
        return None

    m = re.search(r"<w:docDefaults>.*?</w:docDefaults>", styles, re.S)
    default_font = font_in(m.group(0) if m else "")
    d = re.search(r'<w:style\b[^>]*w:type="paragraph"[^>]*w:default="1"[^>]*w:styleId="([^"]+)"', styles)
    default_para = d.group(1) if d else None

    # Word's order for a run: direct formatting, character style, paragraph style chain, defaults.
    used = set()
    for p in re.findall(r"<w:p\b.*?</w:p>", parts, re.S):
        ps = re.search(r'<w:pStyle w:val="([^"]+)"', p)
        pfont = style_font(ps.group(1) if ps else default_para)
        for r in re.findall(r"<w:r\b(?:(?!</w:r>).)*?</w:r>", p, re.S):
            if not re.search(r"<w:t(?:\s[^>]*)?>[^<]*\S", r):
                continue
            rpr = re.search(r"<w:rPr>.*?</w:rPr>", r, re.S)
            rs = re.search(r'<w:rStyle w:val="([^"]+)"', r)
            f = (font_in(rpr.group(0) if rpr else None) or (style_font(rs.group(1)) if rs else None)
                 or pfont or default_font)
            if f:
                used.add(f)
    return used


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
        flat = [(i, j, l) for i, p in enumerate(pages) for j, l in enumerate(content(p["lines"]))]
        if not flat:
            sys.exit("No text found in the rendered document.")
        if body_end is None:
            start = trailing_numbered_list(flat)
            if start is not None:
                i, j, _ = flat[start]
                if j > 0:
                    body_end = (i, content(pages[i]["lines"])[j - 1])
                elif i > 0:
                    body_end = (i - 1, content(pages[i - 1]["lines"])[-1])
                if body_end:
                    print("Stop heading not found; body taken to end before the numbered reference list "
                          "that closes the document (starts on page %d)." % (i + 1))
        if body_end is None:
            body_end = flat[-1][0], flat[-1][2]
            print("Stop heading not found; treating the whole document as body.")

        heights = [l[1] - l[0] for p in pages for l in content(p["lines"]) if 4 < l[1] - l[0] < 30]
        lh = statistics.median(heights) * 1.15 if heights else 14
        full_bottom = max(content(p["lines"])[-1][1] for p in pages if content(p["lines"]))
        bottom = pages[body_end[0]]["h"] - a.bottom_margin_pt if a.bottom_margin_pt else full_bottom
        page_no, line = body_end
        slack = bottom - line[1]

        if not a.file.lower().endswith(".pdf") and shutil.which("pdffonts"):
            got = subprocess.run(["pdffonts", pdf], capture_output=True, text=True).stdout
            have = {norm_font(l.split()[0]) for l in got.splitlines()[2:] if l.split()}
            close, other = [], []
            for f in sorted(used_fonts(a.file)):
                if any(norm_font(f) in h for h in have):
                    continue
                sub = METRIC_COMPATIBLE.get(f.lower())
                if sub and any(norm_font(sub) in h for h in have):
                    close.append("%s (rendered as %s, same metrics)" % (f, sub))
                else:
                    other.append(f)
            if close:
                print("NOTE: substituted with metric-compatible fonts: %s" % "; ".join(close))
                print("      Line breaks should match closely; confirm a tight fit in Word.")
            if other:
                print("WARNING: fonts not available for rendering, substituted: %s" % ", ".join(other))
                print("         Page fit is approximate; export the upload PDF where these fonts are installed.")
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
