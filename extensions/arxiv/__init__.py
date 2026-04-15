"""ArXiv extension — fetches, scores, summarises, and enriches papers."""

import re
from typing import Any

from extensions.arxiv.collector import enrich_papers_with_figures, fetch_papers
from extensions.arxiv.scorer import score_papers
from extensions.arxiv.summarizer import summarize_papers
from extensions.base import BaseExtension, FeedSection


def _category_anchor(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower().replace(".", "-")).strip("-") or "other"


def _prepare_papers(papers: list[dict], preferred_categories: list[str]) -> list[dict]:
    """Assign stable primary category and sort by category rank, then score."""
    if not papers:
        return papers

    rank_map = {cat.lower(): idx for idx, cat in enumerate(preferred_categories)}
    default_rank = len(preferred_categories) + 100

    for paper in papers:
        categories = [c for c in paper.get("categories", []) if c] or ["Other"]
        categories = sorted(
            categories,
            key=lambda c: (rank_map.get(c.lower(), default_rank), c.lower()),
        )
        paper["categories"] = categories

        if len(categories) == 1:
            primary = categories[0]
        else:
            primary = next((c for c in categories if c.lower() in rank_map), categories[0])

        paper["primary_category"] = primary
        paper["primary_category_anchor"] = _category_anchor(primary)
        paper["primary_category_rank"] = rank_map.get(primary.lower(), default_rank)

    return sorted(
        papers,
        key=lambda p: (
            p.get("primary_category_rank", default_rank),
            -float(p.get("score", 0.0)),
            p.get("title", "").lower(),
        ),
    )


class ArxivExtension(BaseExtension):
    key = "arxiv"
    title = "arXiv Papers"
    icon = "📄"
    payload_key = "papers"

    def __init__(self, config: dict, llm_client: Any = None) -> None:
        super().__init__(config, llm_client)
        self._raw_count = 0
        self._scored_count = 0

    def fetch(self) -> list[dict]:
        print("Fetching arXiv papers...")
        papers = fetch_papers(
            categories=self.config.get("categories", []),
            must_include=self.config.get("must_include", []),
            max_results=self.config.get("max_papers_per_run", 500),
        )
        self._raw_count = len(papers)
        print(f"  After keyword filter: {self._raw_count}")
        return papers

    def process(self, items: list[dict]) -> list[dict]:
        if self.config.get("dry_run"):
            print(f"  [dry-run] skipping LLM scoring/summarisation for {len(items)} papers")
            self._scored_count = len(items)
            return items

        scoring_model = self.config["llm_scoring_model"]
        summary_model = self.config["llm_summarization_model"]
        threshold = self.config.get("llm_score_threshold", 7)
        lang = self.config.get("language", "en")

        scored = score_papers(items, self.llm, scoring_model, threshold)
        self._scored_count = len(scored)
        print(f"  After LLM filter: {self._scored_count}")

        summarised = summarize_papers(scored, self.llm, summary_model, lang)

        if summarised:
            print("Fetching arXiv figure previews...")
            summarised = enrich_papers_with_figures(summarised)

        return summarised

    def render(self, items: list[dict]) -> FeedSection:
        prepared = _prepare_papers(items, self.config.get("categories", []))
        return self.build_section(
            items=prepared,
            meta={
                "papers_fetched": self.config.get("max_papers_per_run", 500),
                "papers_after_keyword_filter": self._raw_count,
                "papers_after_llm_filter": self._scored_count,
                "count": len(prepared),
            },
        )
