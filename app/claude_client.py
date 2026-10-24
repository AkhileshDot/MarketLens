from collections.abc import Iterator
from typing import Any

import anthropic
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings

MessageContent = str | list[dict[str, Any]]

SYSTEM_PROMPT = """You are MarketLens, a research assistant for NSE-listed stocks.

Explain trends, ratios and recent events using only the data provided. Never give \
investment advice: no buy/sell/hold calls, no price targets, no recommendations of any \
kind. If asked for a recommendation, explain that you provide analysis only.

Always include a one-line disclaimer at the end: "This is not investment advice."
"""

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0, max_retries=0)


def _is_retryable(exc: BaseException) -> bool:
    """Retry only on rate limits (429), overload (529), and connection errors."""
    if isinstance(exc, anthropic.APIStatusError):
        return exc.status_code in (429, 529)
    return isinstance(exc, anthropic.APIConnectionError)


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    reraise=True,
)
def create_message(user_content: MessageContent) -> anthropic.types.Message:
    return _client.messages.create(
        model=settings.model_id,
        max_tokens=settings.max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )


@retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    reraise=True,
)
def create_turn(
    messages: list[dict],
    tools: list[dict] | None = None,
    tool_choice: dict | None = None,
) -> anthropic.types.Message:
    """Like create_message, but takes the full conversation history and an optional
    tool list — what a multi-turn tool-use loop needs that a single-shot call doesn't."""
    kwargs = {}
    if tools is not None:
        kwargs["tools"] = tools
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice

    return _client.messages.create(
        model=settings.model_id,
        max_tokens=settings.max_tokens,
        system=SYSTEM_PROMPT,
        messages=messages,
        **kwargs,
    )


def extract_text(message: anthropic.types.Message) -> str:
    """Current-gen models run adaptive thinking by default, so content[0] may be a
    ThinkingBlock, not a TextBlock — concatenate every text block instead of indexing."""
    return "".join(block.text for block in message.content if block.type == "text")


def stream_message(user_content: MessageContent) -> Iterator[str]:
    """Yield response text chunks as they arrive. No retry wrapper here —
    a stream can fail mid-flight after already sending partial output to the
    client, so a transparent restart would risk duplicating visible text."""
    with _client.messages.stream(
        model=settings.model_id,
        max_tokens=settings.max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        yield from stream.text_stream
