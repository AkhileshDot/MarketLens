import json
from unittest.mock import patch

from app.data_source import TickerNotFoundError
from app.tools import dispatch


@patch("app.tools.get_quote")
def test_get_quote_success(mock_get_quote):
    mock_get_quote.return_value = {"ticker": "NSE:INFY", "last_price": 1153.8}

    content, is_error = dispatch("get_quote", {"ticker": "NSE:INFY"})

    assert is_error is False
    assert json.loads(content)["last_price"] == 1153.8


@patch("app.tools.get_quote")
def test_get_quote_unknown_ticker_is_error(mock_get_quote):
    mock_get_quote.side_effect = TickerNotFoundError("No quote data for 'NSE:FAKE'")

    content, is_error = dispatch("get_quote", {"ticker": "NSE:FAKE"})

    assert is_error is True
    assert "No quote data" in content


def test_get_quote_missing_ticker_is_error():
    content, is_error = dispatch("get_quote", {})

    assert is_error is True
    assert "ticker" in content


def test_get_ohlc_missing_days_is_error():
    content, is_error = dispatch("get_ohlc", {"ticker": "NSE:INFY"})

    assert is_error is True
    assert "days" in content


@patch("app.tools.get_daily_prices")
def test_get_ohlc_success_returns_csv(mock_get_prices):
    import pandas as pd

    mock_get_prices.return_value = pd.DataFrame({"Close": [100, 101]})

    content, is_error = dispatch("get_ohlc", {"ticker": "NSE:INFY", "days": 2})

    assert is_error is False
    assert "Close" in content


@patch("app.tools.get_financials")
def test_get_financials_success(mock_get_financials):
    mock_get_financials.return_value = {"ticker": "NSE:INFY", "pe_ratio": 15.4}

    content, is_error = dispatch("get_financials", {"ticker": "NSE:INFY"})

    assert is_error is False
    assert json.loads(content)["pe_ratio"] == 15.4


@patch("app.tools.search_news")
def test_search_news_success_uses_default_max_results(mock_search_news):
    mock_search_news.return_value = [{"title": "Infosys news"}]

    content, is_error = dispatch("search_news", {"ticker": "NSE:INFY"})

    assert is_error is False
    mock_search_news.assert_called_once_with("NSE:INFY", max_results=5)


def test_unknown_tool_is_error():
    content, is_error = dispatch("place_order", {"ticker": "NSE:INFY"})

    assert is_error is True
    assert "Unknown tool" in content
