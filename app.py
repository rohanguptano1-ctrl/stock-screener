import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("🚀 AI Equity Research Platform V5.4")

# -----------------------------
# INPUT
# -----------------------------
tickers_input = st.text_input(
    "Enter tickers",
    "LT.NS,ASIANPAINT.NS,BAJFINANCE.NS,TATAMOTORS.NS,ADANIPORTS.NS,HINDUNILVR.NS,COALINDIA.NS,SBIN.NS,ULTRACEMCO.NS,PIDILITIND.NS"
)

years = st.slider("Backtest Period (Years)", 1, 5, 2)
top_n = st.slider("Portfolio Size", 2, 6, 4)

benchmark_choice = st.selectbox(
    "Select Benchmark",
    ["Nifty 50", "Sensex", "Bank Nifty", "Nifty Midcap", "Nifty Smallcap"]
)

tickers = [t.strip() for t in tickers_input.split(",")]
run = st.button("Run Analysis")

# -----------------------------
# BENCHMARK MAPPING
# -----------------------------
def get_benchmark_ticker(choice):
    mapping = {
        "Nifty 50": "^NSEI",
        "Sensex": "^BSESN",
        "Bank Nifty": "^NSEBANK",
        "Nifty Midcap": "^NSEMDCP50",
        "Nifty Smallcap": "^NSEMDCP50"
    }
    return mapping.get(choice, "^NSEI")

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
# LIVE SCORE (TODAY)
# -----------------------------
def compute_live_score(hist):

    if len(hist) < 200:
        return None

    price = hist["Close"].dropna().iloc[-1]
    dma = hist["200DMA"].dropna().iloc[-1]
    rsi = hist["RSI"].dropna().iloc[-1]

    momentum = price / hist["Close"].iloc[-60] - 1

    if price < dma or momentum <= 0:
        return None

    score = 0
    score += 30

    if momentum > 0.20:
        score += 40
    elif momentum > 0.10:
        score += 25
    else:
        score += 10

    if 55 <= rsi <= 75:
        score += 20
    elif rsi > 75:
        score += 10

    return score, price, rsi, momentum

# -----------------------------
# BACKTEST SCORE
# -----------------------------
def compute_score_row(hist, i):

    if i < 200:
        return None

    price = hist["Close"].iloc[i]
    dma = hist["200DMA"].iloc[i]
    rsi = hist["RSI"].iloc[i]

    momentum = price / hist["Close"].iloc[i-60] - 1

    if price < dma or momentum <= 0:
        return None

    score = 0
    score += 30

    if momentum > 0.20:
        score += 40
    elif momentum > 0.10:
        score += 25
    else:
        score += 10

    if 55 <= rsi <= 75:
        score += 20
    elif rsi > 75:
        score += 10

    return score

# -----------------------------
# MAIN
# -----------------------------
if run:

    # =============================
    # 🎯 LIVE RECOMMENDATIONS
    # =============================
    st.subheader("🎯 Top Stock Recommendations (Today)")

    live_results = []

    for ticker in tickers:
        hist = fetch_data(ticker, "1y")

        if hist is None:
            continue

        res = compute_live_score(hist)

        if res is None:
            continue

        score, price, rsi, momentum = res

        live_results.append({
            "Ticker": ticker,
            "Price": round(price, 2),
            "Score": score,
            "RSI": round(rsi, 2),
            "Momentum %": round(momentum * 100, 2)
        })

    if len(live_results) > 0:
        live_df = pd.DataFrame(live_results).sort_values(by="Score", ascending=False)

        st.dataframe(live_df, use_container_width=True)

        st.subheader("🔥 Top Picks (Actionable)")
        st.dataframe(live_df.head(top_n), use_container_width=True)

    else:
        st.warning("No strong opportunities right now")

    # =============================
    # 📊 BACKTEST ENGINE
    # =============================
    st.subheader("📊 Running Strategy Backtest...")

    data = {}

    for ticker in tickers:
        hist = fetch_data(ticker, f"{years}y")
        if hist is not None:
            data[ticker] = hist

    if len(data) == 0:
        st.warning("No data available")
        st.stop()

    dates = list(data[list(data.keys())[0]].index)

    portfolio_returns = []
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

    if len(portfolio_returns) == 0:
        st.warning("No backtest results")
        st.stop()

    portfolio_series = pd.Series(portfolio_returns)
    cumulative = (1 + portfolio_series).cumprod()

    # =============================
    # 📈 BENCHMARK
    # =============================
    benchmark_ticker = get_benchmark_ticker(benchmark_choice)

    benchmark = yf.Ticker(benchmark_ticker).history(period=f"{years}y")

    benchmark_returns = []

    for i in range(0, len(benchmark)-step, step):
        ret = benchmark["Close"].iloc[i+step] / benchmark["Close"].iloc[i] - 1
        benchmark_returns.append(ret)

    benchmark_series = pd.Series(benchmark_returns)
    benchmark_cum = (1 + benchmark_series).cumprod()

    min_len = min(len(cumulative), len(benchmark_cum))

    st.subheader("📈 Strategy vs Benchmark")

    st.line_chart(pd.DataFrame({
        "Strategy": cumulative.iloc[:min_len].values,
        benchmark_choice: benchmark_cum.iloc[:min_len].values
    }))

    strategy_return = cumulative.iloc[-1] - 1
    benchmark_return = benchmark_cum.iloc[-1] - 1

    col1, col2 = st.columns(2)
    col1.metric("Strategy Return", f"{round(strategy_return*100,2)}%")
    col2.metric(f"{benchmark_choice} Return", f"{round(benchmark_return*100,2)}%")
