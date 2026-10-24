from types import SimpleNamespace
from unittest.mock import patch

from app.news_source import search_news


def _fake_entry(title: str, source: str | None = None) -> SimpleNamespace:
    entry = SimpleNamespace(title=title, link="https://news.google.com/rss/articles/xyz")
    entry.get = lambda key, default=None: {"published": "Fri, 23 Oct 2026 10:00:00 GMT"}.get(
        key, default
    )
    if source:
        entry.source = SimpleNamespace(title=source)
    return entry


@patch("app.news_source.feedparser.parse")
def test_search_news_returns_parsed_fields(mock_parse):
    mock_parse.return_value = SimpleNamespace(
        entries=[_fake_entry("Infosys beats estimates", source="Reuters")]
    )

    results = search_news("NSE:INFY")

    assert len(results) == 1
    assert results[0]["title"] == "Infosys beats estimates"
    assert results[0]["source"] == "Reuters"


@patch("app.news_source.feedparser.parse")
def test_search_news_respects_max_results(mock_parse):
    mock_parse.return_value = SimpleNamespace(entries=[_fake_entry(f"Headline {i}") for i in range(10)])

    results = search_news("NSE:INFY", max_results=2)

    assert len(results) == 2


@patch("app.news_source.feedparser.parse")
def test_search_news_no_results_returns_empty_list(mock_parse):
    mock_parse.return_value = SimpleNamespace(entries=[])

    results = search_news("NSE:FAKE")

    assert results == []


@patch("app.news_source.feedparser.parse")
def test_search_news_missing_source_is_none(mock_parse):
    mock_parse.return_value = SimpleNamespace(entries=[_fake_entry("No-source headline")])

    results = search_news("NSE:INFY")

    assert results[0]["source"] is None
