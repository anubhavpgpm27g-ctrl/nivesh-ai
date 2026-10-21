"""Background Yahoo Finance price stream.

One WebSocket connection per server process (shared by every visitor) receives each new trade
price as Yahoo publishes it. The page then refreshes every few seconds by reading this in-memory
store, so fast refreshes cost no extra requests to Yahoo and avoid rate limits.
"""
import threading
import time

import streamlit as st
import yfinance as yf


def _get(msg, *keys):
    for k in keys:
        if k in msg and msg[k] not in (None, ""):
            return msg[k]
    return None


def _f(v):
    try:
        v = float(v)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


class LiveFeed:
    def __init__(self):
        self.prices = {}            # symbol -> latest tick dict
        self.symbols = set()
        self.lock = threading.Lock()
        self.ws = None
        self.connected = False
        self.last_error = None
        self.last_message_at = None
        self._thread = threading.Thread(target=self._run, name="yahoo-live-feed", daemon=True)
        self._thread.start()

    # ---- public ----
    def ensure(self, symbols):
        """Subscribe to any symbols not yet on the stream."""
        new = {s for s in symbols if s} - self.symbols
        if not new:
            return
        with self.lock:
            self.symbols |= new
        ws = self.ws
        if ws is not None and self.connected:
            try:
                ws.subscribe(sorted(new))
            except Exception as exc:  # the reconnect loop will resubscribe everything
                self.last_error = f"subscribe failed: {exc}"

    def tick(self, symbol):
        with self.lock:
            t = self.prices.get(symbol)
            return dict(t) if t else None

    def status(self):
        age = time.time() - self.last_message_at if self.last_message_at else None
        return {"connected": self.connected, "symbols": len(self.symbols), "last_message_age": age, "error": self.last_error}

    # ---- internals ----
    def _handle(self, msg):
        sym = _get(msg, "id")
        price = _f(_get(msg, "price"))
        if not sym or not price:
            return
        ts = _f(_get(msg, "time"))
        if ts and ts > 1e11:  # milliseconds
            ts /= 1000.0
        tick = {
            "price": price,
            "time": ts or time.time(),
            "received": time.time(),
            "change": _f(_get(msg, "change")),
            "change_pct": _f(_get(msg, "changePercent", "change_percent")),
            "day_high": _f(_get(msg, "dayHigh", "day_high")),
            "day_low": _f(_get(msg, "dayLow", "day_low")),
            "prev_close": _f(_get(msg, "previousClose", "previous_close")),
            "open": _f(_get(msg, "openPrice", "open_price")),
            "volume": _f(_get(msg, "dayVolume", "day_volume")),
        }
        with self.lock:
            old = self.prices.get(sym, {})
            # keep earlier non-empty fields when a tick omits them
            self.prices[sym] = {**old, **{k: v for k, v in tick.items() if v is not None}}
        self.last_message_at = time.time()

    def _run(self):
        backoff = 2
        while True:
            if not self.symbols:
                time.sleep(1)
                continue
            try:
                self.ws = yf.WebSocket(verbose=False)
                with self.lock:
                    subs = sorted(self.symbols)
                self.ws.subscribe(subs)
                self.connected = True
                self.last_error = None
                backoff = 2
                self.ws.listen(self._handle)  # blocks until the connection drops
            except Exception as exc:
                self.last_error = str(exc)[:200]
            finally:
                self.connected = False
                try:
                    if self.ws is not None:
                        self.ws.close()
                except Exception:
                    pass
                self.ws = None
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


@st.cache_resource(show_spinner=False)
def get_feed() -> LiveFeed:
    return LiveFeed()
