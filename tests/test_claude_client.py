from unittest.mock import MagicMock, patch

import anthropic
import httpx2 as httpx
import pytest

from app.claude_client import create_message, extract_text


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


def test_extract_text_skips_leading_thinking_block():
    """Current-gen models run adaptive thinking by default, so content[0] can be a
    ThinkingBlock. extract_text must look past it, not assume index 0 is text."""
    thinking_block = MagicMock(type="thinking")
    text_block = MagicMock(type="text", text="Prices moved sideways.")
    message = MagicMock(content=[thinking_block, text_block])

    assert extract_text(message) == "Prices moved sideways."


def test_extract_text_joins_multiple_text_blocks():
    blocks = [MagicMock(type="text", text="Part one. "), MagicMock(type="text", text="Part two.")]
    message = MagicMock(content=blocks)

    assert extract_text(message) == "Part one. Part two."
