# VerusCite V1 Benchmark: Citation Verification Accuracy
Andrew Wheeler
2026-08-03

- [<span class="toc-section-number">1</span> The Problem](#the-problem)
- [<span class="toc-section-number">2</span> Approach](#approach)
  - [<span class="toc-section-number">2.1</span> Design
    Philosophy](#design-philosophy)
- [<span class="toc-section-number">3</span> Pipeline
  Architecture](#pipeline-architecture)
  - [<span class="toc-section-number">3.1</span> Models
    Considered](#models-considered)
  - [<span class="toc-section-number">3.2</span> Verification
    Categories](#verification-categories)
- [<span class="toc-section-number">4</span> Benchmark](#benchmark)
  - [<span class="toc-section-number">4.1</span> Extraction
    Results](#extraction-results)
- [<span class="toc-section-number">5</span> Citation Checking
  Results](#citation-checking-results)
  - [<span class="toc-section-number">5.1</span> False
    Positives](#false-positives)
  - [<span class="toc-section-number">5.2</span> Recall](#recall)
  - [<span class="toc-section-number">5.3</span> Current Production
    Configuration](#current-production-configuration)
  - [<span class="toc-section-number">5.4</span> Cost Breakdown for
    Citation Checking](#cost-breakdown-for-citation-checking)
  - [<span class="toc-section-number">5.5</span> Population Estimates of
    Precision](#population-estimates-of-precision)
- [<span class="toc-section-number">6</span> Comparison between my tool
  and other
  approaches](#comparison-between-my-tool-and-other-approaches)
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
12-fold between 2023 and early 2026 (Topaz et al. 2026). Separate
estimates project roughly 147,000 hallucinated citations across arXiv,
bioRxiv, SSRN, and PMC in 2025 alone (Zhao et al. 2026).

Existing peer review and editorial safeguards largely fail to catch
these errors before publication. The problem spans disciplines:
biomedical research, AI/ML conferences, legal filings, and government
reports.

While AI use is driving a surge in publications (see A. Wheeler 2026 for
a practical overview), the same large language models that create this
problem can also be used to verify citations at scale. VerusCite
([veruscite-data.com](https://veruscite-data.com)) is a tool to
automatically extract and verify citations from uploaded documents. This
report documents the accuracy of the V1 verification pipeline against a
hand-labeled ground truth corpus.

This tool is meant to be a quick and cheap approach to scan a
bibliography for a paper, and determine if a citation is correct, has
minor errors, or appears to have more serious issues, such as an AI
generated hallucination. This paper serves as reference to the overall
architecture and design of the project, as well as a source of false
positive and negative rates on a benchmarked corpus of real papers.

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
trade-off means a human reviewer spends most of their time on citations
that genuinely need attention rather than dismissing false reports.

The application is designed for human-in-the-loop review. Each
citation’s verification status can be manually overridden, and the
interface surfaces the reasoning behind each determination so reviewers
can make informed decisions quickly.

Similar to work in Pangram, I believe that it is necessary to have the
tool have as few of false positives as possible (Emi 2024). While this
report will show that those false positives are not zero (any realistic
tool should report a certain error rate), I believe

## Pipeline Architecture

VerusCite processes documents in two stages:

1.  **Citation Extraction** – An LLM reads the document text and
    identifies individual references, parsing out structured fields
    (title, authors, year, journal, DOI).
2.  **Citation Verification** – Each extracted citation is checked
    against external sources to determine whether it exists as
    described.

For citation extraction, the tool uses text searching across the
document (if a PDF or word document is uploaded) to attempt to determine
the location of the reference section. This tool currently works with
reference sections combined in an article, it does not work with
footnote style citations (as is common in law articles).

If uploading a bibliography file, such as a Bibtext `.bib` file, a
`.ris` file, or an Endnote `.enw` file, the tool uses text tools to
automatically extract out the reference information.

Once the reference section is identified, the reference section is then
chunked into smaller portions, and uses a served LLM model (see later
benchmark results) to extract out the citations into a structured
sections. This means the LLM is only sent the references for the
document, it is not sent other parts of the manuscript.

Each extracted citation is then checked independently. First the
citation is checked against the Crossref database. If it is not found in
Crossref, then an agentic tool uses web-search and fetch to verify
whether the citation exists in external sources.

This independence means that in a document with some errors, other
documents are not falsely assumed to be hallucinated. It also allows
processing the documents in parallel, to return the results back faster.

### Models Considered

Because the task involves web-search, when checking citations that are
not verified via Crossref, this limits the potential pool of LLM
providers. Here I consider two major companies:

- Gemini family models
- OpenAI family models

In particular, I focus on the cheaper models (flash-lite for Gemini and
Nano/Luna for OpenAI) with minimal reasoning. I additionally consider
these same models, but using the web search tools provided by
*Perplexity*.

I do not consider Anthropic, as even their cheapest model (Haiku) is
considerably more expensive than the models I evaluated here. I only
partially evaluated AWS Nova-2 lite with their web search (latency was
too long). Grok 4.3 did well in the benchmark tests but was considerably
more expensive.

Extraction does not need web search, and so while I evaluated many other
models on Bedrock (such as the open source GPT and Gemini models), they
were not as accurate as the frontier served models. Extraction takes
around 2 to 3 cents per document, so at this time I am not concerned
about cost, although in the future likely even smaller open source
models (especially if fine tuned) will be sufficient for the extraction
task.

I would consider additional open source models in the future (such as
DeepSeek flash) for citation checking, although it will be necessary to
incorporate custom web search and fetch tools in conjunction with the
served models. If the models are not provided out of the box by
Perplexity.

### Verification Categories

The checker assigns each citation one of four statuses:

| Status | Meaning |
|----|----|
| **Verified** | Citation confirmed to exist via CrossRef or web search |
| **Minor Error** | Citation likely exists but has metadata discrepancies (wrong year, volume, pages) |
| **Hallucination** | No evidence the cited work exists as described |
| **Not Found** | Unable to confirm or deny – includes bare URL citations and paywalled/very recent works with insufficient search results |

Many citations have minor errors (perhaps on the magnitude of 5% in my
personal assessment). These include many innocuous things that are
likely human introduced errors, like a year off or page numbers wrong.

The major different between a hallucination and a minor error is that
hallucinations tend to have whole cloth differences that are difficult
to explain. Such as journals entirely replaced. For example, Canessa et
al. (2026) has the citation:

> Elrod, Linda D. (2006). “A Move in the Right Direction? Best Interests
> of the Child Emerging as the Standard for Relocation Cases”. Journal
> of the American Academy of Matrimonial Lawyers 15, pp. 1-54.

This is a real paper, but should be cited as:

> Elrod, Linda D. (2006). “A Move in the Right Direction? Best Interests
> of the Child Emerging as the Standard for Relocation Cases”. Journal
> of Child Custody 3, 29–61. https://doi.org/10.1300/J190v03n03_03

While the [Journal of the American Academy of Matrimonial Lawyers does
exist](https://www.aaml.org/resources/aaml-journal/), there is no
combination of volumes and page numbers that could reasonably be
confused with the article in the Journal of Child Custody.

While no automated tool can never find 100% proof that a citation was
hallucinated via a generative AI tool, it is difficult to construct a
scenario where a bibliography had such errors manually generated,
especially the volume and page numbers that do not exist in any
comparable document for the Elrod citation.

Hallucinations can also include when multiple authors are incorrect, but
author name errors are much more common, so they are less likely to be
flagged. For an example of a minor error Mekonen (2026) has the
reference:

> 33. Croft TMA, Allen CK, Arnold F, Assaf S, Balian S. Guide to DHS
>     Statistics: DHS-7 (version 2). Rockville, MD: ICF. 2020.

The actual author list includes an Aileen M.J. Marshall, whose initials
were concatenated into the first author (see page 2 at
<https://dhsprogram.com/pubs/pdf/DHSG1/Guide_to_DHS_Statistics_DHS-7_v2.pdf>).

Minor errors are incredibly prevalent. Any tool intended to do the same
task needs to effectively distinguish between minor errors to be able to
identify actual hallucinated citations.

## Benchmark

The V1 validation corpus contains **2288** hand-labeled citations across
**36 documents**. Sources are intentionally heterogeneous:

- Papers with known hallucinations identified by others on social media
  ([Chris Carothers on
  X](https://x.com/ChrisCarothers/status/2065792749282943030), [David
  Buil-Gil on
  BlueSky](https://bsky.app/profile/davidbuil.bsky.social/post/3mijyzwvet22d))
- GPTZero’s NeurIPS 2025 audit (GPTZero 2026)
- Papers flagged by Reviewer3 (Reviewer3, n.d.)
- A ChatGPT deep-research output where all 12 citations are fabricated
  (Jacques et al. 2026)
- Clean papers (my own dissertation excerpts, open-access criminology,
  PLoS ONE articles)
- MDPI and preprint samples

The corpus spans categories in social sciences, physics, mathematics, as
well as many different formats, including many different pre-print and
journal format examples.

Of the 2288 citations, 1889 (82.6%) are verified, 204 (8.9%) have minor
errors, 141 (6.2%) are hallucinations, and 54 (2.4%) are not found. The
corpus skews heavily toward verified citations (as real documents do),
which makes false positive rate the critical metric.

There are two different metrics a user should be interested in. First is
whether the tool can actually extract out the references accurately.
This is non-trivial in and of itself – a skills based approach
submitting a large document with an extensive bibliography is likely the
generate more errors in this steps.

The second metric is in terms of false positives (e.g. a good citation
is flagged as a hallucination), and recall rates (of all the
hallucinations, how many does the tool capture). Below are those metrics
for this corpus on the current VerusCite tool across different LLM
providers.

### Extraction Results

Citation extraction uses an LLM to parse the document text and identify
individual references. The table below shows extraction accuracy against
the ground truth. There are two types of errors that can occur, you can
miss a reference, or the tool can add in a reference.

<div id="tbl-extraction">

Table 1: Extraction accuracy by model

<div class="cell-output cell-output-display cell-output-markdown"
execution_count="3">

| Model                 | Real | Correct | Missing | Extra | Rate (%) | Wall min | Docs/min | Cost |
|:----------------------|-----:|--------:|--------:|------:|---------:|---------:|---------:|-----:|
| gemini-3.1-flash-lite | 2288 |    2285 |       3 |     3 |     99.9 |      4.9 |      7.4 | 1.15 |
| gpt-5.4-nano          | 2288 |    2285 |       3 |     4 |     99.9 |     12.2 |      3.0 | 0.88 |
| gpt-5.6-luna          | 2288 |    2284 |       4 |     6 |     99.8 |      8.2 |      4.4 | 0.84 |

</div>

</div>

Extraction is very accurate across models. Gemini 3.1 Flash Lite (using
pypdfium2 to read in the text, we additionally considered liteparse with
markdown) correctly extracts over 99.8% of citations at under \$0.03 per
paper for the full corpus. The few “extra” rows are typically page
footers, footnotes, or duplicate listings that the LLM picks up in
addition to the actual bibliography.

I also tested `liteparse` with the markdown export format to extract out
the text from PDFs, which tended to produce slightly more artifacts – it
does not distinguish line breaks for individual citations as cleanly as
pypdfium2, producing a few more missed or merged entries. Results were
largely similar overall (and I may migrate to using liteparse with
markdown in the future).

Both the extraction part of the pipeline and the citation check part of
the pipeline have fallback models, as it is common for these LLM
providers to have downtime with models. The current production version
of VerusCite uses 3.1 flash lite (served by Google) as the primary
extraction model (due to both accuracy and cost). The fallback model is
currently gpt-5.6-luna. While OpenAI (both the 5.4 nano and 5.6 luna
models) are somewhat cheaper, due to the lower accuracy and time, it is
not used at this point. (The cost only saves around 1 cent per paper.)

Generally the prompts are constructed in a way that advanced reasoning
is not necessary. So going up to larger reasoning models (and expanding
the reasoning budget) does not result in higher accuracy. For OpenAI,
you can see that the recent luna model did not result in any more
accurate results than nano.

## Citation Checking Results

The citation checking results break down the benchmark against both the
model, and the provider. When Perplexity is the provider, it means the
tool called Perplexity servers (using their internal web search),
whereas if the provider is gemini it uses Googles web search tool, or
OpenAI uses its internal web search tool. Otherwise all prompts are the
same across each of the models.

The citation checking results input in correct data – extraction and
checking are done in independent benchmarks. So each of the 2288
citations, it is independently run though the checking benchmark,
swapping out the model used.

<div id="tbl-checking">

Table 2: Citation Checking accuracy by model/provider

<div class="cell-output cell-output-display cell-output-markdown"
execution_count="4">

| Model | Provider | FP Hall. | FP Minor | Hall. Recall | NV Recall |
|:---|:---|---:|---:|---:|---:|
| gemini-3.5-flash-lite | gemini | 0.1% (2) | 0.8% (15) | 63.1% (89/141) | 71.9% (286/398) |
| google/gemini-3.1-flash-lite | perplexity | 0.4% (7) | 0.7% (13) | 69.5% (98/141) | 82.7% (329/398) |
| gpt-5.4-nano | openai | 0.2% (3) | 2.2% (42) | 60.3% (85/141) | 88.4% (352/398) |
| gpt-5.6-luna | openai | 0.2% (3) | 2.5% (47) | 74.5% (105/141) | 88.7% (353/398) |
| openai/gpt-5.4-nano | perplexity | 0.4% (7) | 2.5% (47) | 33.3% (47/141) | 84.9% (338/398) |
| openai/gpt-5.6-luna | perplexity | 0.2% (4) | 2.2% (41) | 44.7% (63/141) | 87.7% (349/398) |

</div>

</div>

### False Positives

For key metrics, there are a total of 1889 correct citations in the
corpus. So false positives (FP) rates are of those 1889 correct
citations, how many were falsely flagged by the tool.

The current FP rates for hallucinations are well under 1%, and vary
between 2 to 7 total false positives across the different models in this
corpus. Hallucination false positives are often attributable to
idiosyncratic web search results. (The agentic tools often will return a
response, even if the web search tool is currently inaccessible.)
Verified false-positive rates on Perplexity are broadly similar to the
same model on the provider’s own web-search stack, but **hallucination
recall is not**: Perplexity-hosted OpenAI models (`openai/gpt-5.4-nano`,
`openai/gpt-5.6-luna`) under-detect true hallucinations relative to
OpenAI direct (see Recall below).

For an example of a false positive hallucination in this particular run,
my dissertation has the citation:

> Pearl, J. (2000). Causality: models, reasoning and inference, Volume
> 29. Cambridge Univ Press.

And 5.4 nano lists as reasoning for classifying this as a hallucination:

> Upstream verdict: book exists and matches author/title/year/publisher,
> but the cited “Volume 29” element is not supported by the primary
> publisher/library records surfaced in the tool results and is treated
> as fabricated metadata; therefore status mapped to hallucination.

This behavior is not consistent, either within 5.4. nano or across other
models. (This most often returns a “minor error”, although my ground
truth I have this as “verified”. Some sources list the published year as
2001, causing additional issues beyond just the “Volume 29” addition.) I
have intentionally avoided K-shot examples in the prompt, so there is as
little leakage as possible and the prompts should better generalize to
out of sample data. But given the stochastic nature of LLMs, some errors
will ultimately occur.

FP rates for minor errors are more prevalent, being close to 1% for the
Gemini models, but over 2% for the OpenAI models. Production defaults
are summarized in [Current Production
Configuration](#current-production-configuration): primary checker is
**Perplexity-hosted Gemini 3.1 Flash Lite**, with **OpenAI direct
`gpt-5.6-luna`** as the fallback.

The general approach I took was to evaluate when both OpenAI and Google
models returned false positives. While these do happen in the corpus, in
some cases they are inevitable, as CrossRef or other online data
provides conflicting information. For one example citation:

> \[CS22\] T. Cieśla and M. Sabok. Measurable Hall’s theorem for actions
> of abelian groups, J. Eur. Math. Soc., 24 (2022), 2751-2773 (cit. on
> pp. 3, 44)

Consistently produces a “minor error” category in the tool due to the
citation year. Going to the website, the citation year is correctly
2022. But [crossref lists the publication year as
2021](https://search.crossref.org/search/works?q=10.4171%2FJEMS%2F1164&from_ui=yes).

Many of the false positives are minor errors like this (and likely some
of the labels in the ground truth should be updated – feel free to
contact me if you believe an articles classification is not correct in
the ground truth). False positives for not found tend to be due to
unreliable web search, and so are intermittent and not consistent due to
the tool.

### Recall

Recall is the proportion of the true errors that are captured by the
current tool. These are more variable across the different tools, with
OpenAI models having greater recall (which comes with more false
positives). Hallucination recall for the Gemini configurations is
currently in the 60–70% range, whereas **OpenAI direct `gpt-5.6-luna` is
at about 75%** (105/141). The same luna weights on **Perplexity**
(`openai/gpt-5.6-luna`, 2026-08-01) drop to about **45%** hallucination
recall (63/141), with not-verified recall still high (~88%) because many
misses land in minor error or not found rather than verified. Perplexity
`openai/gpt-5.4-nano` shows the same pattern even more sharply (33%
hallucination recall). Provider web-search quality matters as much as
the base model for this task.

Minor error recall is similarly lower for Gemini direct 3.5 flash-lite,
at 52.7%. OpenAI direct has higher recall (often higher than 70%) for
minor errors. Not found recall is near perfect across all models.

The final category, not verified, collapses the categories of minor
error, hallucination, and not found. So if many hallucinations were
classified into minor error, the direct recall rates would be low, but
not verified (which will typically trigger a human review) would still
be high. These are consistently over 80% across all model runs, with the
exception of Gemini 3.5 flash lite (which is mostly due to low recall on
minor errors).

### Current Production Configuration

Production VerusCite uses the following defaults for citation checking:

| Role                 | Provider        | Model                          |
|----------------------|-----------------|--------------------------------|
| **Primary checker**  | Perplexity      | `google/gemini-3.1-flash-lite` |
| **Fallback checker** | OpenAI (direct) | `gpt-5.6-luna`                 |

**Why Perplexity 3.1 Flash Lite as primary.** Google’s Gemini web-search
stack caps searches at **1,500 per day across all tiers**, which is too
low for multi-user production load (a single large paper can consume
dozens of searches after Crossref misses). Perplexity does not impose
that daily search cap, so agentic verification can keep running under
concurrent documents. On this corpus, Perplexity
`google/gemini-3.1-flash-lite` also has strong precision and solid
not-verified recall (~83%), with hallucination FP still under 0.5%.

Gemini **direct** 3.5 flash-lite remains the fastest and cheapest
full-corpus configuration in the table below (~26s wall-equivalent per
paper under concurrent batching, ~\$0.41/paper), but the search quota
makes it unsuitable as the default production path. It is retained in
the benchmark for comparison.

**Why OpenAI luna as backup.** Direct OpenAI `gpt-5.6-luna` is the
fallback when Perplexity is down or returns persistent errors. It has
the highest hallucination recall among configurations tested (~75%) at
similar cost to the Perplexity primary (~\$0.51/paper). The
Perplexity-hosted OpenAI variants (`openai/gpt-5.4-nano`,
`openai/gpt-5.6-luna`) are **not** used as production fallback: they
under-detect true hallucinations relative to OpenAI direct (see Recall
above).

Extraction production remains Gemini 3.1 Flash Lite (Google) with OpenAI
fallback, as described in the Extraction Results section.

### Cost Breakdown for Citation Checking

For the 2288 total citations, approximately 1310 citations were verified
via Crossref after extraction (about 57%) for each of the models. These
are largely automated, and so incur no additional LLM cost. When those
fail however, an agent based LLM tool needs to use web search and fetch
to identify whether the citation is correct. Thus costs incur for both
token usage as well as web search. Web search costs \$5 per 1000
searches on Perplexity, \$7 per 1000 searches for OpenAI, and \$14 per
1000 searches for Google.

The prompts are generally short enough that token caching does not occur
at all for the Gemini models (needs over 4000 tokens). Some token
caching does occur for OpenAI (although these costs do not include
that), but it is relatively small (and the majority of token costs are
output).

<div id="tbl-cost">

Table 3: Cost and runtime breakdown per full-corpus checker run (36
papers)

<div class="cell-output cell-output-display cell-output-markdown"
execution_count="5">

| Model | Provider | Token Cost (USD) | Search Cost (USD) | Total (USD) | Per Paper (USD) | Sec/paper | Wall min |
|:---|:---|---:|---:|---:|---:|---:|---:|
| gemini-3.5-flash-lite | gemini | 6.14 | 8.44 | 14.59 | 0.41 | 128.9 | 15.7 |
| google/gemini-3.1-flash-lite | perplexity | 12.15 | 7.72 | 19.87 | 0.55 | 406.2 | 51.0 |
| gpt-5.4-nano | openai | 7.17 | 16.28 | 23.45 | 0.65 | 445.5 | 54.4 |
| gpt-5.6-luna | openai | 6.84 | 11.49 | 18.33 | 0.51 | 328.6 | 39.9 |
| openai/gpt-5.4-nano | perplexity | 7.34 | 4.84 | 12.18 | 0.34 | 243.3 | 29.7 |
| openai/gpt-5.6-luna | perplexity | 11.21 | 8.76 | 19.98 | 0.56 | 291.6 | 35.7 |

</div>

</div>

**Sec/paper** is the mean document wall time from each run’s
`document_metrics.csv` (how long one paper takes end-to-end under the
batch concurrency settings). **Wall min** is full-corpus elapsed time
with up to five documents in parallel.

The newer Gemini-direct 3.5 flash lite model has lower token costs and
the shortest per-paper times, but is not the production primary for the
web-search quota reasons above. Across this corpus, costs are typically
around 50 cents per paper, with often more than half of the cost devoted
to web search. Production primary (Perplexity 3.1 flash lite) is about
**\$0.55/paper** and **~7 minutes mean per paper** on this batch setup;
OpenAI direct luna fallback is about **\$0.51/paper** and **~5.5 minutes
mean per paper**. Perplexity `openai/gpt-5.6-luna` lands near OpenAI
direct luna on total cost (~\$20 full corpus) despite cheaper Perplexity
search (\$5/1k vs OpenAI \$10/1k in pricing tables used here): token
spend is higher on the Perplexity run, so the search savings do not
produce a cheaper overall check.

### Population Estimates of Precision

The ground truth sample I have collected is likely not representative of
the overall population of scholarly papers. I have intentionally
selected examples papers that have high rates of hallucinated citations.
In Topaz et al. (2026) and Zhao et al. (2026), they estimate that
pre-print servers and PubMed papers currently have rates of hallucinated
citations ranging from 0.2% to almost 1.9%.

So for an hypothetical example, if false positive rates for
hallucinations in my tool are 0.5%, and the population prevalence rate
of hallucinations are 1%, and my recall rates are 60%, what are the
estimates for precision in the population? The estimated precision in
the population will be only slightly over 50%. So out of 100 citations,
1 is a real hallucination, and 99 are not. Overall I capture that real
hallucination 60% of the time, so 0.6 true positives. Of the 99 I have
`0.99*0.005` false positives, so approximately 0.5 false positives. And
then the precision is then `0.6/(0.5 + 0.6)`, which is slightly over 50%
(**gigerenzer2011natural?**).

If true rates of hallucinations are lower, my population precision will
also be lower. Increasing recall could help, but even if recall is
increased to 80% precision is still only 60%.

As such, it will be necessary for humans to carefully review the output
of the tool. If an article with a single hallucinated is identified, it
does not for sure indicate that AI was used in the production of the
bibliography. If multiple references are flagged as hallucinations
though, it is more likely there are substantive issues with the work
that a dutiful editor should investigate.

Ultimately they overall rate of 1% hallucinations are a mixture of
papers – most scientists likely do a good job, but there are likely a
few bad apples that use AI to generate whole slews of papers. And those
individuals may have hallucination rates in over 20% of their citations
(**walters2023fabrication?**). Although with the improvement of the
generative AI tools, that will likely decrease over time.

## Comparison between my tool and other approaches

For some differences between my work and Topaz et al. (2026) and Zhao et
al. (2026), my tool can flag as hallucinations when authors or journals
are clearly wrong. Both Topaz et al. (2026) and Zhao et al. (2026) focus
on title matches (and mismatches) only. The prior example I gave in
Canessa et al. (2026) would not be classified as a hallucination in
either of these tools, as the title exists – it just clearly swapped out
an incorrect journal.

Additionally both Topaz et al. (2026) and Zhao et al. (2026) use google
scholar as a secondary reference source. I do not consider this as
valid, as I have personally seen google scholar reference hallucinated
citations, see [this example of a hallucinated
reference](https://scholar.google.com/scholar_lookup?title=Spatial%20analysis%20of%20crime%20patterns%20using%20GIS-based%20decision%20support%20tools&author=J.%20Smith&publication_year=2022&pages=125-148),
the citation

> \[5\] J. Smith, Spatial analysis of crime patterns using GIS-based
> decision support tools, J. Quant. Criminol. 38 (2) (2022) 125–148

that is in Kebede et al. (2026) in my ground truth, and actually links
to the (false) google scholar citation.

These methods focus on title matches. So for example, Topaz et al.
(2026) give the example as a *not* hallucinated title:

> For example, a reference listed as *Depression and anxiety in young
> adults with ID* corresponds to the real indexed title *Depression and
> anxiety symptoms during the transition to early adulthood for people
> with intellectual disabilities* and is probably a reference error, not
> a fabrication.

My current system, while calling stochastic LLMs, reliably classifies
this as a *minor error* (across all model permutations).

Other current tools, like GPTZero or Reviewer3, do not publish how they
exactly approach citation checking. While Reviewer3 lists a [reference
set of metrics](https://reviewer3.com/evidence/benchmarks/references),
they do not share the actual citations. (It appears these are simulated,
as the (**walters2023fabrication?**) paper they cite has 636 citations,
and Reviewer3’s reference set only has 476 citations.)

The articles additionally focus on peer reviewed literature, and do not
evaluate hallucinations in non journal articles (grey literature). My
benchmark includes the full corpus in the reference papers, including
blog posts, working papers, datasets, technical reports, law cases, etc.
I have included the not found category for the scenario where a citation
cannot be reasonably identified from web based resources, but including
these sources will likely increase false positive rates, as how they are
even supposed to be correctly cited can be difficult to know exactly.

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

- Ground truth labels for some documents have ambiguous categories that
  likely could be reasonably changed. This is particularly true for the
  minor error category.
- “Not found” is an inherently ambiguous category – some citations are
  bare URLs, others exist but are difficult to locate via web search
  (paywalled, very recent, or in non-English databases).
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

## AI Use Disclosure

This paper was prepared with AI assistance. Drafting and earlier
iterations used **Claude Opus 4.6** (Anthropic), reviewing prior works
by Andrew Wheeler (see A. P. Wheeler (2026) for that workflow).
Additional edits, including the Current Production Configuration section
(Perplexity `google/gemini-3.1-flash-lite` primary, OpenAI
`gpt-5.6-luna` fallback, and per-paper runtime in the cost table), were
assisted by **Grok 4.5** (xAI). Ground-truth labels and final review are
done by myself (Andrew P. Wheeler). All errors are my own.

## References

<div id="refs" class="references csl-bib-body hanging-indent">

<div id="ref-NBERw35482" class="csl-entry">

Canessa, Stella, Gordon B Dahl, Anna Hasselqvist, et al. 2026. *Life
After Divorce: Effects of Joint Custody on Parents and Children*.
Working Paper No. 35482. Working Paper Series. National Bureau of
Economic Research. <https://doi.org/10.3386/w35482>.

</div>

<div id="ref-emi2024falsepositives" class="csl-entry">

Emi, Bradley. 2024. *All about False Positives in AI Detectors*.
<https://www.pangram.com/blog/all-about-false-positives-in-ai-detectors>.

</div>

<div id="ref-gptzero2026neurips" class="csl-entry">

GPTZero. 2026. *GPTZero Finds 100 New Hallucinations in NeurIPS 2025
Accepted Papers*. <https://gptzero.me/news/neurips/>.

</div>

<div id="ref-Jacques03042026" class="csl-entry">

Jacques, Scott, Andrew Wheeler, and Joshua Gerstenfeld. 2026. “Open
Access, Generative Artificial Intelligence, and the Criminology Evidence
Base.” *Evidence Base* 1 (2): 2658591.
<https://doi.org/10.1080/30679125.2026.2658591>.

</div>

<div id="ref-assen2026crime" class="csl-entry">

Kebede, Hailu, Mohammed Motuma Assen, and Merid Abadi Sharew. 2026.
“Crime Hotspot Analysis and Mapping Using Geospatial Technology in
Dessie City, Ethiopia.” *Next Research* 5: 101303.
<https://doi.org/10.1016/j.nexres.2025.101303>.

</div>

<div id="ref-10.1371/journal.pone.0353669" class="csl-entry">

Mekonen, Enyew Getaneh. 2026. “Prevalence and Associated Factors of
Intimate Partner Violence Against Reproductive-Age Women in Africa and
Asia Regions: Insights from 2022–2024 DHS Datasets.” *PLOS ONE* 21 (7):
1–16. <https://doi.org/10.1371/journal.pone.0353669>.

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
