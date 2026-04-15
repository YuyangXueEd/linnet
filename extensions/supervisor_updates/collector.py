import hashlib
import json
from pathlib import Path
from typing import Any

import trafilatura

_DEFAULT_HASHES_PATH = str(
    Path(__file__).parent.parent.parent / "docs" / "data" / "supervisor_hashes.json"
)


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_hashes(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def detect_changes(url: str, current_text: str, hashes_path: str = _DEFAULT_HASHES_PATH) -> bool:
    """Return True if the page content has changed since last check."""
    hashes = _load_hashes(hashes_path)
    current_hash = compute_hash(current_text)
    return hashes.get(url) != current_hash


def update_hashes(url: str, current_text: str, hashes_path: str = _DEFAULT_HASHES_PATH) -> None:
    hashes = _load_hashes(hashes_path)
    hashes[url] = compute_hash(current_text)
    with open(hashes_path, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)


def fetch_supervisor_updates(
    supervisors: list[dict],
    hashes_path: str = _DEFAULT_HASHES_PATH,
) -> list[dict[str, Any]]:
    """
    For each supervisor URL, fetch page text via trafilatura,
    compare hash, return list of changed entries.
    """
    updates = []
    for sup in supervisors:
        url = sup["url"]
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            continue
        text = trafilatura.extract(downloaded) or ""
        if not text:
            continue
        if detect_changes(url, text, hashes_path):
            update_hashes(url, text, hashes_path)
            updates.append(
                {
                    "name": sup.get("name", ""),
                    "institution": sup.get("institution", ""),
                    "url": url,
                    "page_text": text[:3000],  # cap for LLM context
                    "change_summary": "",  # filled by summarizer
                }
            )
    return updates
