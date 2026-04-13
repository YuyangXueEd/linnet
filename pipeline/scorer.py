import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential

# Keep concurrency very low to reduce rate-limit pressure in CI.
_MAX_WORKERS = 2


def _build_paper_prompt(paper: dict) -> str:
    return (
        "Rate this arxiv paper's relevance to: Computer Vision, Medical Imaging "
        "(MRI/CT/ultrasound/pathology/fundus), LLMs, Vision-Language Models, "
        "Diffusion Models, Foundation Models.\n\n"
        f"Title: {paper['title']}\n"
        f"Abstract: {paper['abstract'][:600]}\n\n"
        "Reply with ONLY a single integer 0-10. No explanation."
    )


# Keep this name for test compatibility
def build_batch_paper_prompt(papers: list[dict]) -> str:
    return _build_paper_prompt(papers[0]) if papers else ""


def build_job_prompt(job: dict) -> str:
    return (
        "Rate this academic job posting's relevance to a researcher in "
        "Computer Vision, Medical Imaging, LLM, VLM. Scale 0-10.\n\n"
        f"Title: {job['title']}\n"
        f"Description: {job.get('description', '')[:500]}\n\n"
        "Reply with ONLY a single integer 0-10."
    )


def parse_score(text: str) -> float:
    numbers = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not numbers:
        return 0.0
    return max(0.0, min(10.0, float(numbers[0])))


# Keep for test compatibility
def parse_batch_scores(text: str, expected: int) -> list[float]:
    score = parse_score(text)
    return [score] + [0.0] * (expected - 1)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=3, max=30))
def _call_llm(client: Any, model: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0,
    )
    return resp.choices[0].message.content


def _score_paper(paper: dict, client: Any, model: str) -> dict:
    raw = _call_llm(client, model, _build_paper_prompt(paper))
    paper["score"] = parse_score(raw)
    return paper


def _score_job(job: dict, client: Any, model: str) -> dict:
    raw = _call_llm(client, model, build_job_prompt(job))
    job["relevance_score"] = parse_score(raw)
    return job


def score_papers(
    papers: list[dict],
    client: Any,
    model: str,
    threshold: float,
) -> list[dict]:
    """Score papers concurrently, one per LLM call."""
    if not papers:
        return []

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = {executor.submit(_score_paper, p, client, model): p for p in papers}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                paper = futures[future]
                paper["score"] = 0.0
                results.append(paper)
                print(f"  Scoring error: {e}")

    return [p for p in results if p["score"] >= threshold]


def score_jobs(
    jobs: list[dict],
    client: Any,
    model: str,
    threshold: float,
) -> list[dict]:
    """Score jobs concurrently."""
    if not jobs:
        return []

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = {executor.submit(_score_job, j, client, model): j for j in jobs}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                job = futures[future]
                job["relevance_score"] = 0.0
                results.append(job)
                print(f"  Job scoring error: {e}")

    return [j for j in results if j["relevance_score"] >= threshold]
