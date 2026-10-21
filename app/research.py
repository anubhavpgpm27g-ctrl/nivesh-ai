import os
import yfinance as yf

def answer_research_question(question: str, symbol: str = ""):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        try:  # Streamlit Community Cloud stores keys in st.secrets
            import streamlit as st
            api_key = str(st.secrets.get("OPENAI_API_KEY", "")).strip()
        except Exception:
            api_key = ""
    if not api_key:
        return None, "AI research is not configured: OPENAI_API_KEY is missing. No AI answer was generated."
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        context = "No live company facts were verified in this request. Do not invent current prices, financial results, news, or citations."
        if symbol:
            ticker = symbol.strip().upper()
            if "." not in ticker and not ticker.startswith("^"):
                ticker += ".NS"
            try:
                info = yf.Ticker(ticker).info
                safe_keys = ["longName", "sector", "industry", "longBusinessSummary", "marketCap", "trailingPE", "forwardPE", "profitMargins", "debtToEquity"]
                selected = {k: info.get(k) for k in safe_keys if info.get(k) is not None}
                context = f"Provider metadata for {ticker} (may be missing, stale, or unofficial; verify independently): {selected}"
            except Exception:
                context = f"Company symbol: {ticker}. Provider metadata unavailable; do not invent current facts."
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            instructions=(
                "You are an educational financial research assistant for Indian-market users. "
                "Do not promise returns or present guesses as facts. Clearly distinguish provided data, general explanation, "
                "and facts that need verification. Do not provide personalized financial advice. "
                "Mention uncertainty and relevant downside risks. If sources are not available, say so. "
                "Never claim to have searched live news or official filings unless source material is actually provided."
            ),
            input=f"Context: {context}\nUser question: {question}\nAnswer in concise sections: Summary, Key drivers, Risks, What to verify. Be explicit about missing data."
        )
        return response.output_text, "AI-generated educational research. Company metadata, if present, is provider-supplied and should be verified against official filings."
    except Exception as exc:
        return None, f"AI provider request failed: {exc}. Check API key, model access, network and account billing."
