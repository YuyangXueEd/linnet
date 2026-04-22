"""ArXiv paper relevance scorer."""

from typing import Any

from pipeline.utils import call_llm_scoring, parse_score

# Fallback prompt used when no categories/keywords are configured.
# Users can override the full prompt via sources.yaml → llm.prompts.arxiv_score.
# Available placeholders: {title}, {abstract}
_GENERIC_SCORE_PROMPT = (
    "Rate this arXiv paper's relevance to the user's configured research area.\n\n"
    "Title: {title}\n"
    "Abstract: {abstract}\n\n"
    "Reply with ONLY a single integer 0-10. No explanation."
)


def _build_default_prompt(categories: list[str], must_include: list[str]) -> str:
    """Build a scoring prompt from arxiv.yaml config so any research domain works."""
    parts: list[str] = []
    if categories:
        parts.append(f"arXiv categories: {', '.join(categories)}")
    if must_include:
        parts.append(f"key topics: {', '.join(must_include)}")
    if not parts:
        return _GENERIC_SCORE_PROMPT
    domain = "; ".join(parts)
    return (
        f"Rate this arXiv paper's relevance to a researcher interested in {domain}.\n\n"
        "Title: {title}\n"
        "Abstract: {abstract}\n\n"
        "Reply with ONLY a single integer 0-10. No explanation."
    )


def _build_paper_prompt(
    paper: dict,
    prompt_template: str | None = None,
    categories: list[str] | None = None,
    must_include: list[str] | None = None,
) -> str:
    if prompt_template:
        template = prompt_template
    else:
        template = _build_default_prompt(categories or [], must_include or [])
    return template.format(
        title=paper["title"],
        abstract=paper["abstract"][:600],
    )


def build_batch_paper_prompt(papers: list[dict]) -> str:
    return _build_paper_prompt(papers[0]) if papers else ""


def parse_batch_scores(text: str, expected: int) -> list[float]:
    score = parse_score(text)
    return [score] + [0.0] * (expected - 1)


def _score_paper(
    paper: dict,
    client: Any,
    model: str,
    prompt_template: str | None = None,
    categories: list[str] | None = None,
    must_include: list[str] | None = None,
) -> dict:
    raw = call_llm_scoring(
        client, model, _build_paper_prompt(paper, prompt_template, categories, must_include)
    )
    paper["score"] = parse_score(raw)
    return paper


def score_papers(
    papers: list[dict],
    client: Any,
    model: str,
    threshold: float,
    prompt_template: str | None = None,
    categories: list[str] | None = None,
    must_include: list[str] | None = None,
) -> list[dict]:
    """Score papers sequentially to avoid rate limiting."""
    if not papers:
        return []

    results: list[dict] = []
    for p in papers:
        try:
            results.append(
                _score_paper(p, client, model, prompt_template, categories, must_include)
            )
        except Exception as e:
            p["score"] = 0.0
            results.append(p)
            print(f"  Scoring error: {e}")

    return [p for p in results if p["score"] >= threshold]
