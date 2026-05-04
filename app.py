import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("🚀 AI Equity Research Platform V6.1")

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
# DATA FETCH (CACHE SAFE)
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
        return stock.news[:3]
    except:
        return []

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

    thesis.append("Above 200 DMA" if price > dma else "Below 200 DMA")

    if momentum > 0.15:
        thesis.append("Strong momentum")
    elif momentum > 0:
        thesis.append("Moderate momentum")
    else:
        thesis.append("Weak momentum")

    if rsi > 70:
        thesis.append("Overbought risk")
    elif rsi > 50:
        thesis.append("Healthy RSI")
    else:
        thesis.append("Weak RSI")

    if rec == "BUY":
        thesis.append("Bullish setup")
    elif rec == "HOLD":
        thesis.append("Wait for confirmation")
    else:
        thesis.append("Avoid for now")

    return " | ".join(thesis)

# -----------------------------
# NEWS SENTIMENT
# -----------------------------
def get_sentiment(title):

    title = title.lower()

    if any(x in title for x in ["profit", "growth", "strong", "upgrade"]):
        return "Positive"
    elif any(x in title for x in ["loss", "fall", "weak", "downgrade"]):
        return "Negative"
    else:
        return "Neutral"

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

        news = fetch_news(ticker)

        sentiments = [get_sentiment(n["title"]) for n in news]

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
    # DETAILS
    # -----------------------------
    st.subheader("📰 News + Details")

    for ticker in tickers:

        news = fetch_news(ticker)

        st.markdown(f"### {ticker}")

        for n in news:
            sentiment = get_sentiment(n["title"])
            st.write(f"- {n['title']} ({sentiment})")
