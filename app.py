import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("🚀 AI Equity Research Platform V9.1")

# -----------------------------
# MODE
# -----------------------------
mode = st.sidebar.radio(
    "Select Mode",
    ["Stock Analyzer", "Screener", "Backtest Lab"]
)

# -----------------------------
# BENCHMARK
# -----------------------------
def get_benchmark(choice):
    return {
        "Nifty 50": "^NSEI",
        "Sensex": "^BSESN",
        "Bank Nifty": "^NSEBANK"
    }[choice]

# -----------------------------
# FETCH DATA (FIXED)
# -----------------------------
@st.cache_data
def fetch_data(ticker, period="1y"):
    try:
        hist = yf.Ticker(ticker).history(period=period)

        if hist is None or hist.empty:
            return None

        hist = hist.copy()

        hist["200DMA"] = hist["Close"].rolling(200).mean()
        hist["RSI"] = RSIIndicator(hist["Close"], 14).rsi()

        return hist

    except:
        return None

# -----------------------------
# SAFE ANALYSIS (FIXED)
# -----------------------------
def analyze(hist):

    hist = hist.dropna()

    if len(hist) < 60:
        return None

    price = hist["Close"].iloc[-1]
    dma = hist["200DMA"].iloc[-1]
    rsi = hist["RSI"].iloc[-1]

    momentum = price / hist["Close"].iloc[-60] - 1

    score = 0

    if price > dma:
        score += 30

    if momentum > 0.2:
        score += 40
    elif momentum > 0.1:
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
def thesis(rec, price, dma, rsi, momentum):

    return " | ".join([
        "Uptrend" if price > dma else "Weak trend",
        "Strong momentum" if momentum > 0.15 else "Weak momentum",
        "Healthy RSI" if rsi > 50 else "Weak RSI",
        rec
    ])

# =============================
# 1️⃣ STOCK ANALYZER
# =============================
if mode == "Stock Analyzer":

    ticker = st.text_input("Enter Ticker", "RELIANCE.NS")

    if st.button("Analyze Stock"):

        hist = fetch_data(ticker)

        if hist is None:
            st.error("No data")
        else:
            res = analyze(hist)

            if res is None:
                st.error("Not enough valid data (need ~60 clean days)")
            else:
                score, rec, price, rsi, momentum, dma = res

                col1, col2, col3 = st.columns(3)

                col1.metric("Price", round(price,2))
                col2.metric("RSI", round(rsi,2))
                col3.metric("Momentum %", round(momentum*100,2))

                st.subheader(f"Recommendation: {rec}")
                st.write(thesis(rec, price, dma, rsi, momentum))

# =============================
# 2️⃣ SCREENER
# =============================
elif mode == "Screener":

    tickers_input = st.text_input(
        "Enter tickers",
        "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS"
    )

    tickers = [t.strip() for t in tickers_input.split(",")]

    if st.button("Run Screener"):

        rows = []

        for t in tickers:

            hist = fetch_data(t)

            if hist is None:
                continue

            res = analyze(hist)

            if res is None:
                continue

            score, rec, price, rsi, momentum, dma = res

            rows.append({
                "Ticker": t,
                "Price": round(price,2),
                "Score": score,
                "Recommendation": rec,
                "RSI": round(rsi,2),
                "Momentum %": round(momentum*100,2)
            })

        if len(rows) == 0:
            st.warning("No valid stocks found")
        else:
            df = pd.DataFrame(rows).sort_values(by="Score", ascending=False)
            st.dataframe(df, use_container_width=True)

# =============================
# 3️⃣ BACKTEST LAB
# =============================
elif mode == "Backtest Lab":

    tickers_input = st.text_input(
        "Enter tickers",
        "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS"
    )

    years = st.slider("Years", 1, 5, 2)

    benchmark_choice = st.selectbox(
        "Benchmark",
        ["Nifty 50", "Sensex", "Bank Nifty"]
    )

    tickers = [t.strip() for t in tickers_input.split(",")]

    if st.button("Run Backtest"):

        data = {}

        for t in tickers:
            hist = fetch_data(t, f"{years}y")
            if hist is not None:
                data[t] = hist

        if len(data) == 0:
            st.error("No data")
            st.stop()

        dates = list(data[list(data.keys())[0]].index)

        returns = []
        step = 20

        for i in range(200, len(dates)-step, step):

            scores = {}

            for t, hist in data.items():
                if i >= len(hist):
                    continue

                res = analyze(hist.iloc[:i])

                if res:
                    scores[t] = res[0]

            selected = sorted(scores, key=scores.get, reverse=True)[:3]

            period = []

            for t in selected:
                hist = data[t]

                if i+step < len(hist):
                    r = hist["Close"].iloc[i+step] / hist["Close"].iloc[i] - 1
                    period.append(r)

            returns.append(np.mean(period) if period else 0)

        strat = pd.Series(returns)
        strat_cum = (1 + strat).cumprod()

        # BENCHMARK
        bench = yf.Ticker(get_benchmark(benchmark_choice)).history(period=f"{years}y")

        bench_ret = []

        for i in range(0, len(bench)-step, step):
            r = bench["Close"].iloc[i+step] / bench["Close"].iloc[i] - 1
            bench_ret.append(r)

        bench_cum = (1 + pd.Series(bench_ret)).cumprod()

        min_len = min(len(strat_cum), len(bench_cum))

        st.subheader("Strategy vs Benchmark")

        st.line_chart(pd.DataFrame({
            "Strategy": strat_cum.iloc[:min_len].values,
            benchmark_choice: bench_cum.iloc[:min_len].values
        }))

        col1, col2 = st.columns(2)

        col1.metric("Strategy Return", f"{round((strat_cum.iloc[-1]-1)*100,2)}%")
        col2.metric(f"{benchmark_choice} Return", f"{round((bench_cum.iloc[-1]-1)*100,2)}%")
