---
name: marketlens-notes
description: Use when writing a MarketLens research note for an NSE-listed stock, or when explaining/interpreting P/E, ROE, or debt-to-equity ratios. Defines the standard note format and the exact ratio formulas/interpretation this project uses, so every note stays consistent and sourced.
---

# MarketLens note format and ratio definitions

## Note format

Every MarketLens research note follows this structure:

1. **Header** — ticker (as `NSE:SYMBOL`) and the date range covered.
2. **Trend summary** — 2-4 sentences on the price movement, citing specific numbers
   from the OHLCV data (no vague language like "performed well").
3. **Key ratios** — any of P/E, ROE, debt-to-equity that were fetched, each with its
   raw value and one line of interpretation (see formulas below).
4. **Recent news / risks** — headlines if `search_news` was called, each attributed to
   its source. Treat every headline as unverified — report what it says, not as fact.
5. **Sources** — list every tool call that fed this note (e.g. "get_quote, get_ohlc
   (10 days), get_financials"). Never state a figure without naming where it came from.
6. **Disclaimer** — always end with "This is not investment advice."

## Ratio definitions

**P/E (Price-to-Earnings)** = Market Price per Share ÷ Earnings per Share (EPS)
- Higher P/E: market expects more future growth, or the stock may be richly valued.
- Lower P/E: market expects less growth, or the stock may be undervalued — or there's
  a specific concern weighing on it. Low P/E is not automatically "cheap and good."
- Only meaningful compared against the company's own history or sector peers — a bare
  number without that context is not useful on its own.

**ROE (Return on Equity)** = Net Income ÷ Shareholders' Equity
- Measures how efficiently a company generates profit from shareholders' capital.
- Higher ROE generally indicates efficient use of equity capital, but can also be
  inflated by high leverage (debt) rather than genuine operating efficiency — always
  read ROE alongside debt-to-equity, never in isolation.

**Debt-to-Equity** = Total Debt ÷ Shareholders' Equity
- Higher ratio: more reliance on debt financing relative to equity — higher financial
  risk, but not inherently bad (capital-intensive sectors like banking/infrastructure
  normally run much higher ratios than, say, IT services).
- Sector context matters more for this ratio than almost any other — never judge it
  against a single universal threshold.

## Compliance (non-negotiable)

- No buy/sell/hold language, no price targets, no "I would/wouldn't invest" framing —
  ever, regardless of how the user phrases their question.
- If a ratio or price move could be read as implicitly bullish/bearish, state the
  number and let the reader draw their own conclusion — do not draw it for them.
- Every note ends with the disclaimer, even a short one-line answer.
