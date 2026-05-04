import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("🚀 AI Equity Research Platform V9.2")

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
# FETCH DATA (FIXED PROPERLY)
# -----------------------------
@st.cache_data
def fetch_data(ticker, period="2y"):
    try:
        hist = yf.Ticker(ticker).history(period=period)

        if hist is None or hist.empty:
            return None

        hist["200DMA"] = hist["Close"].rolling(200).mean()
        hist["RSI"] = RSIIndicator(hist["Close"], 14).rsi()

        return hist

    except:
        return None

# -----------------------------
# ANALYSIS (FIXED)
# -----------------------------
def analyze(hist):

    # Only drop rows where Close missing (NOT all columns)
    hist = hist.dropna(subset=["Close"])

    if len(hist) < 220:   # ensure 200DMA stability
        return None

    latest = hist.iloc[-1]

    price = latest["Close"]
    dma = latest["200DMA"]
    rsi = latest["RSI"]

    if pd.isna(dma) or pd.isna(rsi):
        return None

    momentum = price / hist["Close"].iloc[-60] - 1

    score = 0

    # TREND (strong weight)
    if price > dma:
        score += 40

    # MOMENTUM
    if momentum > 0.25:
        score += 30
    elif momentum > 0.15:
        score += 20
    elif momentum > 0:
        score += 10

    # RSI
    if 55 <= rsi <= 70:
        score += 20
    elif rsi > 70:
        score += 10

    # FINAL CALL
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
        "Uptrend" if price > dma else "Downtrend",
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
                st.error("Not enough usable data (need ~220 days)")
            else:
                score, rec, price, rsi, momentum, dma = res

                c1, c2, c3 = st.columns(3)
                c1.metric("Price", round(price,2))
                c2.metric("RSI", round(rsi,2))
                c3.metric("Momentum %", round(momentum*100,2))

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

        if not rows:
            st.warning("No valid stocks found (increase universe or time period)")
        else:
            df = pd.DataFrame(rows).sort_values(by="Score", ascending=False)
            st.dataframe(df, use_container_width=True)

# =============================
# 3️⃣ BACKTEST LAB (IMPROVED)
# =============================
elif mode == "Backtest Lab":

    tickers_input = st.text_input(
        "Enter tickers",
        "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS"
    )

    years = st.slider("Years", 1, 5, 3)

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

        if not data:
            st.error("No data")
            st.stop()

        dates = list(data[list(data.keys())[0]].index)

        returns = []
        step = 20

        for i in range(220, len(dates)-step, step):

            scores = {}

            for t, hist in data.items():

                if i >= len(hist):
                    continue

                res = analyze(hist.iloc[:i])

                if res:
                    scores[t] = res[0]

            # only BUY stocks
            selected = [t for t in scores if scores[t] >= 70]

            if not selected:
                returns.append(0)
                continue

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

        c1, c2 = st.columns(2)
        c1.metric("Strategy Return", f"{round((strat_cum.iloc[-1]-1)*100,2)}%")
        c2.metric(f"{benchmark_choice} Return", f"{round((bench_cum.iloc[-1]-1)*100,2)}%")
