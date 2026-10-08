#!/usr/bin/env python3
"""Audit a .docx against common grant formatting rules before upload.

Checks (standard library only):
  - effective font size of every text run (run -> paragraph style -> defaults)
  - font families against an allowed list (theme fonts resolved)
  - condensed/expanded character spacing and horizontal scaling
  - page margins
  - Track Changes setting, unaccepted revisions, comments, highlights
  - caption and table text checked against their own minimums (--caption-min-pt,
    --table-min-pt); a caption is a "Figure N"/"Table N" paragraph with a caption
    style, a SEQ field, or caption punctuation ("Figure 2." / "Figure 2:"), because
    some funders allow smaller text in figure and table captions (e.g. the NSF
    PAPPG, provided it stays readable); check your current rules
  - placeholder markers ([CLARIFY], TODO, XXX, XX%, "X to Y" (X markers are
    case-sensitive, so "XX/XY" and "xx" are not flagged), lorem ipsum,
    (CITE ...), (REF), ⟦...⟧, "insert ...") and keyboard-mash filler such as
    "Qwfgrthkpz" (reported as a warning)
  - revision marks counted by author
  - hidden content that travels with the file: reference-manager field codes
    (Zotero, Mendeley, EndNote) and whether they embed abstracts, hidden
    (vanish) text, and flag terms found in hidden places (--flag-terms)
  - document properties (title, author, last modified by, company)

Usage:
  docx_audit.py FILE.docx [--min-pt 11] [--caption-min-pt 8] [--table-min-pt 9]
                [--fonts "Arial,Calibri,Times New Roman"]
                [--min-margin-in 0.5] [--max-examples 8] [--flag-terms REGEX]

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
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
NS = {"w": W, "a": A}


def q(tag):
    p, t = tag.split(":")
    return "{%s}%s" % (NS[p], t)


def own_iter(el, tag):
    """Descendants with this tag, not descending into text boxes (they hold their own paragraphs)."""
    txbx = q("w:txbxContent")
    stack = list(el)[::-1]
    while stack:
        n = stack.pop()
        if n.tag == tag:
            yield n
        if n.tag != txbx:
            stack.extend(list(n)[::-1])


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
    ap.add_argument("--table-min-pt", type=float, default=None,
                    help="minimum size for text inside tables (default: same as --min-pt)")
    ap.add_argument("--caption-min-pt", type=float, default=None,
                    help="minimum size for figure/table caption text (default: same as --min-pt)")
    ap.add_argument("--flag-terms", default=r"lorem ipsum|as an AI (language )?model|CLAUDE\.md|AGENTS\.md|\bTODO\b|do not cite|confidential",
                    help="regex searched in hidden content (field codes, hidden text, comments)")
    a = ap.parse_args()
    cap_min = a.min_pt if a.caption_min_pt is None else a.caption_min_pt
    tab_min = a.min_pt if a.table_min_pt is None else a.table_min_pt

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
    small_tab = []
    small, small_cap, badfont, spacing, highlights, placeholders, mash = [], [], [], [], [], [], []
    rev_authors = {}
    cap_re = re.compile(r"^\s*(Figure|Fig\.|Table)\s*\d+", re.I)
    caplike_re = re.compile(r"^\s*(Figure|Fig\.|Table)\s*\d+\s*[.:|\u2013\u2014-]", re.I)
    vowel_run = re.compile(r"[^aeiouyàáâãäéèêëíìîïóòôõöúùûü\W\d_]{6,}", re.I)
    sizes_seen = {}
    revisions = 0
    ph_re = re.compile(r"\[CLARIFY|\bTODO\b|⟦|\bTBD\b|\[insert|"
                       r"\binsert (?:here|name|date)\b|lorem ipsum|\(CITE\b|\[CITE\b|\(REF\)|\[REF\]|\?\?\?", re.I)
    # Case-sensitive: "XX/XY" chromosomes and "xx" in prose are not placeholders.
    ph_x_re = re.compile(r"\bXXX+\b|\bX{1,2}\s?%|\bX to Y\b")

    for part in parts:
        root = read(z, part)
        for tag in ("ins", "del", "moveFrom", "moveTo", "rPrChange", "pPrChange", "sectPrChange", "tblPrChange"):
            for el in root.findall(".//w:%s" % tag, NS):
                revisions += 1
                au = el.get(q("w:author")) or "?"
                rev_authors[au] = rev_authors.get(au, 0) + 1
        in_table = {id(p) for t in root.iter(q("w:tbl")) for p in t.iter(q("w:p"))}
        # Text boxes are stored twice (mc:Choice and mc:Fallback); read only the Choice copy.
        fallback = {id(p) for fb in root.iter("{%s}Fallback" % MC) for p in fb.iter(q("w:p"))}
        for p in root.iter(q("w:p")):
            if id(p) in fallback:
                continue
            ppr = p.find("w:pPr", NS)
            ps = ppr.find("w:pStyle", NS) if ppr is not None else None
            pstyle = ps.get(q("w:val")) if ps is not None else st.default_para
            ptext = "".join(t.text or "" for t in own_iter(p, q("w:t")))
            m_ph = ph_re.search(ptext) or ph_x_re.search(ptext)
            if m_ph:
                st_i = max(0, m_ph.start() - 40)
                placeholders.append("%s: …%s…" % (part.split("/")[-1], ptext[st_i:m_ph.end() + 40].strip()))
            for tok in re.findall(r"[^\W\d_]{6,}", ptext):
                if vowel_run.search(tok) and sum(c.isupper() for c in tok) < 2:
                    mash.append("%s (in: …%s…)" % (tok, ptext[max(0, ptext.find(tok) - 30):ptext.find(tok) + len(tok) + 30].strip()))
            instr = "".join(t.text or "" for t in p.iter(q("w:instrText")))
            instr += " ".join(f.get(q("w:instr"), "") for f in p.iter(q("w:fldSimple")))
            is_cap = bool(cap_re.match(ptext)) and ("caption" in (pstyle or "").lower()
                                                     or "SEQ" in instr or bool(caplike_re.match(ptext)))
            for r in own_iter(p, q("w:r")):
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
                if is_cap or id(p) in in_table:
                    lim, lst = (cap_min, small_cap) if is_cap else (tab_min, small_tab)
                    if size < lim:
                        lst.append("%.1f pt [%s] %s" % (size, pstyle, text[:70]))
                elif size < a.min_pt:
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
    section("body text at or above %g pt (captions checked separately)" % a.min_pt, small)
    section("caption text at or above %g pt" % cap_min, small_cap)
    section("table text at or above %g pt" % tab_min, small_tab)
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
    section("no unaccepted revisions", ["%d revision marks by: %s" % (revisions, ", ".join(
        "%s (%d)" % kv for kv in sorted(rev_authors.items(), key=lambda kv: -kv[1])))] if revisions else [])
    com = read(z, "word/comments.xml")
    n_com = len(com.findall("w:comment", NS)) if com is not None else 0
    section("no comments", ["%d comments" % n_com] if n_com else [])
    section("no highlighted text", highlights)
    section("no placeholders", placeholders)
    if mash:
        print("WARN possible keyboard-mash filler (%d), check by hand:" % len(mash))
        for it in mash[:a.max_examples]:
            print("       - %s" % it)

    # Hidden content that travels with the file
    print("Hidden content:")
    hidden_hits = []
    flag = re.compile(a.flag_terms, re.I)
    raw = z.read("word/document.xml").decode("utf8", "replace")
    instr = re.findall(r"<w:instrText[^>]*>(.*?)</w:instrText>", raw, flags=re.S)
    fields = "".join(instr) + " ".join(re.findall(r'w:instr="([^"]*)"', raw))
    n_zot = len(re.findall(r"ADDIN ZOTERO_ITEM", fields))
    n_men = len(re.findall(r"ADDIN CSL_CITATION|Mendeley", fields))
    n_end = len(re.findall(r"ADDIN EN\.CITE", fields))
    n_abs = len(re.findall(r"&quot;abstract&quot;|\"abstract\"", fields))
    print("       reference-manager fields: Zotero %d, Mendeley/CSL %d, EndNote %d; field-code text %d chars"
          % (n_zot, n_men, n_end, len(fields)))
    if n_abs:
        print("WARN %d embedded abstracts inside citation field codes; they ship with the .docx (not the PDF)."
              " Clear odd abstracts in the reference manager, then refresh, rather than editing the XML." % n_abs)
    for m in flag.finditer(fields):
        hit = "field code: …%s…" % fields[max(0, m.start() - 40):m.end() + 40].replace("\\n", " ")
        if hit not in hidden_hits:
            hidden_hits.append(hit)
    vanish = []
    for part in parts:
        x = z.read(part).decode("utf8", "replace")
        for r_ in re.findall(r"<w:r\b(?:(?!</w:r>).)*?<w:vanish/>.*?</w:r>", x, flags=re.S):
            t = "".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", r_, flags=re.S))
            if t.strip():
                vanish.append(t.strip()[:70])
                for m in flag.finditer(t):
                    hidden_hits.append("hidden text: …%s…" % t[max(0, m.start() - 40):m.end() + 40].strip())
    section("no hidden (vanish) text", vanish)
    if com is not None:
        ctext = "".join(t.text or "" for t in com.iter(q("w:t")))
        for m in flag.finditer(ctext):
            hidden_hits.append("comment: …%s…" % ctext[max(0, m.start() - 40):m.end() + 40])
    section("no flag terms in hidden content (%s)" % a.flag_terms, hidden_hits)

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
