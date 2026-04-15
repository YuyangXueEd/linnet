"""Supervisor extension — watches advisor/lab pages for content changes."""

from extensions.base import BaseExtension, FeedSection
from extensions.supervisor_updates.collector import fetch_supervisor_updates
from extensions.supervisor_updates.summarizer import summarize_supervisor_update


class SupervisorExtension(BaseExtension):
    key = "supervisor_updates"
    title = "Supervisor Updates"
    icon = "👨‍🏫"

    def fetch(self) -> list[dict]:
        supervisors = self.config.get("supervisors", [])
        if not supervisors:
            return []
        print(f"Checking {len(supervisors)} supervisor pages...")
        return fetch_supervisor_updates(supervisors)

    def process(self, items: list[dict]) -> list[dict]:
        if self.config.get("dry_run"):
            print(f"  [dry-run] skipping LLM summarisation for {len(items)} supervisor updates")
            return items

        summary_model = self.config["llm_summarization_model"]
        lang = self.config.get("language", "en")
        return [summarize_supervisor_update(u, self.llm, summary_model, lang) for u in items]

    def render(self, items: list[dict]) -> FeedSection:
        return self.build_section(
            items=items,
            meta={"count": len(items)},
        )
