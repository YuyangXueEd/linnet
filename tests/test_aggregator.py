import json

from pipeline.aggregator import build_weekly_payload, compute_keyword_frequency, load_daily_jsons


def make_daily_json(tmp_path, date_str, papers, jobs):
    d = tmp_path / "data" / "daily"
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "date": date_str,
        "generated_at": f"{date_str}T00:03:00Z",
        "papers": papers,
        "hacker_news": [],
        "jobs": jobs,
        "supervisor_updates": [],
        "meta": {"cost_usd": 0.02, "llm_model": "deepseek"},
    }
    (d / f"{date_str}.json").write_text(json.dumps(payload))
    return payload


def test_load_daily_jsons(tmp_path):
    make_daily_json(tmp_path, "2026-04-07", [], [])
    make_daily_json(tmp_path, "2026-04-08", [], [])
    results = load_daily_jsons(
        ["2026-04-07", "2026-04-08"], data_dir=str(tmp_path / "data" / "daily")
    )
    assert len(results) == 2


def test_compute_keyword_frequency():
    papers = [
        {"keywords_matched": ["foundation model", "segmentation"]},
        {"keywords_matched": ["foundation model", "MRI"]},
        {"keywords_matched": ["segmentation"]},
    ]
    freq = compute_keyword_frequency(papers)
    assert freq["foundation model"] == 2
    assert freq["segmentation"] == 2
    assert freq["MRI"] == 1


def test_build_weekly_payload(tmp_path):
    p = {
        "id": "1",
        "title": "Test",
        "score": 9.0,
        "abstract": "test",
        "authors": [],
        "categories": ["cs.CV"],
        "url": "",
        "pdf_url": "",
        "keywords_matched": ["medical imaging"],
    }
    j = {
        "title": "Postdoc AI",
        "institution": "Oxford",
        "deadline": "",
        "url": "",
        "requirements": "",
        "source": "",
        "relevance_score": 8.0,
        "posted_date": "",
    }
    make_daily_json(tmp_path, "2026-04-07", [p], [j])
    dates = ["2026-04-07"]
    payload = build_weekly_payload(
        dates=dates,
        period="2026-W15",
        summary="本周趋势分析。",
        data_dir=str(tmp_path / "data" / "daily"),
    )
    assert payload["period"] == "2026-W15"
    assert len(payload["top_papers"]) == 1
    assert len(payload["new_jobs"]) == 1
    assert payload["trending_keywords"][0] == "medical imaging"
