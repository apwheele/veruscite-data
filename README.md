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
└── V1/
    ├── pdfs/               # source PDFs
    ├── ground_truth.csv    # one concatenated label file (includes source_pdf)
    ├── extraction_run/     # model extraction outputs
    ├── checking_run/       # model checker outputs
    ├── REPORT.md           # accuracy + speed summary (default model decision)
    └── manifest.json
```

## V1 data

- **36 documents**, **2,287** hand-labeled citations in a single `ground_truth.csv`
- Column `source_pdf` names the PDF under `pdfs/`
- Labels in `expected_status`: `verified`, `minor_error`, `possible_hallucination`, `not_found`
  (`hallucination` is normalized to `possible_hallucination` on export)

| Kind | Models (kept runs) |
|------|--------------------|
| Extraction | **`gemini-3.1-flash-lite`** (2026-07-22, **default**), `gpt-5.4-nano` (2026-07-22) |
| Checking | Perplexity Gemini 3 flash / 3.1 flash-lite, OpenAI gpt-5.4-mini / nano, Gemini 3.5 flash-lite |

### Default extraction model

**Google Gemini 3.1 Flash Lite is the default extraction model** for VerusCite production,
based on the latest full-corpus V1 run (2026-07-22):

| Model | Correct / 2,287 | Missing | Extra | Wall time | Cost |
|-------|-----------------|---------|-------|-----------|------|
| **gemini-3.1-flash-lite** | **2,285** | **2** | **8** | **~4.0 min** | ~$1.17 |
| gpt-5.4-nano | 2,283 | 4 | 13 | ~8.5 min | ~$0.90 |

Higher accuracy (fewer missing and hallucinated extras) and roughly **2× wall-clock speed**
vs gpt-5.4-nano on the same 36-document corpus. See [V1/REPORT.md](V1/REPORT.md).

## Rebuild V1 from CiteCheck

The export script lives in the **CiteCheck** repo:

```bash
cd ~/CiteCheck
./scripts/export_veruscite_v1.sh
# optional:
# DEST=/path/to/veruscite-data/V1 ./scripts/export_veruscite_v1.sh
```

## Metrics for the paper (Quarto)

```python
from src.metrics import extraction_report, checking_report, load_ground_truth

gt = load_ground_truth("V1")
extraction_report("V1")   # one row per extraction run (includes wall time / docs per minute)
checking_report("V1")     # one row per checker run
```

These reproduce the main accuracy tables from CiteCheck’s internal `validation.html`
(extraction correct/missing/extra; checker FP rates and recall). Wire them into Quarto
with pandas tables — no HTML report generator is shipped here.

```bash
pip install -r requirements.txt
PYTHONPATH=. python -c "from src.metrics import extraction_report; print(extraction_report('V1'))"
```

## AI disclosure

This public benchmark package and the V1 accuracy report were prepared with assistance from
**Claude** (Anthropic) and **Grok 4.5** (xAI) for export scripting, report drafting, and
repository maintenance. Ground-truth labels and final acceptance of model defaults were
reviewed by the human author.
