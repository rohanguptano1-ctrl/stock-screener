import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("🚀 AI Equity Research Platform V6 (Decision Engine)")

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
# DATA FETCH
# -----------------------------
@st.cache_data
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if hist.empty:
            return None

        hist["200DMA"] = hist["Close"].rolling(200).mean()
        hist["RSI"] = RSIIndicator(hist["Close"], 14).rsi()

        return hist, stock
    except:
        return None, None

# -----------------------------
# SCORING + RECOMMENDATION
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

    # Recommendation
    if score >= 70:
        rec = "BUY"
    elif score >= 50:
        rec = "HOLD"
    else:
        rec = "AVOID"

    return score, rec, price, rsi, momentum, dma

# -----------------------------
# THESIS GENERATOR
# -----------------------------
def generate_thesis(rec, price, dma, rsi, momentum):

    thesis = []

    if price > dma:
        thesis.append("Strong uptrend (above 200 DMA)")
    else:
        thesis.append("Below long-term trend")

    if momentum > 0.15:
        thesis.append("High price momentum")
    elif momentum > 0:
        thesis.append("Moderate momentum")
    else:
        thesis.append("Weak/negative momentum")

    if rsi > 70:
        thesis.append("Overbought zone (risk of pullback)")
    elif rsi > 50:
        thesis.append("Healthy momentum zone")
    else:
        thesis.append("Weak momentum")

    if rec == "BUY":
        thesis.append("Trend + momentum aligned → bullish setup")
    elif rec == "HOLD":
        thesis.append("Mixed signals → wait for confirmation")
    else:
        thesis.append("Weak setup → avoid")

    return " | ".join(thesis)

# -----------------------------
# NEWS SENTIMENT
# -----------------------------
def get_news_sentiment(stock):

    try:
        news = stock.news[:3]

        sentiments = []

        for item in news:
            title = item["title"].lower()

            if any(word in title for word in ["growth", "profit", "upgrade", "strong"]):
                sentiments.append("Positive")
            elif any(word in title for word in ["fall", "loss", "downgrade", "weak"]):
                sentiments.append("Negative")
            else:
                sentiments.append("Neutral")

        return sentiments, news

    except:
        return [], []

# -----------------------------
# MAIN
# -----------------------------
if run:

    results = []

    for ticker in tickers:

        hist, stock = fetch_data(ticker)

        if hist is None:
            continue

        score, rec, price, rsi, momentum, dma = analyze_stock(hist)

        thesis = generate_thesis(rec, price, dma, rsi, momentum)

        sentiments, news = get_news_sentiment(stock)

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
    # Detailed View
    # -----------------------------
    st.subheader("📰 News + Thesis Details")

    for ticker in tickers:

        hist, stock = fetch_data(ticker)

        if hist is None:
            continue

        st.markdown(f"### {ticker}")

        sentiments, news = get_news_sentiment(stock)

        for i, item in enumerate(news[:3]):
            st.write(f"- {item['title']} ({sentiments[i]})")
