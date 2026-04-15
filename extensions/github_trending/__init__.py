"""GitHub Trending extension — fetches and summarises trending AI/ML repos."""

from extensions.base import BaseExtension, FeedSection
from extensions.github_trending.collector import fetch_github_trending
from extensions.github_trending.summarizer import summarize_github_repos


class GitHubTrendingExtension(BaseExtension):
    key = "github_trending"
    title = "GitHub Trending"
    icon = "⭐"

    def fetch(self) -> list[dict]:
        print("Fetching GitHub trending...")
        max_repos = self.config.get("max_repos", 15)
        repos = fetch_github_trending(max_repos=max_repos)
        print(f"  GitHub trending: {len(repos)} repos")
        return repos

    def process(self, items: list[dict]) -> list[dict]:
        if self.config.get("dry_run"):
            print(f"  [dry-run] skipping LLM summarisation for {len(items)} repos")
            return items
        summary_model = self.config["llm_summarization_model"]
        lang = self.config.get("language", "en")
        prompts = self.config.get("prompts", {})
        return summarize_github_repos(
            items,
            self.llm,
            summary_model,
            lang,
            prompt_template=prompts.get("github_summary"),
        )

    def render(self, items: list[dict]) -> FeedSection:
        return self.build_section(
            items=items,
            meta={"count": len(items)},
        )
