"""Hacker News extension — fetches and summarises top AI/ML stories."""

from extensions.base import BaseExtension, FeedSection
from extensions.hacker_news.collector import fetch_stories
from extensions.hacker_news.summarizer import summarize_hn_stories


class HackerNewsExtension(BaseExtension):
    key = "hacker_news"
    title = "Hacker News"
    icon = "🔥"

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
        if self.config.get("dry_run"):
            print(f"  [dry-run] skipping LLM summarisation for {len(items)} HN stories")
            return items
        summary_model = self.config["llm_summarization_model"]
        lang = self.config.get("language", "en")
        prompts = self.config.get("prompts", {})
        return summarize_hn_stories(
            items,
            self.llm,
            summary_model,
            lang,
            prompt_template=prompts.get("hacker_news_summary"),
        )

    def render(self, items: list[dict]) -> FeedSection:
        return self.build_section(
            items=items,
            meta={"count": len(items)},
        )
