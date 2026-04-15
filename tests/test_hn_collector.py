from extensions.hacker_news.collector import filter_stories, parse_story


def test_filter_stories_by_score():
    stories = [
        {
            "points": 100,
            "title": "New AI model beats GPT-4",
            "url": "https://a.com",
            "objectID": "1",
            "created_at": "2026-04-13T01:00:00.000Z",
        },
        {
            "points": 10,
            "title": "LLM benchmark released",
            "url": "https://b.com",
            "objectID": "2",
            "created_at": "2026-04-13T02:00:00.000Z",
        },
    ]
    result = filter_stories(stories, min_score=50, keywords=["AI", "LLM"])
    assert len(result) == 1
    assert result[0]["objectID"] == "1"


def test_filter_stories_by_keyword():
    stories = [
        {
            "points": 200,
            "title": "Tax reforms proposed by government",
            "url": "https://c.com",
            "objectID": "3",
            "created_at": "2026-04-13T03:00:00.000Z",
        },
        {
            "points": 200,
            "title": "Open source LLM beats proprietary models",
            "url": "https://d.com",
            "objectID": "4",
            "created_at": "2026-04-13T04:00:00.000Z",
        },
    ]
    result = filter_stories(stories, min_score=50, keywords=["AI", "LLM", "machine learning"])
    assert len(result) == 1
    assert result[0]["objectID"] == "4"


def test_parse_story():
    raw = {
        "objectID": "43821045",
        "title": "Meta releases vision model",
        "url": "https://example.com",
        "points": 342,
        "created_at": "2026-04-13T01:00:00.000Z",
    }
    parsed = parse_story(raw)
    assert parsed["id"] == 43821045
    assert parsed["score"] == 342
    assert "comments_url" in parsed
