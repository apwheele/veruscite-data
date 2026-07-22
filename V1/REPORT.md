# VerusCite V1 — Extraction accuracy and speed report

**Package version:** V1  
**Corpus:** 36 PDFs, 2,287 hand-labeled bibliography citations  
**Report date:** 2026-07-22  

## Default extraction model

**Production default: Google Gemini 3.1 Flash Lite** (`gemini-3.1-flash-lite`).

Chosen over OpenAI `gpt-5.4-nano` on this corpus for:

1. **Higher accuracy** — more correctly extracted rows, fewer missing citations, fewer hallucinated/extra rows  
2. **Higher speed** — roughly **half** the wall-clock time on the same full-corpus batch  

`gpt-5.4-nano` remains in the package as a comparison baseline.

## Extraction results (latest kept runs)

Full-corpus batch extraction, OCR backend `pypdfium2`, concurrency 5 documents × 3 section threads.

| Model | Provider | Correct | Missing | Extra | Wall time (s) | Docs / min | Cost (USD) | Run id |
|-------|----------|---------|---------|-------|---------------|------------|------------|--------|
| **gemini-3.1-flash-lite** | gemini | **2285** | **2** | **8** | **238.5** | **~9.1** | 1.17 | `gemini-3.1-flash-lite_2026-07-22T173751Z` |
| gpt-5.4-nano | openai | 2283 | 4 | 13 | 511.0 | ~4.2 | 0.90 | `gpt-5.4-nano_2026-07-22T172556Z` |

Accuracy rates (of 2,287 ground-truth citations):

| Model | Correct rate | Missing rate | Extra count |
|-------|--------------|--------------|-------------|
| **gemini-3.1-flash-lite** | **99.91%** | **0.09%** | 8 |
| gpt-5.4-nano | 99.83% | 0.17% | 13 |

Wall time is end-to-end batch wall clock (including OCR serialization). Extract seconds in run metadata sum per-document LLM time and can exceed wall time under parallel documents.

## Reproduce the table

From the repo root:

```bash
pip install -r requirements.txt
PYTHONPATH=. python - <<'PY'
from src.metrics import extraction_report
print(extraction_report("V1").to_string(index=False))
PY
```

`extraction_report()` columns include `wall_elapsed_seconds`, `extract_seconds`, and `docs_per_minute`.

## Checking (reference)

Checker runs in this package are ground-truth-fed validation of status labels (not re-derived from the new extraction CSVs). See `checking_report("V1")` and `manifest.json` for the kept checker run ids.

## AI disclosure

This report and the V1 data export were prepared with assistance from **Claude** (Anthropic) and **Grok 4.5** (xAI) for scripting, metrics plumbing, and prose. Human authors own ground-truth labels, the default-model decision, and final review of the numbers.
