from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.claude_client import MessageContent, create_message, extract_text, stream_message
from app.data_source import TickerNotFoundError, get_daily_prices
from app.file_input import UnsupportedFileTypeError, build_content_block
from app.logging_config import get_logger, log_event, new_request_id, timed

app = FastAPI(title="MarketLens", version="0.1.0")
logger = get_logger("marketlens")

# Personal demo, frontend dev server only — see CLAUDE.md ground rules (private deployment).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

DISCLAIMER = "This is a personal research demo, not investment advice. Not SEBI registered."


class AnalyzeResponse(BaseModel):
    ticker: str
    note: str
    disclaimer: str = DISCLAIMER


def _build_prompt(
    ticker: str, days: int, request_id: str, file: UploadFile | None = None
) -> MessageContent:
    """Fetch prices and build the analysis prompt, optionally alongside an uploaded
    chart screenshot or results PDF. Raises HTTPException(404) for an unknown ticker,
    HTTPException(400) for an unsupported file type."""
    try:
        prices = get_daily_prices(ticker, days=days)
    except TickerNotFoundError as e:
        log_event(logger, event="analyze_error", request_id=request_id, ticker=ticker, error=str(e))
        raise HTTPException(status_code=404, detail=str(e)) from e

    csv_snippet = prices.tail(days).to_csv()
    text = (
        f"Here are the last {days} days of daily OHLCV data for {ticker}, as CSV:\n\n"
        f"{csv_snippet}\n\n"
        "Write a short, plain-language note explaining the recent price trend. "
        "Do not recommend buying, selling or holding, and do not give a price target."
    )

    if file is None:
        return text

    try:
        block = build_content_block(file.file.read(), file.content_type or "")
    except UnsupportedFileTypeError as e:
        log_event(logger, event="analyze_error", request_id=request_id, ticker=ticker, error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e

    text += (
        "\n\nA chart screenshot or results document is attached — factor it into the "
        "note, citing what it shows alongside the price data above."
    )
    return [block, {"type": "text", "text": text}]


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
def analyze(
    ticker: str = Form(...),
    days: int = Form(90),
    file: UploadFile | None = File(None),
) -> AnalyzeResponse:
    request_id = new_request_id()
    prompt = _build_prompt(ticker, days, request_id, file)

    with timed() as t:
        message = create_message(prompt)

    note = extract_text(message)
    warning = _stop_reason_warning(message.stop_reason)
    if warning:
        note += f"\n\n[Note: {warning}]"

    log_event(
        logger,
        event="analyze",
        request_id=request_id,
        ticker=ticker,
        model=message.model,
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
        stop_reason=message.stop_reason,
        has_file=file is not None,
        **t,
    )

    return AnalyzeResponse(ticker=ticker, note=note)


@app.post("/chat")
def chat(
    ticker: str = Form(...),
    days: int = Form(90),
    file: UploadFile | None = File(None),
):
    request_id = new_request_id()
    prompt = _build_prompt(ticker, days, request_id, file)

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
