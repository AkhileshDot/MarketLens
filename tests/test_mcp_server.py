import asyncio
from unittest.mock import patch

import pytest

from app.data_source import TickerNotFoundError
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp_server.server import server


def _run(coro):
    return asyncio.run(coro)


def test_four_tools_registered():
    tools = _run(server.list_tools())
    assert {t.name for t in tools} == {"get_quote", "get_ohlc", "get_financials", "search_news"}


def test_annual_report_resource_template_registered():
    templates = _run(server.list_resource_templates())
    assert [t.uri_template for t in templates] == ["annual-report://{ticker}"]


@patch("mcp_server.server.get_quote")
def test_get_quote_success(mock_get_quote):
    mock_get_quote.return_value = {"ticker": "NSE:INFY", "last_price": 1153.8}

    result = _run(server.call_tool("get_quote", {"ticker": "NSE:INFY"}))

    assert result.is_error is False
    assert "1153.8" in result.content[0].text


@patch("mcp_server.server.get_quote")
def test_get_quote_unknown_ticker_raises_tool_error(mock_get_quote):
    mock_get_quote.side_effect = TickerNotFoundError("No quote data for 'NSE:FAKE'")

    with pytest.raises(ToolError):
        _run(server.call_tool("get_quote", {"ticker": "NSE:FAKE"}))


@patch("mcp_server.server.get_daily_prices")
def test_get_ohlc_returns_csv(mock_get_prices):
    import pandas as pd

    mock_get_prices.return_value = pd.DataFrame({"Close": [100, 101]})

    result = _run(server.call_tool("get_ohlc", {"ticker": "NSE:INFY", "days": 2}))

    assert result.is_error is False
    assert "Close" in result.content[0].text


@patch("mcp_server.server.search_news")
def test_search_news_passes_max_results(mock_search_news):
    mock_search_news.return_value = [{"title": "headline"}]

    result = _run(server.call_tool("search_news", {"ticker": "NSE:INFY", "max_results": 3}))

    assert result.is_error is False
    mock_search_news.assert_called_once_with("NSE:INFY", max_results=3)


def test_get_annual_report_success():
    content = _run(server.read_resource("annual-report://INFY"))
    assert "INFOSYS" in content[0].content


def test_get_annual_report_unknown_ticker_raises():
    with pytest.raises(ResourceNotFoundError):
        _run(server.read_resource("annual-report://NOTAREALCOMPANY"))
