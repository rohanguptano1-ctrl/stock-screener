import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("🚀 AI Equity Research Platform V8")

# -----------------------------
# MODE SELECTOR
# -----------------------------
mode = st.sidebar.radio(
    "Select Mode",
    ["Stock Analyzer", "Screener", "Backtest Lab"]
)

# -----------------------------
# COMMON FUNCTIONS
# -----------------------------
@st.cache_data
def fetch_data(ticker, period="1y"):
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty:
            return None

        hist["200DMA"] = hist["Close"].rolling(200).mean()
        hist["RSI"] = RSIIndicator(hist["Close"], 14).rsi()
        return hist
    except:
        return None

def analyze(hist):
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

def thesis(rec, price, dma, rsi, momentum):
    parts = []
    parts.append("Uptrend" if price > dma else "Weak trend")

    if momentum > 0.15:
        parts.append("Strong momentum")
    elif momentum > 0:
        parts.append("Moderate momentum")
    else:
        parts.append("Negative momentum")

    if rsi > 70:
        parts.append("Overbought")
    elif rsi > 50:
        parts.append("Healthy RSI")
    else:
        parts.append("Weak RSI")

    parts.append(rec)
    return " | ".join(parts)

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
            score, rec, price, rsi, momentum, dma = analyze(hist)

            st.subheader(f"📊 {ticker} Analysis")

            col1, col2, col3 = st.columns(3)

            col1.metric("Price", round(price,2))
            col2.metric("RSI", round(rsi,2))
            col3.metric("Momentum %", round(momentum*100,2))

            st.write("### Recommendation:", rec)
            st.write("### Thesis:", thesis(rec, price, dma, rsi, momentum))

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

        results = []

        for t in tickers:
            hist = fetch_data(t)

            if hist is None:
                continue

            score, rec, price, rsi, momentum, dma = analyze(hist)

            results.append({
                "Ticker": t,
                "Price": round(price,2),
                "Score": score,
                "Recommendation": rec,
                "RSI": round(rsi,2),
                "Momentum %": round(momentum*100,2)
            })

        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)

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

    tickers = [t.strip() for t in tickers_input.split(",")]

    if st.button("Run Backtest"):

        data = {}

        for t in tickers:
            hist = fetch_data(t, f"{years}y")
            if hist is not None:
                data[t] = hist

        dates = list(data[list(data.keys())[0]].index)

        returns = []
        step = 20

        for i in range(200, len(dates)-step, step):

            scores = {}

            for t, hist in data.items():
                if i >= len(hist):
                    continue

                s, _, _, _, _, _ = analyze(hist.iloc[:i])
                scores[t] = s

            selected = sorted(scores, key=scores.get, reverse=True)[:3]

            period_ret = []

            for t in selected:
                hist = data[t]
                if i+step < len(hist):
                    r = hist["Close"].iloc[i+step]/hist["Close"].iloc[i]-1
                    period_ret.append(r)

            returns.append(np.mean(period_ret) if period_ret else 0)

        strat = pd.Series(returns)
        strat_cum = (1+strat).cumprod()

        st.line_chart(strat_cum)

        st.metric("Strategy Return", f"{round((strat_cum.iloc[-1]-1)*100,2)}%")
