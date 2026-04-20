"""
GitHub Trending collector.

Uses two approaches:
1. GitHub Search API — find repos created/updated recently with AI/ML topics, sorted by stars
2. Scrape https://github.com/trending for the "today" trending list

The Search API is rate-limited to 10 req/min unauthenticated.
We use a GITHUB_TOKEN env var if available (5000 req/hr with auth).
"""

import os
import re
from datetime import UTC
from html import unescape
from typing import Any

import httpx

_SEARCH_URL = "https://api.github.com/search/repositories"
_TRENDING_URL = "https://github.com/trending"

_AI_TOPICS = [
    "machine-learning",
    "deep-learning",
    "computer-vision",
    "large-language-model",
    "diffusion-model",
    "medical-imaging",
    "transformer",
    "llm",
]

_AI_KEYWORDS = [
    "llm",
    "large language model",
    "diffusion",
    "computer vision",
    "medical imaging",
    "deep learning",
    "neural network",
    "transformer",
    "gpt",
    "bert",
    "stable diffusion",
    "multimodal",
    "vision",
]


def _get_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    return {"Accept": "application/vnd.github+json"}


def _is_ai_related(
    name: str,
    description: str,
    topics: list[str],
    ai_keywords: list[str] | None = None,
    ai_topics: list[str] | None = None,
) -> bool:
    kws = ai_keywords if ai_keywords is not None else _AI_KEYWORDS
    topic_set = ai_topics if ai_topics is not None else _AI_TOPICS
    text = f"{name} {description}".lower()
    if any(kw in text for kw in kws):
        return True
    if any(t in topic_set for t in topics):
        return True
    return False


def _clean_html_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_repo_count(article: str, suffix: str) -> int:
    match = re.search(
        rf'href="/[^"]+/{suffix}"[^>]*>.*?</svg>\s*([\d,]+)\s*</a>',
        article,
        re.DOTALL,
    )
    return int(match.group(1).replace(",", "")) if match else 0


def _parse_trending_article(article: str) -> dict[str, Any] | None:
    # Look for the repo link inside the h2 heading to avoid sponsor or login links
    h2_match = re.search(r"<h2[^>]*>(.*?)</h2>", article, re.DOTALL | re.IGNORECASE)
    if not h2_match:
        return None

    hrefs = re.findall(r'href="(/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"', h2_match.group(1))
    if not hrefs:
        return None
    full_name = hrefs[0].lstrip("/")

    desc_match = re.search(r"<p\b[^>]*>(.*?)</p>", article, re.DOTALL)
    description = _clean_html_text(desc_match.group(1)) if desc_match else ""

    stars_match = re.search(r"([\d,]+)\s*stars?\s*today", article, re.IGNORECASE)
    stars_today = int(stars_match.group(1).replace(",", "")) if stars_match else 0

    total_stars = _extract_repo_count(article, "stargazers")

    lang_match = re.search(r'itemprop="programmingLanguage"[^>]*>\s*(.*?)\s*</span>', article)
    language_tag = _clean_html_text(lang_match.group(1)) if lang_match else ""

    return {
        "full_name": full_name,
        "url": f"https://github.com/{full_name}",
        "description": description,
        "stars_today": stars_today,
        "total_stars": total_stars,
        "language": language_tag,
        "topics": [],
        "summary": "",
    }


def fetch_trending_via_search(
    max_repos: int = 20,
    days_back: int = 1,
    ai_topics: list[str] | None = None,
    ai_keywords: list[str] | None = None,
    max_topics: int = 5,
    request_timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """
    Use GitHub Search API to find recently-created repos with high star velocity.
    Queries multiple AI topics and deduplicates.
    """
    from datetime import datetime, timedelta

    topics = ai_topics if ai_topics is not None else _AI_TOPICS
    cutoff = (datetime.now(UTC) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    seen: set[int] = set()
    repos: list[dict] = []

    with httpx.Client(timeout=request_timeout, headers=_get_headers()) as client:
        for topic in topics[:max_topics]:  # limit to avoid rate limit
            try:
                resp = client.get(
                    _SEARCH_URL,
                    params={
                        "q": f"topic:{topic} created:>{cutoff}",
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 10,
                    },
                )
                if resp.status_code == 403:
                    break  # rate limited
                resp.raise_for_status()
                for item in resp.json().get("items", []):
                    rid = item["id"]
                    if rid not in seen:
                        seen.add(rid)
                        repos.append(_parse_repo(item))
            except Exception:
                continue

    # sort by stars descending, take top N
    repos.sort(key=lambda r: r["total_stars"], reverse=True)
    return repos[:max_repos]


def fetch_trending_via_scrape(
    language: str = "",
    since: str = "daily",
    request_timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """
    Scrape github.com/trending for today's trending repos.
    Filters to AI/ML related ones.
    """
    url = _TRENDING_URL
    params = {"since": since}
    if language:
        url = f"{_TRENDING_URL}/{language}"

    try:
        with httpx.Client(timeout=request_timeout, headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            html = resp.text
    except Exception:
        return []

    repos = []
    # Parse repo entries from the trending page HTML
    # Each repo is in an <article class="Box-row"> block
    articles = re.findall(
        r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>', html, re.DOTALL
    )
    for article in articles:
        repo = _parse_trending_article(article)
        if not repo:
            continue
        repos.append(repo)

    return repos


def _parse_repo(item: dict) -> dict[str, Any]:
    return {
        "full_name": item["full_name"],
        "url": item["html_url"],
        "description": item.get("description") or "",
        "stars_today": 0,  # search API doesn't give daily stars
        "total_stars": item.get("stargazers_count", 0),
        "language": item.get("language") or "",
        "topics": item.get("topics", []),
        "summary": "",
    }


def fetch_github_trending(
    max_repos: int = 15,
    language: str = "",
    use_scrape: bool = True,
    ai_topics: list[str] | None = None,
    ai_keywords: list[str] | None = None,
    max_topics: int = 5,
    request_timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """
    Fetch AI/ML trending repos.
    Tries scraping first (has stars-today data), falls back to Search API.
    """
    if use_scrape:
        repos = fetch_trending_via_scrape(language=language, request_timeout=request_timeout)
        if repos:
            return repos[:max_repos]

    return fetch_trending_via_search(
        max_repos=max_repos,
        ai_topics=ai_topics,
        ai_keywords=ai_keywords,
        max_topics=max_topics,
        request_timeout=request_timeout,
    )
