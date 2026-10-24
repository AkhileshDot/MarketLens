"""Read-only market data access. No order-placement capability exists anywhere
in this module or the project — see CLAUDE.md ground rules."""

import pandas as pd
import yfinance as yf


class TickerNotFoundError(Exception):
    pass


def to_yf_symbol(ticker: str) -> str:
    """'NSE:INFY' or 'INFY' -> 'INFY.NS'"""
    symbol = ticker.split(":")[-1].strip().upper()
    if not symbol.endswith(".NS"):
        symbol += ".NS"
    return symbol


def get_daily_prices(ticker: str, days: int = 90) -> pd.DataFrame:
    """Last `days` of daily OHLCV for an NSE ticker."""
    symbol = to_yf_symbol(ticker)
    df = yf.Ticker(symbol).history(period=f"{days}d", interval="1d")
    if df.empty:
        raise TickerNotFoundError(f"No price data for {ticker!r} (resolved to {symbol!r})")
    return df


def get_quote(ticker: str) -> dict:
    """Latest price snapshot: last price, previous close, day high/low, volume."""
    symbol = to_yf_symbol(ticker)
    info = yf.Ticker(symbol).fast_info

    try:
        last_price = info.get("lastPrice")
    except Exception:
        # fast_info lazily fetches on access and can raise deep inside yfinance
        # for an invalid ticker, rather than returning None like a plain dict would.
        # Broad catch is deliberate: this is a boundary to a flaky external library
        # whose failure modes (KeyError, HTTPError, ...) aren't worth enumerating.
        last_price = None

    if last_price is None:
        raise TickerNotFoundError(f"No quote data for {ticker!r} (resolved to {symbol!r})")

    return {
        "ticker": ticker,
        "last_price": last_price,
        "previous_close": info.get("previousClose"),
        "day_high": info.get("dayHigh"),
        "day_low": info.get("dayLow"),
        "volume": info.get("lastVolume"),
        "currency": info.get("currency"),
    }


def get_financials(ticker: str) -> dict:
    """Key ratios: P/E, ROE, debt-to-equity. None where yfinance has no data."""
    symbol = to_yf_symbol(ticker)
    info = yf.Ticker(symbol).info

    if not info or info.get("regularMarketPrice") is None:
        raise TickerNotFoundError(f"No financial data for {ticker!r} (resolved to {symbol!r})")

    return {
        "ticker": ticker,
        "pe_ratio": info.get("trailingPE"),
        "roe": info.get("returnOnEquity"),
        "debt_to_equity": info.get("debtToEquity"),
        "market_cap": info.get("marketCap"),
    }
