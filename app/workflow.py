"""The 'workflow' half of Week 3's comparison: deterministic prompt chaining.
We decide the steps and always fetch the same four data sources — no autonomy,
no tool_use loop. Compare against agents/single_agent.py (Claude Agent SDK),
which decides for itself what to fetch.
"""

from app.claude_client import create_message, extract_text
from app.data_source import get_daily_prices, get_financials, get_quote
from app.news_source import search_news


def _fetch(ticker: str, days: int) -> dict:
    """Step 1: fetch. Always all four sources, in a fixed order — no model
    involved yet, so this step can't go wrong in a surprising way."""
    quote = get_quote(ticker)
    prices_df = get_daily_prices(ticker, days=days)
    financials = get_financials(ticker)
    news = search_news(ticker, max_results=5)
    return {
        "quote": quote,
        "ohlc_csv": prices_df.tail(days).to_csv(),
        "financials": financials,
        "news": news,
    }


def _analyze(ticker: str, data: dict) -> str:
    """Step 2: analyze. One Claude call, no tools — just reasoning over the
    data we already fetched. Produces working notes, not the final note."""
    prompt = (
        f"Analyze this data for {ticker}. Note the price trend, what the ratios "
        f"indicate, and anything notable in the news. Write working notes, not "
        f"a final polished note — bullet points are fine.\n\n"
        f"QUOTE:\n{data['quote']}\n\n"
        f"OHLC (CSV):\n{data['ohlc_csv']}\n\n"
        f"FINANCIALS:\n{data['financials']}\n\n"
        f"NEWS:\n{data['news']}"
    )
    message = create_message(prompt)
    return extract_text(message)


def _write(ticker: str, analysis: str) -> str:
    """Step 3: write. A second Claude call turns the working notes into the
    final, polished note — separating 'figure out what's going on' from
    'write it up well' into two focused calls instead of asking for both at once."""
    prompt = (
        f"Turn these working notes about {ticker} into a polished research note: "
        f"a short trend summary, key ratios with one line of interpretation each, "
        f"relevant news, and sources. No buy/sell/hold language, no price targets. "
        f"End with: \"This is not investment advice.\"\n\n{analysis}"
    )
    message = create_message(prompt)
    return extract_text(message)


def run_workflow(ticker: str, days: int = 90) -> str:
    """fetch -> analyze -> write. Three deterministic steps, two Claude calls.
    Raises TickerNotFoundError for an unknown ticker, same as every other
    entry point in this project — the caller handles it the same way."""
    data = _fetch(ticker, days)
    analysis = _analyze(ticker, data)
    return _write(ticker, analysis)
