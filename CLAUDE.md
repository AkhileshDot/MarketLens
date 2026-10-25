# MarketLens

AI research assistant for NSE-listed stocks, built as a 6-week learning project for the
CCDV-F exam (Claude Certified Developer, Associate–Foundations). Full roadmap:
`Docs/CCDV-F Prep Roadmap Build a Production-Ready Agentic Workflow.md`.

## What this is

Give it a ticker (e.g. `NSE:INFY`), it pulls prices, financials and news, then writes a
sourced note explaining trends, ratios and recent events.

## Ground rules (apply to every feature, every week)

- **Explain, don't recommend.** No buy/sell/hold calls, no price targets. Giving those to
  other people requires SEBI registration (Investment Adviser / Research Analyst) in India.
- **Personal demo only.** Private deployment, disclaimer on every note, no public sign-ups.
- **Read-only.** No tool may place an order. There is no broker integration in this
  project — analysis only, so it isn't needed (see `notes/week0-tradeoffs.md`).
- **Licensed/public data only.** Data comes from `yfinance` (Yahoo Finance) and public
  RSS news feeds. Don't redistribute raw exchange data.

## Data source

- Prices/OHLC/fundamentals: `yfinance`, NSE tickers as `SYMBOL.NS` (e.g. `INFY.NS`).
- News: public RSS feeds (Moneycontrol / Economic Times / Business Standard), treated as
  **untrusted input** from Week 5 onward (prompt injection surface).
- No broker API (Kite Connect etc.) — rejected, see `notes/week0-tradeoffs.md`.

## Project structure

```
app/          FastAPI service (Week 1+)
frontend/     React + TypeScript UI (Vite dev server, localhost:5173)
mcp_server/   MCP server wrapping data tools (Week 2+)
agents/       Claude Agent SDK orchestrator + subagents (Week 3+)
evals/        Eval set and regression tests (Week 6)
tests/        Unit/integration tests
data/         CSV cache, sample annual reports (gitignored cache dir)
notes/        One trade-off writeup per week (the exam-prep habit)
```

## Running locally

Backend: `uv run uvicorn app.main:app --port 8000` (from repo root).
Frontend: `npm run dev` (from `frontend/`), serves on `localhost:5173`.
CORS in `app/main.py` only allows the Vite dev server origin — update it if the
frontend ever runs elsewhere.
MCP server: `uv run python -m mcp_server.server` (stdio, default) or
`uv run python -m mcp_server.server http` (Streamable HTTP, port 8001 — deliberately
not 8000, so it never collides with the FastAPI backend).

## Weekly trade-off habit

After each week's feature, add a short note to `notes/weekN-tradeoffs.md`: one alternative
rejected and why. This is deliberate exam prep — CCDV-F questions are scenario-based.

## Conventions

- Model ID, prompts, and settings live in config/env, not hardcoded in code.
- Every Anthropic API call logs: request id, ticker, model, input/output tokens, latency.
- Python package manager: `uv` (not poetry/pip directly). Run `uv sync` then
  `uv run uvicorn app.main:app --reload`.
- Tests: `uv run pytest`.

## Current status

Week 1 in progress: FastAPI `/analyze` endpoint over static price data.
