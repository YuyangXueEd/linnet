"""
Slack sink — posts the daily digest as a Block Kit message via Incoming Webhook.

Required secret (GitHub Actions / environment variable):
  SLACK_WEBHOOK_URL  — Incoming Webhook URL from your Slack App configuration.
                       https://api.slack.com/messaging/webhooks

Config block in sources.yaml:
  sinks:
    slack:
      enabled: true
      max_papers: 5     # top papers to include (default 5)
      max_hn: 3         # top HN stories to include (default 3)
      max_github: 3     # top GitHub repos to include (default 3)
"""

import os

import httpx

from sinks.base import BaseSink


class SlackSink(BaseSink):
    key = "slack"

    def deliver(self, payload: dict) -> None:
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
        if not webhook_url:
            raise OSError("SLACK_WEBHOOK_URL is not set")

        blocks = self._build_blocks(payload)
        resp = httpx.post(webhook_url, json={"blocks": blocks}, timeout=15)
        resp.raise_for_status()

    # ------------------------------------------------------------------
    # Block Kit builder
    # ------------------------------------------------------------------

    def _build_blocks(self, payload: dict) -> list[dict]:
        date = payload.get("date", "")
        papers = payload.get("papers", [])
        hn = payload.get("hacker_news", [])
        jobs = payload.get("jobs", [])
        github = payload.get("github_trending", [])
        meta = payload.get("meta", {})

        max_papers = self.config.get("max_papers", 5)
        max_hn = self.config.get("max_hn", 3)
        max_github = self.config.get("max_github", 3)

        blocks: list[dict] = []

        # ── Header ──────────────────────────────────────────────────────
        blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📰 Daily Digest — {date}"},
            }
        )

        # ── Stats bar ───────────────────────────────────────────────────
        stats = (
            f"*{len(papers)}* papers  •  "
            f"*{len(hn)}* HN stories  •  "
            f"*{len(jobs)}* jobs  •  "
            f"*{len(github)}* trending repos"
        )
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": stats}})
        blocks.append({"type": "divider"})

        # ── arXiv papers ────────────────────────────────────────────────
        if papers:
            blocks.append(_header_section("📄 Top arXiv Papers"))
            for p in papers[:max_papers]:
                title = p.get("title", "Untitled")
                summary = p.get("abstract", "")
                url = p.get("url", "")
                score = p.get("score", "")
                cat = p.get("primary_category", "")
                score_str = f"  `{cat}` · score {score}" if score else f"  `{cat}`"
                link = f"<{url}|{_escape(title)}>" if url else _escape(title)
                text = f"*{link}*{score_str}\n{_escape(summary)}"
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text}})
            blocks.append({"type": "divider"})

        # ── Hacker News ─────────────────────────────────────────────────
        if hn:
            blocks.append(_header_section("🔥 Hacker News"))
            lines = []
            for s in hn[:max_hn]:
                title = _truncate(s.get("title", ""), 80)
                url = s.get("url", "") or s.get("comments_url", "")
                summary = _truncate(s.get("summary", ""), 200)
                score = s.get("score", "")
                link = f"<{url}|{_escape(title)}>" if url else _escape(title)
                lines.append(f"• {link}  `{score} pts`\n  {_escape(summary)}")
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "\n".join(lines)},
                }
            )
            blocks.append({"type": "divider"})

        # ── GitHub Trending ─────────────────────────────────────────────
        if github:
            blocks.append(_header_section("⭐ GitHub Trending"))
            lines = []
            for r in github[:max_github]:
                name = r.get("full_name", "")
                url = r.get("url", "")
                summary = _truncate(r.get("summary", ""), 200)
                stars_today = r.get("stars_today", 0)
                lang = r.get("language", "")
                meta_str = "  ".join(
                    filter(
                        None,
                        [
                            f"`{lang}`" if lang else "",
                            f"+{stars_today}★ today" if stars_today else "",
                        ],
                    )
                )
                link = f"<{url}|{_escape(name)}>" if url else _escape(name)
                lines.append(f"• {link}  {meta_str}\n  {_escape(summary)}")
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "\n".join(lines)},
                }
            )
            blocks.append({"type": "divider"})

        # ── Jobs summary ─────────────────────────────────────────────────
        if jobs:
            blocks.append(_header_section("💼 Academic Jobs"))
            lines = []
            for j in jobs[:3]:
                title = _truncate(j.get("title", ""), 80)
                inst = _truncate(j.get("institution", ""), 60)
                url = j.get("url", "")
                link = f"<{url}|{_escape(title)}>" if url else _escape(title)
                lines.append(f"• {link}  —  {_escape(inst)}")
            if len(jobs) > 3:
                lines.append(f"_…and {len(jobs) - 3} more_")
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "\n".join(lines)[:3000]},
                }
            )

        # ── Footer ───────────────────────────────────────────────────────
        duration = meta.get("duration_seconds", 0)
        model = meta.get("llm_model", "")
        footer = f"_Generated in {duration}s · {model}_"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": footer}})

        return blocks


# ── Helpers ─────────────────────────────────────────────────────────────────


def _header_section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": f"*{text}*"}}


def _escape(text: str) -> str:
    """Escape Slack mrkdwn special characters."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len characters, appending ellipsis if cut."""
    text = str(text)
    return text if len(text) <= max_len else text[: max_len - 1] + "…"
