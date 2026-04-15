from extensions.arxiv import _prepare_papers as prepare_papers_for_rendering


def test_prepare_papers_for_rendering_sorts_by_preferred_category_then_score():
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

    assert [p["title"] for p in ordered] == ["A", "B", "C"]
    assert ordered[0]["primary_category"] == "cs.CV"
    assert ordered[1]["primary_category"] == "cs.CV"
    # Single category papers should always keep their own category.
    assert ordered[2]["primary_category"] == "cs.AI"
