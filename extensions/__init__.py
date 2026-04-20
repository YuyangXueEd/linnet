"""
extensions/ — pluggable extension system for Linnet.

Each extension is a self-contained unit that:
  1. fetch()   — pulls raw data from a source
  2. process() — scores, filters, summarises (may use LLM)
  3. render()  — packages results into a FeedSection

The orchestrator (main.py) calls ext.run() on every enabled extension
and assembles the results into the final daily payload.

To add a new extension:
  1. Create extensions/my_source/ package subclassing BaseExtension
  2. Add it to REGISTRY below
  3. Add an enabled: true/false block to config/sources.yaml
  4. If the extension needs filter/keyword config, create config/extensions/my_source.yaml
"""

from extensions.arxiv import ArxivExtension
from extensions.base import BaseExtension, FeedSection
from extensions.github_trending import GitHubTrendingExtension
from extensions.hacker_news import HackerNewsExtension
from extensions.hitokoto import HitokotoExtension
from extensions.postdoc_jobs import PostdocJobsExtension
from extensions.quote_of_day import QuoteOfDayExtension
from extensions.supervisor_updates import SupervisorExtension
from extensions.weather import WeatherExtension

# Ordered list of all known extensions.
# The orchestrator iterates this list; disabled extensions are skipped.
REGISTRY: list[type[BaseExtension]] = [
    QuoteOfDayExtension,
    HitokotoExtension,
    ArxivExtension,
    HackerNewsExtension,
    GitHubTrendingExtension,
    PostdocJobsExtension,
    SupervisorExtension,
    WeatherExtension,
]

__all__ = [
    "BaseExtension",
    "FeedSection",
    "REGISTRY",
]
