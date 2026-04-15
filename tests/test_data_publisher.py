import json
from pathlib import Path

from extensions.base import FeedSection
from publishers.data_publisher import build_daily_payload, write_daily_json


def test_build_daily_payload_structure(sample_paper, sample_hn_story, sample_job):
    sample_paper["score"] = 8.5
    sample_paper["abstract"] = "医学图像分割基础模型。"
    sample_paper["keywords_matched"] = ["medical imaging"]
    sample_hn_story["summary"] = "Meta开源视觉模型。"
    sample_job["requirements"] = "需要深度学习经验。"
    sample_job["relevance_score"] = 9.0

    sections = {
        "arxiv": FeedSection(
            key="arxiv",
            title="arXiv Papers",
            icon="📄",
            payload_key="papers",
            items=[sample_paper],
        ),
        "hacker_news": FeedSection(
            key="hacker_news",
            title="Hacker News",
            icon="🔥",
            items=[sample_hn_story],
        ),
        "postdoc_jobs": FeedSection(
            key="postdoc_jobs",
            title="Postdoc Jobs",
            icon="💼",
            payload_key="jobs",
            items=[sample_job],
        ),
    }

    payload = build_daily_payload(
        date_str="2026-04-13",
        sections=sections,
        meta={"papers_fetched": 100, "cost_usd": 0.02},
        display_order=["arxiv", "hacker_news", "postdoc_jobs"],
    )
    assert payload["date"] == "2026-04-13"
    assert len(payload["papers"]) == 1
    assert len(payload["hacker_news"]) == 1
    assert len(payload["jobs"]) == 1
    assert payload["sections_ordered"][0]["key"] == "arxiv"
    assert payload["meta"]["papers_fetched"] == 100


def test_write_daily_json_creates_file(tmp_path, sample_paper, sample_hn_story, sample_job):
    sample_paper.update({"score": 8.5, "abstract": "test", "keywords_matched": []})
    sample_hn_story.update({"summary": "test"})
    sample_job.update({"requirements": "test", "relevance_score": 8.0})

    payload = build_daily_payload(
        "2026-04-13",
        {
            "arxiv": FeedSection(
                key="arxiv",
                title="arXiv Papers",
                icon="📄",
                payload_key="papers",
                items=[sample_paper],
            ),
            "hacker_news": FeedSection(
                key="hacker_news",
                title="Hacker News",
                icon="🔥",
                items=[sample_hn_story],
            ),
            "postdoc_jobs": FeedSection(
                key="postdoc_jobs",
                title="Postdoc Jobs",
                icon="💼",
                payload_key="jobs",
                items=[sample_job],
            ),
        },
        {},
        ["arxiv", "hacker_news", "postdoc_jobs"],
    )
    out_path = write_daily_json(payload, base_dir=str(tmp_path))

    assert Path(out_path).exists()
    with open(out_path) as f:
        data = json.load(f)
    assert data["date"] == "2026-04-13"
