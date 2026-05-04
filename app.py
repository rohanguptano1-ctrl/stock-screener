import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("🚀 AI Equity Research Platform V6.2")

# -----------------------------
# INPUT
# -----------------------------
tickers_input = st.text_input(
    "Enter tickers",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ADANIPORTS.NS"
)

tickers = [t.strip() for t in tickers_input.split(",")]
run = st.button("Run Analysis")

# -----------------------------
# DATA FETCH (SAFE CACHE)
# -----------------------------
@st.cache_data
def fetch_price_data(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="1y")

        if hist.empty:
            return None

        hist["200DMA"] = hist["Close"].rolling(200).mean()
        hist["RSI"] = RSIIndicator(hist["Close"], 14).rsi()

        return hist

    except:
        return None

# -----------------------------
# NEWS (NO CACHE)
# -----------------------------
def fetch_news(ticker):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news

        if not news:
            return []

        return news[:3]

    except:
        return []

# -----------------------------
# SENTIMENT
# -----------------------------
def get_sentiment(title):

    title = title.lower()

    if any(x in title for x in ["profit", "growth", "strong", "upgrade", "beat"]):
        return "Positive"
    elif any(x in title for x in ["loss", "fall", "weak", "downgrade", "miss"]):
        return "Negative"
    else:
        return "Neutral"

# -----------------------------
# ANALYSIS
# -----------------------------
def analyze_stock(hist):

    price = hist["Close"].dropna().iloc[-1]
    dma = hist["200DMA"].dropna().iloc[-1]
    rsi = hist["RSI"].dropna().iloc[-1]

    momentum = price / hist["Close"].iloc[-60] - 1

    score = 0

    if price > dma:
        score += 30

    if momentum > 0.20:
        score += 40
    elif momentum > 0.10:
        score += 25
    elif momentum > 0:
        score += 10

    if 55 <= rsi <= 75:
        score += 20
    elif rsi > 75:
        score += 10

    if score >= 70:
        rec = "BUY"
    elif score >= 50:
        rec = "HOLD"
    else:
        rec = "AVOID"

    return score, rec, price, rsi, momentum, dma

# -----------------------------
# THESIS
# -----------------------------
def generate_thesis(rec, price, dma, rsi, momentum):

    thesis = []

    thesis.append("Above 200 DMA (uptrend)" if price > dma else "Below 200 DMA (weak trend)")

    if momentum > 0.15:
        thesis.append("Strong momentum")
    elif momentum > 0:
        thesis.append("Moderate momentum")
    else:
        thesis.append("Negative momentum")

    if rsi > 70:
        thesis.append("Overbought (risk of pullback)")
    elif rsi > 50:
        thesis.append("Healthy RSI zone")
    else:
        thesis.append("Weak RSI")

    if rec == "BUY":
        thesis.append("Bullish setup")
    elif rec == "HOLD":
        thesis.append("Mixed signals")
    else:
        thesis.append("Avoid for now")

    return " | ".join(thesis)

# -----------------------------
# MAIN
# -----------------------------
if run:

    results = []

    for ticker in tickers:

        hist = fetch_price_data(ticker)

        if hist is None:
            continue

        score, rec, price, rsi, momentum, dma = analyze_stock(hist)

        thesis = generate_thesis(rec, price, dma, rsi, momentum)

        news_items = fetch_news(ticker)

        sentiments = []

        for n in news_items:
            title = n.get("title", "")
            sentiments.append(get_sentiment(title))

        results.append({
            "Ticker": ticker,
            "Price": round(price, 2),
            "Score": score,
            "Recommendation": rec,
            "RSI": round(rsi, 2),
            "Momentum %": round(momentum*100, 2),
            "Thesis": thesis,
            "News Sentiment": ", ".join(sentiments)
        })

    df = pd.DataFrame(results).sort_values(by="Score", ascending=False)

    st.subheader("🎯 Stock Recommendations")
    st.dataframe(df, use_container_width=True)

    # -----------------------------
    # NEWS DETAILS
    # -----------------------------
    st.subheader("📰 News Breakdown")

    for ticker in tickers:

        st.markdown(f"### {ticker}")

        news_items = fetch_news(ticker)

        if not news_items:
            st.write("No recent news")
            continue

        for n in news_items:
            title = n.get("title", "No title available")
            sentiment = get_sentiment(title)
            st.write(f"- {title} ({sentiment})")
