import os
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin

import arxiv
import httpx

_REPO = os.environ.get("GITHUB_REPOSITORY", "YuyangXueEd/Linnet")
_ARXIV_USER_AGENT = f"Linnet/1.0 (https://github.com/{_REPO})"


def keyword_match(text: str, keywords: list[str]) -> bool:
    """Return True if text contains at least one keyword (case-insensitive)."""
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)


def _clean_html_text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


_GREEK_DUPLICATE_LATEX_RE = re.compile(
    r"(["
    r"\u0370-\u03FF"
    r"\u1F00-\u1FFF"
    r"](?:\s+[A-Za-z0-9]+)?)\s+(\\[A-Za-z]+(?:\s*(?:\{[^{}]*\}|_[{][^{}]*[}]|\^[{][^{}]*[}]|_[A-Za-z0-9]+|\^[A-Za-z0-9]+))*)"
)

_LATEX_EXPR_RE = re.compile(
    r"(?<!\\\()(?<!\\\[)"
    r"(\\[A-Za-z]+(?:\s*(?:\{[^{}]*\}|_[{][^{}]*[}]|\^[{][^{}]*[}]|_[A-Za-z0-9]+|\^[A-Za-z0-9]+))*)"
)


def _normalise_caption_math(text: str) -> str:
    """
    Convert arXiv's flattened math text into KaTeX-friendly inline math.

    After tags are stripped, captions often contain duplicated text such as
    ``ρ t \\rho_{t}`` or ``μ \\mu``. We drop the duplicated unicode prefix and
    wrap the remaining LaTeX command in ``\\( ... \\)`` so KaTeX can render it.
    """
    if "\\" not in text:
        return text

    text = _GREEK_DUPLICATE_LATEX_RE.sub(r"\2", text)
    text = _LATEX_EXPR_RE.sub(r"\\( \1 \\)", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_first_figure(html: str, base_url: str) -> dict[str, str] | None:
    figures = re.findall(r"<figure\b[^>]*>(.*?)</figure>", html, re.DOTALL | re.IGNORECASE)
    for figure_html in figures:
        caption_match = re.search(
            r"<figcaption\b[^>]*>(.*?)</figcaption>", figure_html, re.DOTALL | re.IGNORECASE
        )
        if not caption_match:
            continue

        raw_caption = _clean_html_text(caption_match.group(1))
        if not re.search(r"\bFigure\s*1\b", raw_caption, re.IGNORECASE):
            continue

        image_match = re.search(r'<img\b[^>]*src="([^"]+)"', figure_html, re.IGNORECASE)
        if not image_match:
            continue

        caption = re.sub(r"^Figure\s*1\s*:\s*", "", raw_caption, flags=re.IGNORECASE).strip()
        caption = _normalise_caption_math(caption)
        return {
            "figure_url": urljoin(base_url, image_match.group(1)),
            "figure_caption": caption or raw_caption,
        }
    return None


def _parse_author_affiliations(html: str) -> list[str]:
    matches = re.findall(
        r"<meta[^>]+name=[\"']citation_author_institution[\"'][^>]+content=[\"']([^\"']+)[\"']",
        html,
        re.IGNORECASE,
    )
    cleaned = [_clean_html_text(m) for m in matches if m.strip()]
    seen: set[str] = set()
    deduped: list[str] = []
    for item in cleaned:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def enrich_paper_with_figure(
    paper: dict[str, Any],
    request_timeout: float = 20.0,
) -> dict[str, Any]:
    """Best-effort fetch of Figure 1 and author affiliations from arXiv pages."""
    paper_id = paper.get("id", "")
    if not paper_id:
        return paper

    headers = {"User-Agent": _ARXIV_USER_AGENT}

    html_url = f"https://arxiv.org/html/{paper_id}"
    try:
        response = httpx.get(html_url, timeout=request_timeout, headers=headers)
        response.raise_for_status()
        figure = _parse_first_figure(response.text, html_url)
        if figure:
            paper.update(figure)
    except Exception:
        pass

    abs_url = f"https://arxiv.org/abs/{paper_id}"
    try:
        abs_response = httpx.get(abs_url, timeout=request_timeout, headers=headers)
        abs_response.raise_for_status()
        affiliations = _parse_author_affiliations(abs_response.text)
        if affiliations:
            paper["affiliations"] = affiliations
    except Exception:
        pass

    return paper


def enrich_papers_with_figures(
    papers: list[dict[str, Any]],
    request_timeout: float = 20.0,
) -> list[dict[str, Any]]:
    return [enrich_paper_with_figure(paper, request_timeout=request_timeout) for paper in papers]


def fetch_papers(
    categories: list[str],
    must_include: list[str],
    max_results: int = 100,
    max_authors: int = 5,
    api_retries: int = 5,
    api_delay: float = 10.0,
) -> list[dict[str, Any]]:
    """
    Fetch recent papers from arxiv for given categories,
    pre-filter by must_include keywords on title+abstract.
    Returns list of paper dicts ready for LLM scoring.
    """
    if max_results == 0:
        return []

    query = " OR ".join(f"cat:{cat}" for cat in categories)
    client = arxiv.Client(num_retries=api_retries, delay_seconds=api_delay)
    client._session.headers.update({"User-Agent": _ARXIV_USER_AGENT})
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )

    papers = []
    for result in client.results(search):
        combined = f"{result.title} {result.summary}"
        if not keyword_match(combined, must_include):
            continue
        papers.append(
            {
                "id": result.entry_id.split("/abs/")[-1],
                "title": result.title,
                "authors": [a.name for a in result.authors[:max_authors]],
                "categories": list(result.categories),
                "abstract": result.summary,
                "url": result.entry_id,
                "pdf_url": result.pdf_url,
            }
        )

    return papers
