# VerusCite V1 Benchmark: Citation Verification Accuracy
Andrew Wheeler
2026-07-22

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
- [<span class="toc-section-number">7</span> Privacy](#privacy)
- [<span class="toc-section-number">8</span> Limitations and Next
  Steps](#limitations-and-next-steps)
- [<span class="toc-section-number">9</span>
  Reproducibility](#reproducibility)
- [<span class="toc-section-number">10</span> AI Use
  Disclosure](#ai-use-disclosure)
- [<span class="toc-section-number">11</span> References](#references)

## The Problem

Fabricated citations in academic papers have grown sharply since the
widespread adoption of generative AI writing tools. A Lancet audit of
2.5 million biomedical papers found hallucinated reference rates rising
12-fold between 2023 and early 2026 (Topaz et al. 2026). GPTZero’s audit
of NeurIPS 2025 found over 100 confirmed hallucinated citations across
53 accepted papers despite rigorous peer review (GPTZero 2026). Separate
estimates project roughly 147,000 hallucinated citations across arXiv,
bioRxiv, SSRN, and PMC in 2025 alone (Zhao et al. 2026).

Existing peer review and editorial safeguards largely fail to catch
these errors before publication. The problem spans disciplines:
biomedical research, AI/ML conferences, legal filings, and government
reports.

While AI use is driving a surge in publications (see A. Wheeler 2026 for
a practical overview), the same large language models that create this
problem can also be used to verify citations at scale. VerusCite
([veruscite.com](https://veruscite.com)) is a tool to automatically
extract and verify citations from uploaded documents. This report
documents the accuracy of the V1 verification pipeline against a
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

This approach is similar to Pangram, which also emphasizes low false
positive rates for AI-generated content detection. Their published
materials discuss the same tradeoff: when base rates of problematic
content are low, even small false positive rates cause most flagged
items to be false alarms (Emi 2024).

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

| Status | Meaning |
|----|----|
| **Verified** | Citation confirmed to exist via CrossRef or web search |
| **Minor Error** | Citation likely exists but has metadata discrepancies (wrong year, volume, pages) |
| **Hallucination** | No evidence the cited work exists as described |
| **Not Found** | Unable to confirm or deny – includes bare URL citations and paywalled/very recent works with insufficient search results |

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
large frontier models. A full corpus check (36 papers, 2,200+ citations)
runs between \$0.41-\$1.20 per paper depending on the model.

## Ground Truth

The V1 validation corpus contains **2287** hand-labeled citations across
**36 documents**. Sources are intentionally heterogeneous:

- Papers with known hallucinations identified by others on social media
  (Chris Carothers, David Buil-Gil)
- GPTZero’s NeurIPS 2025 audit (GPTZero 2026)
- Papers flagged by Reviewer3 (Reviewer3, n.d.)
- A ChatGPT deep-research output where all 12 citations are fabricated
- Clean papers (dissertation excerpts, open-access criminology, PLoS ONE
  articles)
- MDPI and preprint samples

Of the 2287 citations, 1945 (85.0%) are verified, 148 (6.5%) have minor
errors, 140 (6.1%) are hallucinations, and 54 (2.4%) are not found. The
corpus skews heavily toward verified citations (as real documents do),
which makes false positive rate the critical metric.

## Extraction Results

Citation extraction uses an LLM to parse the document text and identify
individual references. The table below shows extraction accuracy **and
wall-clock speed** against the ground truth (latest kept runs,
2026-07-22).

<div id="tbl-extraction">

Table 1: Extraction accuracy and speed by model (pypdfium2 OCR)

<div class="cell-output cell-output-display cell-output-markdown"
execution_count="3">

| Model | OCR | Real | Correct | Missing | Extra | Rate (%) | Wall (min) | Docs/min | Cost (USD) |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.1-flash-lite | pypdfium2 | 2287 | 2285 | 2 | 8 | 99.9 | 4 | 9.1 | 1.17 |
| gpt-5.4-nano | pypdfium2 | 2287 | 2283 | 4 | 13 | 99.8 | 8.5 | 4.2 | 0.9 |

</div>

</div>

Extraction is very accurate across models. **Gemini 3.1 Flash Lite is
the default production extraction model**: it correctly extracts about
**99.91%** of citations (highest correct count, fewest missing/extra
among the kept runs) and finishes the full 36-document corpus in about
**4.0 minutes** wall time (~9.1 docs/min), roughly twice as fast as
`gpt-5.4-nano` on the same batch. Cost remains on the order of a few
cents per paper for the full corpus.

The few “extra” rows that remain are typically table fragments or rare
non-bibliography lines the model still surfaces; numbered discursive
footnotes and author bios are filtered in the current pipeline.

`gpt-5.4-nano` is retained as a comparison baseline. Both runs use
`pypdfium2` for PDF text extraction.

## Checker Results

<div id="tbl-checking">

Table 2: Checker accuracy by model/provider

<div class="cell-output cell-output-display cell-output-markdown"
execution_count="5">

| Model | Provider | FP Hallucination | FP Minor Error | Hallucination Recall | Not-Verified Recall | CrossRef Verified | Cost (USD) |
|:---|:---|:---|:---|:---|:---|---:|---:|
| gemini-3.5-flash-lite | gemini | 0.1% (2) | 1.4% (27) | 62.9% (88/140) | 66.6% (227/341) | 1331 | 13.6 |
| google/gemini-3-flash-preview | perplexity | 0.2% (4) | 1.5% (30) | 74.3% (104/140) | 71.6% (244/341) | 1345 | 19.87 |
| google/gemini-3-flash-preview | perplexity | 0.1% (1) | 1.8% (36) | 73.6% (103/140) | 73.9% (252/341) | 1331 | 21.81 |
| google/gemini-3.1-flash-lite | perplexity | 0.4% (8) | 2.5% (49) | 70.7% (99/140) | 78.0% (266/341) | 1331 | 14.77 |
| gpt-5.4-mini | openai | 0.2% (4) | 3.1% (61) | 57.1% (80/140) | 81.8% (279/341) | 1346 | 38.56 |
| gpt-5.4-mini | openai | 0.1% (2) | 3.6% (71) | 61.4% (86/140) | 81.8% (279/341) | 1331 | 43.3 |
| gpt-5.4-nano | openai | 0.3% (6) | 4.3% (83) | 57.9% (81/140) | 82.1% (280/341) | 1331 | 23.53 |

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

<div id="tbl-cost">

Table 3: Cost breakdown per full-corpus checker run (36 papers)

<div class="cell-output cell-output-display cell-output-markdown"
execution_count="6">

| Model | Provider | Token Cost (USD) | Search Cost (USD) | Total (USD) | Per Paper (USD) |
|:---|:---|---:|---:|---:|---:|
| gemini-3.5-flash-lite | gemini | 5.33 | 8.27 | 13.6 | 0.38 |
| google/gemini-3-flash-preview | perplexity | 15.53 | 4.34 | 19.87 | 0.55 |
| google/gemini-3-flash-preview | perplexity | 17.13 | 4.68 | 21.81 | 0.61 |
| google/gemini-3.1-flash-lite | perplexity | 9.58 | 5.2 | 14.77 | 0.41 |
| gpt-5.4-mini | openai | 23.11 | 15.45 | 38.56 | 1.07 |
| gpt-5.4-mini | openai | 25.2 | 18.1 | 43.3 | 1.2 |
| gpt-5.4-nano | openai | 7.05 | 16.48 | 23.53 | 0.65 |

</div>

</div>

Perplexity-hosted models are substantially cheaper than direct OpenAI
for equivalent or better accuracy. The Gemini 3.1 Flash Lite
configuration provides the best cost/accuracy ratio at ~\$0.41 per
paper.

### CrossRef as First Pass

Across all checker runs, approximately **1,331** of ~1,946 verified
citations are confirmed via static CrossRef lookup alone (no web search
needed). This is roughly 68% of verified citations resolved without any
LLM cost, which keeps per-citation expenses low and latency down.

## Privacy

VerusCite uses only zero data retention (ZDR) models from all providers.
Uploaded documents are not used for model training by any third party.

Additionally, the pipeline minimizes what is sent to external LLMs.
Citation extraction uses text search on the locally-extracted PDF text
first – only the citation strings themselves are sent to an LLM for
structured parsing. During verification, only the parsed citation
metadata (title, authors, year) is sent to web search, not the full
document text. The full PDF content never leaves the server.

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
- “Not found” is an inherently ambiguous category – some citations are
  bare URLs, others exist but are difficult to locate via web search
  (paywalled, very recent, or in non-English databases).
- The corpus over-represents arXiv preprints relative to other domains
  (law, humanities, clinical medicine).

## Reproducibility

All data for this report is public at
[github.com/apwheele/veruscite-data](https://github.com/apwheele/veruscite-data).
The `V1/` directory contains:

- `ground_truth.csv` – hand-labeled citations with `expected_status`
- `extraction_run/` – raw extraction outputs per model (kept: Gemini 3.1
  Flash Lite + gpt-5.4-nano, 2026-07-22)
- `checking_run/` – raw checker outputs per model
- `manifest.json` – run IDs used in this report
  (`default_extraction_model`: `gemini-3.1-flash-lite`)

To regenerate this report:

``` bash
pip install -r requirements.txt
quarto render report.qmd
```

## AI Use Disclosure

This paper was prepared with AI assistance. Drafting and earlier
iterations used **Claude Opus 4.6** (Anthropic), reviewing prior works
by Andrew Wheeler (see A. P. Wheeler (2026) for that workflow). Updates
for the 2026-07-22 extraction default (Gemini 3.1 Flash Lite), speed
metrics, and this disclosure were assisted by **Grok 4.5** (xAI).
Ground-truth labels, model-default decisions, and final review are
human.

## References

<div id="refs" class="references csl-bib-body hanging-indent">

<div id="ref-emi2024falsepositives" class="csl-entry">

Emi, Bradley. 2024. *All about False Positives in AI Detectors*.
<https://www.pangram.com/blog/all-about-false-positives-in-ai-detectors>.

</div>

<div id="ref-gptzero2026neurips" class="csl-entry">

GPTZero. 2026. *GPTZero Finds 100 New Hallucinations in NeurIPS 2025
Accepted Papers*. <https://gptzero.me/news/neurips/>.

</div>

<div id="ref-reviewer3" class="csl-entry">

Reviewer3. n.d. *Reviewer3: Live arXiv Reference Checking*.
<https://reviewer3.com/live/arxiv>.

</div>

<div id="ref-topaz2026fabricated" class="csl-entry">

Topaz, Maxim, Nir Roguin, Pallavi Gupta, Zhihong Zhang, and Laura-Maria
Peltonen. 2026. “Fabricated Citations: An Audit Across 2.5 Million
Biomedical Papers.” *The Lancet* 407 (10541): 1779–81.
<https://doi.org/10.1016/S0140-6736(26)00603-3>.

</div>

<div id="ref-wheeler2026llmbook" class="csl-entry">

Wheeler, Andrew. 2026. *Large Language Models for Mortals: A Practical
Guide for Analysts with Python*. Crime De-Coder.

</div>

<div id="ref-wheeler2026claude" class="csl-entry">

Wheeler, Andrew P. 2026. *Using Claude Code to Help Me Write*.
<https://andrewpwheeler.com/2026/03/20/using-claude-code-to-help-me-write/>.

</div>

<div id="ref-zhao2026llmhallucinationswildlargescale" class="csl-entry">

Zhao, Zhenyue, Yihe Wang, Toby Stuart, Mathijs De Vaan, Paul Ginsparg,
and Yian Yin. 2026. *LLM Hallucinations in the Wild: Large-Scale
Evidence from Non-Existent Citations*.
<https://arxiv.org/abs/2605.07723>.

</div>

</div>
