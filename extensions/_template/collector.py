"""
Collector for the my_source extension.

Keep all network I/O here. The extension's fetch() method calls into this
module so the logic can be unit-tested without instantiating the extension.

Pattern used by every built-in extension:
  extensions/arxiv/collector.py   — arXiv API + HTML scraping
  extensions/hacker_news/collector.py — HN Algolia API
  extensions/github_trending/collector.py — GitHub trending scraper

Unit test example (no live network calls needed):
    def test_parse_items(requests_mock):
        requests_mock.get("https://example.com/api", json={"items": [...]})
        result = fetch_items(max_items=5, api_key="")
        assert len(result) == 5
        assert "id" in result[0]
"""


def fetch_items(max_items: int = 20, api_key: str = "") -> list[dict]:
    """
    Fetch raw items from the data source.

    Args:
        max_items: Upper bound on items to return.
        api_key:   Optional API credential (read from os.environ by the caller).

    Returns:
        List of item dicts.  Each dict must contain at minimum the fields
        declared in TemplateExtension.fetch() docstring.  Use None for
        optional fields that may not be populated until process().

    Notes:
        - Catch all network errors and return [] rather than raising.
        - Never call the LLM here.
        - Keep this function pure (no side effects other than HTTP requests).
    """
    items: list[dict] = []

    # --- your fetching logic here ---
    # Example:
    #
    # import httpx
    # try:
    #     resp = httpx.get(
    #         "https://api.example.com/feed",
    #         headers={"Authorization": f"Bearer {api_key}"},
    #         timeout=10,
    #     )
    #     resp.raise_for_status()
    #     for raw in resp.json()["items"][:max_items]:
    #         items.append({
    #             "id":          raw["id"],
    #             "title":       raw["title"],
    #             "url":         raw["url"],
    #             "description": raw.get("body", ""),
    #             "summary":     None,   # filled in by process()
    #             "score":       None,   # filled in by process()
    #         })
    # except Exception as exc:
    #     print(f"  my_source: fetch failed — {exc}")

    return items
