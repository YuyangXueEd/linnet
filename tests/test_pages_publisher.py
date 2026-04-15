from pathlib import Path

from publishers.pages_publisher import render_daily_page


def make_daily_payload(**overrides):
    payload = {
        "date": "2026-04-13",
        "generated_at": "2026-04-13T00:03:00Z",
        "sections_ordered": [],
        "papers": [],
        "hacker_news": [],
        "jobs": [],
        "supervisor_updates": [],
        "github_trending": [],
        "weather": [],
        "meta": {"llm_model": "deepseek", "cost_usd": 0.02},
    }
    payload.update(overrides)
    return payload


def test_render_daily_page_contains_date(tmp_path):
    payload = make_daily_payload()
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "2026-04-13" in content
    assert "Daily Digest" in content


def test_render_daily_page_shows_paper(tmp_path, sample_paper):
    sample_paper.update({"score": 8.5, "abstract": "医学分割测试。", "keywords_matched": []})
    payload = make_daily_payload(
        sections_ordered=[
            {
                "key": "arxiv",
                "payload_key": "papers",
                "title": "arXiv Papers",
                "icon": "📄",
                "items": [sample_paper],
                "meta": {},
            }
        ],
        papers=[sample_paper],
        arxiv=[sample_paper],
    )
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "FoundationSeg" in content
    assert "医学分割测试" in content
    assert "Quick Nav" in content
    assert '<a href="#arxiv">📄 arXiv Papers</a>' in content
    assert '<a href="#cat-cs-cv">cs.CV</a>' in content
    assert '<h3 id="cat-cs-cv">cs.CV</h3>' in content
    assert (
        '<h4>1. <a href="https://arxiv.org/abs/2604.12345">FoundationSeg: Universal Medical Image Segmentation</a></h4>'
        in content
    )


def test_render_daily_page_shows_paper_figure(tmp_path, sample_paper):
    sample_paper.update(
        {
            "score": 8.5,
            "abstract": "医学分割测试。",
            "figure_url": "https://arxiv.org/html/2604.12345v1/Figures/figure1.png",
            "figure_caption": "Figure one caption with \\( \\rho_{t} \\).",
        }
    )
    payload = make_daily_payload(
        sections_ordered=[
            {
                "key": "arxiv",
                "payload_key": "papers",
                "title": "arXiv Papers",
                "icon": "📄",
                "items": [sample_paper],
                "meta": {},
            }
        ],
        papers=[sample_paper],
        arxiv=[sample_paper],
    )
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert (
        "![Figure one caption with \\( \\rho_{t} \\).](https://arxiv.org/html/2604.12345v1/Figures/figure1.png)"
        in content
    )
    assert "*Figure 1.* Figure one caption with \\( \\rho_{t} \\)." in content
    assert "katex.min.css" in content
    assert "renderMathInElement" in content


def test_render_daily_page_shows_distinct_models_and_arxiv_warning(tmp_path):
    payload = make_daily_payload(
        sections_ordered=[
            {
                "key": "arxiv",
                "payload_key": "papers",
                "title": "arXiv Papers",
                "icon": "📄",
                "items": [],
                "meta": {},
            }
        ],
        papers=[],
        arxiv=[],
        meta={
            "llm_model": "score=gemma; summary=deepseek",
            "scoring_model": "google/gemma-4-31b-it:free",
            "summarization_model": "deepseek/deepseek-chat",
            "papers_after_keyword_filter": 12,
            "cost_usd": 0.02,
        },
    )
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "Scoring model: google/gemma-4-31b-it:free" in content
    assert "Summary model: deepseek/deepseek-chat" in content
    assert "12 candidates passed keyword filtering" in content


def test_render_daily_page_shows_github_trending_bullets(tmp_path):
    repos = [
        {
            "full_name": "example/repo",
            "url": "https://github.com/example/repo",
            "language": "Python",
            "stars_today": 99,
            "total_stars": 1234,
            "description": "Example repo for testing markdown rendering.",
            "summary": "测试摘要。",
        }
    ]
    payload = make_daily_payload(
        sections_ordered=[
            {
                "key": "github_trending",
                "payload_key": "github_trending",
                "title": "GitHub Trending",
                "icon": "⭐",
                "items": repos,
                "meta": {},
            }
        ],
        github_trending=repos,
    )
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "**[example/repo](https://github.com/example/repo)**" in content
    assert "⭐ +99 today" in content
    assert "测试摘要。" in content


def test_render_daily_page_shows_job_location_and_salary(tmp_path, sample_job):
    sample_job.update(
        {
            "requirements": "Deep learning experience required.",
            "relevance_score": 8.0,
            "institution": "Example University",
            "location": "London, UK",
            "salary": "GBP40000-GBP50000 YEAR",
        }
    )
    payload = make_daily_payload(
        sections_ordered=[
            {
                "key": "postdoc_jobs",
                "payload_key": "jobs",
                "title": "Postdoc Jobs",
                "icon": "💼",
                "items": [sample_job],
                "meta": {},
            }
        ],
        jobs=[sample_job],
        postdoc_jobs=[sample_job],
    )
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "**Location:** London, UK" in content
    assert "**Salary:** GBP40000-GBP50000 YEAR" in content


def test_render_daily_page_shows_weather_section(tmp_path):
    weather_item = {
        "label": "Boston, Massachusetts, United States",
        "forecast_date": "2026-04-13",
        "condition": "Partly cloudy",
        "temperature_c": 14.5,
        "temp_min_c": 8.1,
        "temp_max_c": 16.2,
        "humidity_pct": 62,
        "wind_speed_kmh": 12.3,
        "precipitation_probability_pct": 30,
        "source": "Open-Meteo",
    }
    payload = make_daily_payload(
        sections_ordered=[
            {
                "key": "weather",
                "payload_key": "weather",
                "title": "Weather",
                "icon": "🌦️",
                "items": [weather_item],
                "meta": {},
            }
        ],
        weather=[weather_item],
    )
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "Boston, Massachusetts, United States" in content
    assert "Partly cloudy" in content
    assert "Open-Meteo" in content
