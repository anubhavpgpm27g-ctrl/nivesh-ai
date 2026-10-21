from datetime import datetime, timezone

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from app.market_data import (IST, display_name, fetch_history, fetch_intraday, fetch_live_quote,
                             indian_symbol, inr, lakh_crore, market_status)
from app.prediction import make_prediction
from app.research import answer_research_question

load_dotenv()
st.set_page_config(page_title="Nivesh AI | Investing Intelligence", page_icon="📈", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.3rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {background: rgba(120,120,120,.08); padding: 14px; border-radius: 12px;}
.live-dot {display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:middle;}
</style>
""", unsafe_allow_html=True)

if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame([
        {"Symbol": "RELIANCE", "Quantity": 0, "Avg Buy Price (₹)": 0.0},
        {"Symbol": "TCS", "Quantity": 0, "Avg Buy Price (₹)": 0.0},
    ])

# ---------------- Sidebar ----------------
st.sidebar.title("📈 Nivesh AI")
st.sidebar.caption("AI investing intelligence · India")
page = st.sidebar.radio("Navigate", ["Overview", "Markets & Stocks", "AI Research", "Watchlist", "Portfolio", "About & Risk"])
st.sidebar.divider()
status = market_status()
dot = {"open": "#16a34a", "pre": "#d97706", "closed": "#9ca3af"}[status["state"]]
st.sidebar.markdown(f"<span class='live-dot' style='background:{dot}'></span>**{status['label']}** · {status['time']}", unsafe_allow_html=True)
auto = st.sidebar.toggle("Auto-refresh live prices", value=True, help="Refreshes quotes while NSE is open. Turn off to save data/API calls.")
every = st.sidebar.select_slider("Refresh every", options=[15, 30, 60, 120], value=30, format_func=lambda s: f"{s} s")
if st.sidebar.button("Refresh now"):
    st.cache_data.clear()
    st.rerun()
RUN_EVERY = f"{every}s" if (auto and status["state"] in ("open", "pre")) else None
st.sidebar.caption("Market data: Yahoo Finance via yfinance. Near real-time at best; NSE quotes can be delayed by several minutes. Verify with your broker.")

st.title("Nivesh AI")
st.caption("A beginner-friendly investing research workspace for Indian markets.")
if not status["is_open"]:
    st.info(f"{status['label']} ({status['time']}). Prices below are from the last session. The regular session runs 9:15–15:30 IST, Monday to Friday (holidays not checked).")


# ---------------- Helpers ----------------
def price_chart(df: pd.DataFrame, height=260, time_fmt="%d %b %y"):
    data = df[["Close"]].dropna().reset_index()
    data.columns = ["Time", "Close"]
    data["Time"] = data["Time"].dt.tz_localize(None) if getattr(data["Time"].dt, "tz", None) is not None else data["Time"]
    up = data["Close"].iloc[-1] >= data["Close"].iloc[0]
    color = "#16a34a" if up else "#dc2626"
    lo, hi = float(data["Close"].min()), float(data["Close"].max())
    pad = (hi - lo) * 0.08 or hi * 0.01
    data["Base"] = lo - pad
    base = alt.Chart(data).encode(
        x=alt.X("Time:T", title=None, axis=alt.Axis(format=time_fmt, labelOverlap=True)),
        y=alt.Y("Close:Q", title="₹", scale=alt.Scale(domain=[lo - pad, hi + pad], zero=False, nice=False)),
        tooltip=[alt.Tooltip("Time:T", format="%d %b %Y %H:%M"), alt.Tooltip("Close:Q", format=",.2f")],
    )
    area = base.mark_area(opacity=0.12, color=color).encode(y2="Base:Q")
    line = base.mark_line(color=color, strokeWidth=1.8)
    st.altair_chart((area + line).properties(height=height), use_container_width=True)


def quote_metric(label, symbol, prefix="₹"):
    q, err = fetch_live_quote(symbol)
    if not q:
        st.metric(label, "Unavailable", "Check data source", delta_color="off")
        return None
    delta = f"{q['change']:+,.2f} ({q['change_pct']:+.2f}%)" if q.get("change_pct") is not None else None
    st.metric(label, f"{prefix}{inr(q['last'])}", delta)
    return q


def as_of(q):
    t = q.get("bar_time") or q["fetched_at"]
    try:
        return pd.Timestamp(t).tz_convert(IST).strftime("%d %b %Y, %H:%M IST")
    except Exception:
        return str(t)


# ---------------- Pages ----------------
if page == "Overview":
    st.subheader("Market overview")

    @st.fragment(run_every=RUN_EVERY)
    def live_tiles():
        cols = st.columns(5)
        for col, (sym, label, pre) in zip(cols, [("^NSEI", "NIFTY 50", ""), ("^BSESN", "SENSEX", ""), ("^NSEBANK", "NIFTY BANK", ""),
                                                  ("RELIANCE", "RELIANCE", "₹"), ("TCS", "TCS", "₹")]):
            with col:
                quote_metric(label, sym, pre)
        st.caption(f"Last refreshed {datetime.now(IST).strftime('%H:%M:%S IST')}"
                   + (f" · auto-refresh every {every} s" if RUN_EVERY else " · auto-refresh paused (market closed or turned off)"))
    live_tiles()

    st.divider()
    left, right = st.columns([1.3, 1])
    with left:
        st.subheader("Explore a stock")
        symbol = st.text_input("NSE symbol (e.g., RELIANCE, INFY, SBIN)", "RELIANCE").strip().upper()
        view = st.radio("Chart", ["Today (intraday)", "1 year"], horizontal=True)

        @st.fragment(run_every=RUN_EVERY)
        def live_stock():
            if not symbol:
                return
            q = quote_metric(f"{symbol} · {display_name(symbol)} · live", symbol)
            if q:
                st.caption(f"Price as of {as_of(q)} · Day range ₹{inr(q.get('day_low'))} – ₹{inr(q.get('day_high'))}")
            if view.startswith("Today"):
                bars, err = fetch_intraday(symbol)
                if bars is not None and not bars.empty:
                    price_chart(bars, 260, "%H:%M")
                else:
                    st.warning(err)
            else:
                hist, err = fetch_history(symbol, "1y", "1d")
                if hist is not None and not hist.empty:
                    price_chart(hist, 260)
                else:
                    st.warning(err)
        live_stock()
    with right:
        st.subheader("Your watchlist")

        @st.fragment(run_every=RUN_EVERY)
        def mini_watch():
            for sym in st.session_state.watchlist:
                q, _ = fetch_live_quote(sym)
                a, b = st.columns([2, 1.4])
                a.markdown(f"**{sym}**  \n<span style='color:#7b8492;font-size:.85rem'>{display_name(sym)}</span>", unsafe_allow_html=True)
                if q:
                    chg = q.get("change_pct")
                    color = "#16a34a" if (chg or 0) >= 0 else "#dc2626"
                    b.markdown(f"₹{inr(q['last'])}  \n<span style='color:{color};font-size:.85rem'>{chg:+.2f}%</span>" if chg is not None else f"₹{inr(q['last'])}", unsafe_allow_html=True)
                else:
                    b.write("—")
        mini_watch()
        st.info("Open **Watchlist** to add/remove symbols, or **AI Research** to ask a research question.")

elif page == "Markets & Stocks":
    st.subheader("Markets & stock explorer")
    c1, c2, c3 = st.columns([2, 1, 1])
    symbol = c1.text_input("Enter an Indian stock symbol", "INFY").strip().upper()
    period = c2.selectbox("Historical range", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"], index=5)
    interval_options = {"1d": ["1m", "5m", "15m"], "5d": ["5m", "15m", "1h"], "1mo": ["1h", "1d"]}.get(period, ["1d", "1wk"])
    interval = c3.selectbox("Candle interval", interval_options, index=0)

    if symbol:
        @st.fragment(run_every=RUN_EVERY)
        def live_header():
            q = quote_metric(f"{symbol} · {display_name(symbol)} · live price", symbol)
            if q:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Day high", f"₹{inr(q.get('day_high'))}")
                m2.metric("Day low", f"₹{inr(q.get('day_low'))}")
                m3.metric("52-week high", f"₹{inr(q.get('year_high'))}")
                m4.metric("52-week low", f"₹{inr(q.get('year_low'))}")
                st.caption(f"Price as of {as_of(q)} · Yahoo Finance, may be delayed")
        live_header()

        hist, err = fetch_history(symbol, period=period, interval=interval)
        if hist is None or hist.empty:
            st.error(f"Data unavailable: {err}")
        else:
            price_chart(hist, 320, "%H:%M" if period in ("1d", "5d") else "%d %b %y")

            st.subheader("Experimental AI prediction")
            st.caption("This model uses daily candles to estimate whether the next daily close may be higher. It is not a live trading signal and does not prove profitability.")
            daily, daily_error = fetch_history(symbol, period="5y", interval="1d")
            if daily is not None and not daily.empty:
                prediction = make_prediction(daily)
                if prediction.get("ok"):
                    pc1, pc2, pc3 = st.columns(3)
                    pc1.metric("Estimated probability: up", f"{prediction['probability_up']:.1%}")
                    pc2.metric("Estimated probability: down", f"{prediction['probability_down']:.1%}")
                    pc3.metric("Holdout balanced accuracy", f"{prediction['test_balanced_accuracy']:.1%}")
                    if prediction["test_balanced_accuracy"] < 0.55:
                        st.warning(f"On days it hadn't seen, the model scored {prediction['test_balanced_accuracy']:.1%}, about the same as a coin flip (50%). Treat this estimate as noise, not a signal.")
                    st.caption(f"Model data as of {prediction['as_of']} · {prediction['test_samples']} chronological holdout observations. {prediction['message']}")
                else:
                    st.info(prediction.get("message", "Prediction unavailable."))
            else:
                st.info(f"Prediction unavailable because daily history could not be loaded: {daily_error}")

            st.subheader("Recent candles")
            st.dataframe(hist.tail(20).sort_index(ascending=False), use_container_width=True)
            st.download_button("Download displayed data as CSV", hist.to_csv().encode("utf-8"), f"{symbol}_history.csv", "text/csv")
    st.caption("For Indian cash equities, symbols are automatically mapped to .NS unless already qualified (use .BO for BSE).")

elif page == "AI Research":
    st.subheader("AI research assistant")
    st.write("Ask about a company, its risks, business model, or what to investigate before investing.")
    st.caption("The assistant uses a configured OpenAI API key. Without it, AI responses are disabled rather than fabricated.")
    question = st.text_area("Your research question", placeholder="Explain the key risks and business drivers for RELIANCE. Separate facts from items that need verification.")
    symbol = st.text_input("Company / NSE symbol (optional)", "RELIANCE").strip().upper()
    if st.button("Run AI research", type="primary"):
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            with st.spinner("Preparing research..."):
                answer, source_note = answer_research_question(question, symbol)
            if answer:
                st.markdown(answer)
                st.caption(source_note)
            else:
                st.error(source_note)
                st.info("Add OPENAI_API_KEY to your .env file (or Streamlit Cloud secrets) and restart the app. API usage may incur charges.")
    st.warning("AI-generated content can be wrong or outdated. Verify financial facts using company filings and official exchange disclosures. This is not personalized investment advice.")

elif page == "Watchlist":
    st.subheader("Watchlist")
    with st.form("add_symbol"):
        new_symbol = st.text_input("Add NSE symbol", placeholder="e.g., SBIN").strip().upper()
        submitted = st.form_submit_button("Add to watchlist")
        if submitted:
            if new_symbol and new_symbol not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_symbol)
                st.success(f"Added {new_symbol}")
            elif new_symbol:
                st.info("Symbol is already in the watchlist.")

    @st.fragment(run_every=RUN_EVERY)
    def live_watchlist():
        if not st.session_state.watchlist:
            st.info("Your watchlist is empty.")
            return
        rows = []
        for sym in st.session_state.watchlist:
            q, _ = fetch_live_quote(sym)
            rows.append({"Symbol": sym, "Name": display_name(sym),
                         "Live price (₹)": round(q["last"], 2) if q else None,
                         "Change (₹)": round(q["change"], 2) if q and q.get("change") is not None else None,
                         "Change (%)": round(q["change_pct"], 2) if q and q.get("change_pct") is not None else None,
                         "Day low (₹)": q.get("day_low") if q else None, "Day high (₹)": q.get("day_high") if q else None,
                         "As of": as_of(q) if q else "—"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                     column_config={"Change (%)": st.column_config.NumberColumn(format="%+.2f%%"),
                                    "Day low (₹)": st.column_config.NumberColumn(format="%.2f"),
                                    "Day high (₹)": st.column_config.NumberColumn(format="%.2f")})
        st.caption(f"Last refreshed {datetime.now(IST).strftime('%H:%M:%S IST')}")
    live_watchlist()

    remove = st.selectbox("Remove a symbol", [""] + st.session_state.watchlist)
    if st.button("Remove selected") and remove:
        st.session_state.watchlist.remove(remove)
        st.rerun()

elif page == "Portfolio":
    st.subheader("Portfolio tracker")
    st.caption("Manual portfolio tracker only. Values are stored in this app session and are not synced to a broker or saved account.")
    edited = st.data_editor(
        st.session_state.portfolio,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Symbol": st.column_config.TextColumn("NSE symbol"),
            "Quantity": st.column_config.NumberColumn("Quantity", min_value=0, step=1),
            "Avg Buy Price (₹)": st.column_config.NumberColumn("Average buy price (₹)", min_value=0.0, format="%.2f"),
        },
        key="portfolio_editor",
    )
    st.session_state.portfolio = edited

    @st.fragment(run_every=RUN_EVERY)
    def live_portfolio():
        results = []
        for _, row in edited.iterrows():
            sym = str(row.get("Symbol", "")).strip().upper()
            if not sym or sym == "NAN":
                continue
            qty = float(row.get("Quantity", 0) or 0)
            avg = float(row.get("Avg Buy Price (₹)", 0) or 0)
            q, _ = fetch_live_quote(sym)
            current = q["last"] if q else np.nan
            invested = qty * avg
            value = qty * current if pd.notna(current) else np.nan
            results.append({"Symbol": sym, "Quantity": qty, "Avg cost (₹)": avg, "Live price (₹)": current,
                            "Invested (₹)": invested, "Current value (₹)": value,
                            "Unrealised P/L (₹)": value - invested if pd.notna(value) else np.nan})
        df = pd.DataFrame(results)
        if df.empty or df["Quantity"].sum() == 0:
            st.info("Enter quantities and average prices above to see live values.")
            return
        inv, val = df["Invested (₹)"].sum(), df["Current value (₹)"].sum(skipna=True)
        a, b, c = st.columns(3)
        a.metric("Invested", lakh_crore(inv))
        b.metric("Current value", lakh_crore(val))
        c.metric("Unrealised P/L", lakh_crore(val - inv), f"{(val / inv - 1) * 100:+.2f}%" if inv else None)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={k: st.column_config.NumberColumn(format="%.2f") for k in df.columns if "₹" in k})
        st.caption(f"Live values as of {datetime.now(IST).strftime('%H:%M:%S IST')}. Indicative only; excludes brokerage, STT, GST, stamp duty, taxes and corporate actions.")
    live_portfolio()
    st.download_button("Download portfolio rows", edited.to_csv(index=False).encode("utf-8"), "portfolio.csv", "text/csv")

elif page == "About & Risk":
    st.subheader("About this prototype")
    st.markdown("""
**Included now**
- Live (near real-time) quotes for NSE stocks and indices through Yahoo Finance's unofficial data interface, with auto-refresh while the market is open.
- Intraday (1-minute) and historical price charts with CSV export.
- Session-only watchlist and manual portfolio tracker valued at live prices.
- Optional AI research assistant when an OpenAI API key is configured.
- Experimental historical ML prediction card (see limitations below).

**Not included**
- Broker login or account synchronization.
- Order placement, auto-trading, or guaranteed profitable forecasts.
- A licensed, exchange-certified real-time NSE feed. Yahoo quotes can lag the exchange by several minutes.
- Persisted user accounts or cloud portfolio storage.
""")
    st.subheader("Risk disclosures")
    st.markdown("""
1. This is an educational software prototype, not a SEBI-registered investment adviser or broker.
2. Market data may be delayed, incomplete, unavailable, or inaccurate. Do not use it as the sole basis for a trade.
3. AI-generated research can hallucinate, omit context, or use outdated information.
4. Any model forecast is experimental and does not guarantee future performance or profitability.
5. Historical backtests do not guarantee future results. Realistic testing must account for brokerage, taxes, spread, slippage, liquidity, corporate actions and survivorship bias.
6. Never paste broker passwords, API secrets, OTPs, or account credentials into the research chat.
7. Before offering investment advice, trading, or execution to other users in India, obtain qualified legal/compliance advice about applicable SEBI, exchange, broker, privacy and cybersecurity requirements.
""")
    st.subheader("Provider status")
    st.write(f"App runtime time (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    st.write("Data provider configured: Yahoo Finance via yfinance (unofficial; near real-time at best).")
