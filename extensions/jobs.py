"""Jobs extension — fetches, scores, and summarises academic job postings."""

from collectors.jobs_collector import fetch_jobs
from pipeline.scorer import score_jobs
from pipeline.summarizer import summarize_jobs
from extensions.base import BaseExtension, FeedSection


class JobsExtension(BaseExtension):
    key = "jobs"
    title = "Academic Jobs"

    def fetch(self) -> list[dict]:
        print("Fetching jobs...")
        jobs = fetch_jobs(
            rss_sources=self.config.get("rss_sources", []),
            filter_keywords=self.config.get("filter_keywords", []),
            exclude_keywords=self.config.get("exclude_keywords", []),
            jina_sources=self.config.get("jina_sources", []),
        )
        return jobs

    def process(self, items: list[dict]) -> list[dict]:
        scoring_model = self.config["llm_scoring_model"]
        summary_model = self.config["llm_summarization_model"]
        threshold = self.config.get("llm_score_threshold", 7)

        scored = score_jobs(items, self.llm, scoring_model, threshold)
        summarised = summarize_jobs(scored, self.llm, summary_model)
        print(f"  Jobs: {len(summarised)}")
        return summarised

    def render(self, items: list[dict]) -> FeedSection:
        return FeedSection(
            key=self.key,
            title=self.title,
            items=items,
            meta={"count": len(items)},
        )
