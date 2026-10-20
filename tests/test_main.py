from unittest.mock import MagicMock, patch

import pandas as pd
from fastapi.testclient import TestClient

from app.data_source import TickerNotFoundError
from app.main import _stop_reason_warning, app

client = TestClient(app)


def _fake_prices() -> pd.DataFrame:
    return pd.DataFrame(
        {"Open": [100, 101], "High": [102, 103], "Low": [99, 100], "Close": [101, 102], "Volume": [1000, 1100]},
        index=pd.to_datetime(["2026-10-18", "2026-10-19"]),
    )


def _fake_message(text: str = "Prices moved sideways.", stop_reason: str = "end_turn"):
    message = MagicMock()
    message.content = [MagicMock(text=text)]
    message.stop_reason = stop_reason
    message.model = "claude-sonnet-5"
    message.usage.input_tokens = 100
    message.usage.output_tokens = 50
    return message


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.main.get_daily_prices")
def test_analyze_unknown_ticker_returns_404(mock_get_prices):
    mock_get_prices.side_effect = TickerNotFoundError("No price data for 'NSE:FAKE'")

    response = client.post("/analyze", json={"ticker": "NSE:FAKE", "days": 10})

    assert response.status_code == 404
    assert "FAKE" in response.json()["detail"]


@patch("app.main.create_message")
@patch("app.main.get_daily_prices")
def test_analyze_success(mock_get_prices, mock_create_message):
    mock_get_prices.return_value = _fake_prices()
    mock_create_message.return_value = _fake_message()

    response = client.post("/analyze", json={"ticker": "NSE:INFY", "days": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "NSE:INFY"
    assert body["note"] == "Prices moved sideways."
    assert "not investment advice" in body["disclaimer"].lower()


@patch("app.main.create_message")
@patch("app.main.get_daily_prices")
def test_analyze_appends_warning_on_max_tokens(mock_get_prices, mock_create_message):
    mock_get_prices.return_value = _fake_prices()
    mock_create_message.return_value = _fake_message(stop_reason="max_tokens")

    response = client.post("/analyze", json={"ticker": "NSE:INFY", "days": 2})

    assert response.status_code == 200
    assert "cut off" in response.json()["note"].lower()


def test_stop_reason_warning_end_turn_is_none():
    assert _stop_reason_warning("end_turn") is None


def test_stop_reason_warning_stop_sequence_is_none():
    assert _stop_reason_warning("stop_sequence") is None


def test_stop_reason_warning_max_tokens():
    assert "cut off" in _stop_reason_warning("max_tokens").lower()


def test_stop_reason_warning_tool_use():
    assert "tool call" in _stop_reason_warning("tool_use").lower()


def test_stop_reason_warning_unexpected_value():
    assert "unexpected" in _stop_reason_warning("pause_turn").lower()


@patch("app.main.stream_message")
@patch("app.main.get_daily_prices")
def test_chat_streams_sse_frames_ending_in_done(mock_get_prices, mock_stream_message):
    mock_get_prices.return_value = _fake_prices()
    mock_stream_message.return_value = iter(["Hello ", "world."])

    response = client.get("/chat", params={"ticker": "NSE:INFY", "days": 2})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text == "data: Hello \n\ndata: world.\n\ndata: [DONE]\n\n"


@patch("app.main.get_daily_prices")
def test_chat_unknown_ticker_returns_404(mock_get_prices):
    mock_get_prices.side_effect = TickerNotFoundError("No price data for 'NSE:FAKE'")

    response = client.get("/chat", params={"ticker": "NSE:FAKE", "days": 10})

    assert response.status_code == 404
