"""Layout-aware OCR pipeline: docling for figures/tables + a VLM for text.

Docling's DocLayNet model detects text blocks, pictures, and tables with
correct multi-column reading order. Two strategies are provided:

- process_scanned_docling: OCR each text region separately (DeepSeek-OCR-style).
- process_scanned_olmocr_docling: docling supplies figure/table crops only, and
  a full-page VLM (olmOCR-2 by default, but any provider) transcribes the page.
  This is the recommended path — full-page transcription preserves multi-column
  reading order far better than per-region OCR.

A standalone image is handled by process_image(), which treats it as one page.

The `provider` argument selects the OCR backend:
  "vllm-olmocr" -> call_olmocr_openai (OpenAI-compatible vLLM, olmOCR-2)
  "vllm"        -> call_openai_ocr    (OpenAI-compatible vLLM, generic VLM)
  "openai"      -> call_openai_ocr    (cloud OpenAI, needs api_key)
  "anthropic"   -> call_anthropic_ocr (cloud Claude, needs api_key)
  "ollama"      -> call_ollama_ocr    (Ollama server)

Adapted from Bruno de Medeiros' OntoMorphoGrapher proof-of-concept.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from PIL import Image


def _bbox_to_pil_crop(
    bbox,
    page_height_pts: float,
    scale: float,
    img_w: int,
    img_h: int,
) -> tuple[int, int, int, int]:
    """Convert a docling BoundingBox to PIL crop coords (l, t, r, b) in pixels."""
    from docling_core.types.doc import CoordOrigin

    if bbox.coord_origin == CoordOrigin.BOTTOMLEFT:
        bbox = bbox.to_top_left_origin(page_height_pts)
    l = max(0, int(bbox.l * scale))
    t = max(0, int(bbox.t * scale))
    r = min(img_w, int(bbox.r * scale))
    b = min(img_h, int(bbox.b * scale))
    return l, t, r, b


# Matches figure caption openings as they appear in scientific/technical docs:
# "Fig. 23", "Figure 1", "FIG. 4", "Figs. 1-3", "Plate II", "Pl. 5".
# Anchored at line start to avoid matching in-text mentions like "see Fig. 5".
# Tune this for your corpus if captions use other conventions.
_CAPTION_RE = re.compile(
    r"(?im)^[\s>*_-]*(?:Fig(?:ure|s)?|FIG(?:URE|S)?|Plate|Pl)\.?\s*[\dIVXLCM]+"
)


def _inline_figures_at_captions(text: str, figure_md_list: list[str]) -> str:
    """Insert each figure markdown line above a matching caption in text.

    Figures left over after captions are exhausted are appended at the end.
    """
    if not figure_md_list:
        return text.strip()
    if not text:
        return "\n\n".join(figure_md_list)

    lines = text.split("\n")
    caption_idxs = [i for i, ln in enumerate(lines) if _CAPTION_RE.match(ln)]

    figs_remaining = list(figure_md_list)
    inserts: list[tuple[int, str]] = []
    for ci in caption_idxs:
        if not figs_remaining:
            break
        inserts.append((ci, figs_remaining.pop(0)))

    # Insert from the bottom so earlier indices stay valid.
    for ci, fig in reversed(inserts):
        lines.insert(ci, "")
        lines.insert(ci, fig)

    body = "\n".join(lines).strip()
    if figs_remaining:
        body = body + "\n\n" + "\n\n".join(figs_remaining)
    return body


def make_fullpage_fn(
    provider: str,
    host: str | None,
    model: str | None,
    api_key: str | None = None,
    prompt: str | None = None,
) -> Callable[["Image.Image | Path"], dict]:
    """Build a callable img -> {"response", ...} for the chosen provider.

    Returns the full result dict (so callers can read frontmatter/elapsed).
    """
    import ocr_utils as ou

    if provider == "vllm-olmocr":
        m = model or ou.DEFAULT_MODEL_OLMOCR
        p = prompt or ou.OCR_PROMPT_OLMOCR
        return lambda img: ou.call_olmocr_openai(img, host=host, model=m, prompt=p, api_key=api_key)
    if provider == "vllm":
        m = model or ou.DEFAULT_MODEL_OPENAI
        p = prompt or ou.OCR_PROMPT_GENERIC
        return lambda img: ou.call_openai_ocr(img, host=host, model=m, prompt=p, api_key=api_key)
    if provider == "openai":
        m = model or ou.DEFAULT_MODEL_OPENAI_CLOUD
        p = prompt or ou.OCR_PROMPT_GENERIC
        base = host or "https://api.openai.com/v1"
        return lambda img: ou.call_openai_ocr(img, host=base, model=m, prompt=p, api_key=api_key)
    if provider == "anthropic":
        m = model or ou.DEFAULT_MODEL_ANTHROPIC
        p = prompt or ou.OCR_PROMPT_GENERIC
        return lambda img: ou.call_anthropic_ocr(img, model=m, prompt=p, api_key=api_key)
    if provider == "ollama":
        m = model or ou.DEFAULT_MODEL
        p = prompt or ou.OCR_PROMPT
        return lambda img: ou.call_ollama_ocr(img, host=host, model=m, prompt=p)
    raise ValueError(f"unknown provider: {provider}")


def _safe_fullpage(fullpage_fn, page_img, cache_file: Path, provider: str,
                   model: str | None, page_no: int) -> str:
    """Run the full-page OCR call; on failure, log and return a placeholder.

    A single page that errors (timeout, server 5xx, content-filter 4xx, ...)
    must not abort the whole document. Failed pages are NOT cached, so a re-run
    retries them. Successful pages are cached.
    """
    import json
    import sys
    import ocr_utils as ou

    try:
        resp = fullpage_fn(page_img)
    except Exception as e:
        print(f"  [warn] OCR failed for page {page_no}: {e}", file=sys.stderr)
        return f"<!-- OCR failed for page {page_no}: {type(e).__name__} -->"

    raw = resp.get("response", "")
    body, frontmatter = ou.strip_olmocr_frontmatter(raw)
    cache_file.write_text(json.dumps({
        "model": resp.get("model", model),
        "backend": f"docling+{provider}",
        "response": body,
        "raw": raw,
        "frontmatter": frontmatter,
        "_elapsed_s": resp.get("_elapsed_s"),
    }, indent=2))
    return body


def _ocr_region(
    crop: Image.Image,
    ocr_fn: Callable[[Image.Image], str],
    min_dim: int = 32,
) -> str:
    """OCR a PIL Image crop; returns plain text.

    Regions smaller than min_dim in either axis are skipped (too small to
    contain readable text). Docling's layout classification is trusted for
    everything else — no area-based filtering.
    """
    import ocr_utils as ou

    if crop.width < min_dim or crop.height < min_dim:
        return ""

    try:
        raw = ocr_fn(crop)
    except Exception as e:
        import sys
        print(f"  [warn] OCR region failed ({crop.width}x{crop.height}px): {e}", file=sys.stderr)
        return ""

    text = ou.GROUNDING_RE.sub("", raw)
    text = ou.PLAIN_REF_RE.sub("", text)
    text = ou.DEEPSEEK_OCR2_GROUNDING_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _docling_converter():
    """A docling DocumentConverter configured for layout-only PDF/image parsing.

    Registers both PDF and IMAGE formats with `device="cpu"`: docling's layout
    model uses float64, which Apple MPS does not support, so CPU is required.
    """
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions
    from docling.datamodel.base_models import InputFormat

    opts = PdfPipelineOptions()
    opts.do_ocr = False             # we supply OCR via the VLM
    opts.do_table_structure = True  # TableFormer for structured tables
    opts.generate_page_images = False  # we render our own at higher DPI
    opts.accelerator_options = AcceleratorOptions(device="cpu")  # MPS lacks float64
    # Images are routed through the same standard (PDF) pipeline in docling.
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=opts),
            InputFormat.IMAGE: PdfFormatOption(pipeline_options=opts),
        }
    )


def process_scanned_docling(
    pdf_path: Path,
    out_dir: Path,
    provider: str,
    host: str | None,
    model: str | None,
    dpi: int = 200,
    force: bool = False,
    api_key: str | None = None,
) -> tuple[list[str], int]:
    """Docling layout + per-region OCR. Returns (page_blocks, n_figures)."""
    import fitz  # pymupdf
    import ocr_utils as ou

    figures_dir = out_dir / "figures"
    pages_dir = out_dir / "pages"
    cache_dir = out_dir / "cache"
    for d in (figures_dir, pages_dir, cache_dir):
        d.mkdir(parents=True, exist_ok=True)

    conv = _docling_converter()
    result = conv.convert(str(pdf_path))
    doc = result.document

    page_index: dict[int, dict[str, list]] = {}

    def _get_page(pno: int) -> dict[str, list]:
        if pno not in page_index:
            page_index[pno] = {"texts": [], "pictures": [], "tables": []}
        return page_index[pno]

    for item in doc.texts:
        for prov in item.prov:
            _get_page(prov.page_no)["texts"].append((prov.bbox, item))
    for item in doc.pictures:
        for prov in item.prov:
            _get_page(prov.page_no)["pictures"].append((prov.bbox, item))
    for item in doc.tables:
        for prov in item.prov:
            _get_page(prov.page_no)["tables"].append((prov.bbox, item))

    scale = dpi / 72.0
    n_pages = len(result.pages)
    page_blocks: list[str] = [""] * n_pages
    n_figures = 0

    doc_fitz = fitz.open(str(pdf_path))

    raw_fn = make_fullpage_fn(provider, host, model, api_key)
    ocr_fn = lambda img: raw_fn(img).get("response", "")  # noqa: E731

    for page_result in result.pages:
        page_no = page_result.page_no
        idx = page_no - 1

        page_png = pages_dir / f"page_{page_no:04d}.png"
        if not page_png.exists() or force:
            ou.render_page(doc_fitz[idx], dpi, page_png)
        page_img = Image.open(page_png)
        img_w, img_h = page_img.size
        page_height_pts = page_result.size.height if page_result.size else (img_h / scale)

        elements = page_index.get(page_no, {"texts": [], "pictures": [], "tables": []})
        cache_file = cache_dir / f"page_{page_no:04d}.json"

        # pictures: crop + save
        pic_counter = 0
        picture_parts: list[str] = []
        for bbox, _ in elements["pictures"]:
            box = _bbox_to_pil_crop(bbox, page_height_pts, scale, img_w, img_h)
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            pic_counter += 1
            n_figures += 1
            fname = f"fig_p{page_no:04d}_{pic_counter:02d}.png"
            fpath = figures_dir / fname
            page_img.crop(box).save(fpath)
            rel = fpath.relative_to(out_dir).as_posix()
            picture_parts.append(f"![figure]({rel})")

        # tables: docling markdown export
        table_parts: list[str] = []
        for _bbox, tbl_item in elements["tables"]:
            try:
                tbl_md = tbl_item.export_to_markdown()
            except Exception:
                tbl_md = ""
            if tbl_md.strip():
                table_parts.append(tbl_md)

        # text blocks: OCR each region (use cache when available)
        if cache_file.exists() and not force:
            cached = json.loads(cache_file.read_text())
            texts_ocr = cached.get("texts_ocr", [])
        else:
            texts_ocr = []
            for bbox, _ in elements["texts"]:
                box = _bbox_to_pil_crop(bbox, page_height_pts, scale, img_w, img_h)
                if box[2] <= box[0] or box[3] <= box[1]:
                    texts_ocr.append("")
                    continue
                crop = page_img.crop(box)
                texts_ocr.append(_ocr_region(crop, ocr_fn))
            cache_file.write_text(
                json.dumps(
                    {"model": model, "backend": f"docling+{provider}", "texts_ocr": texts_ocr},
                    indent=2,
                )
            )

        parts = picture_parts + table_parts + [t for t in texts_ocr if t]
        page_blocks[idx] = "\n\n".join(parts)

    doc_fitz.close()
    return page_blocks, n_figures


def process_scanned_olmocr_docling(
    pdf_path: Path,
    out_dir: Path,
    provider: str,
    host: str | None,
    model: str | None,
    dpi: int = 200,
    force: bool = False,
    api_key: str | None = None,
) -> tuple[list[str], int]:
    """Docling for figures/tables + a full-page VLM for text (recommended).

    Despite the name, `provider` may be any full-page backend (vllm-olmocr,
    vllm, openai, anthropic, ollama). olmOCR-2 over vLLM is the default and
    best-performing on the pilot corpus.
    """
    import fitz
    import ocr_utils as ou

    figures_dir = out_dir / "figures"
    pages_dir = out_dir / "pages"
    cache_dir = out_dir / "cache"
    for d in (figures_dir, pages_dir, cache_dir):
        d.mkdir(parents=True, exist_ok=True)

    conv = _docling_converter()
    result = conv.convert(str(pdf_path))
    doc = result.document

    page_index: dict[int, dict[str, list]] = {}

    def _get_page(pno: int) -> dict[str, list]:
        if pno not in page_index:
            page_index[pno] = {"pictures": [], "tables": []}
        return page_index[pno]

    for item in doc.pictures:
        for prov in item.prov:
            _get_page(prov.page_no)["pictures"].append((prov.bbox, item))
    for item in doc.tables:
        for prov in item.prov:
            _get_page(prov.page_no)["tables"].append((prov.bbox, item))

    scale = dpi / 72.0
    n_pages = len(result.pages)
    page_blocks: list[str] = [""] * n_pages
    n_figures = 0

    doc_fitz = fitz.open(str(pdf_path))
    fullpage_fn = make_fullpage_fn(provider, host, model, api_key)

    for page_result in result.pages:
        page_no = page_result.page_no
        idx = page_no - 1

        page_png = pages_dir / f"page_{page_no:04d}.png"
        if not page_png.exists() or force:
            ou.render_page(doc_fitz[idx], dpi, page_png)
        page_img = Image.open(page_png)
        img_w, img_h = page_img.size
        page_height_pts = page_result.size.height if page_result.size else (img_h / scale)

        elements = page_index.get(page_no, {"pictures": [], "tables": []})
        cache_file = cache_dir / f"page_{page_no:04d}.json"

        # pictures from docling layout
        pic_counter = 0
        picture_parts: list[str] = []
        for bbox, _ in elements["pictures"]:
            box = _bbox_to_pil_crop(bbox, page_height_pts, scale, img_w, img_h)
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            pic_counter += 1
            n_figures += 1
            fname = f"fig_p{page_no:04d}_{pic_counter:02d}.png"
            fpath = figures_dir / fname
            page_img.crop(box).save(fpath)
            rel = fpath.relative_to(out_dir).as_posix()
            picture_parts.append(f"![figure]({rel})")

        # text: full-page VLM (tables come back inline as HTML per the prompt)
        if cache_file.exists() and not force:
            cached = json.loads(cache_file.read_text())
            text_md = cached.get("response", "")
        else:
            text_md = _safe_fullpage(fullpage_fn, page_img, cache_file, provider, model, page_no)

        page_blocks[idx] = _inline_figures_at_captions(text_md, picture_parts)

    doc_fitz.close()
    return page_blocks, n_figures


def process_image(
    img_path: Path,
    out_dir: Path,
    provider: str,
    host: str | None,
    model: str | None,
    dpi: int = 200,  # accepted for signature parity; unused for raster images
    force: bool = False,
    api_key: str | None = None,
    use_docling: bool = True,
) -> tuple[list[str], int]:
    """OCR a standalone image as a single page.

    When use_docling is True, docling detects figure crops on the image; the
    full-page VLM transcribes the text. When False (or if docling fails on the
    image), the VLM alone transcribes the whole image.
    """
    import ocr_utils as ou

    figures_dir = out_dir / "figures"
    pages_dir = out_dir / "pages"
    cache_dir = out_dir / "cache"
    for d in (figures_dir, pages_dir, cache_dir):
        d.mkdir(parents=True, exist_ok=True)

    page_img = Image.open(img_path).convert("RGB")
    img_w, img_h = page_img.size
    page_png = pages_dir / "page_0001.png"
    if not page_png.exists() or force:
        page_img.save(page_png)

    picture_parts: list[str] = []
    n_figures = 0
    if use_docling:
        try:
            conv = _docling_converter()
            result = conv.convert(str(img_path))
            doc = result.document
            scale = 1.0  # docling reports image coords in pixels
            for pic_counter, item in enumerate(doc.pictures, start=1):
                for prov in item.prov:
                    box = _bbox_to_pil_crop(prov.bbox, img_h, scale, img_w, img_h)
                    if box[2] <= box[0] or box[3] <= box[1]:
                        continue
                    n_figures += 1
                    fname = f"fig_p0001_{pic_counter:02d}.png"
                    fpath = figures_dir / fname
                    page_img.crop(box).save(fpath)
                    rel = fpath.relative_to(out_dir).as_posix()
                    picture_parts.append(f"![figure]({rel})")
        except Exception as e:
            import sys
            print(f"  [warn] docling image layout failed, using full-page only: {e}", file=sys.stderr)

    cache_file = cache_dir / "page_0001.json"
    if cache_file.exists() and not force:
        cached = json.loads(cache_file.read_text())
        text_md = cached.get("response", "")
    else:
        fullpage_fn = make_fullpage_fn(provider, host, model, api_key)
        text_md = _safe_fullpage(fullpage_fn, page_img, cache_file, provider, model, 1)

    block = _inline_figures_at_captions(text_md, picture_parts)
    return [block], n_figures
