#!/usr/bin/env python3
"""
main.py — CLI entry point for Research Daily Digest pipeline.

Usage:
    python main.py --mode daily       # full daily pipeline
    python main.py --mode weekly      # weekly rollup
    python main.py --mode monthly     # monthly rollup
    python main.py --check-today      # compact summary for SessionStart hook
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from openai import OpenAI

from collectors.arxiv_collector import fetch_papers, enrich_papers_with_figures
from collectors.github_trending_collector import fetch_github_trending
from collectors.hn_collector import fetch_stories
from collectors.jobs_collector import fetch_jobs
from collectors.supervisor_watcher import fetch_supervisor_updates
from pipeline.config_loader import load_keywords, load_sources, load_supervisors
from pipeline.scorer import score_papers, score_jobs
from pipeline.summarizer import (
    summarize_papers, summarize_hn_stories,
    summarize_jobs, summarize_supervisor_update,
    summarize_github_repos,
)
from pipeline.aggregator import build_weekly_payload, build_monthly_payload, load_daily_jsons
from publishers.data_publisher import (
    write_daily_json, write_weekly_json, write_monthly_json, build_daily_payload,
)
from publishers.pages_publisher import (
    render_daily_page, render_weekly_page, render_monthly_page,
)


def _category_anchor(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower().replace(".", "-")).strip("-") or "other"


def prepare_papers_for_rendering(papers: list[dict], preferred_categories: list[str]) -> list[dict]:
    """Assign stable primary category and sort papers by category, then score."""
    if not papers:
        return papers

    rank_map = {cat.lower(): idx for idx, cat in enumerate(preferred_categories)}
    default_rank = len(preferred_categories) + 100

    for paper in papers:
        categories = [c for c in paper.get("categories", []) if c] or ["Other"]

        # Keep configured categories first for readability in the details line.
        categories = sorted(
            categories,
            key=lambda c: (rank_map.get(c.lower(), default_rank), c.lower()),
        )
        paper["categories"] = categories

        # If there is only one category, that is always the primary category.
        if len(categories) == 1:
            primary = categories[0]
        else:
            primary = next((c for c in categories if c.lower() in rank_map), categories[0])

        paper["primary_category"] = primary
        paper["primary_category_anchor"] = _category_anchor(primary)
        paper["primary_category_rank"] = rank_map.get(primary.lower(), default_rank)

    return sorted(
        papers,
        key=lambda p: (
            p.get("primary_category_rank", default_rank),
            -float(p.get("score", 0.0)),
            p.get("title", "").lower(),
        ),
    )


def get_openrouter_client(sources_cfg: dict) -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("WARNING: OPENROUTER_API_KEY not set", file=sys.stderr)
    return OpenAI(
        api_key=api_key,
        base_url=sources_cfg["llm"]["base_url"],
        default_headers={
            "HTTP-Referer": "https://github.com/YuyangXueEd/MyDailyUpdater",
            "X-OpenRouter-Title": "MyDailyUpdater",
        },
    )


def run_daily(kw: dict, sources: dict, supervisors: list) -> None:
    start = time.time()
    client = get_openrouter_client(sources)
    scoring_model = sources["llm"]["scoring_model"]
    summary_model = sources["llm"]["summarization_model"]

    # --- arxiv ---
    print("Fetching arxiv papers...")
    raw_papers = fetch_papers(
        categories=kw["arxiv"]["categories"],
        must_include=kw["arxiv"]["must_include"],
        max_results=sources["arxiv"].get("max_papers_per_run", 500),
    )
    print(f"  After keyword filter: {len(raw_papers)}")
    scored_papers = score_papers(raw_papers, client, scoring_model, kw["arxiv"]["llm_score_threshold"])
    print(f"  After LLM filter: {len(scored_papers)}")
    papers = summarize_papers(scored_papers, client, summary_model)
    if papers:
        print("Fetching arXiv figure previews...")
        papers = enrich_papers_with_figures(papers)
        papers = prepare_papers_for_rendering(papers, kw["arxiv"]["categories"])

    # --- HN ---
    print("Fetching Hacker News...")
    hn_stories = []
    if sources["hacker_news"]["enabled"]:
        raw_hn = fetch_stories(
            keywords=kw["hacker_news"]["keywords"],
            min_score=kw["hacker_news"]["min_score"],
            max_items=kw["hacker_news"]["max_items"],
        )
        hn_stories = summarize_hn_stories(raw_hn, client, summary_model)
    print(f"  HN stories: {len(hn_stories)}")

    # --- Jobs ---
    print("Fetching jobs...")
    jobs = []
    if sources["jobs"]["enabled"]:
        raw_jobs = fetch_jobs(
            rss_sources=kw["jobs"]["rss_sources"],
            filter_keywords=kw["jobs"]["filter_keywords"],
            exclude_keywords=kw["jobs"]["exclude_keywords"],
        )
        scored_jobs = score_jobs(raw_jobs, client, scoring_model, kw["jobs"]["llm_score_threshold"])
        jobs = summarize_jobs(scored_jobs, client, summary_model)
    print(f"  Jobs: {len(jobs)}")

    # --- Supervisors ---
    supervisor_updates = []
    if sources["supervisor_monitoring"]["enabled"] and supervisors:
        print(f"Checking {len(supervisors)} supervisor pages...")
        raw_updates = fetch_supervisor_updates(supervisors)
        supervisor_updates = [summarize_supervisor_update(u, client, summary_model) for u in raw_updates]

    # --- GitHub Trending ---
    github_trending = []
    if sources.get("github_trending", {}).get("enabled", False):
        print("Fetching GitHub trending...")
        max_repos = sources["github_trending"].get("max_repos", 15)
        raw_trending = fetch_github_trending(max_repos=max_repos)
        github_trending = summarize_github_repos(raw_trending, client, summary_model)
        print(f"  GitHub trending: {len(github_trending)} repos")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    meta = {
        "papers_fetched": sources["arxiv"].get("max_papers_per_run", 500),
        "papers_after_keyword_filter": len(raw_papers),
        "papers_after_llm_filter": len(scored_papers),
        "jobs_fetched": 0,
        "jobs_after_filter": len(jobs),
        "supervisor_pages_checked": len(supervisors),
        "supervisor_updates_found": len(supervisor_updates),
        "llm_model": summary_model if scoring_model == summary_model else f"score={scoring_model}; summary={summary_model}",
        "scoring_model": scoring_model,
        "summarization_model": summary_model,
        "cost_usd": 0.0,
        "duration_seconds": round(time.time() - start),
    }

    payload = build_daily_payload(date_str, papers, hn_stories, jobs, supervisor_updates, meta,
                                   github_trending=github_trending)
    json_path = write_daily_json(payload)
    md_path = render_daily_page(payload)
    print(f"Written: {json_path}")
    print(f"Written: {md_path}")


def run_weekly() -> None:
    today = datetime.now(timezone.utc)
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7, 0, -1)]
    period = today.strftime("%Y-W%V")

    sources = load_sources()
    client = get_openrouter_client(sources)
    data_dir = str(Path(__file__).parent / "docs" / "data" / "daily")

    dailies = load_daily_jsons(dates, data_dir)
    all_papers = [p for d in dailies for p in d.get("papers", [])]

    prompt = (
        f"请用中文（300字以内）总结以下{len(all_papers)}篇论文本周的整体趋势，"
        "包括热门方向、值得关注的进展、以及任何显著变化：\n\n"
        + "\n".join(f"- {p['title']}: {p.get('abstract_zh','')}" for p in all_papers[:30])
    )
    resp = client.chat.completions.create(
        model=sources["llm"]["summarization_model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
    )
    summary_zh = resp.choices[0].message.content.strip()

    payload = build_weekly_payload(dates, period, summary_zh, data_dir)
    json_path = write_weekly_json(payload)
    md_path = render_weekly_page(payload)
    print(f"Written: {json_path}")
    print(f"Written: {md_path}")


def run_monthly() -> None:
    today = datetime.now(timezone.utc)
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30, 0, -1)]
    period = today.strftime("%Y-%m")

    sources = load_sources()
    client = get_openrouter_client(sources)
    data_dir = str(Path(__file__).parent / "docs" / "data" / "daily")

    dailies = load_daily_jsons(dates, data_dir)
    all_papers = [p for d in dailies for p in d.get("papers", [])]

    prompt = (
        f"请用中文（500字以内）总结过去30天共{len(all_papers)}篇论文的月度趋势，"
        "包括方向热度变化、值得关注的团队、以及下月值得关注的趋势：\n\n"
        + "\n".join(f"- {p['title']}: {p.get('abstract_zh','')}" for p in all_papers[:50])
    )
    resp = client.chat.completions.create(
        model=sources["llm"]["summarization_model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
    )
    summary_zh = resp.choices[0].message.content.strip()

    payload = build_monthly_payload(dates, period, summary_zh, data_dir)
    json_path = write_monthly_json(payload)
    md_path = render_monthly_page(payload)
    print(f"Written: {json_path}")
    print(f"Written: {md_path}")


def check_today() -> None:
    """Print compact summary for Claude Code SessionStart hook."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    data_dir = Path(__file__).parent / "docs" / "data" / "daily"
    for date_str in [today, yesterday]:
        path = data_dir / f"{date_str}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            label = "" if date_str == today else " [yesterday]"
            papers = data.get("papers", [])
            jobs = data.get("jobs", [])
            hn = data.get("hacker_news", [])
            sup = data.get("supervisor_updates", [])
            gh = data.get("github_trending", [])
            top_paper = papers[0]["title"][:50] + "..." if papers else "none"
            top_hn = hn[0]["title"][:50] + "..." if hn else "none"
            print(f"[Daily Digest {date_str}{label}]")
            print(f"Papers: {len(papers)} new (top: {top_paper})")
            print(f"Jobs: {len(jobs)} new")
            print(f"HN: {top_hn}")
            print(f"GitHub trending: {len(gh)} repos")
            print(f"Supervisor updates: {len(sup)}")
            print("Run /daily-digest for full report.")
            return
    print("[Daily Digest] No data found yet. Run: python main.py --mode daily")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research Daily Digest")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--mode", choices=["daily", "weekly", "monthly"])
    group.add_argument("--check-today", action="store_true")
    args = parser.parse_args()

    if args.check_today:
        check_today()
    else:
        kw = load_keywords()
        sources = load_sources()
        supervisors = load_supervisors()
        if args.mode == "daily":
            run_daily(kw, sources, supervisors)
        elif args.mode == "weekly":
            run_weekly()
        elif args.mode == "monthly":
            run_monthly()
