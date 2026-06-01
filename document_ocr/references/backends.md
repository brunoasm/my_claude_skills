# OCR backends

This skill separates two concerns:

1. **Layout** — docling detects figures, tables, and reading order on the page.
2. **Text OCR** — a vision-language model (VLM) transcribes the page to markdown.

The `--backend` flag picks a combination. All backends except born-digital
extraction require an OCR server or cloud key that you supply (see
`server_setup.md`).

## Backend matrix

| `--backend`        | Layout (figures) | Text OCR model            | Needs        | Notes |
|--------------------|------------------|---------------------------|--------------|-------|
| `olmocr-docling` ★ | docling          | olmOCR-2 (full page) via vLLM | `--host`     | **Recommended.** Best text + figures on the pilot corpus. |
| `vlm-docling`      | docling          | any VLM (full page) via an OpenAI-compatible endpoint | `--host` (+ `--api-key` for cloud) | Use any vLLM/SGLang/LM-Studio model, or cloud OpenAI by pointing `--host` at `https://api.openai.com/v1`. |
| `anthropic-docling`| docling          | Claude (full page) via Anthropic cloud | `--api-key` / `ANTHROPIC_API_KEY` | No local GPU needed. |
| `ollama`           | none (full page) | DeepSeek-OCR via Ollama   | `--host`     | Backup; weaker figure detection. Figures come from grounding tokens, not docling. |
| `docling`          | docling          | per-region OCR via an OpenAI-compatible endpoint | `--host`     | OCRs each text region separately. Weaker on multi-column; kept for completeness. |

★ default and recommended.

## Why full-page beats per-region

On the pilot corpus (historical entomology monographs, 1833–2015), pure
**docling + per-region OCR** (the `docling` backend) caused *catastrophic
content loss on multi-column layouts* — region cropping breaks reading order and
drops text. **Full-page transcription** (`olmocr-docling`) preserves multi-column
reading order, two-page spreads, diacritics, ligatures, and special characters
(♂ ♀ ½ æ, Greek/Latin), while docling supplies reliable figure crops. Prefer the
full-page family (`olmocr-docling`, `vlm-docling`, `anthropic-docling`).

## Choosing a model (`--model`)

Defaults per backend:

- `olmocr-docling` → `allenai/olmOCR-2-7B-1025-FP8`
- `vlm-docling`    → `deepseek-ai/DeepSeek-OCR-2` (override to your served model)
- `anthropic-docling` → `claude-sonnet-4-6`
- `ollama`         → `deepseek-ocr:3b`
- `docling`        → `deepseek-ai/DeepSeek-OCR-2`

For `vlm-docling` against a cloud OpenAI endpoint, pass
`--host https://api.openai.com/v1 --api-key … --model gpt-4o`.

## Tuning notes

- **DPI** (`--dpi`, default 200): higher DPI = sharper crops but slower and
  larger images. 150–200 is a good range for most scans.
- **olmOCR-2 image size**: pages are resized so the longest dimension is **1288
  px**, matching olmOCR-2's training. Don't change this unless you know the
  model was trained differently.
- **Runaway repetition guard** (olmOCR-2): the vLLM payload bans long runs of
  dotted leaders / rules (`bad_words`) so the model can't loop forever on a
  table-of-contents dotted line. If you see runaway output on other repetitive
  glyphs, add them to the `bad_words` list in `ocr_utils.call_olmocr_openai`.
- **Caption regex**: figures are inlined above lines matching `Fig.`/`Figure`/
  `Plate`/`Pl.` (see `_CAPTION_RE` in `docling_pipeline.py`). Adjust for corpora
  using other caption conventions.
- **Languages**: per-page language detection uses the `LANGUAGES` tuple in
  `ocr_utils.py` (English, French, German, Latin, Portuguese, Spanish, Italian).
  Add entries for other languages.

## Cloud vs. local trade-offs

- **Local (vLLM/Ollama)**: no per-page cost, data stays on your hardware, but
  needs a GPU server you maintain. Best for large corpora and sensitive material.
- **Cloud (Anthropic/OpenAI)**: no GPU needed, pay per page, data leaves your
  machine. Best for one-off jobs or when no GPU server is available. Do not send
  confidential documents to a cloud API without authorization.
