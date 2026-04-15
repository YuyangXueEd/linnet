"""ArXiv paper summarizer."""

from typing import Any

from pipeline.utils import _fallback_text, call_llm_summarize, lang_instruction


def _summarize_one_paper(paper: dict, client: Any, model: str, lang: str = "en") -> dict:
    prompt = (
        f"Summarize the core method and contribution of the following paper "
        f"{lang_instruction(lang)}, in 2-3 sentences (≤100 words):\n\n"
        f"Title: {paper['title']}\nAbstract: {paper['abstract'][:1000]}"
    )
    paper["abstract"] = call_llm_summarize(client, model, prompt)
    return paper


def summarize_paper(paper: dict, client: Any, model: str, lang: str = "en") -> dict:
    return _summarize_one_paper(paper, client, model, lang)


def summarize_papers(papers: list[dict], client: Any, model: str, lang: str = "en") -> list[dict]:
    """Summarize all papers sequentially to avoid rate limiting."""
    if not papers:
        return []
    results = []
    for p in papers:
        try:
            results.append(_summarize_one_paper(p, client, model, lang))
        except Exception as e:
            p["abstract"] = _fallback_text("Paper", lang)
            results.append(p)
            print(f"  Paper summarize error: {e}")
    return results
