from unittest.mock import MagicMock, patch

import anthropic
import httpx2 as httpx
import pytest

from app.claude_client import create_message


def _status_error(status_code: int) -> anthropic.APIStatusError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code=status_code, request=request)
    return anthropic.APIStatusError(f"status {status_code}", response=response, body=None)


@patch("app.claude_client._client")
def test_retries_on_429_then_succeeds(mock_client):
    success = MagicMock(stop_reason="end_turn")
    mock_client.messages.create.side_effect = [_status_error(429), success]

    result = create_message("hello")

    assert result is success
    assert mock_client.messages.create.call_count == 2


@patch("app.claude_client._client")
def test_retries_on_529_overloaded(mock_client):
    success = MagicMock(stop_reason="end_turn")
    mock_client.messages.create.side_effect = [_status_error(529), success]

    result = create_message("hello")

    assert result is success
    assert mock_client.messages.create.call_count == 2


@patch("app.claude_client._client")
def test_does_not_retry_bad_request(mock_client):
    mock_client.messages.create.side_effect = _status_error(400)

    with pytest.raises(anthropic.APIStatusError):
        create_message("hello")

    assert mock_client.messages.create.call_count == 1
