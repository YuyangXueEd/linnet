"""
_template.py — starter template for a new MyDailyUpdater extension.

Copy this file to extensions/my_source.py and fill in the three methods.
Then follow the steps in extensions/README.md to register and configure it.

Quick reference:
  self.config  — your config slice merged from sources.yaml + config/extensions/{name}.yaml
  self.llm     — OpenAI-compatible client (or None if extension has no LLM)
  self.enabled — False if sources.yaml sets enabled: false for this key
"""

import os

from extensions.base import BaseExtension, FeedSection


class TemplateExtension(BaseExtension):
    # ── Required class attributes ──────────────────────────────────────────────
    key = "my_source"  # must match your config/sources.yaml key exactly
    title = "My Source"  # shown as the section heading in the rendered output
    icon = "🧩"  # shown in the quick-nav and section heading

    # ── Step 1: fetch ──────────────────────────────────────────────────────────
    def fetch(self) -> list[dict]:
        """
        Pull raw items from the data source.

        Rules:
          - No LLM calls here (cost + latency belong in process()).
          - Return a list of plain dicts; schema is up to you.
          - Read config options via self.config.get("my_option", default).
          - Read credentials from environment variables only:
              api_key = os.environ.get("MY_SOURCE_API_KEY", "")
          - If the source is unavailable, return [] rather than raising.
        """
        # Example: read a config option
        max_items = self.config.get("max_items", 20)

        # Example: read a credential
        api_key = os.environ.get("MY_SOURCE_API_KEY", "")

        items: list[dict] = []

        # --- your fetching logic here ---
        # items = fetch_from_api(api_key, max_items)

        print(f"  {self.title}: fetched {len(items)} items")
        return items

    # ── Step 2: process (optional) ─────────────────────────────────────────────
    def process(self, items: list[dict]) -> list[dict]:
        """
        Score, filter, or summarise items.

        Rules:
          - Always check dry_run first — skip LLM calls when set.
          - Use self.llm for LLM calls (OpenAI-compatible client).
          - Read language from self.config.get("language", "en").
          - Return the filtered/enriched list.

        If your extension needs no LLM processing, delete this method —
        the base class provides a pass-through default.
        """
        if self.config.get("dry_run"):
            print(f"  [dry-run] skipping LLM calls for {len(items)} {self.title} items")
            return items

        model = self.config["llm_summarization_model"]
        lang = self.config.get("language", "en")

        for item in items:
            prompt = (
                f"Summarise the following in one sentence in {lang}:\n{item.get('description', '')}"
            )
            resp = self.llm.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
            )
            item["summary"] = resp.choices[0].message.content.strip()

        return items

    # ── Step 3: render ─────────────────────────────────────────────────────────
    def render(self, items: list[dict]) -> FeedSection:
        """
        Package processed items into a FeedSection.

        Rules:
          - No network or LLM calls here.
          - Put useful counters in meta (shown in pipeline logs).
          - The items list is what the Jinja2 template will iterate over,
            so make sure the field names match what your template expects.
        """
        return self.build_section(
            items=items,
            meta={"count": len(items)},
        )
