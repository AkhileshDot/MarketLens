from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.claude_client import create_message, stream_message
from app.data_source import TickerNotFoundError, get_daily_prices
from app.logging_config import get_logger, log_event, new_request_id, timed

app = FastAPI(title="MarketLens", version="0.1.0")
logger = get_logger("marketlens")

DISCLAIMER = "This is a personal research demo, not investment advice. Not SEBI registered."


class AnalyzeRequest(BaseModel):
    ticker: str
    days: int = 90


class AnalyzeResponse(BaseModel):
    ticker: str
    note: str
    disclaimer: str = DISCLAIMER


def _build_prompt(ticker: str, days: int, request_id: str) -> str:
    """Fetch prices and build the analysis prompt. Raises HTTPException(404) for an
    unknown ticker — shared by every endpoint that needs a priced note."""
    try:
        prices = get_daily_prices(ticker, days=days)
    except TickerNotFoundError as e:
        log_event(logger, event="analyze_error", request_id=request_id, ticker=ticker, error=str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e

    csv_snippet = prices.tail(days).to_csv()
    return (
        f"Here are the last {days} days of daily OHLCV data for {ticker}, as CSV:\n\n"
        f"{csv_snippet}\n\n"
        "Write a short, plain-language note explaining the recent price trend. "
        "Do not recommend buying, selling or holding, and do not give a price target."
    )


def _stop_reason_warning(stop_reason: str | None) -> str | None:
    """Translate a Messages API stop_reason into a user-facing caveat, if any."""
    if stop_reason == "max_tokens":
        return "Response was cut off at the token limit; this note may be incomplete."
    if stop_reason == "tool_use":
        # Not expected here (no tools defined yet) — surfaced for when Week 2 adds tools.
        return "Model attempted a tool call, which this endpoint does not support yet."
    if stop_reason in ("end_turn", "stop_sequence"):
        return None
    return f"Unexpected stop_reason: {stop_reason!r}"


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    request_id = new_request_id()
    prompt = _build_prompt(req.ticker, req.days, request_id)

    with timed() as t:
        message = create_message(prompt)

    note = message.content[0].text
    warning = _stop_reason_warning(message.stop_reason)
    if warning:
        note += f"\n\n[Note: {warning}]"

    log_event(
        logger,
        event="analyze",
        request_id=request_id,
        ticker=req.ticker,
        model=message.model,
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
        stop_reason=message.stop_reason,
        **t,
    )

    return AnalyzeResponse(ticker=req.ticker, note=note)


@app.get("/chat")
def chat(ticker: str, days: int = 90):
    request_id = new_request_id()
    prompt = _build_prompt(ticker, days, request_id)

    def event_stream():
        log_event(logger, event="chat_start", request_id=request_id, ticker=ticker)
        with timed() as t:
            for chunk in stream_message(prompt):
                yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
        log_event(logger, event="chat_end", request_id=request_id, ticker=ticker, **t)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok"}
