"""
Base classes for the extension system.

FeedSection  — standardised container returned by every extension.
BaseExtension — abstract base class all extensions must subclass.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FeedSection:
    """
    The output of one extension for one pipeline run.

    key   — unique snake_case identifier (e.g. "arxiv", "hacker_news").
             The orchestrator uses this to slot items into the daily payload.
    title — human-readable section heading used in rendered output.
    items — list of processed item dicts; schema is extension-specific and
             must match what the Jinja2 templates expect for this section.
    meta  — optional stats/counters (e.g. fetched, filtered, duration).
    """

    key: str
    title: str
    items: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


class BaseExtension(ABC):
    """
    Abstract base for all extensions.

    Subclasses must:
      - Set class-level ``key``  (unique snake_case string)
      - Set class-level ``title`` (display name)
      - Implement ``fetch()``
      - Implement ``render()``
      - Optionally override ``process()`` for scoring / summarising

    The ``llm_client`` passed to ``__init__`` is an OpenAI-compatible client
    (or None for extensions that do not need LLM calls).

    Config layout (merged slice from sources.yaml + keywords.yaml):
    {
        "enabled": true,
        ...source-specific options...
        "llm_scoring_model":      "...",   # injected by orchestrator
        "llm_summarization_model": "...",  # injected by orchestrator
    }
    """

    key: str = ""
    title: str = ""

    def __init__(self, config: dict, llm_client: Any = None) -> None:
        self.config = config
        self.llm = llm_client

    @property
    def enabled(self) -> bool:
        return self.config.get("enabled", True)

    @abstractmethod
    def fetch(self) -> list[dict]:
        """Pull raw items from the data source. No LLM calls here."""
        ...

    def process(self, items: list[dict]) -> list[dict]:
        """
        Score, filter, and summarise items.

        Default implementation is a pass-through.  Override when the
        extension needs LLM-assisted scoring or summarisation.
        """
        return items

    @abstractmethod
    def render(self, items: list[dict]) -> FeedSection:
        """
        Package processed items into a FeedSection.

        The items list passed here is already filtered and enriched by
        process(). render() must not perform any network or LLM calls.
        """
        ...

    def run(self) -> FeedSection:
        """
        Full pipeline: fetch → process → render.

        The orchestrator calls this method.  If the extension is disabled
        it returns an empty FeedSection without calling fetch/process/render.
        """
        if not self.enabled:
            return FeedSection(key=self.key, title=self.title)
        items = self.fetch()
        items = self.process(items)
        return self.render(items)
