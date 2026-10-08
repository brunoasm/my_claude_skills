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

Usage:
  cite_check.py FILE.docx [--heading "References|Works Cited|Literature Cited|Bibliography"]
                          [--bib library.bib]
"""
import argparse
import re
import sys
import unicodedata
import zipfile

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


def docx_paragraphs(path):
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8")
    xml = re.sub(r"<w:del\b[^>]*>.*?</w:del>", "", xml, flags=re.S)
    paras = []
    for p in re.findall(r"<w:p\b.*?</w:p>", xml, flags=re.S):
        t = "".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", p, flags=re.S))
        t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")
        paras.append(t)
    return paras


def split_body_refs(paras, heading):
    h = re.compile(r"^\s*(%s)\s*:?\s*$" % heading, re.I)
    for i, p in enumerate(paras):
        if h.match(p):
            return paras[:i], [r for r in paras[i + 1:] if r.strip()]
    sys.exit("Reference heading not found (try --heading).")


def ref_key(entry):
    m = re.match(r"\s*(?:\[\d+\]|\d+\.)?\s*(" + PARTICLE + r"[^,.(]+)", entry)
    y = re.search(YEAR, entry)
    if not m:
        return None, y.group(0) if y else None
    return norm(m.group(1)), (y.group(0) if y else None)


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
    a = ap.parse_args()

    paras = docx_paragraphs(a.file) if a.file.lower().endswith(".docx") else open(a.file, encoding="utf8").read().split("\n")
    body, refs = split_body_refs(paras, a.heading)
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
