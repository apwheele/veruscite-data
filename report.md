# VerusCite V1 Benchmark: Citation Verification Accuracy
Andrew Wheeler
2026-07-20

- [<span class="toc-section-number">1</span> The Problem](#the-problem)
- [<span class="toc-section-number">2</span> Approach](#approach)
  - [<span class="toc-section-number">2.1</span> Design
    Philosophy](#design-philosophy)
  - [<span class="toc-section-number">2.2</span> Comparison to Similar
    Tools](#comparison-to-similar-tools)
- [<span class="toc-section-number">3</span> Pipeline
  Architecture](#pipeline-architecture)
  - [<span class="toc-section-number">3.1</span> Verification
    Categories](#verification-categories)
  - [<span class="toc-section-number">3.2</span> Verification
    Method](#verification-method)
- [<span class="toc-section-number">4</span> Ground
  Truth](#ground-truth)
- [<span class="toc-section-number">5</span> Extraction
  Results](#extraction-results)
- [<span class="toc-section-number">6</span> Checker
  Results](#checker-results)
  - [<span class="toc-section-number">6.1</span> Cost
    Breakdown](#cost-breakdown)
  - [<span class="toc-section-number">6.2</span> CrossRef as First
    Pass](#crossref-as-first-pass)
- [<span class="toc-section-number">7</span> Limitations and Next
  Steps](#limitations-and-next-steps)
- [<span class="toc-section-number">8</span>
  Reproducibility](#reproducibility)

## The Problem

Fabricated citations in academic papers have grown sharply since the
widespread adoption of generative AI writing tools. A Lancet audit of
2.5 million biomedical papers found hallucinated reference rates rising
12-fold between 2023 and early 2026 (Topaz et al., 2026). GPTZero’s
audit of NeurIPS 2025 found over 100 confirmed hallucinated citations
across 53 accepted papers despite rigorous peer review. Separate
estimates project roughly 147,000 hallucinated citations across arXiv,
bioRxiv, SSRN, and PMC in 2025 alone.

Existing peer review and editorial safeguards largely fail to catch
these errors before publication. The problem spans disciplines:
biomedical research, AI/ML conferences, legal filings, and government
reports.

VerusCite ([veruscite.com](https://veruscite.com)) is a tool to
automatically extract and verify citations from uploaded documents. This
report documents the accuracy of the V1 verification pipeline against a
hand-labeled ground truth corpus.

## Approach

### Design Philosophy

Even in documents with hallucinated citations, the majority of
references are legitimate. A tool with a high false positive rate –
flagging real papers as hallucinations – would waste a reviewer’s time
chasing false alarms rather than finding actual problems. VerusCite
prioritizes **precision over recall**: it is better to miss some
hallucinations than to incorrectly flag verified citations.

The target false positive rate for hallucination flags is below 1%.
Recall for detecting actual hallucinations is around 70-80%. This
tradeoff means a human reviewer spends most of their time on citations
that genuinely need attention rather than dismissing false reports.

The application is designed for human-in-the-loop review. Each
citation’s verification status can be manually overridden, and the
interface surfaces the reasoning behind each determination so reviewers
can make informed decisions quickly.

### Comparison to Similar Tools

This approach is similar to [Pangram](https://www.pangram.co/), which
also emphasizes low false positive rates for AI-generated content
detection. Their published materials discuss the same tradeoff: when
base rates of problematic content are low, even small false positive
rates cause most flagged items to be false alarms (see [Pangram’s
blog](https://www.pangram.co/resources)).

## Pipeline Architecture

VerusCite processes documents in two stages:

1.  **Citation Extraction** – An LLM reads the document text and
    identifies individual references, parsing out structured fields
    (title, authors, year, journal, DOI).
2.  **Citation Verification** – Each extracted citation is checked
    against external sources to determine whether it exists as
    described.

### Verification Categories

The checker assigns each citation one of four statuses:

| Status            | Meaning                                                                           |
|-------------------|-----------------------------------------------------------------------------------|
| **Verified**      | Citation confirmed to exist via CrossRef or web search                            |
| **Minor Error**   | Citation likely exists but has metadata discrepancies (wrong year, volume, pages) |
| **Hallucination** | No evidence the cited work exists as described                                    |
| **Not Found**     | Unable to confirm or deny (insufficient search results)                           |

### Verification Method

Verification proceeds in two passes:

1.  **Static CrossRef lookup** – A title/DOI search against CrossRef
    metadata. Fast and free. Confirms roughly 60% of legitimate
    citations without needing web search.
2.  **Web search verification** – Citations not resolved by CrossRef are
    sent to a web-search-enabled LLM (Perplexity or OpenAI web search
    tools) to locate evidence of the publication.

The primary models used are **Perplexity** (hosting Gemini Flash Lite or
Gemini 3 Flash) and **OpenAI GPT-5.4-mini/nano** as fallback. Having
multiple providers is important operationally – any single provider
experiences periodic outages or rate limits. Results reported here
represent the range across these configurations.

Cost is kept low by using smaller models with web search rather than
large frontier models. A full corpus check (2,200+ citations) runs
between \$15-\$44 depending on the model.

## Ground Truth

The V1 validation corpus contains **2287** hand-labeled citations across
**36 documents**. Sources are intentionally heterogeneous:

- Papers with known hallucinations identified by others on social media
  (Chris Carothers, David Buil-Gil)
- GPTZero’s NeurIPS 2025 audit
  ([gptzero.me/news/neurips](https://gptzero.me/news/neurips/))
- Papers flagged by [Reviewer3](https://reviewer3.com/live/arxiv) (see
  also [@Reviewer3 on
  X](https://x.com/Reviewer3/status/2069835348923019450))
- A ChatGPT deep-research output where all 12 citations are fabricated
- Clean papers (dissertation excerpts, open-access criminology, PLoS ONE
  articles)
- MDPI and preprint samples

Label distribution:

    - Verified: 1945 (85.0%)
    - Minor Error: 148 (6.5%)
    - Hallucination: 140 (6.1%)
    - Not Found: 54 (2.4%)

The corpus skews heavily toward verified citations (as real documents
do), which makes false positive rate the critical metric.

## Extraction Results

Citation extraction uses an LLM to parse the document text and identify
individual references. The table below shows extraction accuracy against
the ground truth.

``` python
ext = extraction_table()
ext
```

<div class="cell-output cell-output-display" execution_count="4">

<div>

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }
&#10;    .dataframe tbody tr th {
        vertical-align: top;
    }
&#10;    .dataframe thead th {
        text-align: right;
    }
</style>

|     | Model                 | OCR       | Real | Correct | Missing | Extra | Rate (%) | Cost (\$) |
|-----|-----------------------|-----------|------|---------|---------|-------|----------|-----------|
| 0   | gemini-3.1-flash-lite | pypdfium2 | 2287 | 2284    | 3       | 12    | 99.9     | 1.156257  |
| 1   | gpt-5.4-nano          | pypdfium2 | 2287 | 2282    | 5       | 13    | 99.8     | 0.882243  |

</div>

</div>

</div>

Extraction is very accurate across models. Gemini 3.1 Flash Lite with
pypdfium2 correctly extracts over 99.8% of citations at under \$1.20 for
the full corpus. The few “extra” rows are typically page footers,
footnotes, or duplicate listings that the LLM picks up in addition to
the actual bibliography.

The `liteparse` OCR backend (a lighter PDF text extractor) produces
slightly more misses than pypdfium2, which handles multi-column layouts
and ligatures better.

## Checker Results

``` python
chk = checking_table()
chk
```

<div class="cell-output cell-output-display" execution_count="5">

<div>

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }
&#10;    .dataframe tbody tr th {
        vertical-align: top;
    }
&#10;    .dataframe thead th {
        text-align: right;
    }
</style>

|     | Model                         | Provider   | FP → Hallucination | FP → Minor Error | Hallucination Recall | Not-Verified Recall | CrossRef Verified | Cost (\$) |
|-----|-------------------------------|------------|--------------------|------------------|----------------------|---------------------|-------------------|-----------|
| 0   | google/gemini-3-flash-preview | perplexity | 0.1% (1)           | 1.8% (36)        | 73.6% (103/140)      | 73.9% (252/341)     | 1331              | 21.809336 |
| 1   | google/gemini-3.1-flash-lite  | perplexity | 0.4% (8)           | 2.5% (49)        | 70.7% (99/140)       | 78.0% (266/341)     | 1331              | 14.773963 |
| 2   | gpt-5.4-mini                  | openai     | 0.1% (2)           | 3.6% (71)        | 61.4% (86/140)       | 81.8% (279/341)     | 1331              | 43.298306 |
| 3   | gpt-5.4-nano                  | openai     | 0.3% (6)           | 4.3% (83)        | 57.9% (81/140)       | 82.1% (280/341)     | 1331              | 23.526988 |

</div>

</div>

</div>

Key metrics:

- **FP → Hallucination**: Percentage of actually-verified citations
  incorrectly flagged as hallucinations. All configurations stay at or
  below 0.4%.
- **Not-Verified Recall**: Percentage of actual problems
  (hallucinations + minor errors + not-found) correctly identified.
  Ranges from 72-82%.
- **Hallucination Recall**: Percentage of actual hallucinations
  correctly flagged. The best configuration (Gemini 3 Flash via
  Perplexity) achieves 73.6%.

### Cost Breakdown

``` python
costs = cost_comparison_table()
costs
```

<div class="cell-output cell-output-display" execution_count="6">

<div>

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }
&#10;    .dataframe tbody tr th {
        vertical-align: top;
    }
&#10;    .dataframe thead th {
        text-align: right;
    }
</style>

|     | Model                         | Provider   | Token Cost (\$) | Search Cost (\$) | Total (\$) |
|-----|-------------------------------|------------|-----------------|------------------|------------|
| 0   | google/gemini-3-flash-preview | perplexity | 17.129258       | 4.680            | 21.809336  |
| 1   | google/gemini-3.1-flash-lite  | perplexity | 9.578944        | 5.195            | 14.773963  |
| 2   | gpt-5.4-mini                  | openai     | 25.198293       | 18.100           | 43.298306  |
| 3   | gpt-5.4-nano                  | openai     | 7.046987        | 16.480           | 23.526988  |

</div>

</div>

</div>

Perplexity-hosted models are substantially cheaper than direct OpenAI
for equivalent or better accuracy. The Gemini 3.1 Flash Lite
configuration provides the best cost/accuracy ratio at ~\$15 per full
run.

### CrossRef as First Pass

Across all checker runs, approximately **1,331** of ~1,946 verified
citations are confirmed via static CrossRef lookup alone (no web search
needed). This is roughly 68% of verified citations resolved without any
LLM cost, which keeps per-citation expenses low and latency down.

## Limitations and Next Steps

The V1 corpus is heterogeneous by design, but 36 documents is a limited
sample. The next evaluation (V2) will use the same prompts and pipeline
but a **completely different validation set** – different documents,
different domains, different sources of known hallucinations. This
ensures the system is not overtrained on the particular examples in V1.

Known limitations of the current evaluation:

- Ground truth labels for some documents were seeded from the checker
  itself and hand-reviewed, which may introduce subtle bias toward the
  checker’s own patterns.
- “Not found” is an inherently ambiguous category – some citations exist
  but are difficult to locate via web search (paywalled, very recent, or
  in non-English databases).
- The corpus over-represents arXiv preprints relative to other domains
  (law, humanities, clinical medicine).

## Reproducibility

All data for this report is public at
[github.com/apwheele/veruscite-data](https://github.com/apwheele/veruscite-data).
The `v1/` directory contains:

- `ground_truth.csv` – hand-labeled citations with `expected_status`
- `extraction_run/` – raw extraction outputs per model
- `checking_run/` – raw checker outputs per model
- `manifest.json` – run IDs used in this report

To regenerate this report:

``` bash
pip install -r requirements.txt
quarto render report.qmd
```
