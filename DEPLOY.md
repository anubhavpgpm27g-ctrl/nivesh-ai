# Put Nivesh AI online (free, ~10 minutes)

The app shows live NSE prices from Yahoo Finance, refreshed automatically while the market is open.
It must run on a real server to reach Yahoo, so host it on Streamlit Community Cloud (free).

## 1. Put the code on GitHub
1. Sign in at https://github.com (create a free account if needed).
2. Click **+ → New repository**, name it `nivesh-ai`, choose **Public**, click **Create repository**.
3. On the new repo page click **uploading an existing file**.
4. Unzip `nivesh_ai_live.zip` on your computer and drag **everything inside the `nivesh_ai_live` folder**
   (app.py, requirements.txt, the `app` folder, etc.) into the upload box. Click **Commit changes**.
   `app.py` must sit at the top level of the repo, not inside another folder.

## 2. Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click **Create app → Deploy a public app from GitHub**.
3. Repository: `your-username/nivesh-ai` · Branch: `main` · Main file path: `app.py`.
4. Optional: under **Advanced settings**, choose Python 3.12.
5. Click **Deploy**. The first build takes 2–5 minutes. You get a link like `https://nivesh-ai.streamlit.app`.

## 3. (Optional) Turn on AI Research
In your app on share.streamlit.io: **⋮ → Settings → Secrets**, paste:
```
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4.1-mini"
```
Save. Never upload a `.env` file with your key to GitHub.

## Good to know
- Yahoo's NSE prices are near real-time at best and can lag the exchange by several minutes. For a
  certified tick-by-tick feed you need a broker or licensed data API (e.g. Upstox, Angel One SmartAPI,
  Zerodha Kite Connect).
- Prices come from Yahoo's live stream (one shared connection), with polling as a fallback. The screen refreshes every 3 s by default
  during NSE hours (9:15–15:30 IST, Mon–Fri). Use the sidebar to change the speed
  or pause it.
- If you see "Too Many Requests" errors, Yahoo is rate-limiting the server. Raise the refresh interval
  to 60–120 s and wait a few minutes.
- Free apps go to sleep after a few days without visitors; opening the link wakes them up.

## Run it on your own computer instead
```
pip install -r requirements.txt
streamlit run app.py
```
