"""
quote_of_day — daily quote from API Ninjas (https://api-ninjas.com/api/quotes).

Set GitHub secret API_NINJAS_KEY to enable.
Falls back gracefully (empty items) when key is not set.
"""

import os

import requests

from extensions.base import BaseExtension, FeedSection


class QuoteOfDayExtension(BaseExtension):
    key = "quote_of_day"
    title = "Words for the Morning"
    icon = "✦"

    def fetch(self) -> list[dict]:
        api_key = os.environ.get("API_NINJAS_KEY", "").strip()
        if not api_key:
            return []

        category = self.config.get("category", "")
        params: dict = {}
        if category:
            params["category"] = category

        try:
            resp = requests.get(
                "https://api.api-ninjas.com/v1/quotes",
                headers={"X-Api-Key": api_key},
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                q = data[0]
                return [
                    {
                        "quote": q.get("quote", ""),
                        "author": q.get("author", ""),
                        "category": q.get("category", ""),
                    }
                ]
        except Exception as exc:
            print(f"  {self.title}: fetch failed — {exc}")
        return []

    def render(self, items: list[dict]) -> FeedSection:
        return self.build_section(items=items, meta={"count": len(items)})
