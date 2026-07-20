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
    └── manifest.json
```

## V1 data

- **36 documents**, **2,287** hand-labeled citations in a single `ground_truth.csv`
- Column `source_pdf` names the PDF under `pdfs/`
- Labels in `expected_status`: `verified`, `minor_error`, `possible_hallucination`, `not_found`
  (`hallucination` is normalized to `possible_hallucination` on export)

| Kind | Models (kept runs) |
|------|--------------------|
| Extraction | `gemini-3.1-flash-lite` (2026-07-16), `gpt-5.4-nano` (2026-07-16) |
| Checking | Perplexity Gemini 3 flash / 3.1 flash-lite, OpenAI gpt-5.4-mini / nano (all 2026-07-19) |

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
extraction_report("V1")   # one row per extraction run
checking_report("V1")     # one row per checker run
```

These reproduce the main accuracy tables from CiteCheck’s internal `validation.html`
(extraction correct/missing/extra; checker FP rates and recall). Wire them into Quarto
with pandas tables — no HTML report generator is shipped here.

```bash
pip install -r requirements.txt
PYTHONPATH=. python -c "from src.metrics import extraction_report; print(extraction_report('V1'))"
```
