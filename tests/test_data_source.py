from unittest.mock import MagicMock, patch

import pytest

from app.data_source import TickerNotFoundError, get_financials, get_quote, to_yf_symbol


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("NSE:INFY", "INFY.NS"),
        ("INFY", "INFY.NS"),
        ("nse:tcs", "TCS.NS"),
        ("TCS.NS", "TCS.NS"),
    ],
)
def test_to_yf_symbol(raw, expected):
    assert to_yf_symbol(raw) == expected


@patch("app.data_source.yf.Ticker")
def test_get_quote_success(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.fast_info = {
        "lastPrice": 1153.8,
        "previousClose": 1153.3,
        "dayHigh": 1197.8,
        "dayLow": 1038.0,
        "lastVolume": 33044499,
        "currency": "INR",
    }
    mock_ticker_cls.return_value = mock_ticker

    quote = get_quote("NSE:INFY")

    assert quote["ticker"] == "NSE:INFY"
    assert quote["last_price"] == 1153.8
    assert quote["currency"] == "INR"


@patch("app.data_source.yf.Ticker")
def test_get_quote_unknown_ticker_raises(mock_ticker_cls):
    mock_ticker = MagicMock()
    fast_info = MagicMock()
    fast_info.get.side_effect = KeyError("currentTradingPeriod")
    mock_ticker.fast_info = fast_info
    mock_ticker_cls.return_value = mock_ticker

    with pytest.raises(TickerNotFoundError):
        get_quote("NSE:FAKE")


@patch("app.data_source.yf.Ticker")
def test_get_financials_success(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "regularMarketPrice": 1153.8,
        "trailingPE": 15.36,
        "returnOnEquity": 0.2995,
        "debtToEquity": 8.567,
        "marketCap": 4673324449792,
    }
    mock_ticker_cls.return_value = mock_ticker

    fin = get_financials("NSE:INFY")

    assert fin["pe_ratio"] == 15.36
    assert fin["roe"] == 0.2995


@patch("app.data_source.yf.Ticker")
def test_get_financials_unknown_ticker_raises(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.info = {}
    mock_ticker_cls.return_value = mock_ticker

    with pytest.raises(TickerNotFoundError):
        get_financials("NSE:FAKE")
