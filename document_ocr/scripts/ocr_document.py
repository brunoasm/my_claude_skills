#!/usr/bin/env python
"""OCR documents (PDFs and images) to markdown + figure crops.

For each PDF, classify as born-digital or needs-OCR. Born-digital PDFs are
extracted with pymupdf (no server needed). Scanned PDFs and standalone images
are sent to a vision-language model through the chosen backend. Per-page
responses are cached as JSON so re-runs are cheap.

This skill assumes an OCR backend is ALREADY available — a running
OpenAI-compatible server (vLLM/SGLang/LM Studio/llama.cpp), an Ollama server,
or a cloud API key (OpenAI/Anthropic). Standing one up is out of scope; see
references/server_setup.md for example commands.

Usage:
    # Recommended: docling figures + olmOCR-2 over a vLLM server
    python ocr_document.py --input docs/ --output-dir out/ \\
        --backend olmocr-docling --host http://HOST:PORT --dpi 200

    # Cloud Claude (no local GPU); needs ANTHROPIC_API_KEY
    python ocr_document.py --input scan.pdf --output-dir out/ \\
        --backend anthropic-docling

    # Just classify, don't OCR
    python ocr_document.py --input docs/ --dry-run

Outputs land in <output-dir>/<stem>/<stem>.md (plus cache/, figures/, pages/).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import fitz
from tqdm import tqdm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ocr_utils as ou  # noqa: E402
import docling_pipeline as dp  # noqa: E402


# backend -> (strategy, provider, requirement)
#   strategy: "olmocr-docling" (docling figs + full-page VLM),
#             "docling" (docling layout + per-region OCR),
#             "ollama" (full-page deepseek + grounding crops)
#   requirement: "host" or "api_key"
BACKENDS = {
    "olmocr-docling": ("olmocr-docling", "vllm-olmocr", "host"),
    "vlm-docling": ("olmocr-docling", "vllm", "host"),
    "anthropic-docling": ("olmocr-docling", "anthropic", "api_key"),
    "ollama": ("ollama", "ollama", "host"),
    "docling": ("docling", "vllm", "host"),
}


def _process_scanned_ollama(
    pdf_path: Path,
    out_dir: Path,
    host: str,
    model: str,
    dpi: int,
    force: bool,
) -> tuple[list[str], int]:
    """Full-page DeepSeek-OCR via Ollama, with grounding-token figure crops."""
    figures_dir = out_dir / "figures"
    pages_dir = out_dir / "pages"
    cache_dir = out_dir / "cache"
    for d in (figures_dir, pages_dir, cache_dir):
        d.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    n_pages = doc.page_count
    page_blocks: list[str] = [""] * n_pages
    n_figures = 0
    try:
        for i in range(n_pages):
            page_png = pages_dir / f"page_{i + 1:04d}.png"
            cache_file = cache_dir / f"page_{i + 1:04d}.json"
            if not page_png.exists() or force:
                ou.render_page(doc[i], dpi, page_png)
            if cache_file.exists() and not force:
                raw_md = json.loads(cache_file.read_text()).get("response", "")
            else:
                resp = ou.call_ollama_ocr(page_png, host=host, model=model)
                raw_md = resp.get("response", "")
                cache_file.write_text(json.dumps(resp, indent=2))
            md_clean, figs = ou.crop_figures_from_grounding(raw_md, page_png, figures_dir, i + 1)
            page_blocks[i] = md_clean
            n_figures += len(figs)
    finally:
        doc.close()
    return page_blocks, n_figures


def process_pdf(pdf_path: Path, out_dir: Path, args: argparse.Namespace,
                host: str | None, api_key: str | None) -> dict:
    stem = pdf_path.stem
    pdf_out = out_dir / stem
    pdf_out.mkdir(parents=True, exist_ok=True)

    strategy, provider, _req = BACKENDS[args.backend]
    cls = ou.is_native_digital(pdf_path)
    t0 = time.time()

    doc = fitz.open(pdf_path)
    n_pages = doc.page_count
    doc.close()

    if cls.is_digital:
        blocks, n_figures = ou.extract_digital_markdown(pdf_path, pdf_out / "figures")
        page_blocks = [blocks[i] if i < len(blocks) else "" for i in range(n_pages)]
        model = None
    else:
        model = ou.resolve_model(provider, args.model)
        if strategy == "olmocr-docling":
            page_blocks, n_figures = dp.process_scanned_olmocr_docling(
                pdf_path, pdf_out, provider=provider, host=host, model=model,
                dpi=args.dpi, force=args.force, api_key=api_key)
        elif strategy == "docling":
            page_blocks, n_figures = dp.process_scanned_docling(
                pdf_path, pdf_out, provider=provider, host=host, model=model,
                dpi=args.dpi, force=args.force, api_key=api_key)
        else:  # ollama
            page_blocks, n_figures = _process_scanned_ollama(
                pdf_path, pdf_out, host=host, model=model,
                dpi=args.dpi, force=args.force)

    per_page_lang, ranges, primary = ou.detect_languages_per_page(page_blocks)
    out_md = pdf_out / f"{stem}.md"
    recorded_backend = "born-digital" if cls.is_digital else args.backend
    ou.stitch_markdown(out_md, pdf_path, cls, model, args.dpi if not cls.is_digital else None,
                       page_blocks, ranges, primary, backend=recorded_backend)
    return {
        "source": pdf_path.name,
        "classification": "digital" if cls.is_digital else "needs_ocr",
        "pages": n_pages, "figures": n_figures,
        "language_primary": primary, "elapsed_s": round(time.time() - t0, 1),
    }


def process_image(img_path: Path, out_dir: Path, args: argparse.Namespace,
                  host: str | None, api_key: str | None) -> dict:
    stem = img_path.stem
    img_out = out_dir / stem
    img_out.mkdir(parents=True, exist_ok=True)
    strategy, provider, _req = BACKENDS[args.backend]
    if strategy == "ollama":  # ollama path has no docling; use plain full-page
        provider = "ollama"
    model = ou.resolve_model(provider, args.model)
    t0 = time.time()
    page_blocks, n_figures = dp.process_image(
        img_path, img_out, provider=provider, host=host, model=model,
        dpi=args.dpi, force=args.force, api_key=api_key, use_docling=(strategy != "ollama"))
    _pp, ranges, primary = ou.detect_languages_per_page(page_blocks)
    cls = ou.Classification(False, "image input", {})
    out_md = img_out / f"{stem}.md"
    ou.stitch_markdown(out_md, img_path, cls, model, None, page_blocks,
                       ranges, primary, backend=args.backend)
    return {
        "source": img_path.name, "classification": "image",
        "pages": 1, "figures": n_figures,
        "language_primary": primary, "elapsed_s": round(time.time() - t0, 1),
    }


def collect_inputs(input_path: Path) -> tuple[list[Path], list[Path]]:
    """Return (pdfs, images) found at input_path (file or directory)."""
    if input_path.is_dir():
        files = sorted(p for p in input_path.iterdir() if p.is_file())
    else:
        files = [input_path]
    pdfs = [p for p in files if p.suffix.lower() == ".pdf"]
    images = [p for p in files if p.suffix.lower() in ou.IMAGE_EXTS]
    return pdfs, images


def resolve_credentials(args: argparse.Namespace) -> tuple[str | None, str | None]:
    """Resolve (host, api_key) from flags then environment."""
    host = args.host or os.environ.get("OCR_HOST")
    if args.api_key:
        api_key = args.api_key
    elif args.backend == "anthropic-docling":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
    return host, api_key


def preflight(args: argparse.Namespace, host: str | None, api_key: str | None,
              needs_ocr: bool) -> str | None:
    """Return an error message if the backend can't run, else None."""
    if not needs_ocr:
        return None  # everything is born-digital; no server needed
    _strategy, _provider, req = BACKENDS[args.backend]
    if req == "host" and not host:
        return (f"Backend '{args.backend}' needs an OCR server, but no host was given.\n"
                f"  Start/point to a server, then pass --host http://HOST:PORT "
                f"(or set OCR_HOST).\n"
                f"  Setting up a server is out of scope — see references/server_setup.md.")
    if req == "api_key" and not api_key:
        env = "ANTHROPIC_API_KEY" if args.backend == "anthropic-docling" else "OPENAI_API_KEY"
        return (f"Backend '{args.backend}' needs a cloud API key, but none was found.\n"
                f"  Pass --api-key, or set {env} in your environment.")
    if req == "host" and host:
        # Soft reachability probe — warn only, don't fail (server may reject GET).
        try:
            import requests
            base = host if host.startswith(("http://", "https://")) else "http://" + host
            requests.get(base, timeout=3)
        except Exception:
            print(f"  [warn] could not reach {host} (proceeding anyway; OCR calls may fail).",
                  file=sys.stderr)
    return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, type=Path,
                   help="A PDF/image file, or a directory of them.")
    p.add_argument("--output-dir", type=Path, default=Path("ocr_output"))
    p.add_argument("--backend", choices=list(BACKENDS), default="olmocr-docling",
                   help="OCR backend (default: olmocr-docling, recommended).")
    p.add_argument("--host", default=None,
                   help="Server base URL for host backends (or set OCR_HOST).")
    p.add_argument("--model", default=None,
                   help="Model name (default depends on backend).")
    p.add_argument("--api-key", default=None,
                   help="Cloud API key (or set OPENAI_API_KEY / ANTHROPIC_API_KEY).")
    p.add_argument("--dpi", type=int, default=200,
                   help="Render DPI for scanned pages (default: 200).")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--force", action="store_true", help="ignore cache, re-OCR all pages")
    p.add_argument("--dry-run", action="store_true",
                   help="classify PDFs only; do not OCR or call any server")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1

    pdfs, images = collect_inputs(args.input)
    if not pdfs and not images:
        print("No PDFs or images found at input.", file=sys.stderr)
        return 1

    # Classify PDFs up front (cheap) so we can decide if a server is needed.
    pdf_class = {p: ou.is_native_digital(p) for p in pdfs}

    if args.dry_run:
        print(f"Classifying {len(pdfs)} PDF(s), {len(images)} image(s) (dry run)\n")
        for p in pdfs:
            cls = pdf_class[p]
            tag = "DIGITAL" if cls.is_digital else "NEEDS_OCR"
            print(f"  [{tag:9s}] {p.name}  — {cls.reason}")
        for p in images:
            print(f"  [IMAGE    ] {p.name}  — needs OCR")
        return 0

    needs_ocr = bool(images) or any(not c.is_digital for c in pdf_class.values())
    host, api_key = resolve_credentials(args)
    err = preflight(args, host, api_key, needs_ocr)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for p in tqdm(pdfs, desc="PDFs", disable=not pdfs):
        try:
            results.append(process_pdf(p, args.output_dir, args, host, api_key))
        except Exception as e:
            print(f"  FAILED {p.name}: {e!r}", file=sys.stderr)
    for p in tqdm(images, desc="images", disable=not images):
        try:
            results.append(process_image(p, args.output_dir, args, host, api_key))
        except Exception as e:
            print(f"  FAILED {p.name}: {e!r}", file=sys.stderr)

    for r in results:
        print(f"  done {r['source']}: {r['classification']}, {r['pages']} pages, "
              f"{r['figures']} figs, lang={r['language_primary']}, {r['elapsed_s']}s")
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
