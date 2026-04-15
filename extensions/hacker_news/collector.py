from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"
_HN_ITEM_URL = "https://news.ycombinator.com/item?id={}"


def filter_stories(
    stories: list[dict],
    min_score: int,
    keywords: list[str],
) -> list[dict]:
    """Keep stories that meet score threshold AND contain at least one keyword."""
    result = []
    for s in stories:
        if s.get("points", 0) < min_score:
            continue
        title = (s.get("title") or "").lower()
        if not any(kw.lower() in title for kw in keywords):
            continue
        result.append(s)
    return result


def parse_story(raw: dict) -> dict[str, Any]:
    return {
        "id": int(raw["objectID"]),
        "title": raw.get("title", ""),
        "url": raw.get("url", ""),
        "score": raw.get("points", 0),
        "created_at": raw.get("created_at", ""),
        "comments_url": _HN_ITEM_URL.format(raw["objectID"]),
        "summary": "",  # filled by summarizer
    }


def fetch_stories(
    keywords: list[str],
    min_score: int,
    max_items: int,
    hours_back: int = 24,
) -> list[dict[str, Any]]:
    """Fetch top HN stories from Algolia API, filter by score and keywords."""
    cutoff = int((datetime.now(UTC) - timedelta(hours=hours_back)).timestamp())
    seen_ids: set[str] = set()
    all_stories: list[dict] = []

    search_terms = ["AI", "LLM", "machine learning", "computer vision", "deep learning"]
    with httpx.Client(timeout=30) as client:
        for term in search_terms:
            resp = client.get(
                _ALGOLIA_URL,
                params={
                    "query": term,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{cutoff},points>{min_score}",
                    "hitsPerPage": 50,
                },
            )
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                oid = hit.get("objectID")
                if oid and oid not in seen_ids:
                    seen_ids.add(oid)
                    all_stories.append(hit)

    filtered = filter_stories(all_stories, min_score=min_score, keywords=keywords)
    filtered.sort(key=lambda s: s.get("points", 0), reverse=True)
    return [parse_story(s) for s in filtered[:max_items]]
