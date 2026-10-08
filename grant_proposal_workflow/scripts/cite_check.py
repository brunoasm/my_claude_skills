#!/usr/bin/env python3
"""Cross-check author-year citations against the reference list.

Reads a .docx (tracked deletions ignored, insertions kept) or a .txt/.md file,
splits it at the reference-list heading, and reports:
  - in-text citations with no matching reference (by first-author surname + year)
  - references never cited in the text
  - references that use "et al." (some funders require all author names)
  - with --bib: references whose first author + year is not in the BibTeX file

Designed for author-year styles (APA, Chicago author-date, Harvard, journal
styles such as "Smith et al. 2020"). For numbered styles it checks that every
number cited exists in the list and every entry is cited.

Matching is heuristic. Treat the output as a list to check by hand, not a verdict.

The reference list is found, in order of preference: in a separate file given
with --refs (funders such as NSF require References Cited as its own upload);
after a heading matching --heading; at a reference-manager bibliography field
(Zotero, EndNote, Mendeley); or as the trailing run of numbered entries.

Usage:
  cite_check.py FILE.docx [--refs REFERENCES.docx]
                          [--heading "References|Works Cited|Literature Cited|Bibliography"]
                          [--bib library.bib]
"""
import argparse
import re
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

PARTICLE = r"(?:(?:de|da|das|do|dos|del|della|der|den|di|du|la|le|van|von|ten|ter|st\.?)\s+)*"
NAME = r"[A-ZÀ-Þ][\w'’\-]+"
AUTHOR = PARTICLE + NAME + r"(?:\s+" + NAME + r")?"
YEAR = r"(?:19|20)\d{2}[a-z]?"
CITE_RE = re.compile(
    r"(?<![\w])(" + AUTHOR + r")"
    r"(?:\s+et\s+al\.?|\s*(?:,\s*" + NAME + r",?)*\s*(?:&|and)\s+" + PARTICLE + NAME + r")?"
    r",?\s*\(?(" + YEAR + r"(?:\s*,\s*" + YEAR + r")*)"
)
STOP = set("""in on at by of from since during until before after between the a an this that these those
fall spring summer winter january february march april may june july august september october november december
year years fy version vol volume figure fig table section aim phase page pp no grant award census plan act
nsf nih usda doe nasa noaa epa total since circa""".split())


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().replace("’", "'").strip()


BIBL_FIELD = re.compile(r"ADDIN (ZOTERO_BIBL|EN\.REFLIST|Mendeley Bibliography|CSL_BIBLIOGRAPHY)")
NUMBERED = re.compile(r"\s*(\[\d+\]|\d+\.)\s")


def docx_paragraphs(path, marks=None):
    """Paragraph texts in document order, including tables and text boxes."""
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8")
    xml = re.sub(r"<w:(?:del|moveFrom)\b[^>]*/>", "", xml)
    xml = re.sub(r"<w:(del|moveFrom)\b[^>]*>.*?</w:\1>", "", xml, flags=re.S)
    xml = re.sub(r"<mc:Fallback>.*?</mc:Fallback>", "", xml, flags=re.S)
    root = ET.fromstring(xml)
    paras = []

    def own(el, tag):
        stack = list(el)[::-1]
        while stack:
            n = stack.pop()
            if n.tag == tag:
                yield n
            if n.tag != W + "txbxContent":
                stack.extend(list(n)[::-1])

    for p in root.iter(W + "p"):
        instr = "".join(t.text or "" for t in own(p, W + "instrText"))
        instr += " ".join(f.get(W + "instr", "") for f in own(p, W + "fldSimple"))
        if marks is not None and BIBL_FIELD.search(instr):
            marks.append(len(paras))
        paras.append("".join(t.text or "" for t in own(p, W + "t")))
    return paras


def split_body_refs(paras, heading, marks=()):
    h = re.compile(r"^\s*(%s)\s*:?\s*$" % heading, re.I)
    for i, p in enumerate(paras):
        if h.match(p):
            return paras[:i], [r for r in paras[i + 1:] if r.strip()], "after heading"
    if marks:
        i = marks[0]
        return paras[:i], [r for r in paras[i:] if r.strip()], "at reference-manager bibliography field"
    j = len(paras)
    while j > 0 and (NUMBERED.match(paras[j - 1]) or not paras[j - 1].strip()):
        j -= 1
    if sum(1 for r in paras[j:] if r.strip()) >= 3:
        return paras[:j], [r for r in paras[j:] if r.strip()], "trailing numbered list"
    sys.exit("Reference list not found: pass --refs FILE, or --heading.")


def ref_key(entry):
    m = re.match(r"\s*(?:\[\d+\]|\d+\.)?\s*(" + PARTICLE + r"[^,.(]+)", entry)
    y = re.search(YEAR, entry)
    if not m:
        return None, y.group(0) if y else None
    sur = re.sub(r"\s+[A-Z]{1,3}$", "", m.group(1).strip())  # "Smith AB" (Vancouver/NSF style) -> "Smith"
    return norm(sur), (y.group(0) if y else None)


def bib_keys(path):
    text = open(path, encoding="utf8").read()
    keys = set()
    for entry in re.split(r"\n@", text):
        a = re.search(r"\bauthor\s*=\s*[{\"](.+?)[}\"]\s*,?\s*\n", entry, re.S | re.I)
        y = re.search(r"\b(?:year|date)\s*=\s*[{\"]?(\d{4})", entry, re.I)
        if not (a and y):
            continue
        first = re.split(r"\s+and\s+", a.group(1))[0].strip().strip("{}")
        sur = first.split(",")[0] if "," in first else first.split()[-1]
        keys.add((norm(sur.replace("{", "").replace("}", "")), y.group(1)))
    return keys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--heading", default=r"References( Cited)?|Works Cited|Literature Cited|Bibliography")
    ap.add_argument("--bib", default=None)
    ap.add_argument("--refs", default=None, help="separate reference-list file (.docx, .txt, .md)")
    a = ap.parse_args()

    def load(path, marks=None):
        if path.lower().endswith(".docx"):
            return docx_paragraphs(path, marks)
        return open(path, encoding="utf8").read().split("\n")

    marks = []
    paras = load(a.file, marks)
    if a.refs:
        rparas = load(a.refs)
        hh = re.compile(r"^\s*(%s)\s*:?\s*$" % a.heading, re.I)
        body, refs, where = paras, [r for r in rparas if r.strip() and not hh.match(r)], "separate file %s" % a.refs
    else:
        body, refs, where = split_body_refs(paras, a.heading, marks)
    print("Reference list: %d entries (%s)" % (len(refs), where))
    body_text = "\n".join(body)

    numbered = sum(bool(re.match(r"\s*(\[\d+\]|\d+\.)\s", r)) for r in refs) > len(refs) / 2
    if numbered:
        cited = set()
        for grp in re.findall(r"\[(\d+(?:\s*[-–,]\s*\d+)*)\]", body_text):
            for part in re.split(r"\s*,\s*", grp):
                if re.search(r"[-–]", part):
                    lo, hi = map(int, re.split(r"\s*[-–]\s*", part))
                    cited.update(range(lo, hi + 1))
                else:
                    cited.add(int(part))
        n = len(refs)
        print("Numbered style: %d references, %d distinct numbers cited" % (n, len(cited)))
        print("Cited but not in list:", sorted(c for c in cited if c > n) or "none")
        print("In list but never cited:", sorted(set(range(1, n + 1)) - cited) or "none")
        return

    ref_index = {}
    for r in refs:
        k = ref_key(r)
        if k[0]:
            ref_index.setdefault(k, []).append(r)

    citations = {}
    for m in CITE_RE.finditer(body_text):
        author = m.group(1).strip()
        last_word = author.split()[-1]
        if norm(author) in STOP or norm(last_word) in STOP or norm(author.split()[0]) in STOP and len(author.split()) == 1:
            continue
        for y in re.findall(YEAR, m.group(2)):
            citations.setdefault((norm(author), y), m.group(0).strip())

    def find(key):
        sur, y = key
        for (rs, ry) in ref_index:
            if ry == y and (rs == sur or rs.endswith(" " + sur) or sur.endswith(" " + rs) or rs.split()[-1] == sur.split()[-1]):
                return (rs, ry)
        return None

    matched = set()
    missing = []
    for key, txt in sorted(citations.items()):
        hit = find(key)
        if hit:
            matched.add(hit)
        else:
            missing.append(txt)

    uncited = [ref_index[k][0][:110] for k in ref_index if k not in matched]
    etal = [r[:110] for r in refs if re.search(r"\bet al\b", r)]

    print("File: %s" % a.file)
    print("References in list: %d; distinct author-year citations found in text: %d" % (len(refs), len(citations)))
    print("\nCited in text, no matching reference (%d):" % len(missing))
    for t in missing:
        print("  - %s" % t)
    print("\nIn reference list, not found in text (%d):" % len(uncited))
    for t in uncited:
        print("  - %s" % t)
    print("\nReference entries using 'et al.' (%d):" % len(etal))
    for t in etal:
        print("  - %s" % t)
    if a.bib:
        bk = bib_keys(a.bib)
        notbib = [ref_index[k][0][:110] for k in ref_index
                  if not any(by == k[1] and (bs == k[0] or k[0].endswith(bs) or bs.endswith(k[0].split()[-1])) for bs, by in bk)]
        print("\nIn reference list, not found in %s (%d):" % (a.bib, len(notbib)))
        for t in notbib:
            print("  - %s" % t)
    print("\nHeuristic matching: check each item by hand.")


if __name__ == "__main__":
    main()
