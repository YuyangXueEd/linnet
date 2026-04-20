import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def arxiv_config():
    with open("config/extensions/arxiv.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def sources_config():
    with open("config/sources.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def sample_paper():
    return {
        "id": "2604.12345",
        "title": "FoundationSeg: Universal Medical Image Segmentation",
        "authors": ["Zhang Wei", "Li Ming"],
        "categories": ["cs.CV", "eess.IV"],
        "abstract": "We propose a foundation model for medical image segmentation using diffusion-based pretraining on 1M CT and MRI scans.",
        "url": "https://arxiv.org/abs/2604.12345",
        "pdf_url": "https://arxiv.org/pdf/2604.12345",
    }


@pytest.fixture
def sample_hn_story():
    return {
        "objectID": "43821045",
        "title": "Meta releases new open-source vision model",
        "url": "https://example.com/meta-vision",
        "points": 342,
        "created_at": "2026-04-13T01:00:00.000Z",
    }


@pytest.fixture
def sample_job():
    return {
        "title": "Research Associate in Medical Imaging AI",
        "institution": "Imperial College London",
        "deadline": "2026-05-15",
        "url": "https://jobs.ac.uk/job/ABC123",
        "description": "We seek a postdoc with expertise in computer vision and medical image segmentation using deep learning.",
        "source": "jobs.ac.uk",
        "posted_date": "2026-04-12",
    }
