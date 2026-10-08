#!/usr/bin/env python3
"""Identify loose PDFs before filing them in the bibliography.

For each PDF (files or folders given; folders are not searched recursively),
reports:
  - page count and whether there is a text layer (no text = a scan to read by eye)
  - the most likely DOI (document metadata first, then the first page), other
    DOIs nearby, and any arXiv ID or PMID
  - a title guess (metadata title if plausible, else the first substantial line)
    and a year guess
  - whether it looks like supplementary material
  - duplicates: within the files given, and with --library, against the
    library's PDFs (by checksum) and library.csv (by DOI)

Report only: nothing is moved, renamed, or downloaded. Guesses are leads; confirm
each work against an authoritative record (DOI, PubMed) before filing it.

Requires poppler's pdftotext and pdfinfo.

Usage:
  pdf_identify.py PATH [PATH ...] [--library 98_bibliography] [--csv OUT.csv]
"""
import argparse
import csv
import hashlib
import os
import re
import subprocess
import sys
from collections import Counter

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>{}]+)", re.I)
ARXIV_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})(v\d+)?", re.I)
PMID_RE = re.compile(r"\bPMID:?\s*(\d{6,9})\b")
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")
SUPP_RE = re.compile(r"supplementary (information|material|data|methods)|supporting information|"
                     r"electronic supplementary|appendix s\d|\bfigure s\d|\btable s\d", re.I)
BAD_TITLE = re.compile(r"^(microsoft word|untitled|document\d*$|\S+\.(docx?|pdf|tex)$)|^(pdf|untitled)$", re.I)
SKIP_LINE = re.compile(r"(journal|volume|vol\.|issn|doi|https?:|www\.|©|copyright|received|accepted|published|"
                       r"downloaded|creative commons|open access|research article|original article|"
                       r"page \d|^\d+$|e-?mail|correspondence|arxiv:|biorxiv|preprint)", re.I)


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace").stdout
    except FileNotFoundError:
        sys.exit("%s not found; install poppler" % cmd[0])


def clean_doi(d):
    d = d.rstrip(".,;:)]}'")
    if d.count("(") < d.count(")"):
        d = d.rstrip(")")
    return d.lower()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def identify(path):
    info = run(["pdfinfo", path])
    meta = dict(re.findall(r"^([A-Za-z ]+):\s*(.*)$", info, re.M))
    pages = int(meta.get("Pages", "0") or 0)
    if not pages:
        raise ValueError("not a readable PDF (damaged, incomplete download, or not a PDF)")
    xmp = run(["pdfinfo", "-meta", path])
    first = run(["pdftotext", "-l", "1", "-layout", path, "-"])
    early = run(["pdftotext", "-l", "2", path, "-"])

    meta_text = " ".join([meta.get("Subject", ""), meta.get("Keywords", ""), meta.get("Title", ""), xmp])
    meta_dois = [clean_doi(d) for d in DOI_RE.findall(meta_text)]
    page_dois = [clean_doi(d) for d in DOI_RE.findall(first)]
    doi = (meta_dois or page_dois or [""])[0]
    others = sorted(set(clean_doi(d) for d in DOI_RE.findall(early)) - {doi})

    title = meta.get("Title", "").strip()
    if not title or len(title) < 15 or BAD_TITLE.search(title):
        title = ""
        for line in first.splitlines():
            s = re.sub(r"\s{2,}", " ", line).strip()
            if len(s.split()) >= 4 and len(s) >= 25 and not SKIP_LINE.search(s):
                title = s
                break
    years = Counter(YEAR_RE.findall(first))
    year = years.most_common(1)[0][0] if years else ""

    arxiv = ARXIV_RE.search(first + meta_text)
    pmid = PMID_RE.search(first)
    return {
        "file": path,
        "pages": pages,
        "text_layer": "yes" if len(re.findall(r"\w", early)) >= 20 else "NO (scan?)",
        "doi": doi,
        "other_dois": len(others),
        "arxiv": arxiv.group(1) if arxiv else "",
        "pmid": pmid.group(1) if pmid else "",
        "title_guess": title[:120],
        "year_guess": year,
        "supplementary": "yes" if SUPP_RE.search(first[:3000]) else "",
        "sha256": sha256(path),
    }


def load_library(lib):
    hashes, dois = {}, {}
    pdf_dir = os.path.join(lib, "pdfs")
    if os.path.isdir(pdf_dir):
        for n in os.listdir(pdf_dir):
            if n.lower().endswith(".pdf"):
                hashes[sha256(os.path.join(pdf_dir, n))] = os.path.join("pdfs", n)
    index = os.path.join(lib, "library.csv")
    if os.path.exists(index):
        with open(index, newline="", encoding="utf8") as f:
            for row in csv.DictReader(f):
                if row.get("doi"):
                    dois[clean_doi(row["doi"])] = row.get("key") or row.get("file") or "?"
                if row.get("sha256"):
                    hashes.setdefault(row["sha256"], row.get("file") or row.get("key") or "?")
    return hashes, dois


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--library", default=None, help="bibliography folder holding pdfs/ and library.csv")
    ap.add_argument("--csv", default=None, help="also write the report as CSV")
    a = ap.parse_args()

    files = []
    for p in a.paths:
        if os.path.isdir(p):
            files += sorted(os.path.join(p, n) for n in os.listdir(p)
                            if n.lower().endswith(".pdf") and not n.startswith((".", "~$")))
        elif p.lower().endswith(".pdf"):
            files.append(p)
    if not files:
        sys.exit("No PDFs found.")

    lib_hashes, lib_dois = load_library(a.library) if a.library else ({}, {})
    rows, seen_hash, seen_doi = [], {}, {}
    for f in files:
        try:
            r = identify(f)
        except Exception as e:  # a damaged PDF should not stop the inventory
            r = {"file": f, "error": str(e)}
            rows.append(r)
            continue
        # A supplement usually carries its parent's DOI: link it rather than call it a duplicate.
        dup, parent = [], []
        if r["sha256"] in lib_hashes:
            dup.append("same file as library %s" % lib_hashes[r["sha256"]])
        elif r["doi"] in lib_dois:
            if r["supplementary"]:
                parent.append("library %s" % lib_dois[r["doi"]])
            else:
                dup.append("same DOI as library %s" % lib_dois[r["doi"]])
        if r["sha256"] in seen_hash:
            dup.append("same file as %s" % os.path.basename(seen_hash[r["sha256"]]))
        elif r["doi"] in seen_doi:
            if r["supplementary"]:
                parent.append(os.path.basename(seen_doi[r["doi"]]))
            else:
                dup.append("same DOI as %s" % os.path.basename(seen_doi[r["doi"]]))
        seen_hash.setdefault(r["sha256"], f)
        if r["doi"] and not r["supplementary"]:
            seen_doi.setdefault(r["doi"], f)
        r["duplicate"] = "; ".join(dup)
        r["supplement_of"] = "; ".join(parent)
        rows.append(r)

    for r in rows:
        print("\n%s" % os.path.basename(r["file"]))
        if "error" in r:
            print("  ERROR: %s" % r["error"])
            continue
        print("  pages %d, text layer %s%s" % (r["pages"], r["text_layer"],
                                              ", looks SUPPLEMENTARY" if r["supplementary"] else ""))
        ids = ["DOI %s" % r["doi"] if r["doi"] else "no DOI found"]
        if r["arxiv"]:
            ids.append("arXiv %s" % r["arxiv"])
        if r["pmid"]:
            ids.append("PMID %s" % r["pmid"])
        if r["other_dois"]:
            ids.append("%d other DOI(s) on pages 1-2, likely citations" % r["other_dois"])
        print("  " + "; ".join(ids))
        print("  title guess: %s" % (r["title_guess"] or "-"))
        print("  year guess:  %s" % (r["year_guess"] or "-"))
        if r["supplement_of"]:
            print("  SUPPLEMENT of: %s" % r["supplement_of"])
        if r["duplicate"]:
            print("  DUPLICATE: %s" % r["duplicate"])

    ok = [r for r in rows if "error" not in r]
    print("\n%d PDF(s): %d with a DOI, %d without a text layer, %d possible duplicates, %d errors."
          % (len(rows), sum(bool(r["doi"]) for r in ok), sum(r["text_layer"] != "yes" for r in ok),
             sum(bool(r["duplicate"]) for r in ok), len(rows) - len(ok)))
    print("Guesses are leads: confirm each work against its DOI or PubMed record before filing.")

    if a.csv:
        cols = ["file", "pages", "text_layer", "doi", "other_dois", "arxiv", "pmid", "title_guess",
                "year_guess", "supplementary", "supplement_of", "duplicate", "sha256", "error"]
        with open(a.csv, "w", newline="", encoding="utf8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in cols})


if __name__ == "__main__":
    main()
