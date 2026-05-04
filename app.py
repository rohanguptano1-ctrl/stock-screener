import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from textblob import TextBlob

st.set_page_config(layout="wide")
st.title("🧠 AI Equity Research Platform V4 (Backtesting Enabled)")

# -----------------------------
# INPUT
# -----------------------------
tickers_input = st.text_input(
    "Enter tickers",
    "SUZLON.NS,IRCON.NS,NBCC.NS,HFCL.NS,IDFCFIRSTB.NS"
)

backtest_years = st.slider("Backtest Period (years)", 1, 5, 1)

tickers = [t.strip() for t in tickers_input.split(",")]
run = st.button("Run Analysis + Backtest")

# -----------------------------
# DATA FETCH
# -----------------------------
@st.cache_data
def fetch_data(ticker, period="1y"):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        if hist.empty:
            return None

        hist["200DMA"] = hist["Close"].rolling(200).mean()
        hist["RSI"] = RSIIndicator(hist["Close"], 14).rsi()

        return hist

    except:
        return None


# -----------------------------
# SCORING LOGIC (same as V3.4)
# -----------------------------
def compute_score(hist):
    price = hist["Close"].iloc[-1]
    rsi = hist["RSI"].iloc[-1]
    dma = hist["200DMA"].iloc[-1]

    momentum = price / hist["Close"].iloc[-60] - 1 if len(hist) > 60 else 0

    score = 5  # base

    # Trend
    if price > dma:
        score += 20

    # RSI
    if 55 <= rsi <= 75:
        score += 20
    elif 45 <= rsi < 55:
        score += 10
    elif rsi > 75:
        score += 5

    # Momentum
    if momentum > 0.15:
        score += 20
    elif momentum > 0:
        score += 10

    return score, rsi, momentum


def recommendation(score):
    if score >= 70:
        return "BUY"
    elif score >= 50:
        return "HOLD"
    else:
        return "AVOID"


# -----------------------------
# MAIN SCREEN
# -----------------------------
if run:

    results = {}
    full_data = {}

    for ticker in tickers:
        hist = fetch_data(ticker, "1y")

        if hist is None:
            continue

        score, rsi, momentum = compute_score(hist)

        results[ticker] = {
            "Price": round(hist["Close"].iloc[-1], 2),
            "Score": score,
            "RSI": round(rsi, 2),
            "Momentum %": round(momentum * 100, 2),
            "Recommendation": recommendation(score)
        }

        full_data[ticker] = hist

    df = pd.DataFrame(results).T
    df["Rank"] = df["Score"].rank(pct=True)

    st.subheader("📊 Screener Output")
    st.dataframe(df)

    # -----------------------------
    # BACKTEST
    # -----------------------------
    st.subheader("📈 Backtest Results")

    portfolio_returns = []

    for ticker in tickers:
        hist = fetch_data(ticker, f"{backtest_years}y")

        if hist is None:
            continue

        hist["Return"] = hist["Close"].pct_change()
        portfolio_returns.append(hist["Return"])

    if portfolio_returns:
        combined = pd.concat(portfolio_returns, axis=1)
        combined.columns = tickers[:len(combined.columns)]

        combined["Portfolio"] = combined.mean(axis=1)

        combined["Cumulative"] = (1 + combined["Portfolio"]).cumprod()

        # Benchmark (Nifty ETF proxy)
        nifty = yf.Ticker("^NSEI").history(period=f"{backtest_years}y")
        nifty["Return"] = nifty["Close"].pct_change()
        nifty["Cumulative"] = (1 + nifty["Return"]).cumprod()

        st.line_chart(pd.DataFrame({
            "Strategy": combined["Cumulative"],
            "Nifty": nifty["Cumulative"]
        }))

        # Metrics
        total_return = combined["Cumulative"].iloc[-1] - 1
        nifty_return = nifty["Cumulative"].iloc[-1] - 1

        st.metric("Strategy Return", f"{round(total_return*100,2)}%")
        st.metric("Nifty Return", f"{round(nifty_return*100,2)}%")

    else:
        st.warning("Backtest failed (data issue)")
