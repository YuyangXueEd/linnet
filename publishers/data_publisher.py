import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_DEFAULT_DATA_DIR = str(Path(__file__).parent.parent / "docs" / "data" / "daily")


def build_daily_payload(
    date_str: str,
    sections: dict,
    meta: dict,
    display_order: list[str],
) -> dict[str, Any]:
    sections_ordered = [
        {
            "key": key,
            "payload_key": sections[key].payload_key or key,
            "title": sections[key].title,
            "icon": sections[key].icon,
            "items": sections[key].items,
            "meta": sections[key].meta,
        }
        for key in display_order
        if key in sections
    ]

    flat_sections: dict[str, list[dict]] = {}
    for key, sec in sections.items():
        flat_sections[key] = sec.items
        payload_key = sec.payload_key or key
        flat_sections[payload_key] = sec.items

    return {
        "date": date_str,
        "generated_at": datetime.now(UTC).isoformat(),
        "sections_ordered": sections_ordered,
        "meta": meta,
        **flat_sections,
    }


def write_daily_json(payload: dict, base_dir: str = _DEFAULT_DATA_DIR) -> str:
    os.makedirs(base_dir, exist_ok=True)
    out_path = os.path.join(base_dir, f"{payload['date']}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


def write_weekly_json(payload: dict) -> str:
    base_dir = str(Path(__file__).parent.parent / "docs" / "data" / "weekly")
    os.makedirs(base_dir, exist_ok=True)
    out_path = os.path.join(base_dir, f"{payload['period']}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


def write_monthly_json(payload: dict) -> str:
    base_dir = str(Path(__file__).parent.parent / "docs" / "data" / "monthly")
    os.makedirs(base_dir, exist_ok=True)
    out_path = os.path.join(base_dir, f"{payload['period']}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path
