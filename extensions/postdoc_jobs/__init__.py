"""postdoc_jobs extension — fetches, scores, and summarises postdoc and academic job postings."""

from extensions.base import BaseExtension, FeedSection
from extensions.postdoc_jobs.collector import fetch_jobs
from extensions.postdoc_jobs.scorer import score_jobs
from extensions.postdoc_jobs.summarizer import summarize_jobs


class PostdocJobsExtension(BaseExtension):
    key = "postdoc_jobs"
    title = "Postdoc Jobs"
    icon = "💼"
    payload_key = "jobs"

    def fetch(self) -> list[dict]:
        print("Fetching postdoc jobs...")
        jobs = fetch_jobs(
            rss_sources=self.config.get("rss_sources", []),
            filter_keywords=self.config.get("filter_keywords", []),
            exclude_keywords=self.config.get("exclude_keywords", []),
            jina_sources=self.config.get("jina_sources", []),
        )
        return jobs

    def process(self, items: list[dict]) -> list[dict]:
        if self.config.get("dry_run"):
            print(f"  [dry-run] skipping LLM processing for {len(items)} jobs")
            return items

        scoring_model = self.config["llm_scoring_model"]
        summary_model = self.config["llm_summarization_model"]
        threshold = self.config.get("llm_score_threshold", 7)
        lang = self.config.get("language", "en")

        scored = score_jobs(items, self.llm, scoring_model, threshold)
        summarised = summarize_jobs(scored, self.llm, summary_model, lang)
        print(f"  Postdoc Jobs: {len(summarised)}")
        return summarised

    def render(self, items: list[dict]) -> FeedSection:
        return self.build_section(
            items=items,
            meta={"count": len(items)},
        )
