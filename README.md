# VerusCite Data

Public accuracy benchmark for [VerusCite](https://veruscite.com).

## Layout

```
veruscite-data/
├── README.md
├── requirements.txt
├── src/                    # small Python helpers for the Quarto paper
│   ├── metrics.py          # extraction_report(), checking_report(), load_ground_truth()
│   └── match.py            # citation pairing used by extraction metrics
├── report.qmd              # Quarto source for the public benchmark report
├── report.md / report.pdf  # rendered outputs (`quarto render report.qmd`)
└── V1/
    ├── pdfs/               # source PDFs
    ├── ground_truth.csv    # one concatenated label file (includes source_pdf)
    ├── extraction_run/     # model extraction outputs
    ├── checking_run/       # model checker outputs
    └── manifest.json
```

## V1 data

- **36 documents**, **2,288** hand-labeled citations in a single `ground_truth.csv`
- Column `source_pdf` names the PDF under `pdfs/`
- Labels in `expected_status`: `verified`, `minor_error`, `possible_hallucination`, `not_found`
  (`hallucination` is normalized to `possible_hallucination` on export)

| Kind | Models (kept runs) |
|------|--------------------|
| Extraction | **`gemini-3.1-flash-lite`** (2026-07-30, **default**), `gpt-5.4-nano` (2026-07-30), `gpt-5.6-luna` (2026-07-30) |
| Checking | Perplexity `google/gemini-3.1-flash-lite` (2026-07-30), Perplexity `openai/gpt-5.4-nano` (2026-07-30), OpenAI `gpt-5.4-nano` (2026-07-30), OpenAI `gpt-5.6-luna` (2026-07-30), Gemini `gemini-3.5-flash-lite` direct (2026-07-29) |

### Default extraction model

**Google Gemini 3.1 Flash Lite is the default extraction model** for VerusCite production,
based on the latest full-corpus V1 runs (2026-07-30):

| Model | Correct / 2,288 | Missing | Extra | Wall time | Cost |
|-------|-----------------|---------|-------|-----------|------|
| **gemini-3.1-flash-lite** | **2,285** | **3** | **3** | **~4.9 min** | ~$1.15 |
| gpt-5.4-nano | 2,285 | 3 | 4 | ~12.2 min | ~$0.88 |
| gpt-5.6-luna | 2,284 | 4 | 6 | ~8.2 min | ~$0.84 |

Same correct count as nano for Gemini, fewer extras, and roughly **2.5× wall-clock speed**
on the same 36-document corpus. See the Quarto report
([`report.qmd`](report.qmd) → [`report.pdf`](report.pdf) / [`report.md`](report.md)).

## Rebuild V1 from CiteCheck

The export script lives in the **CiteCheck** repo:

```bash
cd ~/CiteCheck
./scripts/export_veruscite_v1.sh
# optional:
# DEST=/path/to/veruscite-data/V1 ./scripts/export_veruscite_v1.sh
```

## Metrics and report (Quarto)

```bash
pip install -r requirements.txt
quarto render report.qmd    # writes report.md + report.pdf
```

Helpers used by the Quarto document:

```python
from src.metrics import extraction_report, checking_report, load_ground_truth

gt = load_ground_truth("V1")
extraction_report("V1")   # includes wall time / docs per minute
checking_report("V1")
```

## AI disclosure

See the **AI Use Disclosure** section in [`report.qmd`](report.qmd) / rendered report:
drafting with **Claude** (Anthropic); 2026-07-30 extraction/checker refresh (including
`gpt-5.6-luna` and Perplexity `openai/gpt-5.4-nano`), DOI recovery notes, and report
updates with **Grok 4.5** (xAI). Ground-truth labels and final model-default decisions
are human-reviewed.
