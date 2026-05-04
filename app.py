import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("🚀 AI Equity Research Platform V5.1 (Aggressive Momentum)")

# -----------------------------
# INPUT
# -----------------------------
tickers_input = st.text_input(
    "Enter tickers",
    "LT.NS,ASIANPAINT.NS,BAJFINANCE.NS,TATAMOTORS.NS,ADANIPORTS.NS,HINDUNILVR.NS,COALINDIA.NS,SBIN.NS,ULTRACEMCO.NS,PIDILITIND.NS"
)

years = st.slider("Backtest Period (Years)", 1, 5, 2)
top_n = st.slider("Portfolio Size", 2, 6, 4)

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
# SCORE FUNCTION (AGGRESSIVE)
# -----------------------------
def compute_score_row(hist, i):

    if i < 200:
        return None

    price = hist["Close"].iloc[i]
    dma = hist["200DMA"].iloc[i]
    rsi = hist["RSI"].iloc[i]

    momentum = price / hist["Close"].iloc[i-60] - 1

    # HARD FILTER (IMPORTANT)
    if price < dma or momentum <= 0:
        return None

    score = 0

    # Strong trend
    score += 30

    # Momentum heavy weight
    if momentum > 0.20:
        score += 40
    elif momentum > 0.10:
        score += 25
    else:
        score += 10

    # RSI confirmation
    if 55 <= rsi <= 75:
        score += 20
    elif rsi > 75:
        score += 10

    return score


# -----------------------------
# MAIN
# -----------------------------
if run:

    st.subheader("📊 Running Aggressive Backtest...")

    data = {}

    for ticker in tickers:
        hist = fetch_full_data(ticker, f"{years}y")
        if hist is not None:
            data[ticker] = hist

    if len(data) == 0:
        st.warning("No data available")
        st.stop()

    dates = list(data[list(data.keys())[0]].index)

    portfolio_returns = []

    # 🔥 Faster rebalancing (15 days)
    step = 15

    for i in range(200, len(dates)-step, step):

        scores = {}

        for ticker, hist in data.items():
            if i >= len(hist):
                continue

            score = compute_score_row(hist, i)

            if score is not None:
                scores[ticker] = score

        if len(scores) == 0:
            portfolio_returns.append(0)
            continue

        # Pick top N
        selected = sorted(scores, key=scores.get, reverse=True)[:top_n]

        period_returns = []

        for ticker in selected:
            hist = data[ticker]

            if i+step < len(hist):
                ret = hist["Close"].iloc[i+step] / hist["Close"].iloc[i] - 1
                period_returns.append(ret)

        if len(period_returns) > 0:
            portfolio_returns.append(np.mean(period_returns))
        else:
            portfolio_returns.append(0)

    # Convert to cumulative
    portfolio_series = pd.Series(portfolio_returns)
    cumulative = (1 + portfolio_series).cumprod()

    # Benchmark
    nifty = yf.Ticker("^NSEI").history(period=f"{years}y")
    nifty["Return"] = nifty["Close"].pct_change()
    nifty["Cumulative"] = (1 + nifty["Return"]).cumprod()

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
