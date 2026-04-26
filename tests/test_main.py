import main
from extensions.arxiv import _prepare_papers as prepare_papers_for_rendering


def test_prepare_papers_for_rendering_sorts_by_score_first():
    papers = [
        {
            "title": "A",
            "score": 9.1,
            "categories": ["cs.LG", "cs.CV"],
        },
        {
            "title": "B",
            "score": 8.8,
            "categories": ["cs.CV", "cs.LG"],
        },
        {
            "title": "C",
            "score": 9.9,
            "categories": ["cs.AI"],
        },
    ]

    ordered = prepare_papers_for_rendering(papers, ["cs.CV", "cs.AI", "cs.LG"])

    # Should be sorted by score descending: C (9.9), A (9.1), B (8.8)
    assert [p["title"] for p in ordered] == ["C", "A", "B"]
    assert ordered[0]["primary_category"] == "cs.AI"
    assert ordered[1]["primary_category"] == "cs.CV"
    assert ordered[2]["primary_category"] == "cs.CV"


def test_get_llm_client_uses_provider_specific_api_key_env(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(main, "OpenAI", FakeOpenAI)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")

    main.get_llm_client(
        {
            "llm": {
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key_env": "OPENAI_API_KEY",
            }
        }
    )

    assert captured["api_key"] == "sk-openai-test"
    assert captured["base_url"] == "https://api.openai.com/v1"
    assert "default_headers" not in captured


def test_get_llm_client_only_adds_openrouter_headers_for_openrouter(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(main, "OpenAI", FakeOpenAI)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    main.get_llm_client(
        {
            "llm": {
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_env": "OPENROUTER_API_KEY",
            }
        }
    )

    assert captured["api_key"] == "sk-or-test"
    assert captured["base_url"] == "https://openrouter.ai/api/v1"
    assert captured["default_headers"] == {
        "HTTP-Referer": "https://github.com/YuyangXueEd/linnet",
        "X-OpenRouter-Title": "Linnet",
    }


def test_get_llm_client_loads_api_key_from_dotenv(tmp_path, monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    env_path = tmp_path / ".env"
    env_path.write_text("OPENROUTER_API_KEY=sk-or-from-dotenv\n", encoding="utf-8")

    monkeypatch.setattr(main, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(main, "DOTENV_PATH", env_path)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    main.get_llm_client(
        {
            "llm": {
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_env": "OPENROUTER_API_KEY",
            }
        }
    )

    assert captured["api_key"] == "sk-or-from-dotenv"


def test_build_extension_configs_sources_override_extension_defaults(monkeypatch):
    monkeypatch.setattr(
        main,
        "load_extension_config",
        lambda name: {"enabled": False, "max_sector_overview": 8} if name == "us_stocks" else {},
    )

    configs = main._build_extension_configs(
        {
            "llm": {
                "scoring_model": "score-model",
                "summarization_model": "summary-model",
            },
            "language": "en",
            "us_stocks": {
                "enabled": True,
                "max_sector_overview": 3,
            },
        }
    )

    assert configs["us_stocks"]["enabled"] is True
    assert configs["us_stocks"]["max_sector_overview"] == 3
