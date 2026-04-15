"""Postdoc job summarizer."""

from typing import Any

from pipeline.utils import _fallback_text, call_llm_summarize, lang_instruction


def summarize_job(job: dict, client: Any, model: str, lang: str = "en") -> dict:
    description = (job.get("description", "") or "")[:1800]
    location = job.get("location", "") or "N/A"
    salary = job.get("salary", "") or "N/A"
    deadline = job.get("deadline", "") or "N/A"
    contract_type = job.get("contract_type", "") or "N/A"
    hours = job.get("hours", "") or "N/A"
    placed_on = job.get("placed_on", "") or job.get("posted_date", "") or "N/A"
    job_ref = job.get("job_ref", "") or "N/A"

    prompt = (
        f"You are an academic job posting assistant. Extract structured key points "
        f"from the posting below and respond {lang_instruction(lang)}.\n"
        "Rules:\n"
        "1) Output exactly the following 5 lines with fixed prefixes. No other text.\n"
        "2) Write 'N/A' if information is missing. Do not invent details.\n"
        "3) Be specific about technical and research directions.\n\n"
        "Output format:\n"
        "Research Area: ...\n"
        "Key Requirements: ...\n"
        "Application Info: deadline/start date, required materials, contact (if any)\n"
        "Position Details: location, contract type, workload, salary\n"
        "One-line Advice: match assessment for CV/medical imaging/LLM applicants\n\n"
        f"Title: {job['title']}\nInstitution: {job.get('institution', '')}\n"
        f"Location: {location}\nSalary: {salary}\nDeadline: {deadline}\n"
        f"Contract: {contract_type}\nHours: {hours}\nPosted: {placed_on}\nRef: {job_ref}\n"
        f"Description: {description}"
    )

    try:
        job["requirements"] = call_llm_summarize(client, model, prompt)
    except Exception:
        fallback_lines = [
            "Research Area: auto-extraction failed — see original posting.",
            "Key Requirements: check method skills, degree, and publication requirements.",
            f"Application Info: deadline {deadline}; posted {placed_on}; ref {job_ref}.",
            f"Position Details: {location}; {contract_type}; {hours}; {salary}.",
            "One-line Advice: if your area matches the job title closely, apply promptly.",
        ]
        job["requirements"] = "\n".join(fallback_lines)
    return job


def summarize_jobs(jobs: list[dict], client: Any, model: str, lang: str = "en") -> list[dict]:
    """Summarize jobs sequentially to avoid rate limiting."""
    if not jobs:
        return []
    results = []
    for j in jobs:
        try:
            results.append(summarize_job(j, client, model, lang))
        except Exception:
            j["requirements"] = _fallback_text("Job", lang)
            results.append(j)
    return results
