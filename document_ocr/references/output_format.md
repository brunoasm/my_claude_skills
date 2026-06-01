# Output format

For each input document, the tool creates a folder under `--output-dir` named
after the file stem:

```
out/
└── <stem>/
    ├── <stem>.md          # main output: markdown with frontmatter + inlined figures
    ├── cache/
    │   └── page_0001.json # per-page cache (model, backend, response, frontmatter, timing)
    ├── figures/
    │   └── fig_p0001_01.png  # cropped figures (docling layout, or grounding for ollama)
    └── pages/
        └── page_0001.png  # rendered page images (scanned PDFs / images)
```

## The markdown file

A YAML frontmatter header followed by per-page blocks separated by `<!-- page N -->`
markers and `---` rules:

```markdown
---
source: /path/to/input.pdf
classification: needs_ocr        # or "digital" (born-digital fast path)
classification_reason: no embedded fonts on any sampled page
classification_signals:
  sampled_pages: 3
  ocr_font_pages: 0
  empty_font_pages: 3
  full_image_pages: 3
  suspicious_text_pages: 0
  avg_text_chars: 0.0
page_count: 3
backend: anthropic-docling       # or "born-digital" for the digital fast path
model: claude-sonnet-4-6         # null for born-digital
dpi: 150                         # null for born-digital / images
language_primary: en
languages_detected:
  - lang: en
    pages: "1-3"
generated_at: 2026-06-01T12:08:26-0500
---

<!-- page 1 -->

# Document title

...page 1 markdown, with figures inlined above their captions...

![figure](figures/fig_p0001_01.png)

---

<!-- page 2 -->
...
```

## Frontmatter fields

| Field | Meaning |
|-------|---------|
| `source` | Path to the input file. |
| `classification` | `digital`, `needs_ocr`, or `needs_ocr`/`image input` for images. |
| `classification_reason` / `_signals` | Why the classifier chose the path (PDFs). |
| `page_count` | Number of pages. |
| `backend` | Backend used (`born-digital` when the digital fast path ran). |
| `model` | OCR model name; `null` for born-digital. |
| `dpi` | Render DPI for scanned input; `null` for born-digital. |
| `language_primary` / `languages_detected` | Per-page language detection (lingua). |

## Caching and re-runs

Each page's OCR result is cached in `cache/page_NNNN.json`. Re-running reuses the
cache (cheap), so you can iterate on stitching/figures without re-paying for OCR.
Pass `--force` to ignore the cache and re-OCR every page. **Pages that failed**
(timeout, server error, content filter) are *not* cached — they show a
`<!-- OCR failed for page N: ... -->` placeholder and are retried on the next run.

## Figures

- **docling backends** (`olmocr-docling`, `vlm-docling`, `anthropic-docling`,
  `docling`): figures and pictures are detected by docling, cropped from the
  rendered page, and inlined in the markdown immediately above the matching
  caption line (`Fig.`/`Figure`/`Plate`/`Pl.`). Figures with no matching caption
  are appended at the end of the page block.
- **ollama backend**: figures come from DeepSeek-OCR grounding tokens instead.
