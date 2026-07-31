# VerusCite Data

Public ground-truth corpus and reproducible scripts for [VerusCite](https://veruscite-data.com).

This repo holds labeled citations, model run outputs, and a Quarto report that regenerates benchmark metrics from those artifacts. For metric results, see [`report.md`](report.md) (or [`report.pdf`](report.pdf)).

## Reproduce the report

```bash
pip install -r requirements.txt
quarto render report.qmd
```

## Layout

```
v1/
  ground_truth.csv    # hand-labeled citations
  pdfs/               # source documents
  extraction_run/     # extraction model outputs
  checking_run/       # checker model outputs
  manifest.json
src/                  # metrics helpers used by the report
report.qmd            # Quarto source
```
