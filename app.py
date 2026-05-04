import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("🧠 AI Equity Research Platform V5 (Rebalancing Engine)")

# -----------------------------
# INPUT
# -----------------------------
tickers_input = st.text_input(
    "Enter tickers",
    "LT.NS,ASIANPAINT.NS,BAJFINANCE.NS,TATAMOTORS.NS,ADANIPORTS.NS,HINDUNILVR.NS,COALINDIA.NS,SBIN.NS,ULTRACEMCO.NS,PIDILITIND.NS"
)

years = st.slider("Backtest Period (Years)", 1, 5, 2)
top_n = st.slider("Number of Stocks in Portfolio", 2, 6, 3)

tickers = [t.strip() for t in tickers_input.split(",")]
run = st.button("Run Strategy")

# -----------------------------
# DATA FETCH
# -----------------------------
@st.cache_data
def fetch_full_data(ticker, period):
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
# SCORE FUNCTION
# -----------------------------
def compute_score_row(hist, i):

    if i < 200:
        return None

    price = hist["Close"].iloc[i]
    dma = hist["200DMA"].iloc[i]
    rsi = hist["RSI"].iloc[i]

    momentum = price / hist["Close"].iloc[i-60] - 1

    score = 5

    if price > dma:
        score += 20

    if 55 <= rsi <= 75:
        score += 20
    elif 45 <= rsi < 55:
        score += 10
    elif rsi > 75:
        score += 5

    if momentum > 0.15:
        score += 20
    elif momentum > 0:
        score += 10

    return score


# -----------------------------
# MAIN
# -----------------------------
if run:

    st.subheader("📊 Running Monthly Rebalancing Backtest...")

    data = {}

    for ticker in tickers:
        hist = fetch_full_data(ticker, f"{years}y")
        if hist is not None:
            data[ticker] = hist

    if len(data) == 0:
        st.warning("No data available")
        st.stop()

    # Align dates
    dates = list(data[list(data.keys())[0]].index)

    portfolio_returns = []

    for i in range(200, len(dates)-1, 21):  # monthly steps (~21 trading days)

        scores = {}

        for ticker, hist in data.items():
            if i >= len(hist):
                continue

            score = compute_score_row(hist, i)

            if score is not None:
                scores[ticker] = score

        if len(scores) == 0:
            continue

        # Pick top N
        selected = sorted(scores, key=scores.get, reverse=True)[:top_n]

        # Compute next month return
        period_returns = []

        for ticker in selected:
            hist = data[ticker]

            if i+21 < len(hist):
                ret = hist["Close"].iloc[i+21] / hist["Close"].iloc[i] - 1
                period_returns.append(ret)

        if len(period_returns) > 0:
            portfolio_returns.append(np.mean(period_returns))

    if len(portfolio_returns) == 0:
        st.warning("No backtest results")
        st.stop()

    # Convert to cumulative
    portfolio_series = pd.Series(portfolio_returns)
    cumulative = (1 + portfolio_series).cumprod()

    # Benchmark
    nifty = yf.Ticker("^NSEI").history(period=f"{years}y")
    nifty["Return"] = nifty["Close"].pct_change()
    nifty["Cumulative"] = (1 + nifty["Return"]).cumprod()

    # Align lengths
    min_len = min(len(cumulative), len(nifty))
    cumulative = cumulative.iloc[:min_len]
    nifty = nifty.iloc[:min_len]

    st.subheader("📈 Strategy vs Nifty")

    st.line_chart(pd.DataFrame({
        "Strategy": cumulative.values,
        "Nifty": nifty["Cumulative"].values
    }))

    strategy_return = cumulative.iloc[-1] - 1
    nifty_return = nifty["Cumulative"].iloc[-1] - 1

    col1, col2 = st.columns(2)
    col1.metric("Strategy Return", f"{round(strategy_return*100,2)}%")
    col2.metric("Nifty Return", f"{round(nifty_return*100,2)}%")
