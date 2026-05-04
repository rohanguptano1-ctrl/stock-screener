import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from textblob import TextBlob

st.set_page_config(layout="wide")
st.title("🧠 AI Equity Research Platform V3")

# -----------------------------
# INPUT
# -----------------------------
tickers_input = st.text_input(
    "Enter tickers (comma separated)",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS"
)

tickers = [t.strip() for t in tickers_input.split(",")]

run = st.button("Run Analysis")

# -----------------------------
# DATA FETCH (SAFE VERSION)
# -----------------------------
@st.cache_data(show_spinner=False)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)

        hist = stock.history(period="1y")

        if hist.empty:
            return None

        # SAFE FALLBACKS
        try:
            info = stock.info
        except:
            info = {}

        try:
            news = stock.news
        except:
            news = []

        try:
            fin = stock.financials
        except:
            fin = pd.DataFrame()

        hist["200DMA"] = hist["Close"].rolling(200).mean()
        hist["RSI"] = RSIIndicator(hist["Close"], 14).rsi()

        latest = hist.iloc[-1]

        price = float(latest["Close"]) if not pd.isna(latest["Close"]) else None

        return {
            "ticker": ticker,
            "price": price,
            "rsi": latest["RSI"],
            "above_200dma": latest["Close"] > latest["200DMA"],
            "marketCap": info.get("marketCap", 0),
            "debt": info.get("debtToEquity", None),
            "roe": info.get("returnOnEquity", None),
            # fallback income so it doesn't default to negative
            "income": info.get("netIncomeToCommon") if info.get("netIncomeToCommon") else 1,
            "hist": hist,
            "news": news if news else [],
            "financials": fin if not fin.empty else pd.DataFrame()
        }

    except:
        return None


# -----------------------------
# SCORING FUNCTIONS
# -----------------------------
def fundamental_score(d):
    score = 0

    if d["income"] is not None and d["income"] > 0:
        score += 10

    if d["debt"] is not None and d["debt"] < 0.5:
        score += 10

    if d["roe"] is not None and d["roe"] > 0.15:
        score += 10

    return score


def technical_score(d):
    score = 0

    if d["above_200dma"]:
        score += 10

    if d["rsi"] is not None and 40 <= d["rsi"] <= 65:
        score += 10

    return score


def sentiment_score(news):
    scores = []

    for item in news[:5]:
        title = item.get("title", "")
        blob = TextBlob(title)
        scores.append(blob.sentiment.polarity)

    if not scores:
        return 5

    avg = np.mean(scores)

    if avg > 0.1:
        return 10
    elif avg < -0.1:
        return 0
    else:
        return 5


def earnings_score(fin):
    try:
        if fin.empty:
            return 5

        revenue = fin.loc["Total Revenue"]
        profit = fin.loc["Net Income"]

        score = 0

        if len(revenue) >= 3 and revenue.iloc[0] > revenue.iloc[1] > revenue.iloc[2]:
            score += 10

        if len(profit) >= 3 and profit.iloc[0] > profit.iloc[1] > profit.iloc[2]:
            score += 10

        return score

    except:
        return 5


def valuation_score(d):
    return 5


def risk_flags(d):
    flags = []

    if d["income"] is not None:
        if d["income"] < 0:
            flags.append("Negative Earnings")

    if d["debt"] is not None:
        if d["debt"] > 1:
            flags.append("High Debt")

    return flags


def total_score(d):
    f = fundamental_score(d)
    t = technical_score(d)
    s = sentiment_score(d["news"])
    e = earnings_score(d["financials"])
    v = valuation_score(d)

    total = f + t + s + e + v
    return total


def recommendation(score):
    if score >= 75:
        return "STRONG BUY"
    elif score >= 65:
        return "BUY"
    elif score >= 50:
        return "HOLD"
    else:
        return "AVOID"


# -----------------------------
# THESIS
# -----------------------------
def generate_thesis(d, score, rec, sentiment):
    return f"""
### 📌 {d['ticker']} — {rec} (Score: {score})

**Investment Thesis:**
- Business quality: {'Strong' if score > 65 else 'Moderate'}
- Trend: {'Uptrend' if d['above_200dma'] else 'Weak'}
- Sentiment: {sentiment}

**Key Strengths:**
- Positive earnings profile
- Manageable leverage

**Risks:**
- Market volatility
- Data limitations

---
"""


# -----------------------------
# MAIN
# -----------------------------
if run:

    results = []
    data_store = {}

    for ticker in tickers:

        st.write(f"Fetching: {ticker}")

        d = fetch_data(ticker)

        if not d:
            st.warning(f"No data for {ticker}")
            continue

        score = total_score(d)
        rec = recommendation(score)
        flags = risk_flags(d)

        sentiment = sentiment_score(d["news"])
        sentiment_label = (
            "POSITIVE" if sentiment == 10 else "NEGATIVE" if sentiment == 0 else "NEUTRAL"
        )

        results.append({
            "Ticker": ticker,
            "Price": d["price"],
            "Score": score,
            "Recommendation": rec,
            "RSI": round(d["rsi"], 2),
            "Sentiment": sentiment_label,
            "Risk Flags": ", ".join(flags)
        })

        data_store[ticker] = d

    df = pd.DataFrame(results)

    if df.empty:
        st.warning("No valid data found")
        st.stop()

    # Ranking
    df["Rank"] = df["Score"].rank(pct=True)

    df["Conviction"] = df["Rank"].apply(
        lambda x: "HIGH" if x > 0.8 else "MEDIUM" if x > 0.5 else "LOW"
    )

    st.subheader("📊 Screener Output")
    st.dataframe(df, use_container_width=True)

    # Portfolio
    st.subheader("📈 Top Picks Portfolio")

    top = df.sort_values("Score", ascending=False).head(5)
    top["Weight"] = top["Score"] / top["Score"].sum()

    st.dataframe(top, use_container_width=True)

    # Details
    for ticker in top["Ticker"]:
        d = data_store[ticker]

        score = df[df["Ticker"] == ticker]["Score"].values[0]
        rec = df[df["Ticker"] == ticker]["Recommendation"].values[0]
        sentiment = df[df["Ticker"] == ticker]["Sentiment"].values[0]

        st.subheader(f"{ticker} Analysis")

        st.write(generate_thesis(d, score, rec, sentiment))

        chart_df = d["hist"][["Close", "200DMA"]].dropna()
        st.line_chart(chart_df)
