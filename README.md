# Nivesh AI — Indian Investing Intelligence (Prototype)

**To put this app online with live prices, see [DEPLOY.md](DEPLOY.md).**

A beginner-friendly Streamlit web app for exploring Indian stocks, watchlists, a manual portfolio tracker, experimental historical ML estimates, and an optional AI research assistant.

## Important limitations

- Market prices are fetched through `yfinance` (Yahoo Finance), with live quotes and auto-refresh during NSE hours. It is **not a licensed real-time NSE feed**: quotes can lag the exchange by several minutes, and data may be incomplete, unavailable or rate-limited.
- The model is an experimental logistic-regression classifier trained on daily historical bars. It estimates whether the next daily close may be higher; it does not generate a reliable price target or prove a profitable strategy.
- AI research requires an OpenAI API key and may incur charges. Without a key, AI answers remain disabled.
- There is no broker connection, account sync, order placement, or automatic trading.
- Watchlist and portfolio state are session-only in this prototype. No production user authentication or cloud persistence is implemented.

## 1. Install Python

Install Python 3.11 or 3.12 from https://www.python.org/downloads/ . On Windows, enable **Add Python to PATH** during setup.

## 2. Open a terminal in this project folder

Windows PowerShell:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, use Command Prompt:
```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Streamlit should open a local browser page, usually at http://localhost:8501 .

## 3. Enable AI research (optional)

1. Copy `.env.example` to `.env`.
2. Add your own API key after `OPENAI_API_KEY=`.
3. Save the file and restart Streamlit.

Do not paste API keys into chat or commit `.env` to Git. API use may cost money. If the provider/model is unavailable to your account, check your API account and model access.

## 4. Use the app

- **Overview:** index snapshots and a stock chart.
- **Markets & Stocks:** retrieve history and download CSV.
- **AI Research:** ask an educational research question; it only responds when the API is configured.
- **Watchlist:** add and remove symbols.
- **Portfolio:** enter quantities and average costs; values are indicative.
- **About & Risk:** limitations and risk disclosures.

For Indian equities, enter NSE symbols without the suffix, e.g. `RELIANCE`, `INFY`, `SBIN`. The app appends `.NS`. Indices use supported symbols such as `^NSEI`.

## 5. Data and forecast caveats

- The Overview page reports the latest candle returned by the provider, not necessarily a live price.
- The prediction model uses daily candles and an 80/20 chronological split. The reported test metrics are a small historical holdout and can be unstable; they are not evidence of future profitability.
- Historical market data can contain missing values, corporate-action effects and other issues.
- Before evaluating a strategy, add walk-forward validation, realistic execution assumptions, fees, taxes, spread, slippage, liquidity filters, and a strict out-of-sample period.
- Never use this prototype as the sole basis for a financial decision.

## Production roadmap

Before public launch:
1. Replace unofficial data with a licensed provider/API whose terms allow the intended display and redistribution.
2. Add backend services, database migrations, secure authentication, per-user data isolation, rate limits, audit logging and monitoring.
3. Build a robust ML pipeline with versioned datasets, walk-forward testing, probability calibration and model-drift checks.
4. Add verified source retrieval for financial research, with source links and timestamps.
5. Obtain legal/compliance review for applicable Indian securities, investment-advice, data, privacy, cybersecurity and trading requirements.
6. Add broker integration only after permissions, operational controls, and regulatory requirements have been reviewed.
