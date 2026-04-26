"""Deterministic scoring for the US stocks pre-market signal board."""

from __future__ import annotations

from statistics import mean
from typing import Any

POSITIVE_NEWS_TERMS = {
    "beat",
    "beats",
    "raise",
    "raises",
    "raised",
    "upgrade",
    "upgraded",
    "partnership",
    "contract",
    "wins",
    "record",
    "growth",
    "surge",
    "rally",
    "demand",
    "expansion",
    "guidance",
}

NEGATIVE_NEWS_TERMS = {
    "miss",
    "misses",
    "cut",
    "cuts",
    "downgrade",
    "downgraded",
    "lawsuit",
    "probe",
    "investigation",
    "delay",
    "delayed",
    "weak",
    "slump",
    "falls",
    "drops",
    "warning",
    "risk",
}

DEFAULT_WEIGHTS = {
    "premarket_move": 0.18,
    "news": 0.25,
    "earnings_financials": 0.12,
    "technicals": 0.22,
    "sector_trend": 0.18,
    "risk_flags": 0.05,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return ((current - previous) / previous) * 100.0


def _history_change(history: list[dict[str, Any]], days: int) -> float | None:
    if len(history) < days + 1:
        return None
    return _pct_change(history[-1].get("close"), history[-days - 1].get("close"))


def _volume_ratio(history: list[dict[str, Any]], days: int = 20) -> float | None:
    volumes = [row.get("volume", 0) for row in history if row.get("volume")]
    if len(volumes) < 2:
        return None
    baseline = volumes[-days - 1 : -1] if len(volumes) > days else volumes[:-1]
    if not baseline:
        return None
    avg_volume = mean(baseline)
    if avg_volume <= 0:
        return None
    return volumes[-1] / avg_volume


def _news_tone(news: list[dict[str, Any]]) -> tuple[float, list[str]]:
    score = 0.0
    flags: list[str] = []
    for item in news:
        title = str(item.get("title", "")).lower()
        positive_hits = [term for term in POSITIVE_NEWS_TERMS if term in title]
        negative_hits = [term for term in NEGATIVE_NEWS_TERMS if term in title]
        score += min(len(positive_hits), 2) * 0.5
        score -= min(len(negative_hits), 2) * 0.65
        if negative_hits:
            flags.append(f"negative headline: {item.get('title', '')}")
    return _clamp(score, -2.0, 2.0), flags[:2]


def _technical_score(
    change_5d: float | None, change_20d: float | None, volume_ratio: float | None
) -> float:
    score = 50.0
    if change_5d is not None:
        score += _clamp(change_5d * 2.0, -18.0, 18.0)
    if change_20d is not None:
        score += _clamp(change_20d * 0.8, -18.0, 18.0)
    if volume_ratio is not None and volume_ratio > 1.5 and change_5d is not None:
        score += 6.0 if change_5d > 0 else -6.0
    return _clamp(score, 0.0, 100.0)


def _move_score(change_pct: float | None) -> float:
    if change_pct is None:
        return 50.0
    return _clamp(50.0 + change_pct * 7.0, 0.0, 100.0)


def _sector_score(benchmark_changes: list[float]) -> float:
    if not benchmark_changes:
        return 50.0
    avg = mean(benchmark_changes)
    return _clamp(50.0 + avg * 8.0, 0.0, 100.0)


def _news_score(news: list[dict[str, Any]]) -> tuple[float, list[str], str]:
    if not news:
        return 45.0, [], "sparse"
    tone, risk_flags = _news_tone(news)
    score = 50.0 + tone * 18.0 + min(len(news), 3) * 3.0
    sentiment = "positive" if score >= 60 else "negative" if score <= 42 else "mixed"
    return _clamp(score, 0.0, 100.0), risk_flags, sentiment


def _filings_score(filings: list[dict[str, Any]]) -> tuple[float, str]:
    if not filings:
        return 50.0, "none"
    important = {"8-K", "10-Q", "10-K", "S-1"}
    forms = {str(filing.get("form", "")) for filing in filings}
    if forms & important:
        return 56.0, ", ".join(sorted(forms & important))
    return 52.0, ", ".join(sorted(forms)[:3])


def _normalize_weights(raw: dict[str, Any] | None) -> dict[str, float]:
    weights = {**DEFAULT_WEIGHTS, **(raw or {})}
    clean = {key: max(float(value), 0.0) for key, value in weights.items()}
    total = sum(clean.values())
    if total <= 0:
        return DEFAULT_WEIGHTS
    return {key: value / total for key, value in clean.items()}


def _confidence_label(score: float, data_points: int, high_confidence: float) -> str:
    distance = abs(score - 50.0)
    high_distance = abs(high_confidence - 50.0)
    if distance >= high_distance and data_points >= 3:
        return "high"
    if distance >= 18 and data_points >= 2:
        return "medium"
    return "low"


def _signal(score: float, thresholds: dict[str, Any]) -> str:
    bullish = float(thresholds.get("bullish", 70))
    bearish = float(thresholds.get("bearish", 35))
    if score >= bullish:
        return "bullish"
    if score <= bearish:
        return "bearish"
    return "neutral"


def _driver_for_signal(item: dict[str, Any]) -> str:
    signal = item["signal"]
    pieces = []
    move = item.get("premarket_change_pct")
    if move is not None and abs(move) >= 0.8:
        pieces.append(f"{move:+.1f}% vs previous close")
    if item.get("sector_trend") in {"positive", "negative"}:
        pieces.append(f"{item['sector_trend']} sector tape")
    if item.get("news_count", 0):
        pieces.append(f"{item['news_count']} recent headline(s)")
    if not pieces:
        return "Data is limited; signal is based on baseline price and sector inputs."
    prefix = {
        "bullish": "Bullish setup from",
        "bearish": "Bearish/risk setup from",
        "neutral": "Watchlist item from",
    }[signal]
    return f"{prefix} " + ", ".join(pieces) + "."


def score_stock(
    raw: dict[str, Any],
    benchmarks: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    quote = raw.get("quote") or {}
    history = quote.get("history") or []
    price = quote.get("price")
    previous_close = quote.get("previous_close")
    premarket_change_pct = _pct_change(price, previous_close)
    change_5d = _history_change(history, 5)
    change_20d = _history_change(history, 20)
    volume_ratio = _volume_ratio(history)

    benchmark_changes = []
    for benchmark in raw.get("benchmark_etfs", []):
        b_history = (benchmarks.get(benchmark) or {}).get("history") or []
        b_change = _history_change(b_history, 5)
        if b_change is not None:
            benchmark_changes.append(b_change)

    news = raw.get("news") or []
    filings = raw.get("filings") or []
    news_score, news_risks, news_sentiment = _news_score(news)
    filings_score, earnings_status = _filings_score(filings)
    technical_score = _technical_score(change_5d, change_20d, volume_ratio)
    move_score = _move_score(premarket_change_pct)
    sector_score = _sector_score(benchmark_changes)
    risk_score = 35.0 if news_risks else 50.0
    weights = _normalize_weights(config.get("scoring_weights"))
    score = (
        move_score * weights["premarket_move"]
        + news_score * weights["news"]
        + filings_score * weights["earnings_financials"]
        + technical_score * weights["technicals"]
        + sector_score * weights["sector_trend"]
        + risk_score * weights["risk_flags"]
    )
    thresholds = config.get("signal_thresholds", {})
    signal = _signal(score, thresholds)
    data_points = sum(
        [
            quote.get("price") is not None,
            bool(news),
            bool(benchmark_changes),
            change_5d is not None,
            bool(filings),
        ]
    )
    item = {
        "symbol": raw["symbol"],
        "name": raw.get("name", raw["symbol"]),
        "sector": raw.get("sector", ""),
        "sector_key": raw.get("sector_key", ""),
        "benchmark_etfs": raw.get("benchmark_etfs", []),
        "signal": signal,
        "score": round(score),
        "confidence": _confidence_label(
            score,
            data_points,
            float(thresholds.get("high_confidence", 75)),
        ),
        "setup_type": _setup_type(signal, premarket_change_pct, news, benchmark_changes),
        "price": round(price, 2) if price is not None else None,
        "previous_close": round(previous_close, 2) if previous_close is not None else None,
        "premarket_change_pct": round(premarket_change_pct, 2)
        if premarket_change_pct is not None
        else None,
        "change_5d_pct": round(change_5d, 2) if change_5d is not None else None,
        "change_20d_pct": round(change_20d, 2) if change_20d is not None else None,
        "volume_ratio": round(volume_ratio, 2) if volume_ratio is not None else None,
        "relative_strength_pct": round((change_5d or 0.0) - mean(benchmark_changes), 2)
        if benchmark_changes and change_5d is not None
        else None,
        "sector_trend": _trend_label(mean(benchmark_changes) if benchmark_changes else None),
        "news_sentiment": news_sentiment,
        "news_count": len(news),
        "earnings_status": earnings_status,
        "summary": "",
        "drivers": [],
        "invalidation": [],
        "risk_flags": news_risks,
        "sources": news[:3],
        "filings": filings[:3],
        "data_quality": {
            "quote": quote.get("data_quality", "missing") if quote else "missing",
            "news": "fresh" if news else "sparse",
            "financials": "fresh"
            if filings
            else "reference"
            if raw.get("filing_lookup_url")
            else "unavailable",
        },
        "source_url": quote.get("source_url") or f"https://finance.yahoo.com/quote/{raw['symbol']}",
        "financial_source_url": raw.get("filing_lookup_url", ""),
    }
    item["summary"] = _driver_for_signal(item)
    item["drivers"] = _build_drivers(item)
    item["invalidation"] = _build_invalidation(item)
    return item


def score_all_stocks(raw_payload: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    items = [
        score_stock(stock, raw_payload.get("benchmarks", {}), config)
        for stock in raw_payload.get("stocks", [])
        if stock.get("quote") or stock.get("news") or stock.get("filings")
    ]
    include_neutral = config.get("include_neutral", True)
    if not include_neutral:
        items = [item for item in items if item["signal"] != "neutral"]
    signal_rank = {"bullish": 0, "bearish": 1, "neutral": 2}
    items.sort(
        key=lambda item: (
            signal_rank.get(item["signal"], 3),
            -abs(item["score"] - 50),
            -item.get("news_count", 0),
            item["symbol"],
        )
    )
    return items


def _safe_mean(values: list[float]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return mean(clean)


def build_sector_overview(
    items: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Aggregate scored stock rows into the compact sector tape shown above the board."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        key = str(item.get("sector_key") or item.get("sector") or "unknown")
        groups.setdefault(key, []).append(item)

    thresholds = config.get("signal_thresholds", {})
    rows = []
    for sector_key, sector_items in groups.items():
        scores = [float(item["score"]) for item in sector_items if item.get("score") is not None]
        avg_score = mean(scores) if scores else 50.0
        top = max(sector_items, key=lambda item: abs(float(item.get("score", 50)) - 50))
        counts = {
            "bullish": sum(1 for item in sector_items if item.get("signal") == "bullish"),
            "bearish": sum(1 for item in sector_items if item.get("signal") == "bearish"),
            "neutral": sum(1 for item in sector_items if item.get("signal") == "neutral"),
        }
        trend_votes = [item.get("sector_trend") for item in sector_items]
        trend = "flat"
        if trend_votes.count("positive") > trend_votes.count("negative"):
            trend = "positive"
        elif trend_votes.count("negative") > trend_votes.count("positive"):
            trend = "negative"

        rows.append(
            {
                "sector_key": sector_key,
                "sector": sector_items[0].get("sector") or sector_key.replace("_", " ").title(),
                "signal": _signal(avg_score, thresholds),
                "avg_score": round(avg_score),
                "avg_change_5d_pct": _round_optional(
                    _safe_mean([item.get("change_5d_pct") for item in sector_items])
                ),
                "avg_relative_strength_pct": _round_optional(
                    _safe_mean([item.get("relative_strength_pct") for item in sector_items])
                ),
                "sector_trend": trend,
                "counts": counts,
                "top_symbol": top.get("symbol"),
                "top_signal": top.get("signal"),
                "top_score": top.get("score"),
                "stock_count": len(sector_items),
            }
        )

    rows.sort(
        key=lambda row: (
            -abs(float(row.get("avg_score", 50)) - 50),
            -(row.get("counts", {}).get("bullish", 0) + row.get("counts", {}).get("bearish", 0)),
            row.get("sector", ""),
        )
    )
    max_sectors = int(config.get("max_sector_overview", 8) or 8)
    return rows[:max_sectors]


def _round_optional(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _trend_label(change: float | None) -> str:
    if change is None:
        return "unknown"
    if change >= 1.0:
        return "positive"
    if change <= -1.0:
        return "negative"
    return "flat"


def _setup_type(
    signal: str,
    premarket_change_pct: float | None,
    news: list[dict[str, Any]],
    benchmark_changes: list[float],
) -> str:
    if signal == "bearish":
        return "risk_watch"
    if premarket_change_pct is not None and premarket_change_pct >= 1.0 and news:
        return "gap_up_news"
    if benchmark_changes and mean(benchmark_changes) >= 1.0:
        return "sector_tailwind"
    if news:
        return "news_watch"
    return "baseline_watch"


def _build_drivers(item: dict[str, Any]) -> list[str]:
    drivers = []
    move = item.get("premarket_change_pct")
    if move is not None:
        drivers.append(f"Move vs previous close: {move:+.1f}%.")
    if item.get("relative_strength_pct") is not None:
        drivers.append(f"5-day relative strength: {item['relative_strength_pct']:+.1f} pts.")
    if item.get("news_count", 0):
        drivers.append(f"{item['news_count']} recent headline(s) in the news window.")
    if item.get("earnings_status") not in {"none", ""}:
        drivers.append(f"Recent filing/event forms: {item['earnings_status']}.")
    return drivers[:3] or ["No strong catalyst; surfaced by baseline ranking."]


def _build_invalidation(item: dict[str, Any]) -> list[str]:
    signal = item.get("signal")
    if signal == "bullish":
        return ["Weakens if price fades below previous close or sector benchmarks roll over."]
    if signal == "bearish":
        return [
            "Improves if price reclaims previous close and negative headlines are not confirmed."
        ]
    return ["Needs fresh price/news confirmation before becoming an actionable setup."]


def score_stocks(raw_payload: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    max_items = int(config.get("max_items", 12))
    return score_all_stocks(raw_payload, config)[:max_items]
