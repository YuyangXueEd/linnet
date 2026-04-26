"""LLM synthesis for US stock pre-market signals."""

from __future__ import annotations

import json
import re
from typing import Any

from pipeline.utils import lang_instruction

_DEFAULT_SYNTHESIS_PROMPT = """
You are helping prepare a pre-market US stock signal board for research and education.
Use only the evidence provided. Do not invent prices, headlines, or filings.
This is not financial advice.

Return strict JSON with this shape:
{{
  "signals": [
    {{
      "symbol": "NVDA",
      "summary": "one concise sentence",
      "drivers": ["1-3 evidence-backed bullets"],
      "invalidation": ["1-2 conditions that weaken the setup"],
      "risk_flags": ["0-3 concrete risks"]
    }}
  ]
}}

Write the text fields {lang}. Keep each bullet under 18 words.

Evidence packets:
{packets}
""".strip()


def _json_blob(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in LLM response")
    return stripped[start : end + 1]


def parse_signal_synthesis(text: str) -> dict[str, dict[str, Any]]:
    """Parse model JSON into a mapping keyed by ticker symbol."""
    data = json.loads(_json_blob(text))
    rows = data.get("signals", [])
    parsed: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).upper().strip()
        if not symbol:
            continue
        parsed[symbol] = {
            "summary": str(row.get("summary", "")).strip(),
            "drivers": _string_list(row.get("drivers"), limit=3),
            "invalidation": _string_list(row.get("invalidation"), limit=2),
            "risk_flags": _string_list(row.get("risk_flags"), limit=3),
        }
    return parsed


def _string_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:limit]


def _packet(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": item.get("symbol"),
        "name": item.get("name"),
        "sector": item.get("sector"),
        "signal": item.get("signal"),
        "score": item.get("score"),
        "confidence": item.get("confidence"),
        "setup_type": item.get("setup_type"),
        "premarket_change_pct": item.get("premarket_change_pct"),
        "change_5d_pct": item.get("change_5d_pct"),
        "relative_strength_pct": item.get("relative_strength_pct"),
        "sector_trend": item.get("sector_trend"),
        "news_sentiment": item.get("news_sentiment"),
        "earnings_status": item.get("earnings_status"),
        "risk_flags": item.get("risk_flags", []),
        "headlines": [
            {
                "title": source.get("title", ""),
                "provider": source.get("provider", ""),
                "published_at": source.get("published_at", ""),
            }
            for source in item.get("sources", [])[:3]
        ],
        "filings": item.get("filings", [])[:3],
        "data_quality": item.get("data_quality", {}),
    }


def synthesize_us_stock_signals(
    items: list[dict],
    client: Any,
    model: str,
    lang: str = "en",
    prompt_template: str | None = None,
    max_items: int = 8,
) -> list[dict]:
    """Enrich top ranked stock signals with structured LLM text."""
    if not items or client is None or max_items <= 0:
        return items

    top = items[:max_items]
    template = prompt_template or _DEFAULT_SYNTHESIS_PROMPT
    prompt = template.format(
        lang=lang_instruction(lang),
        packets=json.dumps([_packet(item) for item in top], ensure_ascii=False, indent=2),
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=900,
        temperature=0.2,
    )
    raw = resp.choices[0].message.content.strip()
    synth = parse_signal_synthesis(raw)

    for item in top:
        enriched = synth.get(str(item.get("symbol", "")).upper())
        if not enriched:
            continue
        if enriched.get("summary"):
            item["summary"] = enriched["summary"]
        if enriched.get("drivers"):
            item["drivers"] = enriched["drivers"]
        if enriched.get("invalidation"):
            item["invalidation"] = enriched["invalidation"]
        merged_risks = list(
            dict.fromkeys([*item.get("risk_flags", []), *enriched.get("risk_flags", [])])
        )
        item["risk_flags"] = merged_risks[:4]
        item["llm_synthesized"] = True

    return items
