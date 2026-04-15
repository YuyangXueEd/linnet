"""
<MySink> sink — one-line description of where this delivers the digest.

Required environment variable(s):
  MY_SINK_API_KEY  — description of credential and where to get it

Config block in sources.yaml:
  sinks:
    my_sink:
      enabled: true
      # add any display/limit options here
"""

import os

# import httpx  # or whatever HTTP client you need
from sinks.base import BaseSink


class MySink(BaseSink):
    # ── Identity ─────────────────────────────────────────────────────────
    # Must match the key under sinks: in sources.yaml
    key = "my_sink"

    # ── deliver() ────────────────────────────────────────────────────────
    def deliver(self, payload: dict) -> None:
        """
        Format and post the payload to the external service.

        payload keys (all optional — check before accessing):
          date            str           "YYYY-MM-DD"
          papers          list[dict]    arXiv papers
          hacker_news     list[dict]    HN stories
          github_trending list[dict]    GitHub trending repos
          jobs            list[dict]    academic jobs (if enabled)
          supervisor_updates list[dict] supervisor page changes (if enabled)
          meta            dict          {"duration_seconds": N, "llm_model": "…"}

        Raise an exception on unrecoverable errors — the orchestrator will
        catch and log without aborting the rest of the pipeline.
        """
        # 1. Read credentials from environment (never from self.config)
        api_key = os.environ.get("MY_SINK_API_KEY", "")
        if not api_key:
            raise OSError("MY_SINK_API_KEY is not set")

        # 2. Read display limits from config (with sensible defaults)
        max_papers = self.config.get("max_papers", 5)

        # 3. Build your payload / message
        date = payload.get("date", "")
        papers = payload.get("papers", [])[:max_papers]
        message = self._format_message(date, papers)

        # 4. Deliver
        # resp = httpx.post("https://api.example.com/post", json={"text": message},
        #                   headers={"Authorization": f"Bearer {api_key}"}, timeout=15)
        # resp.raise_for_status()
        raise NotImplementedError("Replace this with your actual delivery logic")

    # ── Helpers ──────────────────────────────────────────────────────────

    def _format_message(self, date: str, papers: list[dict]) -> str:
        """Build the text/payload to send. Keep under service character limits."""
        lines = [f"Daily Digest — {date}", ""]
        for p in papers:
            title = p.get("title", "Untitled")
            url = p.get("url", "")
            lines.append(f"• {title}  {url}")
        return "\n".join(lines)
