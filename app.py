import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from textblob import TextBlob

st.set_page_config(layout="wide")
st.title("🧠 AI Equity Research Platform V3.3")

# INPUT
tickers_input = st.text_input(
    "Enter tickers (comma separated)",
    "SUZLON.NS,IRCON.NS,NBCC.NS,HFCL.NS,IDFCFIRSTB.NS"
)

tickers = [t.strip() for t in tickers_input.split(",")]
run = st.button("Run Analysis")

# DATA FETCH
@st.cache_data(show_spinner=False)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if hist.empty:
            return None

        valid_close = hist["Close"].dropna()
        if valid_close.empty:
            return None

        price = float(valid_close.iloc[-1])

        hist["200DMA"] = hist["Close"].rolling(200).mean()
        hist["RSI"] = RSIIndicator(hist["Close"], 14).rsi()

        rsi = hist["RSI"].dropna().iloc[-1]
        dma = hist["200DMA"].dropna().iloc[-1]

        # 3-month momentum
        momentum = price / hist["Close"].iloc[-60] - 1 if len(hist) > 60 else 0

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
            "rsi": rsi,
            "above_200dma": price > dma,
            "momentum": momentum,
            "roe": info.get("returnOnEquity", None),
            "debt": info.get("debtToEquity", None),
            "profit": info.get("netIncomeToCommon", None),
            "news": news if news else [],
            "hist": hist
        }

    except:
        return None


# FUNDAMENTALS (LIGHT WEIGHT)
def fundamental_score(d):
    score = 5  # base score (IMPORTANT FIX)

    if d["profit"] is not None and d["profit"] > 0:
        score += 10

    if d["roe"] is not None and d["roe"] > 0.12:
        score += 5

    if d["debt"] is not None and d["debt"] < 1:
        score += 5

    return score  # max ~25


# TECHNICALS (PRIMARY DRIVER)
def technical_score(d):
    score = 0

    if d["above_200dma"]:
        score += 20

    if d["rsi"] is not None:
        if 45 <= d["rsi"] <= 65:
            score += 15
        elif d["rsi"] > 70:
            score -= 5

    # momentum boost
    if d["momentum"] > 0.10:
        score += 15
    elif d["momentum"] > 0:
        score += 5

    return score  # max ~50


# SENTIMENT
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


# TOTAL
def total_score(d):
    return (
        fundamental_score(d)
        + technical_score(d)
        + sentiment_score(d["news"])
    )


def recommendation(score):
    if score >= 65:
        return "BUY"
    elif score >= 45:
        return "HOLD"
    else:
        return "AVOID"


# MAIN
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
            "POSITIVE" if sentiment_val == 10 else
            "NEGATIVE" if sentiment_val == 0 else
            "NEUTRAL"
        )

        results.append({
            "Ticker": ticker,
            "Price": d["price"],
            "Score": score,
            "Recommendation": rec,
            "RSI": round(d["rsi"], 2),
            "Momentum": round(d["momentum"] * 100, 2),
            "Sentiment": sentiment_label
        })

        data_store[ticker] = d

    df = pd.DataFrame(results)

    if df.empty:
        st.warning("No valid data found")
        st.stop()

    df["Rank"] = df["Score"].rank(pct=True)

    df["Conviction"] = df["Rank"].apply(
        lambda x: "HIGH" if x > 0.8 else "MEDIUM" if x > 0.5 else "LOW"
    )

    st.subheader("📊 Screener Output")
    st.dataframe(df, use_container_width=True)

    st.subheader("📈 Top Picks Portfolio")

    top = df.sort_values("Score", ascending=False).head(5)
    top["Weight"] = top["Score"] / top["Score"].sum()

    st.dataframe(top, use_container_width=True)

    for ticker in top["Ticker"]:
        d = data_store[ticker]

        st.subheader(f"{ticker} Chart")

        chart_df = d["hist"][["Close", "200DMA"]].dropna()
        st.line_chart(chart_df)
