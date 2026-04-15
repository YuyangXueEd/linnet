"""
extensions/ — pluggable extension system for Research Daily Digest.

Each extension is a self-contained unit that:
  1. fetch()   — pulls raw data from a source
  2. process() — scores, filters, summarises (may use LLM)
  3. render()  — packages results into a FeedSection

The orchestrator (main.py) calls ext.run() on every enabled extension
and assembles the results into the final daily payload.

To add a new extension:
  1. Create extensions/my_source.py subclassing BaseExtension
  2. Add it to REGISTRY below
  3. Add its config key to config/sources.yaml and config/keywords.yaml
"""

from extensions.base import BaseExtension, FeedSection
from extensions.arxiv import ArxivExtension
from extensions.hacker_news import HackerNewsExtension
from extensions.jobs import JobsExtension
from extensions.supervisor import SupervisorExtension
from extensions.github_trending import GitHubTrendingExtension

# Ordered list of all known extensions.
# The orchestrator iterates this list; disabled extensions are skipped.
REGISTRY: list[type[BaseExtension]] = [
    ArxivExtension,
    HackerNewsExtension,
    JobsExtension,
    SupervisorExtension,
    GitHubTrendingExtension,
]

__all__ = [
    "BaseExtension",
    "FeedSection",
    "REGISTRY",
]
