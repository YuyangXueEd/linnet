"""
MyDailyUpdater extension template — copy this *package* to start a new extension.

Usage
-----
1. Copy the entire directory:
       cp -r extensions/_template extensions/my_source

2. Rename the class and set the three required attributes:
       key   = "my_source"       # must be unique and match sources.yaml exactly
       title = "My Source"       # section heading shown in the rendered digest
       icon  = "🧩"              # shown in the quick-nav and section heading

3. Implement the three pipeline methods below (fetch, process, render).

4. Register, configure, and test — see extensions/README.md for the full checklist.

Self.config reference
---------------------
The orchestrator merges your sources.yaml block with config/extensions/{key}.yaml
and injects additional keys. Everything below is available via self.config:

    self.config["enabled"]                  bool   — False if disabled in sources.yaml
    self.config["language"]                 str    — output language code, e.g. "en"
    self.config["llm_scoring_model"]        str    — model name for scoring calls
    self.config["llm_summarization_model"]  str    — model name for summarisation calls
    self.config["dry_run"]                  bool   — True when --dry-run flag is set
    self.config.get("my_option", default)          — any key you put in sources.yaml

    Never put API keys or secrets in config — read them from os.environ only.
"""

import os

from extensions.base import BaseExtension, FeedSection
from extensions._template.collector import fetch_items


class TemplateExtension(BaseExtension):
    # ── Required class attributes ──────────────────────────────────────────────
    key = "my_source"       # snake_case; must match sources.yaml key exactly
    title = "My Source"     # shown as the section heading in the rendered digest
    icon = "🧩"             # shown in the quick-nav and section heading

    # ── Step 1: fetch ──────────────────────────────────────────────────────────
    def fetch(self) -> list[dict]:
        """
        Pull raw items from the data source. Return a list of plain dicts.

        Contract:
          - No LLM calls here (cost + latency belong in process()).
          - Return [] if the source is unavailable — do not raise.
          - Read config with self.config.get("option", default).
          - Read credentials from os.environ only — never from config files.
          - Print a brief status line so pipeline logs are informative.

        Output item dict — define the schema your template expects.
        Every key you use in template.md.j2 must be present here (use None
        for optional fields so the template can guard with `{% if item.field %}`).

        Example schema:
            {
                "id":          str,          # unique identifier
                "title":       str,          # display title
                "url":         str,          # canonical link
                "description": str | None,   # raw description, pre-summarisation
                "summary":     str | None,   # filled in by process()
                "score":       float | None, # filled in by process()
            }
        """
        max_items: int = self.config.get("max_items", 20)
        api_key: str = os.environ.get("MY_SOURCE_API_KEY", "")

        items = fetch_items(max_items=max_items, api_key=api_key)

        print(f"  {self.title}: fetched {len(items)} items")
        return items

    # ── Step 2: process (optional) ─────────────────────────────────────────────
    def process(self, items: list[dict]) -> list[dict]:
        """
        Score, filter, or summarise items using the LLM.

        Contract:
          - ALWAYS check dry_run first and skip ALL LLM calls when set.
          - Use self.llm for LLM calls — it is an OpenAI-compatible client.
          - Read self.config["llm_summarization_model"] for the model name.
          - Read self.config.get("language", "en") for the output language.
          - Return the filtered/enriched list (may be shorter than input).

        If your extension needs no LLM processing, delete this method entirely.
        The base class provides a pass-through default.
        """
        if self.config.get("dry_run"):
            print(f"  [dry-run] skipping LLM calls for {len(items)} {self.title} items")
            return items

        if not items:
            return items

        model: str = self.config["llm_summarization_model"]
        lang: str = self.config.get("language", "en")
        lang_note = f" Respond in {lang}." if lang != "en" else ""

        results = []
        for item in items:
            try:
                resp = self.llm.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"Summarise the following in one sentence.{lang_note}\n\n"
                                f"{item.get('description', '')}"
                            ),
                        }
                    ],
                    max_tokens=80,
                )
                item["summary"] = resp.choices[0].message.content.strip()
            except Exception as exc:
                item["summary"] = item.get("description", "")
                print(f"  {self.title}: summarise error — {exc}")
            results.append(item)

        return results

    # ── Step 3: render ─────────────────────────────────────────────────────────
    def render(self, items: list[dict]) -> FeedSection:
        """
        Package processed items into a FeedSection for the daily digest.

        Contract:
          - No network or LLM calls here.
          - Put useful counters in meta (shown in pipeline logs).
          - The items list is exactly what your Jinja2 template receives as
            `sec["items"]` — field names must match template.md.j2 exactly.
        """
        return self.build_section(
            items=items,
            meta={"count": len(items)},
        )
