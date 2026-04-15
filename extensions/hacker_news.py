"""Hacker News extension — fetches and summarises top AI/ML stories."""

from collectors.hn_collector import fetch_stories
from pipeline.summarizer import summarize_hn_stories
from extensions.base import BaseExtension, FeedSection


class HackerNewsExtension(BaseExtension):
    key = "hacker_news"
    title = "Hacker News"

    def fetch(self) -> list[dict]:
        print("Fetching Hacker News...")
        stories = fetch_stories(
            keywords=self.config.get("keywords", []),
            min_score=self.config.get("min_score", 50),
            max_items=self.config.get("max_items", 20),
        )
        print(f"  HN stories: {len(stories)}")
        return stories

    def process(self, items: list[dict]) -> list[dict]:
        summary_model = self.config["llm_summarization_model"]
        return summarize_hn_stories(items, self.llm, summary_model)

    def render(self, items: list[dict]) -> FeedSection:
        return FeedSection(
            key=self.key,
            title=self.title,
            items=items,
            meta={"count": len(items)},
        )
