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
