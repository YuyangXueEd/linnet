from datetime import date

from extensions.base import FeedSection
from extensions.us_stocks import USStocksExtension
from extensions.us_stocks.collector import (
    fetch_finnhub_news,
    fetch_gdelt_news,
    fetch_google_news_rss,
    fetch_nasdaq_chart,
    fetch_us_stock_inputs,
    is_us_market_day,
    load_stock_targets,
    parse_finnhub_news,
    parse_finnhub_quote,
    parse_google_news_rss,
    parse_nasdaq_quote,
    parse_yahoo_chart,
)
from extensions.us_stocks.scorer import build_sector_overview, score_all_stocks, score_stocks
from extensions.us_stocks.summarizer import parse_signal_synthesis, synthesize_us_stock_signals


def _chart_payload(
    *,
    symbol: str = "NVDA",
    price: float = 121.0,
    previous_close: float = 119.0,
    premarket: float | None = None,
    closes: list[float] | None = None,
) -> dict:
    closes = closes or [100, 102, 104, 106, 108, 110, 112, 114, 116, 119, price]
    timestamps = [1762300800 + idx * 86400 for idx in range(len(closes))]
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "USD",
                        "symbol": symbol,
                        "exchangeName": "NMS",
                        "marketState": "PRE",
                        "regularMarketPrice": price,
                        "preMarketPrice": premarket,
                        "previousClose": previous_close,
                    },
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "close": closes,
                                "volume": [100, 120, 130, 140, 150, 160, 180, 210, 240, 260, 500],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


def _nasdaq_info_payload(symbol: str = "NVDA") -> dict:
    return {
        "data": {
            "symbol": symbol,
            "companyName": "NVIDIA Corporation Common Stock",
            "exchange": "NASDAQ-GS",
            "primaryData": {
                "lastSalePrice": "$123.00",
                "netChange": "+4.00",
                "percentageChange": "+3.36%",
                "marketStatus": "Closed",
                "volume": "10,000,000",
            },
        }
    }


def _nasdaq_history_payload() -> dict:
    return {
        "data": {
            "tradesTable": {
                "rows": [
                    {"date": "04/24/2026", "close": "$123.00", "volume": "10,000,000"},
                    {"date": "04/23/2026", "close": "$119.00", "volume": "8,000,000"},
                    {"date": "04/22/2026", "close": "$117.00", "volume": "7,500,000"},
                ]
            }
        }
    }


def _finnhub_quote_payload() -> dict:
    return {"c": 123.0, "pc": 119.0, "d": 4.0, "dp": 3.36, "t": 1777046400}


def _finnhub_candle_payload() -> dict:
    return {
        "s": "ok",
        "t": [1776816000, 1776902400, 1776988800],
        "c": [117.0, 119.0, 123.0],
        "v": [7_500_000, 8_000_000, 10_000_000],
    }


def _finnhub_news_payload() -> list[dict]:
    return [
        {
            "headline": "Nvidia shares rally as AI demand grows",
            "url": "https://news.example.com/nvda",
            "source": "Example News",
            "datetime": 1777032000,
        }
    ]


def _google_rss_payload() -> str:
    return """
    <rss version="2.0">
      <channel>
        <item>
          <title>Nvidia stock rises as AI demand improves</title>
          <link>https://news.example.com/nvda</link>
          <pubDate>Fri, 24 Apr 2026 12:00:00 GMT</pubDate>
          <source url="https://news.example.com">Example News</source>
        </item>
      </channel>
    </rss>
    """


def _small_config() -> dict:
    return {
        "as_of_date": "2026-04-24",
        "max_items": 5,
        "history_days": 30,
        "news_window_hours": 18,
        "max_news_per_symbol": 2,
        "sectors": {
            "chips": {
                "label": "Chips",
                "benchmark_etfs": ["SMH"],
                "tickers": [{"symbol": "NVDA", "name": "Nvidia"}],
            }
        },
    }


def test_us_market_day_skips_weekends_and_common_holidays():
    assert is_us_market_day(date(2026, 4, 24))
    assert not is_us_market_day(date(2026, 4, 25))
    assert not is_us_market_day(date(2026, 12, 25))
    assert not is_us_market_day(date(2026, 4, 3))  # Good Friday
    assert not is_us_market_day(date(2021, 12, 31))  # 2022 New Year's Day observed


def test_parse_yahoo_chart_extracts_price_and_history():
    parsed = parse_yahoo_chart(
        "NVDA",
        _chart_payload(price=121.0, previous_close=119.0, premarket=123.0),
    )

    assert parsed is not None
    assert parsed["symbol"] == "NVDA"
    assert parsed["price"] == 123.0
    assert parsed["previous_close"] == 119.0
    assert parsed["data_quality"] == "delayed"
    assert len(parsed["history"]) == 11


def test_parse_nasdaq_quote_extracts_delayed_fallback_history():
    parsed = parse_nasdaq_quote(
        "NVDA",
        _nasdaq_info_payload(),
        _nasdaq_history_payload(),
        "stocks",
    )

    assert parsed is not None
    assert parsed["provider"] == "nasdaq"
    assert parsed["price"] == 123.0
    assert parsed["previous_close"] == 119.0
    assert parsed["data_quality"] == "delayed_fallback"
    assert [row["date"] for row in parsed["history"]] == ["2026-04-22", "2026-04-23", "2026-04-24"]


def test_fetch_nasdaq_chart_tries_stock_assetclass(httpx_mock):
    httpx_mock.add_response(json=_nasdaq_info_payload())
    httpx_mock.add_response(json=_nasdaq_history_payload())

    import httpx

    with httpx.Client() as client:
        parsed = fetch_nasdaq_chart("NVDA", client, end_date=date(2026, 4, 24))

    assert parsed is not None
    assert parsed["provider"] == "nasdaq"


def test_parse_finnhub_quote_extracts_quote_and_candles():
    parsed = parse_finnhub_quote("NVDA", _finnhub_quote_payload(), _finnhub_candle_payload())

    assert parsed is not None
    assert parsed["provider"] == "finnhub"
    assert parsed["price"] == 123.0
    assert parsed["previous_close"] == 119.0
    assert parsed["history"][-1]["close"] == 123.0


def test_parse_finnhub_news_extracts_company_news():
    articles = parse_finnhub_news(_finnhub_news_payload(), max_items=1)

    assert articles[0]["provider"] == "finnhub"
    assert articles[0]["title"].startswith("Nvidia")


def test_fetch_finnhub_news_skips_without_key(httpx_mock):
    target = load_stock_targets(_small_config())[0]

    import httpx

    with httpx.Client() as client:
        articles = fetch_finnhub_news(target, client, window_hours=18, max_items=1, api_key="")

    assert articles == []
    assert len(httpx_mock.get_requests()) == 0


def test_parse_google_news_rss_extracts_articles():
    articles = parse_google_news_rss(_google_rss_payload(), max_items=2)

    assert len(articles) == 1
    assert articles[0]["provider"] == "google_news_rss"
    assert articles[0]["title"].startswith("Nvidia")


def test_fetch_google_news_rss_uses_configured_window(httpx_mock):
    target = load_stock_targets(_small_config())[0]
    httpx_mock.add_response(text=_google_rss_payload())

    import httpx

    with httpx.Client() as client:
        articles = fetch_google_news_rss(target, client, window_hours=18, max_items=1)

    assert articles[0]["title"].startswith("Nvidia")


def test_fetch_us_stock_inputs_uses_yahoo_and_gdelt(httpx_mock, monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    monkeypatch.delenv("LINNET_SEC_USER_AGENT", raising=False)
    httpx_mock.add_response(json=_chart_payload(symbol="SMH", price=250.0, previous_close=246.0))
    httpx_mock.add_response(
        json=_chart_payload(symbol="NVDA", price=121.0, previous_close=119.0, premarket=123.0)
    )
    httpx_mock.add_response(
        json={
            "articles": [
                {
                    "title": "Nvidia shares rally as AI demand grows",
                    "url": "https://example.com/nvda",
                    "domain": "example.com",
                    "seendate": "20260424T120000Z",
                }
            ]
        }
    )

    payload = fetch_us_stock_inputs(_small_config())

    assert payload["market_status"] == "premarket"
    assert payload["provider_coverage"]["quotes"]["ok"] == 1
    assert payload["provider_coverage"]["news"]["ok"] == 1
    assert payload["provider_coverage"]["filings"]["fallback_ok"] == 1
    assert payload["stocks"][0]["symbol"] == "NVDA"
    assert payload["stocks"][0]["news"][0]["title"].startswith("Nvidia")
    assert payload["stocks"][0]["filing_lookup_url"].startswith("https://www.sec.gov/edgar/browse/")


def test_fetch_us_stock_inputs_uses_google_news_fallback_when_gdelt_is_empty(
    httpx_mock, monkeypatch
):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    monkeypatch.delenv("LINNET_SEC_USER_AGENT", raising=False)
    httpx_mock.add_response(json=_chart_payload(symbol="SMH", price=250.0, previous_close=246.0))
    httpx_mock.add_response(json=_chart_payload(symbol="NVDA", price=121.0, previous_close=119.0))
    httpx_mock.add_response(json={"articles": []})
    httpx_mock.add_response(text=_google_rss_payload())

    payload = fetch_us_stock_inputs(_small_config())

    assert payload["provider_coverage"]["news"]["providers"] == {"google_news_rss": 1}
    assert payload["stocks"][0]["news"][0]["provider"] == "google_news_rss"


def test_keyed_provider_without_env_falls_back_to_public_providers(httpx_mock, monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    monkeypatch.delenv("LINNET_SEC_USER_AGENT", raising=False)
    config = _small_config()
    config["data_providers"] = {
        "quotes": {"order": ["finnhub", "yahoo", "nasdaq"]},
        "news": {"order": ["finnhub", "gdelt", "google_news_rss"]},
        "filings": {"order": ["sec_company_page"]},
    }
    httpx_mock.add_response(json=_chart_payload(symbol="SMH", price=250.0, previous_close=246.0))
    httpx_mock.add_response(json=_chart_payload(symbol="NVDA", price=121.0, previous_close=119.0))
    httpx_mock.add_response(
        json={
            "articles": [
                {
                    "title": "Nvidia shares rally as AI demand grows",
                    "url": "https://example.com/nvda",
                }
            ]
        }
    )

    payload = fetch_us_stock_inputs(config)

    assert payload["provider_coverage"]["quotes"]["providers"] == {"yahoo": 1}
    assert payload["provider_coverage"]["news"]["providers"] == {"gdelt": 1}
    requested_urls = [str(request.url) for request in httpx_mock.get_requests()]
    assert not any("finnhub.io" in url for url in requested_urls)


def test_fetch_us_stock_inputs_respects_max_symbols_on_market_day(httpx_mock, monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    monkeypatch.delenv("LINNET_SEC_USER_AGENT", raising=False)
    config = _small_config()
    config["max_symbols"] = 1
    config["sectors"]["chips"]["tickers"].append(
        {"symbol": "AMD", "name": "Advanced Micro Devices"}
    )
    httpx_mock.add_response(json=_chart_payload(symbol="SMH", price=250.0, previous_close=246.0))
    httpx_mock.add_response(json=_chart_payload(symbol="NVDA", price=121.0, previous_close=119.0))
    httpx_mock.add_response(json={"articles": []})
    httpx_mock.add_response(text="<rss><channel /></rss>")

    payload = fetch_us_stock_inputs(config)

    assert [stock["symbol"] for stock in payload["stocks"]] == ["NVDA"]
    assert payload["provider_coverage"]["quotes"]["total"] == 1


def test_gdelt_non_json_response_degrades_to_empty_news(httpx_mock):
    target = load_stock_targets(_small_config())[0]
    httpx_mock.add_response(text="temporarily unavailable", status_code=200)

    import httpx

    with httpx.Client() as client:
        assert fetch_gdelt_news(target, client) == []


def test_score_stocks_ranks_bullish_news_and_sector_strength():
    config = {**_small_config(), "signal_thresholds": {"bullish": 65, "bearish": 35}}
    raw_payload = {
        "benchmarks": {
            "SMH": parse_yahoo_chart(
                "SMH",
                _chart_payload(symbol="SMH", price=250.0, previous_close=245.0),
            )
        },
        "stocks": [
            {
                "symbol": "NVDA",
                "name": "Nvidia",
                "sector": "Chips",
                "sector_key": "chips",
                "benchmark_etfs": ["SMH"],
                "quote": parse_yahoo_chart(
                    "NVDA",
                    _chart_payload(price=121.0, previous_close=119.0, premarket=123.0),
                ),
                "news": [
                    {
                        "title": "Nvidia upgraded as AI demand growth accelerates",
                        "url": "https://example.com/nvda",
                    }
                ],
                "filings": [{"form": "8-K", "filed_at": "2026-04-24"}],
            }
        ],
    }

    items = score_stocks(raw_payload, config)

    assert len(items) == 1
    assert items[0]["signal"] == "bullish"
    assert items[0]["setup_type"] in {"gap_up_news", "sector_tailwind"}
    assert items[0]["data_quality"]["quote"] == "delayed"
    assert items[0]["sources"][0]["title"].startswith("Nvidia")


def test_score_stocks_allows_high_confidence_bearish_setups():
    config = {
        **_small_config(),
        "signal_thresholds": {"bullish": 70, "bearish": 35, "high_confidence": 75},
        "scoring_weights": {
            "premarket_move": 0.7,
            "news": 0.2,
            "earnings_financials": 0.0,
            "technicals": 0.0,
            "sector_trend": 0.0,
            "risk_flags": 0.1,
        },
    }
    raw_payload = {
        "benchmarks": {},
        "stocks": [
            {
                "symbol": "NVDA",
                "name": "Nvidia",
                "sector": "Chips",
                "sector_key": "chips",
                "benchmark_etfs": [],
                "quote": parse_yahoo_chart(
                    "NVDA",
                    _chart_payload(price=100.0, previous_close=119.0, premarket=100.0),
                ),
                "news": [
                    {"title": "Nvidia warning as AI demand drops", "url": "https://example.com"}
                ],
                "filings": [{"form": "8-K", "filed_at": "2026-04-24"}],
            }
        ],
    }

    items = score_stocks(raw_payload, config)

    assert items[0]["signal"] == "bearish"
    assert items[0]["confidence"] == "high"


def test_sector_overview_aggregates_ranked_signals():
    config = {**_small_config(), "signal_thresholds": {"bullish": 65, "bearish": 35}}
    raw_payload = {
        "benchmarks": {
            "SMH": parse_yahoo_chart(
                "SMH",
                _chart_payload(symbol="SMH", price=250.0, previous_close=245.0),
            )
        },
        "stocks": [
            {
                "symbol": "NVDA",
                "name": "Nvidia",
                "sector": "Chips",
                "sector_key": "chips",
                "benchmark_etfs": ["SMH"],
                "quote": parse_yahoo_chart(
                    "NVDA",
                    _chart_payload(price=121.0, previous_close=119.0, premarket=123.0),
                ),
                "news": [
                    {"title": "Nvidia upgraded as AI demand grows", "url": "https://example.com"}
                ],
                "filings": [],
                "filing_lookup_url": "https://www.sec.gov/edgar/browse/?CIK=NVDA",
            },
            {
                "symbol": "AMD",
                "name": "Advanced Micro Devices",
                "sector": "Chips",
                "sector_key": "chips",
                "benchmark_etfs": ["SMH"],
                "quote": parse_yahoo_chart(
                    "AMD",
                    _chart_payload(symbol="AMD", price=102.0, previous_close=101.0),
                ),
                "news": [],
                "filings": [],
                "filing_lookup_url": "https://www.sec.gov/edgar/browse/?CIK=AMD",
            },
        ],
    }

    items = score_all_stocks(raw_payload, config)
    overview = build_sector_overview(items, config)

    assert len(overview) == 1
    assert overview[0]["sector"] == "Chips"
    assert overview[0]["stock_count"] == 2
    assert overview[0]["counts"]["bullish"] >= 1
    assert overview[0]["top_symbol"] in {"NVDA", "AMD"}


def test_parse_signal_synthesis_accepts_fenced_json():
    parsed = parse_signal_synthesis(
        """
        ```json
        {
          "signals": [
            {
              "symbol": "NVDA",
              "summary": "AI demand is the main driver.",
              "drivers": ["Positive headline", "Sector tape is firm"],
              "invalidation": ["Fades below previous close"],
              "risk_flags": ["Valuation sensitivity"]
            }
          ]
        }
        ```
        """
    )

    assert parsed["NVDA"]["summary"] == "AI demand is the main driver."
    assert parsed["NVDA"]["drivers"] == ["Positive headline", "Sector tape is firm"]


def test_synthesize_us_stock_signals_updates_top_items_with_llm_json():
    class FakeCompletions:
        def create(self, **kwargs):
            class Message:
                content = """
                {
                  "signals": [
                    {
                      "symbol": "NVDA",
                      "summary": "LLM summary focused on AI demand.",
                      "drivers": ["AI demand headline", "Positive sector trend"],
                      "invalidation": ["Loses previous close"],
                      "risk_flags": ["Crowded trade"]
                    }
                  ]
                }
                """

            class Choice:
                message = Message()

            class Response:
                choices = [Choice()]

            assert kwargs["temperature"] == 0.2
            return Response()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    items = [
        {
            "symbol": "NVDA",
            "name": "Nvidia",
            "sector": "Chips",
            "signal": "bullish",
            "score": 82,
            "confidence": "high",
            "summary": "deterministic",
            "drivers": ["old"],
            "invalidation": ["old"],
            "risk_flags": [],
            "sources": [{"title": "Nvidia upgraded", "provider": "fixture"}],
            "data_quality": {"quote": "fixture"},
        }
    ]

    enriched = synthesize_us_stock_signals(items, FakeClient(), "test-model")

    assert enriched[0]["summary"] == "LLM summary focused on AI demand."
    assert enriched[0]["drivers"] == ["AI demand headline", "Positive sector trend"]
    assert enriched[0]["invalidation"] == ["Loses previous close"]
    assert enriched[0]["risk_flags"] == ["Crowded trade"]
    assert enriched[0]["llm_synthesized"] is True


def test_extension_skips_closed_market_day():
    ext = USStocksExtension(
        {
            "as_of_date": "2026-04-25",
            "sectors": {
                "chips": {
                    "label": "Chips",
                    "tickers": [{"symbol": "NVDA", "name": "Nvidia"}],
                }
            },
        }
    )

    items = ext.fetch()
    processed = ext.process(items)
    section = ext.render(processed)

    assert processed == []
    assert isinstance(section, FeedSection)
    assert section.meta["market_status"] == "closed"
    assert section.meta["skip_reason"] == "weekend_or_us_market_holiday"
