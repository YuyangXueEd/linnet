"""GitHub Trending extension — fetches and summarises trending AI/ML repos."""

from collectors.github_trending_collector import fetch_github_trending
from pipeline.summarizer import summarize_github_repos
from extensions.base import BaseExtension, FeedSection


class GitHubTrendingExtension(BaseExtension):
    key = "github_trending"
    title = "GitHub Trending"

    def fetch(self) -> list[dict]:
        print("Fetching GitHub trending...")
        max_repos = self.config.get("max_repos", 15)
        repos = fetch_github_trending(max_repos=max_repos)
        print(f"  GitHub trending: {len(repos)} repos")
        return repos

    def process(self, items: list[dict]) -> list[dict]:
        summary_model = self.config["llm_summarization_model"]
        return summarize_github_repos(items, self.llm, summary_model)

    def render(self, items: list[dict]) -> FeedSection:
        return FeedSection(
            key=self.key,
            title=self.title,
            items=items,
            meta={"count": len(items)},
        )
