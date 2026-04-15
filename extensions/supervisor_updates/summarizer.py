"""Supervisor page update summarizer."""

from typing import Any

from pipeline.utils import call_llm_summarize, lang_instruction


def summarize_supervisor_update(update: dict, client: Any, model: str, lang: str = "en") -> dict:
    prompt = (
        f"The following is the latest content from a supervisor's homepage. "
        f"Summarize {lang_instruction(lang)} (≤80 words) whether there are new position openings, "
        f"including research direction, deadlines, and key details:\n\n"
        f"Supervisor: {update['name']} ({update['institution']})\n"
        f"Page content: {update['page_text'][:2000]}"
    )
    update["change_summary"] = call_llm_summarize(client, model, prompt)
    return update
