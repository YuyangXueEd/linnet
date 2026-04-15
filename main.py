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
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from extensions import REGISTRY, FeedSection
from sinks import SINK_REGISTRY
from pipeline.config_loader import load_keywords, load_sources, load_supervisors
from pipeline.summarizer import lang_instruction
from pipeline.aggregator import build_weekly_payload, build_monthly_payload, load_daily_jsons
from publishers.data_publisher import (
    write_daily_json, write_weekly_json, write_monthly_json, build_daily_payload,
)
from publishers.pages_publisher import (
    render_daily_page, render_weekly_page, render_monthly_page,
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


def _build_extension_configs(
    sources: dict, keywords: dict, supervisors: list
) -> dict[str, dict]:
    """
    Merge per-extension config slices from sources.yaml and keywords.yaml.

    Each extension receives a single flat dict containing:
      - source settings (enabled flag, limits, URLs)
      - keyword / filter settings
      - injected LLM model names
    """
    llm = {
        "llm_scoring_model": sources["llm"]["scoring_model"],
        "llm_summarization_model": sources["llm"]["summarization_model"],
        "language": sources.get("language", "en"),
    }
    return {
        "arxiv": {**sources.get("arxiv", {}), **keywords.get("arxiv", {}), **llm},
        "hacker_news": {
            **sources.get("hacker_news", {}),
            **keywords.get("hacker_news", {}),
            **llm,
        },
        "jobs": {**sources.get("jobs", {}), **keywords.get("jobs", {}), **llm},
        "supervisor_updates": {
            **sources.get("supervisor_monitoring", {}),
            "supervisors": supervisors,
            **llm,
        },
        "github_trending": {**sources.get("github_trending", {}), **llm},
    }


def _instantiate_extensions(
    configs: dict[str, dict], llm_client: Any
) -> list[Any]:
    """Instantiate all registered extensions with their merged configs."""
    extensions = []
    for ext_class in REGISTRY:
        cfg = configs.get(ext_class.key, {})
        extensions.append(ext_class(cfg, llm_client))
    return extensions


def run_daily(kw: dict, sources: dict, supervisors: list) -> None:
    start = time.time()
    client = get_openrouter_client(sources)
    configs = _build_extension_configs(sources, kw, supervisors)
    extensions = _instantiate_extensions(configs, client)

    sections: dict[str, FeedSection] = {}
    for ext in extensions:
        sections[ext.key] = ext.run()

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    arxiv_meta = sections["arxiv"].meta
    summary_model = sources["llm"]["summarization_model"]
    scoring_model = sources["llm"]["scoring_model"]

    meta = {
        "papers_fetched": arxiv_meta.get("papers_fetched", 0),
        "papers_after_keyword_filter": arxiv_meta.get("papers_after_keyword_filter", 0),
        "papers_after_llm_filter": arxiv_meta.get("papers_after_llm_filter", 0),
        "llm_model": (
            summary_model
            if scoring_model == summary_model
            else f"score={scoring_model}; summary={summary_model}"
        ),
        "scoring_model": scoring_model,
        "summarization_model": summary_model,
        "cost_usd": 0.0,
        "duration_seconds": round(time.time() - start),
    }

    payload = build_daily_payload(
        date_str,
        papers=sections["arxiv"].items,
        hn_stories=sections["hacker_news"].items,
        jobs=[],
        supervisor_updates=[],
        meta=meta,
        github_trending=sections["github_trending"].items,
    )
    json_path = write_daily_json(payload)
    md_path = render_daily_page(payload)
    print(f"Written: {json_path}")
    print(f"Written: {md_path}")

    # ── Deliver to enabled sinks ─────────────────────────────────────
    sinks_cfg = sources.get("sinks", {})
    for sink_class in SINK_REGISTRY:
        cfg = sinks_cfg.get(sink_class.key, {})
        sink = sink_class(cfg)
        if sink.enabled:
            print(f"Delivering to {sink_class.key}...")
            try:
                sink.deliver(payload)
                print(f"  {sink_class.key}: OK")
            except Exception as e:
                print(f"  {sink_class.key}: FAILED — {e}")


def run_weekly() -> None:
    today = datetime.now(timezone.utc)
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7, 0, -1)]
    period = today.strftime("%Y-W%V")

    sources = load_sources()
    client = get_openrouter_client(sources)
    data_dir = str(Path(__file__).parent / "docs" / "data" / "daily")

    lang = sources.get("language", "en")
    dailies = load_daily_jsons(dates, data_dir)
    all_papers = [p for d in dailies for p in d.get("papers", [])]

    prompt = (
        f"Summarize the overall weekly trends of the following {len(all_papers)} papers "
        f"{lang_instruction(lang)}, in ≤300 words. Cover popular directions, "
        f"notable advances, and any significant shifts:\n\n"
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

    lang = sources.get("language", "en")
    dailies = load_daily_jsons(dates, data_dir)
    all_papers = [p for d in dailies for p in d.get("papers", [])]

    prompt = (
        f"Summarize the monthly trends of the following {len(all_papers)} papers from the past 30 days "
        f"{lang_instruction(lang)}, in ≤500 words. Cover shifts in research direction popularity, "
        f"notable groups or labs, and trends to watch next month:\n\n"
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
