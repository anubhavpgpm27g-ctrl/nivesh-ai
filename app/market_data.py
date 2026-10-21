"""Market data helpers: live quotes, intraday bars and daily history from Yahoo Finance (via yfinance).

Yahoo Finance is an unofficial source. NSE prices there are near real-time at best and can be
delayed by several minutes, rate-limited or missing. Results are cached briefly so that
auto-refresh does not hammer the provider.
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yfinance as yf

IST = ZoneInfo("Asia/Kolkata")

NAMES = {
    "^NSEI": "NIFTY 50", "^NSEBANK": "NIFTY BANK", "^BSESN": "SENSEX", "^CNXIT": "NIFTY IT",
    "RELIANCE": "Reliance Industries", "TCS": "Tata Consultancy Services", "INFY": "Infosys",
    "HDFCBANK": "HDFC Bank", "ICICIBANK": "ICICI Bank", "SBIN": "State Bank of India", "ITC": "ITC",
    "BHARTIARTL": "Bharti Airtel", "LT": "Larsen & Toubro", "HINDUNILVR": "Hindustan Unilever",
    "KOTAKBANK": "Kotak Mahindra Bank", "AXISBANK": "Axis Bank", "MARUTI": "Maruti Suzuki",
    "SUNPHARMA": "Sun Pharmaceutical", "WIPRO": "Wipro", "ASIANPAINT": "Asian Paints",
    "BAJFINANCE": "Bajaj Finance", "TITAN": "Titan Company",
}


def indian_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not symbol:
        return symbol
    if symbol.startswith("^") or "." in symbol or "=" in symbol:
        return symbol
    return f"{symbol}.NS"


def display_name(symbol: str) -> str:
    return NAMES.get(symbol.strip().upper(), symbol.strip().upper())


def market_status(now: datetime | None = None) -> dict:
    """NSE regular session 09:15-15:30 IST, Mon-Fri. Exchange holidays are not checked."""
    now = now or datetime.now(IST)
    weekday = now.weekday() < 5
    t = now.time()
    if weekday and time(9, 15) <= t < time(15, 30):
        state, label = "open", "NSE open"
    elif weekday and time(9, 0) <= t < time(9, 15):
        state, label = "pre", "NSE pre-open"
    else:
        state, label = "closed", "NSE closed"
    return {"state": state, "label": label, "time": now.strftime("%H:%M:%S IST"), "is_open": state == "open"}


def _clean(data: pd.DataFrame) -> pd.DataFrame:
    data = data.rename_axis("Timestamp")
    data = data[~data.index.duplicated(keep="last")].sort_index()
    if getattr(data.index, "tz", None) is not None:
        data.index = data.index.tz_convert(IST)
    return data


@st.cache_data(ttl=300, show_spinner=False)
def fetch_history(symbol: str, period="1y", interval="1d"):
    ticker = indian_symbol(symbol)
    try:
        data = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        if data is None or data.empty:
            return None, f"No data returned for {ticker}. Check the symbol, interval, provider availability and network."
        return _clean(data), None
    except Exception as exc:  # provider errors, rate limits, network
        return None, f"Provider request failed: {exc}"


@st.cache_data(ttl=30, show_spinner=False)
def fetch_intraday(symbol: str):
    """1-minute bars for the latest session (falls back to 5-minute bars of the last trading day)."""
    ticker = indian_symbol(symbol)
    try:
        t = yf.Ticker(ticker)
        data = t.history(period="1d", interval="1m", auto_adjust=False)
        if data is None or data.empty:
            data = t.history(period="5d", interval="5m", auto_adjust=False)
            if data is None or data.empty:
                return None, f"No intraday data returned for {ticker}."
            data = _clean(data)
            last_day = data.index[-1].date()
            return data[data.index.date == last_day], None
        return _clean(data), None
    except Exception as exc:
        return None, f"Provider request failed: {exc}"


@st.cache_data(ttl=20, show_spinner=False)
def fetch_live_quote(symbol: str):
    """Latest traded price and day stats. Returns (quote_dict, error)."""
    ticker = indian_symbol(symbol)
    quote = {"symbol": ticker, "name": display_name(symbol), "fetched_at": datetime.now(IST)}
    try:
        fi = yf.Ticker(ticker).fast_info
        last = _num(fi, "last_price")
        prev = _num(fi, "previous_close") or _num(fi, "regular_market_previous_close")
        quote.update(last=last, prev_close=prev, day_high=_num(fi, "day_high"), day_low=_num(fi, "day_low"),
                     open=_num(fi, "open"), year_high=_num(fi, "year_high"), year_low=_num(fi, "year_low"))
    except Exception:
        last = prev = None
    # Fall back to (or confirm with) the latest intraday bar, which also gives a timestamp.
    bars, err = fetch_intraday(symbol)
    if bars is not None and not bars.empty:
        close = bars["Close"].dropna()
        if not close.empty:
            quote["bar_time"] = close.index[-1]
            if not last:
                quote["last"] = float(close.iloc[-1])
                quote["day_high"] = quote.get("day_high") or float(bars["High"].max())
                quote["day_low"] = quote.get("day_low") or float(bars["Low"].min())
    if not quote.get("prev_close"):
        daily, _ = fetch_history(symbol, period="5d", interval="1d")
        if daily is not None and len(daily) >= 2:
            quote["prev_close"] = float(daily["Close"].dropna().iloc[-2])
    if not quote.get("last"):
        return None, err or f"No live price returned for {ticker}."
    p = quote.get("prev_close")
    quote["change"] = quote["last"] - p if p else None
    quote["change_pct"] = (quote["last"] / p - 1) * 100 if p else None
    return quote, None


def _num(obj, key):
    try:
        v = obj[key]
    except Exception:
        v = getattr(obj, key, None)
    try:
        v = float(v)
        return v if v == v and v > 0 else None  # drop NaN / non-positive
    except (TypeError, ValueError):
        return None


def fetch_quote_summary(symbol: str):
    """Kept for compatibility with the original module."""
    q, err = fetch_live_quote(symbol)
    if not q:
        return None, err
    return {"symbol": q["symbol"], "close": q["last"], "change_pct": q.get("change_pct") or 0,
            "timestamp": str(q.get("bar_time", q["fetched_at"]))}, None


def inr(v, decimals=2):
    """Indian digit grouping: 12,34,567.89"""
    if v is None or v != v:
        return "—"
    neg = v < 0
    s = f"{abs(v):.{decimals}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return ("-" if neg else "") + whole + ("." + frac if frac else "")


def lakh_crore(v):
    if v is None or v != v:
        return "—"
    a, sign = abs(v), "-" if v < 0 else ""
    if a >= 1e7:
        return f"{sign}₹{inr(a / 1e7)} Cr"
    if a >= 1e5:
        return f"{sign}₹{inr(a / 1e5)} L"
    return f"{sign}₹{inr(a, 0)}"
