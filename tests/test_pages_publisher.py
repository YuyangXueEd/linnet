from pathlib import Path
from publishers.pages_publisher import render_daily_page, render_weekly_page


def test_render_daily_page_contains_date(tmp_path):
    payload = {
        "date": "2026-04-13",
        "generated_at": "2026-04-13T00:03:00Z",
        "papers": [],
        "hacker_news": [],
        "jobs": [],
        "supervisor_updates": [],
        "meta": {"llm_model": "deepseek", "cost_usd": 0.02},
    }
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "2026-04-13" in content
    assert "科研日报" in content


def test_render_daily_page_shows_paper(tmp_path, sample_paper):
    sample_paper.update({"score": 8.5, "abstract_zh": "医学分割测试。", "keywords_matched": []})
    payload = {
        "date": "2026-04-13",
        "generated_at": "2026-04-13T00:03:00Z",
        "papers": [sample_paper],
        "hacker_news": [],
        "jobs": [],
        "supervisor_updates": [],
        "meta": {"llm_model": "deepseek", "cost_usd": 0.02},
    }
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "FoundationSeg" in content
    assert "医学分割测试" in content
    assert "| 评分 | 论文 | 方向 |" not in content
    assert "## 导航" in content
    assert "[arXiv 精选](#arxiv)" in content
    assert "[1. FoundationSeg: Universal Medical Image Segmentation](#paper-1)" in content
    assert '<h3 id="paper-1">1. <a href="https://arxiv.org/abs/2604.12345">FoundationSeg: Universal Medical Image Segmentation</a></h3>' in content


def test_render_daily_page_shows_paper_figure(tmp_path, sample_paper):
    sample_paper.update({
        "score": 8.5,
        "abstract_zh": "医学分割测试。",
        "figure_url": "https://arxiv.org/html/2604.12345v1/Figures/figure1.png",
        "figure_caption": "Figure one caption.",
    })
    payload = {
        "date": "2026-04-13",
        "generated_at": "2026-04-13T00:03:00Z",
        "papers": [sample_paper],
        "hacker_news": [],
        "jobs": [],
        "supervisor_updates": [],
        "meta": {"llm_model": "deepseek", "cost_usd": 0.02},
    }
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "![Figure one caption.](https://arxiv.org/html/2604.12345v1/Figures/figure1.png)" in content
    assert "*Figure 1.* Figure one caption." in content


def test_render_daily_page_shows_distinct_models_and_arxiv_warning(tmp_path):
    payload = {
        "date": "2026-04-13",
        "generated_at": "2026-04-13T00:03:00Z",
        "papers": [],
        "hacker_news": [],
        "jobs": [],
        "supervisor_updates": [],
        "meta": {
            "llm_model": "score=gemma; summary=deepseek",
            "scoring_model": "google/gemma-4-31b-it:free",
            "summarization_model": "deepseek/deepseek-chat",
            "papers_after_keyword_filter": 12,
            "cost_usd": 0.02,
        },
    }
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "评分模型：google/gemma-4-31b-it:free" in content
    assert "总结模型：deepseek/deepseek-chat" in content
    assert "关键词预筛后共有 12 篇候选" in content


def test_render_daily_page_shows_github_trending_bullets(tmp_path):
    payload = {
        "date": "2026-04-13",
        "generated_at": "2026-04-13T00:03:00Z",
        "papers": [],
        "hacker_news": [],
        "jobs": [],
        "supervisor_updates": [],
        "github_trending": [{
            "full_name": "example/repo",
            "url": "https://github.com/example/repo",
            "language": "Python",
            "stars_today": 99,
            "total_stars": 1234,
            "description": "Example repo for testing markdown rendering.",
            "summary_zh": "测试摘要。",
        }],
        "meta": {"llm_model": "deepseek", "cost_usd": 0.02},
    }
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "**[example/repo](https://github.com/example/repo)**" in content
    assert "⭐ +99 今日" in content
    assert "测试摘要。" in content
    assert "| 仓库 | 语言 | Stars | 简介 |" not in content


def test_render_daily_page_shows_job_location_and_salary(tmp_path, sample_job):
    sample_job.update({
        "requirements_zh": "需要深度学习经验。",
        "relevance_score": 8.0,
        "institution": "Example University",
        "location": "London, UK",
        "salary": "GBP40000-GBP50000 YEAR",
    })
    payload = {
        "date": "2026-04-13",
        "generated_at": "2026-04-13T00:03:00Z",
        "papers": [],
        "hacker_news": [],
        "jobs": [sample_job],
        "supervisor_updates": [],
        "meta": {"llm_model": "deepseek", "cost_usd": 0.02},
    }
    out_path = render_daily_page(payload, docs_dir=str(tmp_path))
    content = Path(out_path).read_text(encoding="utf-8")
    assert "**地点：** London, UK" in content
    assert "**薪资：** GBP40000-GBP50000 YEAR" in content
