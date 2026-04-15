"""Supervisor extension — watches advisor/lab pages for content changes."""

from collectors.supervisor_watcher import fetch_supervisor_updates
from pipeline.summarizer import summarize_supervisor_update
from extensions.base import BaseExtension, FeedSection


class SupervisorExtension(BaseExtension):
    key = "supervisor_updates"
    title = "Supervisor Updates"

    def fetch(self) -> list[dict]:
        supervisors = self.config.get("supervisors", [])
        if not supervisors:
            return []
        print(f"Checking {len(supervisors)} supervisor pages...")
        return fetch_supervisor_updates(supervisors)

    def process(self, items: list[dict]) -> list[dict]:
        summary_model = self.config["llm_summarization_model"]
        return [summarize_supervisor_update(u, self.llm, summary_model) for u in items]

    def render(self, items: list[dict]) -> FeedSection:
        return FeedSection(
            key=self.key,
            title=self.title,
            items=items,
            meta={"count": len(items)},
        )
