import sys
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent.parent / "config"
EXTENSIONS_CONFIG_DIR = CONFIG_DIR / "extensions"


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_sources() -> dict:
    return _load_yaml(CONFIG_DIR / "sources.yaml")


def load_extension_config(name: str) -> dict:
    """Load per-extension config from config/extensions/{name}.yaml.

    Returns an empty dict if no config file exists for this extension.
    This allows extensions with no filter/keyword config (e.g. github_trending)
    to omit the file entirely.
    """
    path = EXTENSIONS_CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        return {}
    return _load_yaml(path)


def validate_sources(sources: dict) -> None:
    """Check sources.yaml for common misconfigurations and print friendly errors."""
    errors = []

    llm = sources.get("llm", {})
    if not llm.get("scoring_model"):
        errors.append("  • llm.scoring_model is missing in sources.yaml")
    if not llm.get("summarization_model"):
        errors.append("  • llm.summarization_model is missing in sources.yaml")
    if not llm.get("base_url"):
        errors.append("  • llm.base_url is missing in sources.yaml")

    arxiv = sources.get("arxiv", {})
    max_papers = arxiv.get("max_papers_per_run", 300)
    if not isinstance(max_papers, int) or max_papers < 1:
        errors.append(
            f"  • arxiv.max_papers_per_run must be a positive integer, got: {max_papers!r}"
        )

    lang = sources.get("language", "en")
    if not isinstance(lang, str) or not lang:
        errors.append(f"  • language must be a non-empty string (e.g. 'en', 'zh'), got: {lang!r}")

    if errors:
        print("ERROR: Invalid configuration in sources.yaml:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)


def validate_arxiv_config(arxiv_cfg: dict) -> None:
    """Check config/extensions/arxiv.yaml for common misconfigurations."""
    errors = []

    if not arxiv_cfg.get("categories"):
        errors.append("  • categories is empty — no papers will be fetched")
    if not arxiv_cfg.get("must_include"):
        errors.append("  • must_include is empty — all fetched papers will pass keyword filter")

    threshold = arxiv_cfg.get("llm_score_threshold", 7)
    if not isinstance(threshold, (int, float)) or not (0 <= threshold <= 10):
        errors.append(f"  • llm_score_threshold must be between 0 and 10, got: {threshold!r}")

    if errors:
        print(
            "WARNING: Possible misconfiguration in config/extensions/arxiv.yaml:", file=sys.stderr
        )
        for e in errors:
            print(e, file=sys.stderr)
