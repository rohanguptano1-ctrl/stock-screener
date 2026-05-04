import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("🧠 AI Equity Research Platform V4.1")

# INPUT
tickers_input = st.text_input(
    "Enter tickers",
    "SUZLON.NS,IRCON.NS,NBCC.NS,HFCL.NS,IDFCFIRSTB.NS"
)

years = st.slider("Backtest Period (Years)", 1, 5, 1)

tickers = [t.strip() for t in tickers_input.split(",")]
run = st.button("Run Analysis + Backtest")

# DATA FETCH
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


# SCORE FUNCTION
def compute_score(hist):
    close = hist["Close"].dropna()
    if len(close) < 60:
        return None

    price = float(close.iloc[-1])
    rsi = hist["RSI"].dropna().iloc[-1]
    dma = hist["200DMA"].dropna().iloc[-1]

    momentum = price / close.iloc[-60] - 1

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

    return score, price, rsi, momentum


def recommendation(score):
    if score >= 70:
        return "BUY"
    elif score >= 50:
        return "HOLD"
    else:
        return "AVOID"


# MAIN
if run:

    results = {}
    full_data = {}

    for ticker in tickers:
        hist = fetch_data(ticker, "1y")

        if hist is None:
            continue

        res = compute_score(hist)
        if res is None:
            continue

        score, price, rsi, momentum = res

        results[ticker] = {
            "Price": round(price, 2),
            "Score": score,
            "RSI": round(rsi, 2),
            "Momentum %": round(momentum * 100, 2),
            "Recommendation": recommendation(score)
        }

        full_data[ticker] = hist

    df = pd.DataFrame(results).T

    if df.empty:
        st.warning("No valid data")
        st.stop()

    df["Rank"] = df["Score"].rank(pct=True)

    st.subheader("📊 Screener Output")
    st.dataframe(df)

    # -----------------------------
    # IMPROVED BACKTEST
    # -----------------------------
    st.subheader("📈 Backtest Results (BUY Only)")

    returns_list = []

    for ticker in df[df["Recommendation"] == "BUY"].index:
        hist = fetch_data(ticker, f"{years}y")

        if hist is None:
            continue

        hist["Return"] = hist["Close"].pct_change()
        returns_list.append(hist["Return"])

    if len(returns_list) == 0:
        st.warning("No BUY signals → no backtest")
    else:
        combined = pd.concat(returns_list, axis=1)

        combined["Portfolio"] = combined.mean(axis=1)
        combined["Cumulative"] = (1 + combined["Portfolio"]).cumprod()

        # Benchmark
        nifty = yf.Ticker("^NSEI").history(period=f"{years}y")
        nifty["Return"] = nifty["Close"].pct_change()
        nifty["Cumulative"] = (1 + nifty["Return"]).cumprod()

        st.line_chart(pd.DataFrame({
            "Strategy": combined["Cumulative"],
            "Nifty": nifty["Cumulative"]
        }))

        strategy_return = combined["Cumulative"].iloc[-1] - 1
        nifty_return = nifty["Cumulative"].iloc[-1] - 1

        st.metric("Strategy Return", f"{round(strategy_return*100,2)}%")
        st.metric("Nifty Return", f"{round(nifty_return*100,2)}%")
