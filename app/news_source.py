"""News search via public RSS. UNTRUSTED INPUT — headlines come from the open web
and are not reviewed before reaching the model. Week 5 adds prompt-injection defenses;
until then, treat every result's title/source as attacker-controllable text."""

import feedparser

from app.data_source import to_yf_symbol

_FEED_URL = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"


def search_news(ticker: str, max_results: int = 5) -> list[dict]:
    """Recent headlines for an NSE ticker, newest first."""
    symbol = to_yf_symbol(ticker).removesuffix(".NS")
    query = f"{symbol}+NSE".replace(" ", "+")
    feed = feedparser.parse(_FEED_URL.format(query=query))

    return [
        {
            "title": entry.title,
            "link": entry.link,
            "published": entry.get("published"),
            "source": entry.source.title if hasattr(entry, "source") else None,
        }
        for entry in feed.entries[:max_results]
    ]
