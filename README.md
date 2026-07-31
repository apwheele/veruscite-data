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


## Cite

To cite this report, you can use:

    Wheeler, A. (2026). VerusCite V1 Benchmark: Citation Verification Accuracy. CrimRxiv. Retrieved from https://github.com/apwheele/veruscite-data

You can also see a persisitent identifier from the pre-print posted on [CrimRXiV](https://www.crimrxiv.com/pub/s63si1hl/release/1).