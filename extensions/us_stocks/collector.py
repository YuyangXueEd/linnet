"""Data collectors for the US stocks pre-market signal extension."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_CHART_URLS = (
    YAHOO_CHART_URL,
    "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
)
NASDAQ_INFO_URL = "https://api.nasdaq.com/api/quote/{symbol}/info"
NASDAQ_HISTORY_URL = "https://api.nasdaq.com/api/quote/{symbol}/historical"
FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"
FINNHUB_CANDLE_URL = "https://finnhub.io/api/v1/stock/candle"
FINNHUB_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"
GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
MARKET_TZ = ZoneInfo("America/New_York")
NASDAQ_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; Linnet US stocks extension)",
}
DEFAULT_PROVIDER_ORDER = {
    "quotes": ("yahoo", "nasdaq"),
    "news": ("gdelt", "google_news_rss"),
    "filings": ("sec", "sec_company_page"),
}
PROVIDER_ALIASES = {
    "google_news": "google_news_rss",
    "google": "google_news_rss",
    "nasdaq_api": "nasdaq",
    "edgar_page": "sec_company_page",
}
DEFAULT_API_KEY_ENV = {
    "finnhub": "FINNHUB_API_KEY",
}


@dataclass(frozen=True)
class StockTarget:
    symbol: str
    name: str
    sector_key: str
    sector_label: str
    benchmark_etfs: tuple[str, ...]


def _observed_date(month: int, day: int, year: int) -> date:
    actual = date(year, month, day)
    if actual.weekday() == 5:
        return actual - timedelta(days=1)
    if actual.weekday() == 6:
        return actual + timedelta(days=1)
    return actual


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    current = date(year, month, 1)
    while current.weekday() != weekday:
        current += timedelta(days=1)
    return current + timedelta(days=7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    current = date(year, month + 1, 1) - timedelta(days=1)
    while current.weekday() != weekday:
        current -= timedelta(days=1)
    return current


def _easter_date(year: int) -> date:
    """Return Gregorian Easter date for US market Good Friday calculation."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    weekday_offset = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * weekday_offset) // 451
    month = (h + weekday_offset - 7 * m + 114) // 31
    day = ((h + weekday_offset - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def us_market_holidays(year: int) -> set[date]:
    """Common NYSE/Nasdaq full-market holidays for the given year."""
    holidays = {
        _observed_date(1, 1, year),
        _observed_date(1, 1, year + 1),
        _nth_weekday(year, 1, 0, 3),  # Martin Luther King Jr. Day
        _nth_weekday(year, 2, 0, 3),  # Washington's Birthday
        _easter_date(year) - timedelta(days=2),  # Good Friday
        _last_weekday(year, 5, 0),  # Memorial Day
        _observed_date(6, 19, year),  # Juneteenth
        _observed_date(7, 4, year),
        _nth_weekday(year, 9, 0, 1),  # Labor Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving
        _observed_date(12, 25, year),
    }
    return {d for d in holidays if d.year == year}


def is_us_market_day(day: date) -> bool:
    return day.weekday() < 5 and day not in us_market_holidays(day.year)


def market_date_from_config(config: dict[str, Any]) -> date:
    """Return the New York market date, optionally overridden for tests."""
    as_of = config.get("as_of_date")
    if as_of:
        return date.fromisoformat(str(as_of))
    return datetime.now(MARKET_TZ).date()


def load_stock_targets(config: dict[str, Any]) -> list[StockTarget]:
    targets: list[StockTarget] = []
    sectors = config.get("sectors", {})
    for sector_key, sector in sectors.items():
        label = sector.get("label", sector_key.replace("_", " ").title())
        benchmark_etfs = tuple(str(t).upper() for t in sector.get("benchmark_etfs", []) if t)
        for raw in sector.get("tickers", []):
            if isinstance(raw, str):
                symbol = raw.upper()
                name = symbol
            else:
                symbol = str(raw.get("symbol", "")).upper()
                name = raw.get("name") or symbol
            if not symbol:
                continue
            targets.append(
                StockTarget(
                    symbol=symbol,
                    name=name,
                    sector_key=sector_key,
                    sector_label=label,
                    benchmark_etfs=benchmark_etfs,
                )
            )
    return targets


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if value.upper() in {"", "N/A", "NA", "--"}:
                return None
            value = re.sub(r"[$,%]", "", value).replace(",", "")
        return float(value)
    except (TypeError, ValueError):
        return None


def _provider_name(provider: Any) -> str:
    name = str(provider or "").strip().lower().replace("-", "_")
    return PROVIDER_ALIASES.get(name, name)


def provider_order(config: dict[str, Any], kind: str) -> tuple[str, ...]:
    """Return configured provider order with a no-key fallback when omitted."""
    raw: Any = None
    data_providers = config.get("data_providers")
    if isinstance(data_providers, dict):
        entry = data_providers.get(kind)
        if isinstance(entry, dict):
            raw = entry.get("order")
        elif isinstance(entry, list):
            raw = entry
    if raw is None and isinstance(config.get("provider_order"), dict):
        raw = config["provider_order"].get(kind)
    if raw is None:
        raw = DEFAULT_PROVIDER_ORDER[kind]
    return tuple(dict.fromkeys(_provider_name(provider) for provider in raw if provider))


def provider_api_key(config: dict[str, Any], provider: str) -> str:
    env_map = config.get("api_key_env") if isinstance(config.get("api_key_env"), dict) else {}
    env_name = env_map.get(provider) or DEFAULT_API_KEY_ENV.get(provider, "")
    return os.environ.get(env_name, "") if env_name else ""


def _parse_chart_history(result: dict[str, Any]) -> list[dict[str, Any]]:
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators", {})
    quote = (indicators.get("quote") or [{}])[0]
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []
    history = []
    for idx, ts in enumerate(timestamps):
        close = _as_float(closes[idx] if idx < len(closes) else None)
        if close is None:
            continue
        history.append(
            {
                "date": datetime.fromtimestamp(ts, tz=UTC).date().isoformat(),
                "close": close,
                "volume": int(volumes[idx] or 0) if idx < len(volumes) and volumes[idx] else 0,
            }
        )
    return history


def parse_yahoo_chart(symbol: str, data: dict[str, Any]) -> dict[str, Any] | None:
    result = ((data.get("chart") or {}).get("result") or [None])[0]
    if not result:
        return None

    meta = result.get("meta", {})
    history = _parse_chart_history(result)
    regular_price = _as_float(meta.get("regularMarketPrice"))
    pre_market_price = _as_float(meta.get("preMarketPrice"))
    post_market_price = _as_float(meta.get("postMarketPrice"))
    previous_close = _as_float(meta.get("chartPreviousClose") or meta.get("previousClose"))

    latest_close = history[-1]["close"] if history else None
    price = pre_market_price or post_market_price or regular_price or latest_close
    if previous_close is None and len(history) >= 2:
        previous_close = history[-2]["close"]

    return {
        "symbol": symbol.upper(),
        "provider": "yahoo",
        "currency": meta.get("currency", "USD"),
        "exchange": meta.get("exchangeName", ""),
        "market_state": meta.get("marketState", ""),
        "price": price,
        "regular_market_price": regular_price,
        "pre_market_price": pre_market_price,
        "post_market_price": post_market_price,
        "previous_close": previous_close,
        "history": history,
        "data_quality": "delayed",
        "source_url": f"https://finance.yahoo.com/quote/{symbol.upper()}",
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def fetch_yahoo_chart(
    symbol: str,
    client: httpx.Client,
    history_days: int = 90,
) -> dict[str, Any] | None:
    last_error: httpx.HTTPError | None = None
    for url_template in YAHOO_CHART_URLS:
        try:
            resp = client.get(
                url_template.format(symbol=symbol.upper()),
                params={
                    "range": f"{max(history_days, 5)}d",
                    "interval": "1d",
                    "includePrePost": "true",
                    "events": "div,splits",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            last_error = exc
            continue
        except ValueError:
            continue
        parsed = parse_yahoo_chart(symbol, data)
        if parsed:
            return parsed
    if last_error:
        raise last_error
    return None


def _parse_nasdaq_date(value: str) -> str | None:
    value = value.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_nasdaq_quote(
    symbol: str,
    info_data: dict[str, Any],
    history_data: dict[str, Any],
    assetclass: str,
) -> dict[str, Any] | None:
    info = info_data.get("data") or {}
    if not info:
        return None
    primary = info.get("primaryData") or {}
    rows = ((history_data.get("data") or {}).get("tradesTable") or {}).get("rows") or []
    history = []
    for row in reversed(rows):
        close = _as_float(row.get("close"))
        parsed_date = _parse_nasdaq_date(str(row.get("date", "")))
        if close is None or not parsed_date:
            continue
        history.append(
            {
                "date": parsed_date,
                "close": close,
                "volume": int(_as_float(row.get("volume")) or 0),
            }
        )

    price = _as_float(primary.get("lastSalePrice"))
    latest_close = history[-1]["close"] if history else None
    price = price or latest_close
    net_change = _as_float(primary.get("netChange"))
    previous_close = price - net_change if price is not None and net_change is not None else None
    if previous_close is None and len(history) >= 2:
        previous_close = history[-2]["close"]

    return {
        "symbol": symbol.upper(),
        "provider": "nasdaq",
        "currency": "USD",
        "exchange": info.get("exchange", ""),
        "market_state": primary.get("marketStatus") or "",
        "price": price,
        "regular_market_price": price,
        "pre_market_price": None,
        "post_market_price": None,
        "previous_close": previous_close,
        "history": history,
        "data_quality": "delayed_fallback",
        "source_url": f"https://www.nasdaq.com/market-activity/{assetclass}/{symbol.lower()}",
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def fetch_nasdaq_chart(
    symbol: str,
    client: httpx.Client,
    history_days: int = 90,
    end_date: date | None = None,
) -> dict[str, Any] | None:
    end_date = end_date or datetime.now(MARKET_TZ).date()
    start_date = end_date - timedelta(days=max(history_days, 5) + 7)
    for assetclass in ("stocks", "etf"):
        try:
            info_resp = client.get(
                NASDAQ_INFO_URL.format(symbol=symbol.upper()),
                params={"assetclass": assetclass},
                headers=NASDAQ_HEADERS,
            )
            info_resp.raise_for_status()
            info_data = info_resp.json()
            if not info_data.get("data"):
                continue
            history_resp = client.get(
                NASDAQ_HISTORY_URL.format(symbol=symbol.upper()),
                params={
                    "assetclass": assetclass,
                    "fromdate": start_date.isoformat(),
                    "todate": end_date.isoformat(),
                    "limit": max(history_days + 10, 30),
                },
                headers=NASDAQ_HEADERS,
            )
            history_resp.raise_for_status()
            history_data = history_resp.json()
        except (httpx.HTTPError, ValueError):
            continue
        parsed = parse_nasdaq_quote(symbol, info_data, history_data, assetclass)
        if parsed:
            return parsed
    return None


def parse_finnhub_quote(
    symbol: str,
    quote_data: dict[str, Any],
    candle_data: dict[str, Any],
) -> dict[str, Any] | None:
    price = _as_float(quote_data.get("c"))
    previous_close = _as_float(quote_data.get("pc"))
    timestamps = candle_data.get("t") or []
    closes = candle_data.get("c") or []
    volumes = candle_data.get("v") or []
    history = []
    if candle_data.get("s") == "ok":
        for idx, ts in enumerate(timestamps):
            close = _as_float(closes[idx] if idx < len(closes) else None)
            if close is None:
                continue
            history.append(
                {
                    "date": datetime.fromtimestamp(ts, tz=UTC).date().isoformat(),
                    "close": close,
                    "volume": int(volumes[idx] or 0) if idx < len(volumes) and volumes[idx] else 0,
                }
            )

    latest_close = history[-1]["close"] if history else None
    price = price or latest_close
    if previous_close is None and len(history) >= 2:
        previous_close = history[-2]["close"]
    if price is None and previous_close is None:
        return None

    return {
        "symbol": symbol.upper(),
        "provider": "finnhub",
        "currency": "USD",
        "exchange": "",
        "market_state": "",
        "price": price,
        "regular_market_price": price,
        "pre_market_price": None,
        "post_market_price": None,
        "previous_close": previous_close,
        "history": history,
        "data_quality": "api",
        "source_url": f"https://finnhub.io/quote/{symbol.upper()}",
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def fetch_finnhub_quote(
    symbol: str,
    client: httpx.Client,
    history_days: int,
    market_day: date,
    api_key: str,
) -> dict[str, Any] | None:
    if not api_key:
        return None
    start = datetime.combine(
        market_day - timedelta(days=max(history_days, 5) + 7), time.min, tzinfo=UTC
    )
    end = datetime.combine(market_day + timedelta(days=1), time.min, tzinfo=UTC)
    quote_resp = client.get(
        FINNHUB_QUOTE_URL,
        params={"symbol": symbol.upper(), "token": api_key},
    )
    quote_resp.raise_for_status()
    candle_resp = client.get(
        FINNHUB_CANDLE_URL,
        params={
            "symbol": symbol.upper(),
            "resolution": "D",
            "from": int(start.timestamp()),
            "to": int(end.timestamp()),
            "token": api_key,
        },
    )
    candle_resp.raise_for_status()
    try:
        quote_data = quote_resp.json()
        candle_data = candle_resp.json()
    except ValueError:
        return None
    return parse_finnhub_quote(symbol, quote_data, candle_data)


def fetch_quote_with_fallback(
    symbol: str,
    client: httpx.Client,
    history_days: int,
    providers: tuple[str, ...],
    market_day: date,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    for provider in providers:
        try:
            if provider == "finnhub":
                quote = fetch_finnhub_quote(
                    symbol,
                    client=client,
                    history_days=history_days,
                    market_day=market_day,
                    api_key=provider_api_key(config, "finnhub"),
                )
            elif provider == "yahoo":
                quote = fetch_yahoo_chart(symbol, client=client, history_days=history_days)
            elif provider == "nasdaq":
                quote = fetch_nasdaq_chart(
                    symbol,
                    client=client,
                    history_days=history_days,
                    end_date=market_day,
                )
            else:
                continue
        except httpx.HTTPError:
            quote = None
        if quote:
            quote["fallback_chain"] = list(providers)
            return quote
    return None


def parse_gdelt_articles(data: dict[str, Any], max_items: int) -> list[dict[str, Any]]:
    articles = []
    for raw in (data.get("articles") or [])[:max_items]:
        title = raw.get("title") or ""
        url = raw.get("url") or raw.get("url_mobile") or ""
        if not title or not url:
            continue
        articles.append(
            {
                "title": title,
                "url": url,
                "domain": raw.get("domain", ""),
                "published_at": raw.get("seendate") or "",
                "provider": "gdelt",
                "source": raw.get("sourcecountry", ""),
            }
        )
    return articles


def fetch_gdelt_news(
    target: StockTarget,
    client: httpx.Client,
    window_hours: int = 18,
    max_items: int = 3,
) -> list[dict[str, Any]]:
    query = f'("{target.symbol}" OR "{target.name}") stock'
    resp = client.get(
        GDELT_DOC_URL,
        params={
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": max_items,
            "sort": "HybridRel",
            "timespan": f"{max(window_hours, 1)}h",
        },
    )
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError:
        return []
    return parse_gdelt_articles(data, max_items)


def parse_finnhub_news(data: Any, max_items: int) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    articles = []
    for raw in data[:max_items]:
        title = raw.get("headline") or raw.get("title") or ""
        url = raw.get("url") or ""
        if not title or not url:
            continue
        published_at = ""
        published_ts = _as_float(raw.get("datetime"))
        if published_ts is not None:
            published_at = datetime.fromtimestamp(published_ts, tz=UTC).isoformat()
        articles.append(
            {
                "title": title,
                "url": url,
                "domain": raw.get("source", ""),
                "published_at": published_at,
                "provider": "finnhub",
                "source": raw.get("source", ""),
            }
        )
    return articles


def fetch_finnhub_news(
    target: StockTarget,
    client: httpx.Client,
    window_hours: int,
    max_items: int,
    api_key: str,
) -> list[dict[str, Any]]:
    if not api_key:
        return []
    today = datetime.now(MARKET_TZ).date()
    start = today - timedelta(days=max(1, (window_hours + 23) // 24))
    resp = client.get(
        FINNHUB_COMPANY_NEWS_URL,
        params={
            "symbol": target.symbol.upper(),
            "from": start.isoformat(),
            "to": today.isoformat(),
            "token": api_key,
        },
    )
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError:
        return []
    return parse_finnhub_news(data, max_items)


def parse_google_news_rss(text: str, max_items: int) -> list[dict[str, Any]]:
    articles = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    for raw in root.findall("./channel/item")[:max_items]:
        title = (raw.findtext("title") or "").strip()
        url = (raw.findtext("link") or "").strip()
        if not title or not url:
            continue
        published_at = raw.findtext("pubDate") or ""
        if published_at:
            try:
                published_at = parsedate_to_datetime(published_at).astimezone(UTC).isoformat()
            except (TypeError, ValueError, AttributeError):
                pass
        source = raw.find("source")
        articles.append(
            {
                "title": title,
                "url": url,
                "domain": source.get("url", "") if source is not None else "",
                "published_at": published_at,
                "provider": "google_news_rss",
                "source": (source.text or "") if source is not None else "Google News",
            }
        )
    return articles


def fetch_google_news_rss(
    target: StockTarget,
    client: httpx.Client,
    window_hours: int = 18,
    max_items: int = 3,
) -> list[dict[str, Any]]:
    window_days = max(1, (window_hours + 23) // 24)
    query = f'"{target.name}" "{target.symbol}" stock when:{window_days}d'
    resp = client.get(
        GOOGLE_NEWS_RSS_URL,
        params={
            "q": query,
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        },
    )
    resp.raise_for_status()
    return parse_google_news_rss(resp.text, max_items)


def fetch_news_with_fallback(
    target: StockTarget,
    client: httpx.Client,
    providers: tuple[str, ...],
    window_hours: int,
    max_items: int,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    for provider in providers:
        try:
            if provider == "finnhub":
                news = fetch_finnhub_news(
                    target,
                    client=client,
                    window_hours=window_hours,
                    max_items=max_items,
                    api_key=provider_api_key(config, "finnhub"),
                )
            elif provider == "gdelt":
                news = fetch_gdelt_news(
                    target,
                    client=client,
                    window_hours=window_hours,
                    max_items=max_items,
                )
            elif provider == "google_news_rss":
                news = fetch_google_news_rss(
                    target,
                    client=client,
                    window_hours=window_hours,
                    max_items=max_items,
                )
            else:
                continue
        except httpx.HTTPError:
            news = []
        if news:
            return news
    return []


def _sec_headers() -> dict[str, str] | None:
    user_agent = os.environ.get("SEC_USER_AGENT") or os.environ.get("LINNET_SEC_USER_AGENT")
    if not user_agent:
        return None
    return {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate", "Host": "www.sec.gov"}


def fetch_recent_sec_filings(
    symbols: list[str],
    client: httpx.Client,
    max_filings: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch recent filing metadata when the user configured a SEC User-Agent."""
    headers = _sec_headers()
    if not headers:
        return {}

    try:
        tickers_resp = client.get(SEC_COMPANY_TICKERS_URL, headers=headers)
        tickers_resp.raise_for_status()
        ticker_rows = tickers_resp.json().values()
    except httpx.HTTPError:
        return {}
    except ValueError:
        return {}

    cik_by_symbol = {
        str(row.get("ticker", "")).upper(): str(row.get("cik_str", "")).zfill(10)
        for row in ticker_rows
    }
    filings_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for symbol in symbols:
        cik = cik_by_symbol.get(symbol.upper())
        if not cik:
            continue
        try:
            resp = client.get(
                SEC_SUBMISSIONS_URL.format(cik=cik),
                headers={**headers, "Host": "data.sec.gov"},
            )
            resp.raise_for_status()
            recent = (resp.json().get("filings") or {}).get("recent") or {}
        except (httpx.HTTPError, ValueError):
            continue

        forms = recent.get("form") or []
        dates = recent.get("filingDate") or []
        accession_numbers = recent.get("accessionNumber") or []
        filings = []
        for idx, form in enumerate(forms[:max_filings]):
            filed_at = dates[idx] if idx < len(dates) else ""
            accession = accession_numbers[idx] if idx < len(accession_numbers) else ""
            filings.append(
                {
                    "form": form,
                    "filed_at": filed_at,
                    "accession_number": accession,
                    "provider": "sec",
                }
            )
        filings_by_symbol[symbol.upper()] = filings
    return filings_by_symbol


def sec_company_page_url(symbol: str) -> str:
    return f"https://www.sec.gov/edgar/browse/?CIK={symbol.upper()}&owner=exclude"


def fetch_us_stock_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Fetch raw data for the configured US stock universe."""
    market_day = market_date_from_config(config)
    if not is_us_market_day(market_day):
        return {
            "market_date": market_day.isoformat(),
            "market_status": "closed",
            "skip_reason": "weekend_or_us_market_holiday",
            "stocks": [],
            "benchmarks": {},
            "provider_coverage": {},
            "invalid_symbols": [],
        }

    targets = load_stock_targets(config)
    max_symbols = int(config.get("max_symbols", 0) or 0)
    if max_symbols > 0:
        targets = targets[:max_symbols]
    history_days = int(config.get("history_days", 90))
    news_window_hours = int(config.get("news_window_hours", 18))
    max_news_per_symbol = int(config.get("max_news_per_symbol", 3))
    timeout = float(config.get("request_timeout", 20.0))
    quote_providers = provider_order(config, "quotes")
    news_providers = provider_order(config, "news")
    filing_providers = provider_order(config, "filings")

    stocks = []
    benchmarks: dict[str, dict[str, Any]] = {}
    benchmark_symbols = sorted({etf for target in targets for etf in target.benchmark_etfs})
    quote_ok = 0
    news_ok = 0
    quote_missing: list[str] = []
    quote_provider_counts: dict[str, int] = {}
    news_provider_counts: dict[str, int] = {}

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for symbol in benchmark_symbols:
            quote = fetch_quote_with_fallback(
                symbol,
                client=client,
                history_days=history_days,
                providers=quote_providers,
                market_day=market_day,
                config=config,
            )
            if quote:
                benchmarks[symbol] = quote

        for target in targets:
            quote = fetch_quote_with_fallback(
                target.symbol,
                client=client,
                history_days=history_days,
                providers=quote_providers,
                market_day=market_day,
                config=config,
            )
            if quote:
                quote_ok += 1
                provider = str(quote.get("provider", "unknown"))
                quote_provider_counts[provider] = quote_provider_counts.get(provider, 0) + 1
            else:
                quote_missing.append(target.symbol)
            news = fetch_news_with_fallback(
                target,
                client=client,
                providers=news_providers,
                window_hours=news_window_hours,
                max_items=max_news_per_symbol,
                config=config,
            )
            if news:
                news_ok += 1
                provider = str(news[0].get("provider", "unknown"))
                news_provider_counts[provider] = news_provider_counts.get(provider, 0) + 1
            stocks.append(
                {
                    "symbol": target.symbol,
                    "name": target.name,
                    "sector_key": target.sector_key,
                    "sector": target.sector_label,
                    "benchmark_etfs": list(target.benchmark_etfs),
                    "quote": quote,
                    "news": news,
                    "filings": [],
                    "filing_lookup_url": sec_company_page_url(target.symbol)
                    if "sec_company_page" in filing_providers
                    else "",
                }
            )

        filings = (
            fetch_recent_sec_filings([target.symbol for target in targets], client=client)
            if "sec" in filing_providers
            else {}
        )
        for stock in stocks:
            stock["filings"] = filings.get(stock["symbol"], [])

    return {
        "market_date": market_day.isoformat(),
        "market_status": "premarket",
        "skip_reason": "",
        "stocks": stocks,
        "benchmarks": benchmarks,
        "provider_coverage": {
            "quotes": {
                "provider": quote_providers[0] if quote_providers else "none",
                "order": list(quote_providers),
                "providers": quote_provider_counts,
                "ok": quote_ok,
                "total": len(targets),
            },
            "news": {
                "provider": news_providers[0] if news_providers else "none",
                "order": list(news_providers),
                "providers": news_provider_counts,
                "ok": news_ok,
                "total": len(targets),
            },
            "filings": {
                "provider": filing_providers[0] if filing_providers else "none",
                "order": list(filing_providers),
                "providers": {"sec": sum(1 for stock in stocks if stock.get("filings"))},
                "ok": sum(1 for stock in stocks if stock.get("filings")),
                "fallback_ok": sum(1 for stock in stocks if stock.get("filing_lookup_url")),
                "total": len(targets),
                "requires_env": "SEC_USER_AGENT or LINNET_SEC_USER_AGENT",
            },
        },
        "invalid_symbols": quote_missing,
    }
