# arxiv extension

Fetches papers from the arXiv daily feed, scores them for relevance with an LLM, summarises each one, and enriches them with the first figure from the paper's HTML page.

This extension also ships a page-level `head.html.j2` include that loads KaTeX, so inline LaTeX found in figure captions can be rendered on the generated site.

## Pipeline

```
fetch()    — pulls today's submissions for configured categories
           → keyword pre-filter (must_include list)
process()  — LLM batch scoring → drops papers below threshold
           → LLM summarisation (one paragraph per paper)
           → figure enrichment (scrapes arxiv HTML for first image)
render()   — sorts by category rank then score, wraps in FeedSection
```

## Config (`config/sources.yaml` + `config/extensions/arxiv.yaml`)

| Key | Where | Default | Notes |
|---|---|---|---|
| `enabled` | sources.yaml | `true` | |
| `max_papers_per_run` | sources.yaml | `300` | Papers fetched before any filtering |
| `categories` | extensions/arxiv.yaml | `[]` | arXiv category codes, e.g. `cs.CV`, `cs.LG` |
| `must_include` | extensions/arxiv.yaml | `[]` | At least one term must appear in title or abstract |
| `boost_keywords` | extensions/arxiv.yaml | `[]` | Increase LLM score if matched |
| `llm_score_threshold` | extensions/arxiv.yaml | `7` | Papers scoring below this (0–10) are dropped |

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
