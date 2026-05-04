import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from textblob import TextBlob

st.set_page_config(layout="wide")
st.title("🧠 AI Equity Research Platform V3.1")

# -----------------------------
# INPUT
# -----------------------------
tickers_input = st.text_input(
    "Enter tickers (comma separated)",
    "SUZLON.NS,IRCON.NS,NBCC.NS,HFCL.NS,IDFCFIRSTB.NS"
)

tickers = [t.strip() for t in tickers_input.split(",")]

run = st.button("Run Analysis")

# -----------------------------
# DATA FETCH
# -----------------------------
@st.cache_data(show_spinner=False)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)

        hist = stock.history(period="1y")
        if hist.empty:
            return None

        # PRICE FIX
        valid_close = hist["Close"].dropna()
        if valid_close.empty:
            return None
        price = float(valid_close.iloc[-1])

        # TECHNICALS
        hist["200DMA"] = hist["Close"].rolling(200).mean()
        hist["RSI"] = RSIIndicator(hist["Close"], 14).rsi()
        latest_rsi = hist["RSI"].dropna().iloc[-1]

        # FUNDAMENTALS
        try:
            fin = stock.financials
        except:
            fin = pd.DataFrame()

        try:
            info = stock.info
        except:
            info = {}

        try:
            news = stock.news
        except:
            news = []

        return {
            "ticker": ticker,
            "price": price,
            "rsi": latest_rsi,
            "above_200dma": price > hist["200DMA"].iloc[-1],
            "debt": info.get("debtToEquity", None),
            "roe": info.get("returnOnEquity", None),
            "financials": fin,
            "news": news if news else [],
            "hist": hist
        }

    except:
        return None


# -----------------------------
# FUNDAMENTAL SCORE (NEW)
# -----------------------------
def fundamental_score(d):
    score = 0

    fin = d["financials"]

    try:
        if not fin.empty:
            revenue = fin.loc["Total Revenue"]
            profit = fin.loc["Net Income"]

            # Revenue growth
            if len(revenue) >= 3 and revenue.iloc[0] > revenue.iloc[1] > revenue.iloc[2]:
                score += 15

            # Profit growth
            if len(profit) >= 3 and profit.iloc[0] > profit.iloc[1] > profit.iloc[2]:
                score += 15

    except:
        pass

    # ROE
    if d["roe"] is not None and d["roe"] > 0.15:
        score += 10

    # Debt
    if d["debt"] is not None and d["debt"] < 0.5:
        score += 10

    return score  # max ~50


# -----------------------------
# TECHNICAL SCORE
# -----------------------------
def technical_score(d):
    score = 0

    if d["above_200dma"]:
        score += 10

    if d["rsi"] is not None and 40 <= d["rsi"] <= 65:
        score += 10

    return score  # max 20


# -----------------------------
# SENTIMENT
# -----------------------------
def sentiment_score(news):
    scores = []

    for item in news[:5]:
        title = item.get("title", "")
        blob = TextBlob(title)
        scores.append(blob.sentiment.polarity)

    if not scores:
        return 3  # slight neutral-negative bias

    avg = np.mean(scores)

    if avg > 0.1:
        return 10
    elif avg < -0.1:
        return 0
    else:
        return 5


# -----------------------------
# TOTAL SCORE
# -----------------------------
def total_score(d):
    f = fundamental_score(d)   # 50
    t = technical_score(d)     # 20
    s = sentiment_score(d["news"])  # 10

    total = f + t + s
    return total


def recommendation(score):
    if score >= 60:
        return "BUY"
    elif score >= 45:
        return "HOLD"
    else:
        return "AVOID"


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

        sentiment_val = sentiment_score(d["news"])
        sentiment_label = (
            "POSITIVE" if sentiment_val == 10 else "NEGATIVE" if sentiment_val == 0 else "NEUTRAL"
        )

        results.append({
            "Ticker": ticker,
            "Price": d["price"],
            "Score": score,
            "Recommendation": rec,
            "RSI": round(d["rsi"], 2),
            "Sentiment": sentiment_label
        })

        data_store[ticker] = d

    df = pd.DataFrame(results)

    if df.empty:
        st.warning("No valid data found")
        st.stop()

    df["Rank"] = df["Score"].rank(pct=True)

    st.subheader("📊 Screener Output")
    st.dataframe(df, use_container_width=True)

    # Portfolio
    st.subheader("📈 Top Picks Portfolio")

    top = df.sort_values("Score", ascending=False).head(5)
    top["Weight"] = top["Score"] / top["Score"].sum()

    st.dataframe(top, use_container_width=True)

    # Charts
    for ticker in top["Ticker"]:
        d = data_store[ticker]

        st.subheader(f"{ticker} Chart")

        chart_df = d["hist"][["Close", "200DMA"]].dropna()
        st.line_chart(chart_df)
