import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("🚀 AI Equity Research Platform V10 (Alpha Engine)")

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
# FETCH DATA
# -----------------------------
@st.cache_data
def fetch_data(ticker, period="2y"):
    try:
        df = yf.Ticker(ticker).history(period=period)

        if df is None or df.empty:
            return None

        df["200DMA"] = df["Close"].rolling(200).mean()
        df["RSI"] = RSIIndicator(df["Close"], 14).rsi()

        return df

    except:
        return None

# -----------------------------
# ANALYSIS ENGINE (V10)
# -----------------------------
def analyze(stock_df, bench_df):

    stock_df = stock_df.dropna(subset=["Close"])
    bench_df = bench_df.dropna(subset=["Close"])

    if len(stock_df) < 220 or len(bench_df) < 220:
        return None

    s = stock_df.iloc[-1]
    b = bench_df.iloc[-1]

    price = s["Close"]
    dma = s["200DMA"]
    rsi = s["RSI"]

    if pd.isna(dma) or pd.isna(rsi):
        return None

    # -----------------------------
    # MOMENTUM
    # -----------------------------
    mom_20 = price / stock_df["Close"].iloc[-20] - 1
    mom_60 = price / stock_df["Close"].iloc[-60] - 1

    # -----------------------------
    # RELATIVE STRENGTH
    # -----------------------------
    stock_ret = price / stock_df["Close"].iloc[-60] - 1
    bench_ret = b["Close"] / bench_df["Close"].iloc[-60] - 1

    rs = stock_ret - bench_ret

    # -----------------------------
    # SCORING
    # -----------------------------
    score = 0

    # RS (most important)
    if rs > 0.10:
        score += 40
    elif rs > 0:
        score += 25

    # TREND
    if price > dma:
        score += 20

    # MOMENTUM
    if mom_20 > 0.10:
        score += 15
    elif mom_20 > 0:
        score += 10

    if mom_60 > 0.20:
        score += 10
    elif mom_60 > 0:
        score += 5

    # RSI
    if 55 <= rsi <= 70:
        score += 15
    elif rsi > 70:
        score += 10

    # -----------------------------
    # RECOMMENDATION
    # -----------------------------
    if score >= 70:
        rec = "BUY"
    elif score >= 50:
        rec = "HOLD"
    else:
        rec = "AVOID"

    return {
        "price": price,
        "rsi": rsi,
        "mom20": mom_20,
        "mom60": mom_60,
        "rs": rs,
        "score": score,
        "rec": rec,
        "dma": dma
    }

# -----------------------------
# THESIS
# -----------------------------
def thesis(res):

    return " | ".join([
        "Outperforming market" if res["rs"] > 0 else "Underperforming",
        "Above 200DMA" if res["price"] > res["dma"] else "Below 200DMA",
        "Strong short-term momentum" if res["mom20"] > 0 else "Weak short-term momentum",
        res["rec"]
    ])

# =============================
# 1️⃣ STOCK ANALYZER
# =============================
if mode == "Stock Analyzer":

    ticker = st.text_input("Enter Ticker", "RELIANCE.NS")

    benchmark_choice = st.selectbox(
        "Benchmark",
        ["Nifty 50", "Sensex", "Bank Nifty"]
    )

    if st.button("Analyze Stock"):

        stock = fetch_data(ticker)
        bench = fetch_data(get_benchmark(benchmark_choice))

        if stock is None or bench is None:
            st.error("Data issue")
        else:
            res = analyze(stock, bench)

            if res is None:
                st.error("Not enough usable data")
            else:
                c1, c2, c3, c4 = st.columns(4)

                c1.metric("Price", round(res["price"],2))
                c2.metric("RSI", round(res["rsi"],2))
                c3.metric("Momentum 20d %", round(res["mom20"]*100,2))
                c4.metric("Relative Strength", round(res["rs"]*100,2))

                st.subheader(f"Recommendation: {res['rec']}")
                st.write(thesis(res))

# =============================
# 2️⃣ SCREENER
# =============================
elif mode == "Screener":

    tickers_input = st.text_input(
        "Enter tickers",
        "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS"
    )

    benchmark_choice = st.selectbox(
        "Benchmark",
        ["Nifty 50", "Sensex", "Bank Nifty"]
    )

    tickers = [t.strip() for t in tickers_input.split(",")]

    if st.button("Run Screener"):

        bench = fetch_data(get_benchmark(benchmark_choice))

        rows = []

        for t in tickers:

            stock = fetch_data(t)

            if stock is None or bench is None:
                continue

            res = analyze(stock, bench)

            if res is None:
                continue

            rows.append({
                "Ticker": t,
                "Price": round(res["price"],2),
                "Score": res["score"],
                "Recommendation": res["rec"],
                "RSI": round(res["rsi"],2),
                "Rel Strength %": round(res["rs"]*100,2),
                "Mom20 %": round(res["mom20"]*100,2)
            })

        if not rows:
            st.warning("No valid stocks")
        else:
            df = pd.DataFrame(rows).sort_values(by="Score", ascending=False)
            st.dataframe(df, use_container_width=True)

# =============================
# 3️⃣ BACKTEST LAB (UPGRADED)
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
        bench = fetch_data(get_benchmark(benchmark_choice), f"{years}y")

        for t in tickers:
            df = fetch_data(t, f"{years}y")
            if df is not None:
                data[t] = df

        if not data or bench is None:
            st.error("No data")
            st.stop()

        dates = list(bench.index)
        step = 20
        returns = []

        for i in range(220, len(dates)-step, step):

            scores = {}

            for t, df in data.items():

                if i >= len(df):
                    continue

                res = analyze(df.iloc[:i], bench.iloc[:i])

                if res:
                    scores[t] = res["score"]

            selected = sorted(scores, key=scores.get, reverse=True)[:3]

            period = []

            for t in selected:
                df = data[t]

                if i+step < len(df):
                    r = df["Close"].iloc[i+step] / df["Close"].iloc[i] - 1
                    period.append(r)

            returns.append(np.mean(period) if period else 0)

        strat = pd.Series(returns)
        strat_cum = (1 + strat).cumprod()

        # BENCHMARK
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
