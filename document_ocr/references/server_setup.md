# Setting up an OCR backend (out of scope — examples only)

> **This skill does not start or manage servers.** It assumes a backend is
> already available and reachable. The commands below are *illustrative
> examples* to help you stand one up yourself; they are not maintained or
> guaranteed, and exact flags change between releases. Consult each project's
> own docs.

You need exactly **one** of the following.

## Option A — vLLM serving olmOCR-2 (recommended, needs a GPU)

olmOCR-2 is the best-performing backend (`--backend olmocr-docling`). Serve it
with vLLM's OpenAI-compatible server on a GPU host:

```bash
# On a machine with a CUDA GPU (the FP8 weights need ~16 GB VRAM)
pip install vllm
vllm serve allenai/olmOCR-2-7B-1025-FP8 \
    --port 30001 \
    --max-model-len 16384
```

Then point the skill at it:

```bash
python scripts/ocr_document.py --input docs/ --output-dir out/ \
    --backend olmocr-docling --host http://YOUR_HOST:30001
```

Any OpenAI-compatible server works for `--backend vlm-docling` (vLLM, SGLang,
LM Studio, llama.cpp's server). Set `--model` to whatever the server serves.

> ⚠️ olmOCR-2 (a Qwen2.5-VL fine-tune) is **not viable under Ollama/llama.cpp**:
> there is a known M-RoPE bug for Qwen2.5-VL that crashes or hallucinates. Use
> vLLM for olmOCR-2.

## Option B — Ollama (CPU/GPU, easiest local setup)

```bash
# Install Ollama from https://ollama.com, then:
ollama pull deepseek-ocr:3b
ollama serve            # serves on http://localhost:11434
```

```bash
python scripts/ocr_document.py --input docs/ --output-dir out/ \
    --backend ollama --host http://localhost:11434
```

Weaker on figures than the docling backends, but no GPU server to manage.

## Option C — Cloud vision API (no local GPU)

Set an API key in your environment and use a cloud backend:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/ocr_document.py --input scan.pdf --output-dir out/ \
    --backend anthropic-docling
```

For cloud OpenAI, use `vlm-docling` pointed at the OpenAI base URL:

```bash
export OPENAI_API_KEY=sk-...
python scripts/ocr_document.py --input scan.pdf --output-dir out/ \
    --backend vlm-docling --host https://api.openai.com/v1 --model gpt-4o
```

> Cloud APIs charge per page and send your document off-machine. Do not use them
> for confidential material without authorization. Note also that strict content
> filters can reject some pages (e.g. forms with personal data); such pages are
> skipped with a placeholder and the rest of the document still processes.

## Passing the host without flags

All host backends read `OCR_HOST` if `--host` is omitted; cloud backends read
`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` if `--api-key` is omitted.

```bash
export OCR_HOST=http://YOUR_HOST:30001
python scripts/ocr_document.py --input docs/ --output-dir out/ --backend olmocr-docling
```
