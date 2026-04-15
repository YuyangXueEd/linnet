"""Hacker News story summarizer."""

from typing import Any

from pipeline.utils import _fallback_text, call_llm_summarize, lang_instruction


def _summarize_one_hn(story: dict, client: Any, model: str, lang: str = "en") -> dict:
    prompt = (
        f"Summarize the core content of the following tech news story "
        f"{lang_instruction(lang)}, in one sentence (≤50 words):\n\n"
        f"Title: {story['title']}\nURL: {story.get('url', '')}"
    )
    story["summary"] = call_llm_summarize(client, model, prompt, max_tokens=100)
    return story


def summarize_hn_story(story: dict, client: Any, model: str, lang: str = "en") -> dict:
    return _summarize_one_hn(story, client, model, lang)


def summarize_hn_stories(
    stories: list[dict], client: Any, model: str, lang: str = "en"
) -> list[dict]:
    """Summarize HN stories sequentially to avoid rate limiting."""
    if not stories:
        return []
    results = []
    for s in stories:
        try:
            results.append(_summarize_one_hn(s, client, model, lang))
        except Exception:
            s["summary"] = _fallback_text("Story", lang)
            results.append(s)
    return results
