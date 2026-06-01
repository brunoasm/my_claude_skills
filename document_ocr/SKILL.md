---
name: document-ocr
description: Convert scanned PDFs and document images into clean Markdown using docling for layout (figures, tables, reading order) plus a vision-language OCR model. Use when a user needs high-quality OCR of scanned documents, historical literature, or photographed pages — preserving multi-column reading order, diacritics, special characters, and figures. Supports local vLLM/Ollama servers and cloud vision APIs (OpenAI, Anthropic). Assumes an OCR backend already exists.
---

# Document OCR (docling + vision-language model)

## Purpose

Turn scanned PDFs and document images into clean, structured **Markdown** with
figures preserved. The pipeline combines:

1. **docling** — detects layout (figures, tables, multi-column reading order) on
   each page, entirely on CPU.
2. **A vision-language model (VLM)** — transcribes each full page to Markdown,
   preserving reading order, diacritics, ligatures, special characters (♂ ♀ ½ æ,
   Greek/Latin), equations (LaTeX), and tables (HTML).

docling supplies reliable figure/table crops; the VLM supplies high-quality
text. Born-digital PDFs are detected and extracted directly (no server needed).

Adapted from Bruno de Medeiros' OntoMorphoGrapher proof-of-concept, where the
`olmocr-docling` backend processed an 18-PDF historical-entomology corpus
(1833–2015, 5 languages) with no catastrophic failures.

## When to use this skill

Use when:
- A user has **scanned PDFs or photographed/image pages** needing accurate OCR.
- Figures and multi-column reading order must be preserved.
- The text has diacritics, special characters, or non-English content.

Do **not** use when:
- The PDF is already born-digital and reads fine (this tool handles it via the
  fast path, but you may not need it at all).
- The goal is extracting *structured fields* into a database — that is the
  `extract-from-pdfs` skill, which can run **downstream** of this one.

## ⚠️ Prerequisites — an OCR backend must already exist

**This skill does not start or manage any server. Standing one up is out of
scope.** Before running, the user must have **one** of:

- a running **OpenAI-compatible server** (vLLM/SGLang/LM Studio/llama.cpp) with a
  vision model — best with olmOCR-2 (`--backend olmocr-docling`);
- a running **Ollama** server with a vision OCR model (`--backend ollama`);
- a **cloud API key** — Anthropic (`--backend anthropic-docling`) or OpenAI
  (`--backend vlm-docling` pointed at the OpenAI base URL).

Always **remind the user of this requirement** and confirm which backend they
have. For example setup commands (illustrative, not maintained), see
`references/server_setup.md`. The born-digital PDF fast path needs no backend.

## Setup

```bash
conda env create -f environment.yml
conda activate document_ocr
```

Then make the backend reachable (pick one):

```bash
export OCR_HOST=http://YOUR_HOST:30001     # vLLM / Ollama / OpenAI-compatible
# or
export ANTHROPIC_API_KEY=sk-ant-...        # cloud Claude
# or
export OPENAI_API_KEY=sk-...               # cloud OpenAI
```

## Choosing a backend

| `--backend`        | What it uses                              | Needs |
|--------------------|-------------------------------------------|-------|
| `olmocr-docling` ★ | docling figures + olmOCR-2 (vLLM)         | `--host` |
| `vlm-docling`      | docling figures + any VLM (OpenAI-compat) | `--host` (+ `--api-key` for cloud) |
| `anthropic-docling`| docling figures + Claude (cloud)          | `--api-key` / `ANTHROPIC_API_KEY` |
| `ollama`           | full-page DeepSeek-OCR (Ollama)           | `--host` |
| `docling`          | docling layout + per-region OCR           | `--host` |

★ Recommended. See `references/backends.md` for the full matrix, why full-page
beats per-region OCR, model defaults, and tuning notes.

## Workflow

1. **Confirm the backend** (see Prerequisites). Ask the user which one they have
   and the host/model or API key. Do not assume a server is running.
2. **Gather inputs**: a PDF, an image (`.png/.jpg/.jpeg/.tif/.tiff`), or a
   directory of them. Ask where output should go.
3. **Classify first** (free, no server):
   ```bash
   python scripts/ocr_document.py --input docs/ --dry-run
   ```
   This labels each PDF `DIGITAL` or `NEEDS_OCR` so the user knows what will hit
   the server.
4. **Run OCR**:
   ```bash
   python scripts/ocr_document.py \
       --input docs/ --output-dir out/ \
       --backend olmocr-docling --host "$OCR_HOST" --dpi 200
   ```
   The tool runs a preflight check and fails with a clear message if the backend
   isn't configured. Per-page failures (timeouts, content filters) are skipped
   with a placeholder; the rest of the document still processes.
5. **Review** `out/<stem>/<stem>.md` and the `figures/` crops. Iterate if needed:
   raise `--dpi`, switch `--model`, or adjust the caption regex / `bad_words` /
   language list (see `references/backends.md`).

## Output

Per-document folder with the stitched markdown (`<stem>.md`), a per-page JSON
`cache/`, cropped `figures/`, and rendered `pages/`. Full schema and frontmatter
fields: `references/output_format.md`.

## Communication guidelines

- State up front that a backend is required and is the user's responsibility.
- Before any cloud run, note that pages are sent off-machine and billed per page;
  do not send confidential documents to a cloud API without authorization.
- For large corpora, suggest `--dry-run` first and a small sample before the full
  run, so cost and quality are known before committing.

## Attribution

Pipeline and prompts adapted from Bruno de Medeiros' **OntoMorphoGrapher**
proof-of-concept (docling + olmOCR-2 over vLLM).
