#!/usr/bin/env python3
"""Audit figures, tables, and their captions and cross-references in a .docx.

Reports:
  - caption numbering per kind (Figure, Table): gaps, duplicates, out of order
  - in-text references to a number with no caption, and captions never referenced
  - first mention order (Figure 3 cited before Figure 2) and mentions far from
    the caption
  - every embedded image: format, printed size in inches, the paragraph style it
    sits in (an image inside a heading paragraph is a layout risk), and whether a
    caption is nearby
  - vector formats (EMF/WMF) whose internal text cannot be checked here and that
    may render differently outside Word
  - images and captions inside table cells and text boxes are included
  - caption numbers produced by SEQ fields are checked like typed ones; a gap,
    duplicate, or out-of-order number there usually means fields need updating
    in Word (select all, F9) before export

A paragraph counts as a caption when it starts with "Figure N"/"Table N" and has
a caption style, a SEQ field, or caption punctuation ("Figure 2." / "Figure 2:");
a sentence such as "Figure 2 shows ..." is treated as a reference, not a caption.

Tracked changes are accepted in memory. Standard library only.

Usage:
  figure_audit.py FILE.docx [--min-height-in 1.5] [--far 40]
"""
import argparse
import posixpath
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
EMU = 914400.0
KINDS = {"figure": "Figure", "fig": "Figure", "figs": "Figure", "figures": "Figure", "table": "Table", "tables": "Table"}
CAP_RE = re.compile(r"^\s*(Figure|Fig\.|Table)\s*(\d+)\b", re.I)
CAPLIKE_RE = re.compile(r"^\s*(Figure|Fig\.|Table)\s*\d+\s*[.:|\u2013\u2014-]", re.I)
REF_RE = re.compile(r"\b(Figures?|Figs?\.|Tables?)\s*(\d+)(?:\s*(?:[-–,]|and|&)\s*(\d+))?", re.I)


def q(ns, tag):
    return "{%s}%s" % (ns, tag)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx")
    ap.add_argument("--min-height-in", type=float, default=1.5, help="flag images printed shorter than this")
    ap.add_argument("--far", type=int, default=40, help="paragraphs between first mention and caption to flag")
    a = ap.parse_args()

    z = zipfile.ZipFile(a.docx)
    xml = z.read("word/document.xml").decode("utf8")
    xml = re.sub(r"<w:(?:del|moveFrom)\b[^>]*/>", "", xml)
    xml = re.sub(r"<w:(del|moveFrom)\b[^>]*>.*?</w:\1>", "", xml, flags=re.S)
    xml = re.sub(r"<mc:Fallback>.*?</mc:Fallback>", "", xml, flags=re.S)
    body = ET.fromstring(xml).find(q(W, "body"))
    rels = {}
    try:
        for r in ET.fromstring(z.read("word/_rels/document.xml.rels")):
            rels[r.get("Id")] = r.get("Target")
    except KeyError:
        pass

    # Walk body in order; tables count as one block each. Paragraphs inside
    # floating text boxes (a common place for captions) become their own blocks.
    TXBX = q(W, "txbxContent")

    def own_iter(el, tag):
        """Iterate descendants with this tag, not descending into text boxes."""
        stack = list(el)[::-1]
        while stack:
            n = stack.pop()
            if n.tag == tag:
                yield n
            if n.tag == TXBX:
                continue
            stack.extend(list(n)[::-1])

    def para_block(el, floating=False):
        ppr = el.find(q(W, "pPr"))
        ps = ppr.find(q(W, "pStyle")) if ppr is not None else None
        style = ps.get(q(W, "val")) if ps is not None else "Normal"
        text = "".join(t.text or "" for t in own_iter(el, q(W, "t")))
        images = []
        for d in own_iter(el, q(W, "drawing")):
            blip = next(d.iter(q(A, "blip")), None)
            if blip is None:
                continue  # text box or shape, not a picture
            ext = next(d.iter(q(WP, "extent")), None)
            target = rels.get(blip.get(q(R, "embed")))
            images.append({"cx": int(ext.get("cx", 0)) / EMU if ext is not None else 0,
                           "cy": int(ext.get("cy", 0)) / EMU if ext is not None else 0,
                           "file": posixpath.basename(target) if target else "?",
                           "floating": d.find(q(WP, "anchor")) is not None})
        instr = "".join(t.text or "" for t in own_iter(el, q(W, "instrText")))
        seq = re.findall(r"SEQ\s+(\w+)", instr)
        for f in own_iter(el, q(W, "fldSimple")):
            seq += re.findall(r"SEQ\s+(\w+)", f.get(q(W, "instr"), ""))
        return {"type": "p", "style": style, "text": text, "images": images, "seq": seq, "floating": floating}

    blocks = []

    def add_para(el, top, in_table=False):
        b = para_block(el)
        b["top"], b["in_table"] = top, in_table
        blocks.append(b)
        for tb in own_iter(el, TXBX):
            for p in tb.iter(q(W, "p")):
                b = para_block(p, floating=True)
                b["top"], b["in_table"] = top, in_table
                blocks.append(b)

    for top, el in enumerate(body):
        if el.tag == q(W, "tbl"):
            blocks.append({"type": "table", "style": "", "text": "", "images": [], "seq": [], "top": top})
            # Figures are often laid out in tables; their paragraphs count too.
            for p in own_iter(el, q(W, "p")):
                add_para(p, top, in_table=True)
            continue
        if el.tag == q(W, "p"):
            add_para(el, top)

    problems = 0

    def report(ok_msg, items, fail=True):
        nonlocal problems
        if not items:
            print("OK   " + ok_msg)
            return
        if fail:
            problems += 1
        print(("FAIL " if fail else "WARN ") + ok_msg)
        for it in items:
            print("       - " + it)

    captions = {"Figure": [], "Table": []}
    for i, b in enumerate(blocks):
        if b["type"] != "p":
            continue
        m = CAP_RE.match(b["text"])
        if m and ("caption" in b["style"].lower() or b["seq"] or CAPLIKE_RE.match(b["text"])):
            kind = "Table" if m.group(1).lower().startswith("tab") else "Figure"
            captions[kind].append((int(m.group(2)), i, b))
    floating_caps = ["%s caption in a floating text box: \"%s\"" % (k, b["text"][:50])
                     for k, caps in captions.items() for _, _, b in caps if b.get("floating")]

    print("File: %s" % a.docx)
    for kind, caps in captions.items():
        nums = [n for n, _, _ in caps]
        print("\n%s captions found: %s" % (kind, nums or "none"))
        issues = []
        if nums:
            expected = list(range(1, max(nums) + 1))
            gaps = [n for n in expected if n not in nums]
            dups = sorted({n for n in nums if nums.count(n) > 1})
            if gaps:
                issues.append("missing number(s): %s" % gaps)
            if dups:
                issues.append("duplicate number(s): %s" % dups)
            if nums != sorted(nums):
                issues.append("captions out of order: %s" % nums)
            if issues and any(b["seq"] for _, _, b in caps):
                issues.append("captions use SEQ fields: update fields in Word (select all, F9) and re-check")
        report("%s numbering continuous and in order" % kind, issues)

    # References in text
    refs = {"Figure": {}, "Table": {}}
    cap_idx = {(k, n): i for k, caps in captions.items() for n, i, _ in caps}
    cap_blocks = {i for caps in captions.values() for _, i, _ in caps}
    for i, b in enumerate(blocks):
        if b["type"] != "p" or i in cap_blocks:
            continue
        for m in REF_RE.finditer(b["text"]):
            kind = "Table" if m.group(1).lower().startswith("tab") else "Figure"
            lo = int(m.group(2))
            hi = int(m.group(3)) if m.group(3) else lo
            for n in range(lo, max(lo, hi) + 1) if hi - lo < 10 else (lo, hi):
                refs[kind].setdefault(n, []).append(i)
    for kind in refs:
        capnums = {n for n, _, _ in captions[kind]}
        dangling = ["%s %d cited (block %s) but no caption with that number" % (kind, n, refs[kind][n][0])
                    for n in sorted(refs[kind]) if n not in capnums]
        report("every cited %s number has a caption" % kind.lower(), dangling)
        unref = ["%s %d has a caption but is never cited in the text" % (kind, n) for n in sorted(capnums) if n not in refs[kind]]
        report("every %s is cited in the text" % kind.lower(), unref, fail=False)
        firsts = sorted((min(v), n) for n, v in refs[kind].items() if n in capnums)
        order = [n for _, n in firsts]
        if order != sorted(order):
            report("%ss first cited in numerical order" % kind.lower(), ["first-mention order: %s" % order], fail=False)
        far = []
        for n, v in refs[kind].items():
            ci = cap_idx.get((kind, n))
            if ci is not None and abs(min(v) - ci) > a.far:
                far.append("%s %d: first cited at block %d, caption at block %d" % (kind, n, min(v), ci))
        report("%ss placed near their first mention (within %d blocks)" % (kind.lower(), a.far), far, fail=False)

    # Images
    print("\nImages:")
    small, vector, in_heading, in_heading_float, uncaptioned = [], [], [], [], []
    for i, b in enumerate(blocks):
        for img in b.get("images", []):
            ext = img["file"].rsplit(".", 1)[-1].lower() if "." in img["file"] else "?"
            near_cap = any(abs(i - ci) <= 2 for (k, n), ci in cap_idx.items() if k == "Figure")
            print("       block %d: %s  %.2f x %.2f in  style=%s%s" % (
                i, img["file"], img["cx"], img["cy"], b["style"], "" if near_cap else "  (no Figure caption within 2 blocks)"))
            if img["cy"] < a.min_height_in:
                small.append("%s is %.2f in tall: check every label is legible at print size" % (img["file"], img["cy"]))
            if ext in ("emf", "wmf"):
                vector.append("%s (%s): text inside cannot be checked here; may render differently outside Word" % (img["file"], ext.upper()))
            if re.match(r"(heading|title)", b["style"], re.I):
                (in_heading_float if img.get("floating") else in_heading).append(
                    "%s is anchored in a %s paragraph" % (img["file"], b["style"]))
            if not near_cap:
                uncaptioned.append(img["file"])
    report("no images shorter than %.1f in" % a.min_height_in, small, fail=False)
    report("no vector EMF/WMF images", vector, fail=False)
    report("no inline images inside heading paragraphs", in_heading)
    report("no floating images anchored to heading paragraphs (they move with the heading)", in_heading_float, fail=False)
    floats = [img["file"] for b in blocks for img in b.get("images", []) if img.get("floating")]
    report("no floating (wrapped) images; floats can shift between Word and PDF renderers",
           ["%d floating images: %s" % (len(floats), ", ".join(floats))] if floats else [], fail=False)
    report("no captions in floating text boxes (they can detach from their figure)", floating_caps, fail=False)

    # Table captions near tables
    far_tab = []
    tbl_top = [b["top"] for b in blocks if b["type"] == "table"]
    for n, i, b in captions["Table"]:
        d = min((abs(b["top"] - t) for t in tbl_top), default=999)
        if d > 1:
            far_tab.append("Table %d caption is %d paragraphs from the nearest table" % (n, d))
    report("table captions adjacent to a table", far_tab)

    print("\n%s" % ("Problems found." if problems else "No blocking problems found; review WARN items."))
    print("Text inside images is invisible to this script: open the rendered PDF at 100% to check labels.")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
