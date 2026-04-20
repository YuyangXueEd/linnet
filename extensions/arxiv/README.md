# arxiv extension

Fetches papers from the arXiv daily feed, scores them for relevance with an LLM, summarises each one, and enriches them with the first figure from the paper's HTML page.

LaTeX in figure captions is rendered by the Astro `PaperCard` component.

## Pipeline

```
fetch()    — pulls today's submissions for configured categories
           → keyword pre-filter (must_include list)
process()  — LLM batch scoring → drops papers below threshold
           → LLM summarisation (one paragraph per paper)
           → figure enrichment (scrapes arxiv HTML for first image)
render()   — sorts by category rank then score, wraps in FeedSection
```

## Config

`config/sources.yaml` — toggle only:

| Key | Default | Notes |
|---|---|---|
| `enabled` | `true` | |

`config/extensions/arxiv.yaml` — all other settings (see [`arxiv.yaml.example`](arxiv.yaml.example) to restore defaults):

| Key | Default | Notes |
|---|---|---|
| `categories` | `[]` | arXiv category codes, e.g. `cs.CV`, `cs.LG` |
| `must_include` | `[]` | At least one term must appear in title or abstract |
| `boost_keywords` | `[]` | Increase LLM score if matched |
| `llm_score_threshold` | `7` | Papers scoring below this (0–10) are dropped |
| `max_papers_per_run` | `100` | Papers fetched from arXiv before any filtering |
| `max_papers_to_show` | `20` | Top papers included in the digest |
| `max_authors` | `5` | Authors listed per paper |
| `api_retries` | `5` | Retry attempts on arXiv API 429/errors |
| `api_delay` | `10.0` | Seconds between arXiv API requests |
| `request_timeout` | `20.0` | Seconds for figure/affiliation HTTP fetches |

## Setup Wizard mapping

The setup wizard keeps the arXiv path intentionally opinionated:

- Step 2 lets the user pick **one primary preset** at a time, not a long multi-select combination
- `Custom only` is available when the user wants to drive categories and keywords directly
- if `Custom only` is chosen but `categories` is left blank, the wizard keeps a safe default category set so the fetch step still works
- the wizard's custom tags map to:
  - `Custom categories` → `categories`
  - `Custom keywords` → `must_include`
  - `Boost keywords` → `boost_keywords`
- the generated file is still `config/extensions/arxiv.yaml`

This keeps the first-run experience shorter while preserving full manual control in the final YAML.

## Output item schema

```python
{
  "id":                      str,   # arXiv ID, e.g. "2604.12345"
  "title":                   str,
  "authors":                 list[str],
  "affiliations":            list[str],
  "categories":              list[str],   # sorted by preference rank
  "primary_category":        str,
  "primary_category_anchor": str,         # URL-safe slug for nav anchors
  "url":                     str,         # https://arxiv.org/abs/<id>
  "score":                   float,       # LLM relevance score 0–10
  "abstract":                str,         # LLM-generated summary
  "keywords_matched":        list[str],
  "figure_url":              str | None,  # first figure from HTML page
  "figure_caption":          str | None,
}
```

## Underlying collectors

- `collectors/arxiv_collector.py`
  - `fetch_papers(categories, must_include, max_results)` — arXiv API
  - `enrich_papers_with_figures(papers)` — scrapes arxiv HTML for figures

- `pipeline/scorer.py` — `score_papers(papers, llm, model, threshold)`
- `pipeline/summarizer.py` — `summarize_papers(papers, llm, model, lang)`

## Tests

```bash
PYTHONPATH=. pytest tests/test_arxiv_collector.py tests/test_scorer.py tests/test_summarizer.py -v
```
