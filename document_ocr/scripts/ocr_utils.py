"""Helpers for OCRing documents (PDFs and images) to markdown + figure crops.

Three input paths:
- Born-digital PDFs: extract text and embedded images via pymupdf (no server).
- Scanned PDFs: render pages, send to a vision-language model, stitch markdown.
- Standalone images: treat as a single page and send to a VLM.

OCR backends are pluggable. The call_*() functions below all return the same
dict shape: {"model", "response", "done", "_elapsed_s"}.
  - call_olmocr_openai : olmOCR-2 over an OpenAI-compatible (vLLM) endpoint
  - call_openai_ocr    : any VLM over an OpenAI-compatible endpoint (local or cloud)
  - call_ollama_ocr    : DeepSeek-OCR (or any vision model) over Ollama
  - call_anthropic_ocr : Claude over the Anthropic cloud API

This module never hardcodes a server host: callers pass `host` (and, for cloud
endpoints, `api_key`). Standing up a server is out of scope for this skill.

Adapted from Bruno de Medeiros' OntoMorphoGrapher proof-of-concept.
"""

from __future__ import annotations

import base64
import io
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # pymupdf
import requests
from PIL import Image


# ---------------------------------------------------------------------------
# Prompts and model identifiers
# ---------------------------------------------------------------------------

# DeepSeek-OCR via Ollama / vLLM (grounding-token output).
OCR_PROMPT = "<image>\n<|grounding|>Convert the document to markdown."
DEFAULT_MODEL = "deepseek-ocr:3b"

DEFAULT_MODEL_OPENAI = "deepseek-ai/DeepSeek-OCR-2"
OCR_PROMPT_OPENAI = "<image>\n<|grounding|>Convert the document to markdown."

# olmOCR-2 (Qwen2.5-VL-7B fine-tune by Allen AI). Expects full-page images
# resized so the longest dimension is 1288 px, and the official prompt below.
# Served via vLLM (OpenAI-compatible). Ollama is not viable: llama.cpp has
# a known M-RoPE/seq_add bug with Qwen2.5-VL that crashes or hallucinates.
DEFAULT_MODEL_OLMOCR = "allenai/olmOCR-2-7B-1025-FP8"
OLMOCR_TARGET_LONGEST_DIM = 1288
# Verbatim from olmocr.prompts.build_no_anchoring_v4_yaml_prompt().
OCR_PROMPT_OLMOCR = (
    "Attached is one page of a document that you must process. "
    "Just return the plain text representation of this document as if you were reading it naturally. "
    "Convert equations to LateX and tables to HTML.\n"
    "If there are any figures or charts, label them with the following markdown syntax "
    "![Alt text describing the contents of the figure](page_startx_starty_width_height.png)\n"
    "Return your output as markdown, with a front matter section on top specifying values for "
    "the primary_language, is_rotation_valid, rotation_correction, is_table, and is_diagram parameters."
)

# Generic full-page prompt for VLMs without a model-specific protocol
# (e.g. cloud GPT-4o / Claude, or an arbitrary vLLM-served vision model).
OCR_PROMPT_GENERIC = (
    "Transcribe this document page to clean Markdown exactly as written. "
    "Preserve reading order, headings, italics, diacritics, and special characters. "
    "Render equations as LaTeX and tables as HTML. Do not summarize, translate, "
    "or add commentary. For each figure or photograph, emit a markdown image "
    "placeholder with a short alt description, e.g. ![brief description](figure.png). "
    "Return only the page content."
)

# Default cloud model names (override with --model).
DEFAULT_MODEL_ANTHROPIC = "claude-sonnet-4-6"
DEFAULT_MODEL_OPENAI_CLOUD = "gpt-4o"

# Default model per provider (used by make_fullpage_fn and for frontmatter).
PROVIDER_DEFAULT_MODEL = {
    "vllm-olmocr": DEFAULT_MODEL_OLMOCR,
    "vllm": DEFAULT_MODEL_OPENAI,
    "openai": DEFAULT_MODEL_OPENAI_CLOUD,
    "anthropic": DEFAULT_MODEL_ANTHROPIC,
    "ollama": DEFAULT_MODEL,
}


def resolve_model(provider: str, model: str | None) -> str:
    """Return the explicit model, or the provider's default."""
    return model or PROVIDER_DEFAULT_MODEL[provider]

# Matches the YAML front-matter block at the top of olmOCR-2 output.
OLMOCR_FRONTMATTER_RE = re.compile(r"\A\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Fonts that signal a PDF whose only text layer was added by Tesseract/ABBYY OCR.
OCR_FONT_MARKERS = ("GlyphLessFont", "Tesseract", "OCR")

FIGURE_LABELS = {"figure", "image", "table", "plate", "picture"}

# Common raster image extensions handled as single-page documents.
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}

GROUNDING_RE = re.compile(
    r"<\|ref\|>(?P<label>[^<]+?)<\|/ref\|>\s*<\|det\|>\[\[(?P<box>[^\]]+)\]\]<\|/det\|>"
)
# Non-figure refs we want to strip while keeping their inner text (the model
# sometimes wraps headings/paragraphs in <|ref|>...<|/ref|><|det|>...).
PLAIN_REF_RE = re.compile(
    r"<\|ref\|>(?P<inner>[^<]*?)<\|/ref\|>\s*<\|det\|>\[\[[^\]]+\]\]<\|/det\|>"
)
# DeepSeek-OCR-2 (vLLM) grounding format: lines like "text[[x,y,x2,y2], ...]"
# or "sub_title[[x,y,x2,y2]]" preceding the actual OCR'd text.
# Strip them — docling already provides layout.
DEEPSEEK_OCR2_GROUNDING_RE = re.compile(
    r"^[a-z_]+\[\[[\d,\s\[\]]+\]\]\n?",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


@dataclass
class Classification:
    is_digital: bool
    reason: str
    signals: dict = field(default_factory=dict)


def is_native_digital(pdf_path: Path) -> Classification:
    """Heuristic: born-digital (extractable text layer) vs. needs OCR."""
    doc = fitz.open(pdf_path)
    try:
        # Skip the first 2 pages — frequently cover/wrapper pages that distort
        # the body of the document.
        body_start = 2 if doc.page_count > 4 else 0
        body_pages = list(range(body_start, doc.page_count))
        if len(body_pages) <= 10:
            idx = body_pages
        else:
            step = len(body_pages) / 10
            idx = sorted({body_pages[int(i * step)] for i in range(10)})
        ocr_font_pages = 0
        empty_font_pages = 0
        full_image_pages = 0
        text_lengths: list[int] = []
        suspicious_text_pages = 0

        for i in idx:
            page = doc[i]
            fonts = page.get_fonts()
            font_names = [f[3] or "" for f in fonts]
            if not font_names:
                empty_font_pages += 1
            if any(any(m in fn for m in OCR_FONT_MARKERS) for fn in font_names):
                ocr_font_pages += 1

            page_area = page.rect.width * page.rect.height
            img_area = 0.0
            for img in page.get_images(full=True):
                xref = img[0]
                try:
                    bboxes = page.get_image_rects(xref)
                except Exception:
                    bboxes = []
                for b in bboxes:
                    img_area += abs(b.width * b.height)
            if page_area > 0 and (img_area / page_area) >= 0.85:
                full_image_pages += 1

            text = page.get_text("text") or ""
            text_lengths.append(len(text.strip()))
            # crude garbled-text signals
            if text:
                bad = sum(text.count(c) for c in ("�",))
                ones = sum(1 for w in text.split() if len(w) == 1 and w.isalpha())
                if bad > 5 or (len(text) > 200 and ones / max(1, len(text.split())) > 0.4):
                    suspicious_text_pages += 1

        n = len(idx)
        avg_text = sum(text_lengths) / max(1, n)
        signals = {
            "sampled_pages": n,
            "ocr_font_pages": ocr_font_pages,
            "empty_font_pages": empty_font_pages,
            "full_image_pages": full_image_pages,
            "suspicious_text_pages": suspicious_text_pages,
            "avg_text_chars": round(avg_text, 1),
        }

        if ocr_font_pages >= max(1, n // 3):
            return Classification(False, "OCR-marker fonts present", signals)
        if empty_font_pages == n:
            return Classification(False, "no embedded fonts on any sampled page", signals)
        if full_image_pages >= max(2, 0.4 * n):
            return Classification(
                False, "body pages contain page-sized images (scanned)", signals
            )
        if avg_text < 100:
            return Classification(False, "very little extractable text", signals)
        if suspicious_text_pages >= max(1, n // 2):
            return Classification(False, "extracted text looks garbled", signals)
        return Classification(True, "born-digital text layer", signals)
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_page(page: fitz.Page, dpi: int, out_path: Path) -> tuple[int, int]:
    """Render a PDF page to PNG at dpi; return (width, height) of the PNG."""
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(out_path)
    return pix.width, pix.height


def _resize_longest(img: Image.Image, target: int) -> Image.Image:
    """Resize img so the longest side equals target (preserve aspect)."""
    w, h = img.size
    longest = max(w, h)
    if longest == target:
        return img
    scale = target / longest
    new_size = (max(1, round(w * scale)), max(1, round(h * scale)))
    return img.resize(new_size, Image.LANCZOS)


def _img_to_b64_png(image: "Path | Image.Image") -> str:
    """Base64-encode an image (Path or PIL Image) as PNG."""
    if isinstance(image, Path):
        return base64.b64encode(image.read_bytes()).decode("ascii")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# OCR backends
# ---------------------------------------------------------------------------


def call_ollama_ocr(
    image: "Path | Image.Image",
    host: str,
    model: str = DEFAULT_MODEL,
    prompt: str = OCR_PROMPT,
    timeout: float = 600.0,
    num_ctx: int = 8192,
) -> dict:
    """POST one image to an Ollama /api/generate endpoint.

    Accepts either a file Path or a PIL Image.
    """
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    url = host.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [_img_to_b64_png(image)],
        "stream": False,
        "options": {"num_ctx": num_ctx},
    }
    t0 = time.time()
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return {
        "model": model,
        "response": data.get("response", ""),
        "done": True,
        "_elapsed_s": round(time.time() - t0, 2),
    }


def call_openai_ocr(
    image: "Path | Image.Image",
    host: str,
    model: str = DEFAULT_MODEL_OPENAI,
    prompt: str = OCR_PROMPT_OPENAI,
    timeout: float = 300.0,
    max_tokens: int = 8192,
    api_key: str | None = None,
) -> dict:
    """POST one image to an OpenAI-compatible /v1/chat/completions endpoint.

    Works against a local server (vLLM, SGLang, LM Studio, llama.cpp) and, when
    `api_key` is set and `host` points at a cloud base URL (e.g.
    https://api.openai.com/v1), against the cloud OpenAI API.

    Accepts either a file Path or a PIL Image. Returns
    {"model", "response", "done", "_elapsed_s"}.
    """
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    url = host.rstrip("/") + "/v1/chat/completions"

    img_b64 = _img_to_b64_png(image)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": max_tokens,
        "stream": False,
    }
    t0 = time.time()
    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    return {
        "model": model,
        "response": text,
        "done": True,
        "_elapsed_s": round(time.time() - t0, 2),
    }


def call_olmocr_openai(
    image: "Path | Image.Image",
    host: str,
    model: str = DEFAULT_MODEL_OLMOCR,
    prompt: str = OCR_PROMPT_OLMOCR,
    timeout: float = 600.0,
    max_tokens: int = 14000,
    target_longest_dim: int = OLMOCR_TARGET_LONGEST_DIM,
    api_key: str | None = None,
) -> dict:
    """POST a page image to olmOCR-2 via an OpenAI-compatible vLLM endpoint.

    Resizes the image so its longest dimension equals target_longest_dim
    (1288 by default, matching olmOCR-2 training). Returns
    {"model","response","done","_elapsed_s"}.
    """
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    url = host.rstrip("/") + "/v1/chat/completions"

    if isinstance(image, Path):
        with Image.open(image) as im:
            img = _resize_longest(im.convert("RGB"), target_longest_dim)
    else:
        img = _resize_longest(image.convert("RGB"), target_longest_dim)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        # olmOCR-2 can run away on repetitive typographic patterns (dotted
        # leaders, section-break rules) until it hits max_tokens. Ban long
        # runs of each so the model is forced to emit the next real token.
        # 21 dots for leaders (observed runaway); 30 for everything else
        # (safety net for pathological cases only — well above any
        # legitimate typesetting in scientific monographs).
        "bad_words": [
            " . . . . . . . . . . . . . . . . . . . . .",     # 21 spaced dots — dotted leader
            ".....................",                          # 21 unspaced dots
            "—" * 30,                                     # em-dash rule
            "-" * 30,                                          # hyphen rule
            "_" * 30,                                          # underscore rule
            "*" * 30,                                          # asterisk break
            "* " * 30,                                         # spaced asterisks
            "=" * 30,                                          # equals rule
        ],
        "stream": False,
    }
    t0 = time.time()
    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    return {
        "model": model,
        "response": text,
        "done": True,
        "_elapsed_s": round(time.time() - t0, 2),
    }


def call_anthropic_ocr(
    image: "Path | Image.Image",
    model: str = DEFAULT_MODEL_ANTHROPIC,
    prompt: str = OCR_PROMPT_GENERIC,
    api_key: str | None = None,
    timeout: float = 300.0,
    max_tokens: int = 8192,
) -> dict:
    """OCR one image with Claude via the Anthropic cloud API.

    Requires an API key (argument or ANTHROPIC_API_KEY env var) and the
    `anthropic` package. Returns the same dict shape as the other callers.
    """
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"), timeout=timeout)
    img_b64 = _img_to_b64_png(image)
    t0 = time.time()
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    text = "".join(block.text for block in msg.content if getattr(block, "type", None) == "text")
    return {
        "model": model,
        "response": text,
        "done": True,
        "_elapsed_s": round(time.time() - t0, 2),
    }


def strip_olmocr_frontmatter(text: str) -> tuple[str, dict]:
    """Split olmOCR-2 YAML front matter off the response.

    Returns (body_text, frontmatter_dict). If no front matter is present
    the body is returned unchanged and the dict is empty.
    """
    m = OLMOCR_FRONTMATTER_RE.match(text)
    if not m:
        return text.strip(), {}
    fm: dict = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    body = text[m.end():].strip()
    return body, fm


# ---------------------------------------------------------------------------
# Grounding parsing (DeepSeek-OCR figure crops)
# ---------------------------------------------------------------------------


def _parse_box(box_str: str) -> tuple[int, int, int, int]:
    parts = [p.strip() for p in box_str.split(",")]
    nums = [int(float(p)) for p in parts[:4]]
    return tuple(nums)  # type: ignore[return-value]


def crop_figures_from_grounding(
    markdown: str,
    page_png: Path,
    figures_dir: Path,
    page_num: int,
) -> tuple[str, list[dict]]:
    """Replace figure grounding tokens with markdown image links + save crops.

    Returns (rewritten_markdown, list of figure metadata dicts with bbox in
    page-png pixel coords).
    """
    figures_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(page_png)
    W, H = img.size
    figures: list[dict] = []
    counter = [0]

    def _replace(m: re.Match) -> str:
        label = m.group("label").strip().lower()
        try:
            x1, y1, x2, y2 = _parse_box(m.group("box"))
        except Exception:
            return m.group(0)

        # DeepSeek-OCR coords are normalized 0..999
        def to_px(v: int, dim: int) -> int:
            return max(0, min(dim, round(v / 999 * dim)))

        px = (to_px(x1, W), to_px(y1, H), to_px(x2, W), to_px(y2, H))
        if label in FIGURE_LABELS and px[2] > px[0] and px[3] > px[1]:
            counter[0] += 1
            fname = f"fig_p{page_num:04d}_{counter[0]:02d}.png"
            fpath = figures_dir / fname
            img.crop(px).save(fpath)
            figures.append(
                {
                    "label": label,
                    "page": page_num,
                    "bbox_px": px,
                    "path": str(fpath.relative_to(figures_dir.parent)),
                    "source": "deepseek",
                }
            )
            rel = fpath.relative_to(figures_dir.parent)
            return f"![{label}]({rel.as_posix()})"
        # Non-figure ref (title/text/sub_title/etc.): drop the wrapper entirely;
        # the actual content follows the token on the next line.
        return ""

    rewritten = GROUNDING_RE.sub(_replace, markdown)
    rewritten = PLAIN_REF_RE.sub("", rewritten)
    rewritten = re.sub(r"\n{3,}", "\n\n", rewritten)
    return rewritten, figures


# ---------------------------------------------------------------------------
# Digital extraction (born-digital PDFs, no server needed)
# ---------------------------------------------------------------------------


def extract_digital_markdown(
    pdf_path: Path,
    figures_dir: Path,
) -> tuple[list[str], int]:
    """Convert a born-digital PDF to per-page markdown with figure crops.

    Uses pymupdf4llm for structured text (headings, tables, italic) and
    pymupdf directly for embedded raster figures.

    Returns (list_of_page_markdown_blocks, figure_count).
    """
    import pymupdf4llm

    figures_dir.mkdir(parents=True, exist_ok=True)
    chunks = pymupdf4llm.to_markdown(
        str(pdf_path),
        page_chunks=True,
        write_images=False,
        ignore_images=True,
        ignore_graphics=True,
        show_progress=False,
    )

    doc = fitz.open(pdf_path)
    blocks: list[str] = []
    figure_count = 0
    try:
        for i, ch in enumerate(chunks):
            text = ch.get("text", "") if isinstance(ch, dict) else str(ch)
            if i < doc.page_count:
                page = doc[i]
                page_area = page.rect.width * page.rect.height
                appended: list[str] = []
                for k, img in enumerate(page.get_images(full=True), start=1):
                    xref = img[0]
                    try:
                        rects = page.get_image_rects(xref)
                    except Exception:
                        rects = []
                    # Skip page-sized images (cover/back wrappers, scan backgrounds).
                    if page_area > 0 and any(
                        abs(r.width * r.height) > 0.70 * page_area for r in rects
                    ):
                        continue
                    try:
                        info = doc.extract_image(xref)
                    except Exception:
                        continue
                    ext = info.get("ext", "png")
                    fname = f"fig_p{i + 1:04d}_{k:02d}.{ext}"
                    fpath = figures_dir / fname
                    fpath.write_bytes(info["image"])
                    rel = fpath.relative_to(figures_dir.parent).as_posix()
                    appended.append(f"![figure]({rel})")
                    figure_count += 1
                if appended:
                    text = text.rstrip() + "\n\n" + "\n\n".join(appended) + "\n"
            blocks.append(text)
    finally:
        doc.close()
    return blocks, figure_count


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

# Candidate languages for per-page detection. Extend as needed for your corpus.
LANGUAGES = (
    "ENGLISH",
    "FRENCH",
    "GERMAN",
    "LATIN",
    "PORTUGUESE",
    "SPANISH",
    "ITALIAN",
)

_DETECTOR = None


def _get_detector():
    global _DETECTOR
    if _DETECTOR is None:
        from lingua import Language, LanguageDetectorBuilder

        langs = [getattr(Language, name) for name in LANGUAGES]
        _DETECTOR = LanguageDetectorBuilder.from_languages(*langs).build()
    return _DETECTOR


def detect_language(text: str) -> str | None:
    text = (text or "").strip()
    if len(text) < 40:
        return None
    try:
        det = _get_detector()
        lang = det.detect_language_of(text)
        if lang is None:
            return None
        return lang.iso_code_639_1.name.lower()
    except Exception:
        return None


def detect_languages_per_page(
    page_texts: list[str],
    first_n: int = 10,
    sample_total: int = 20,
) -> tuple[list[str | None], list[dict], str | None]:
    """Detect language per page on a subset of pages, then propagate to neighbors.

    Returns (per_page_lang, ranges, primary).
    """
    n = len(page_texts)
    if n == 0:
        return [], [], None

    sampled: set[int] = set(range(min(first_n, n)))
    remaining_budget = max(0, sample_total - len(sampled))
    if remaining_budget > 0 and n > first_n:
        body_n = n - first_n
        step = max(1, body_n // remaining_budget)
        sampled.update(range(first_n, n, step))

    detections: dict[int, str | None] = {}
    for i in sorted(sampled):
        detections[i] = detect_language(page_texts[i])

    # Propagate: for each page, use nearest sampled detection (forward fill, then back).
    per_page: list[str | None] = [None] * n
    last: str | None = None
    sampled_sorted = sorted(detections)
    j = 0
    for i in range(n):
        while j < len(sampled_sorted) and sampled_sorted[j] <= i:
            last = detections[sampled_sorted[j]] or last
            j += 1
        per_page[i] = last
    # back-fill leading Nones
    first_known = next((x for x in per_page if x), None)
    if first_known:
        for i in range(n):
            if per_page[i] is None:
                per_page[i] = first_known
            else:
                break

    # Collapse to ranges
    ranges: list[dict] = []
    if per_page:
        start = 0
        cur = per_page[0]
        for i in range(1, n):
            if per_page[i] != cur:
                ranges.append({"lang": cur, "pages": f"{start + 1}-{i}"})
                start = i
                cur = per_page[i]
        ranges.append({"lang": cur, "pages": f"{start + 1}-{n}"})

    counts: dict[str, int] = {}
    for lang in per_page:
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    primary = max(counts, key=counts.get) if counts else None
    return per_page, ranges, primary


# ---------------------------------------------------------------------------
# Stitching
# ---------------------------------------------------------------------------


def stitch_markdown(
    out_md: Path,
    source: Path,
    classification: Classification,
    model: str | None,
    dpi: int | None,
    page_blocks: list[str],
    language_ranges: list[dict] | None,
    language_primary: str | None,
    backend: str | None = None,
) -> None:
    """Write the per-document markdown file with a YAML frontmatter header."""
    import yaml  # pyyaml is in env

    front = {
        "source": str(source),
        "classification": "digital" if classification.is_digital else "needs_ocr",
        "classification_reason": classification.reason,
        "classification_signals": classification.signals,
        "page_count": len(page_blocks),
        "backend": backend,
        "model": model if not classification.is_digital else None,
        "dpi": dpi if not classification.is_digital else None,
        "language_primary": language_primary,
        "languages_detected": language_ranges or [],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    out_md.parent.mkdir(parents=True, exist_ok=True)
    with out_md.open("w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.safe_dump(front, f, allow_unicode=True, sort_keys=False)
        f.write("---\n\n")
        for i, block in enumerate(page_blocks, start=1):
            f.write(f"<!-- page {i} -->\n\n")
            f.write(block.rstrip())
            f.write("\n\n---\n\n")
