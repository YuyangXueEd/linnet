"""GitHub Trending repo summarizer."""

from typing import Any

from pipeline.utils import _fallback_text, call_llm_summarize, lang_instruction


def _summarize_one_github_repo(repo: dict, client: Any, model: str, lang: str = "en") -> dict:
    prompt = (
        f"Summarize the core function and key features of the following GitHub repository "
        f"{lang_instruction(lang)}, in one sentence (≤60 words):\n\n"
        f"Repo: {repo['full_name']}\nDescription: {repo['description']}"
    )
    repo["summary"] = call_llm_summarize(client, model, prompt, max_tokens=120)
    return repo


def summarize_github_repos(
    repos: list[dict], client: Any, model: str, lang: str = "en"
) -> list[dict]:
    """Summarize GitHub trending repos sequentially to avoid rate limiting."""
    if not repos:
        return []
    results = []
    for r in repos:
        try:
            results.append(_summarize_one_github_repo(r, client, model, lang))
        except Exception:
            r["summary"] = _fallback_text("Repo", lang)
            results.append(r)
    return results
