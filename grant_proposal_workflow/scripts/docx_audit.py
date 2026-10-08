#!/usr/bin/env python3
"""Audit a .docx against common grant formatting rules before upload.

Checks (standard library only):
  - effective font size of every text run (run -> paragraph style -> defaults)
  - font families against an allowed list (theme fonts resolved)
  - condensed/expanded character spacing and horizontal scaling
  - page margins
  - Track Changes setting, unaccepted revisions, comments, highlights
  - placeholder markers ([CLARIFY], TODO, XXX, ⟦...⟧, "insert")
  - document properties (title, author, last modified by, company)

Usage:
  docx_audit.py FILE.docx [--min-pt 11] [--fonts "Arial,Calibri,Times New Roman"]
                [--min-margin-in 0.5] [--max-examples 8]

Exit code 1 if any problem is found, else 0. Effective sizes are a close
approximation of Word's inheritance (table styles and fields are not resolved),
so confirm borderline cases in Word.
"""
import argparse
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"w": W, "a": A}


def q(tag):
    p, t = tag.split(":")
    return "{%s}%s" % (NS[p], t)


def read(z, name):
    try:
        return ET.fromstring(z.read(name))
    except KeyError:
        return None


def theme_fonts(z):
    root = read(z, "word/theme/theme1.xml")
    out = {}
    if root is None:
        return out
    for kind in ("majorFont", "minorFont"):
        el = root.find(".//a:%s/a:latin" % kind, NS)
        if el is not None:
            out[kind] = el.get("typeface")
    return out


def rfont(rpr, theme):
    if rpr is None:
        return None
    f = rpr.find("w:rFonts", NS)
    if f is None:
        return None
    if f.get(q("w:ascii")):
        return f.get(q("w:ascii"))
    t = f.get(q("w:asciiTheme"))
    if t:
        return theme.get("majorFont" if t.startswith("major") else "minorFont")
    return None


def rsize(rpr):
    if rpr is None:
        return None
    s = rpr.find("w:sz", NS)
    return int(s.get(q("w:val"))) / 2 if s is not None else None


class Styles:
    def __init__(self, z, theme):
        self.theme = theme
        self.by_id = {}
        self.default_size, self.default_font = 10.0, None
        self.default_para = None
        root = read(z, "word/styles.xml")
        if root is None:
            return
        d = root.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
        if rsize(d):
            self.default_size = rsize(d)
        self.default_font = rfont(d, theme)
        for s in root.findall("w:style", NS):
            sid = s.get(q("w:styleId"))
            self.by_id[sid] = s
            if s.get(q("w:type")) == "paragraph" and s.get(q("w:default")) == "1":
                self.default_para = sid

    def resolve(self, sid, getter, seen=None):
        seen = seen or set()
        while sid and sid not in seen:
            seen.add(sid)
            s = self.by_id.get(sid)
            if s is None:
                return None
            v = getter(s.find("w:rPr", NS))
            if v is not None:
                return v
            b = s.find("w:basedOn", NS)
            sid = b.get(q("w:val")) if b is not None else None
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx")
    ap.add_argument("--min-pt", type=float, default=11.0)
    ap.add_argument("--fonts", default="", help="comma-separated allowed font families (empty = do not check)")
    ap.add_argument("--min-margin-in", type=float, default=None)
    ap.add_argument("--max-examples", type=int, default=8)
    a = ap.parse_args()

    allowed = {f.strip().lower() for f in a.fonts.split(",") if f.strip()}
    z = zipfile.ZipFile(a.docx)
    theme = theme_fonts(z)
    st = Styles(z, theme)
    problems = 0

    def section(title, items, limit=a.max_examples):
        nonlocal problems
        if not items:
            print("OK   %s" % title)
            return
        problems += 1
        print("FAIL %s (%d)" % (title, len(items)))
        for it in items[:limit]:
            print("       - %s" % it)
        if len(items) > limit:
            print("       … %d more" % (len(items) - limit))

    parts = [n for n in z.namelist() if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", n)]
    small, badfont, spacing, highlights, placeholders = [], [], [], [], []
    sizes_seen = {}
    revisions = 0
    ph_re = re.compile(r"\[CLARIFY|\bTODO\b|\bXXX\b|⟦|\bTBD\b|\[insert|\binsert (?:here|name|date)\b", re.I)

    for part in parts:
        root = read(z, part)
        for tag in ("ins", "del", "moveFrom", "moveTo", "rPrChange", "pPrChange", "sectPrChange", "tblPrChange"):
            revisions += len(root.findall(".//w:%s" % tag, NS))
        for p in root.iter(q("w:p")):
            ppr = p.find("w:pPr", NS)
            ps = ppr.find("w:pStyle", NS) if ppr is not None else None
            pstyle = ps.get(q("w:val")) if ps is not None else st.default_para
            ptext = "".join(t.text or "" for t in p.iter(q("w:t")))
            if ph_re.search(ptext):
                placeholders.append("%s: %s" % (part, ptext.strip()[:90]))
            for r in p.iter(q("w:r")):
                text = "".join(t.text or "" for t in r.findall("w:t", NS)).strip()
                if not text:
                    continue
                rpr = r.find("w:rPr", NS)
                rs = rpr.find("w:rStyle", NS) if rpr is not None else None
                rstyle = rs.get(q("w:val")) if rs is not None else None
                size = (rsize(rpr) or st.resolve(rstyle, rsize) or st.resolve(pstyle, rsize) or st.default_size)
                font = (rfont(rpr, theme) or st.resolve(rstyle, lambda x: rfont(x, theme))
                        or st.resolve(pstyle, lambda x: rfont(x, theme)) or st.default_font)
                sizes_seen[size] = sizes_seen.get(size, 0) + len(text)
                if size < a.min_pt:
                    small.append("%.1f pt [%s] %s" % (size, pstyle, text[:70]))
                if allowed and font and font.lower() not in allowed:
                    badfont.append("%s: %s" % (font, text[:70]))
                if rpr is not None:
                    sp = rpr.find("w:spacing", NS)
                    if sp is not None and int(sp.get(q("w:val"), "0")) != 0:
                        spacing.append("spacing %s twips: %s" % (sp.get(q("w:val")), text[:60]))
                    sc = rpr.find("w:w", NS)
                    if sc is not None and sc.get(q("w:val")) not in (None, "100"):
                        spacing.append("scale %s%%: %s" % (sc.get(q("w:val")), text[:60]))
                    if rpr.find("w:highlight", NS) is not None:
                        highlights.append(text[:70])

    print("File: %s" % a.docx)
    print("Text by effective size (pt: characters): %s" %
          ", ".join("%g: %d" % (k, v) for k, v in sorted(sizes_seen.items())))
    section("text at or above %g pt" % a.min_pt, small)
    if allowed:
        section("fonts in allowed list (%s)" % a.fonts, badfont)
    section("standard character spacing and scale", spacing)

    doc = read(z, "word/document.xml")
    margins = []
    if a.min_margin_in is not None:
        for i, pm in enumerate(doc.iter(q("w:pgMar"))):
            for side in ("top", "bottom", "left", "right"):
                v = pm.get(q("w:" + side))
                if v is not None and abs(int(v)) / 1440 < a.min_margin_in - 1e-6:
                    margins.append("section %d %s = %.2f in" % (i + 1, side, abs(int(v)) / 1440))
        section("margins at least %g in" % a.min_margin_in, margins)

    settings = read(z, "word/settings.xml")
    tr = settings is not None and settings.find("w:trackRevisions", NS) is not None
    section("Track Changes switched off", ["trackRevisions is on"] if tr else [])
    section("no unaccepted revisions", ["%d revision marks" % revisions] if revisions else [])
    com = read(z, "word/comments.xml")
    n_com = len(com.findall("w:comment", NS)) if com is not None else 0
    section("no comments", ["%d comments" % n_com] if n_com else [])
    section("no highlighted text", highlights)
    section("no placeholders", placeholders)

    print("Document properties (check they are appropriate):")
    core = read(z, "docProps/core.xml")
    if core is not None:
        for el in core:
            tag = el.tag.split("}")[1]
            if tag in ("title", "creator", "lastModifiedBy", "subject", "description", "keywords") and (el.text or "").strip():
                print("       %s: %s" % (tag, el.text.strip()))
    app = read(z, "docProps/app.xml")
    if app is not None:
        for el in app:
            tag = el.tag.split("}")[1]
            if tag in ("Company", "Manager", "Template") and (el.text or "").strip():
                print("       %s: %s" % (tag, el.text.strip()))

    print("\n%s" % ("Problems found." if problems else "No problems found."))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
