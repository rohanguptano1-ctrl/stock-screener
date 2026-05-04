import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")

st.title("🚀 AI Equity Research Platform V11.1 (Stable)")

# ==============================
# INPUTS
# ==============================

mode = st.radio("Select Mode", ["📊 Screener", "🔍 Single Stock", "📈 Backtest"])

tickers_input = st.text_input(
    "Enter Tickers",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS"
)

tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]

benchmark_map = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "Bank Nifty": "^NSEBANK"
}

benchmark_choice = st.selectbox("Benchmark", list(benchmark_map.keys()))
benchmark_symbol = benchmark_map[benchmark_choice]

years = st.slider("Backtest Years", 1, 5, 3)

# ==============================
# DATA FETCH
# ==============================

@st.cache_data
def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="5y", progress=False)
        if df is None or df.empty:
            return None
        df = df.dropna()
        return df
    except:
        return None

# ==============================
# METRICS
# ==============================

def compute_metrics(df, benchmark_df=None):

    if df is None or len(df) < 200:
        return None

    df = df.copy()

    df["Returns"] = df["Close"].pct_change()

    # RSI
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # Moving averages
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()

    # Momentum
    df["Mom_20"] = df["Close"].pct_change(20) * 100

    latest = df.iloc[-1]

    # SAFE scalar extraction
    close = float(latest["Close"])
    sma200 = float(latest["SMA200"])
    rsi = float(latest["RSI"])
    mom = float(latest["Mom_20"])

    # Relative strength
    rs_value = 0
    if benchmark_df is not None and len(benchmark_df) > 0:
        aligned = df.join(benchmark_df["Close"], how="inner", rsuffix="_bench")
        if len(aligned) > 0:
            rel = (aligned["Close"] / aligned["Close"].iloc[0]) / (
                aligned["Close_bench"] / aligned["Close_bench"].iloc[0]
            )
            rs_value = float(rel.iloc[-1] * 100 - 100)

    return {
        "price": round(close, 2),
        "rsi": round(rsi, 2),
        "mom": round(mom, 2),
        "above_200dma": bool(close > sma200),
        "rs": round(rs_value, 2)
    }

# ==============================
# SCORING
# ==============================

def score_stock(m):

    score = 0
    thesis = []

    if m["above_200dma"]:
        score += 20
        thesis.append("Uptrend")
    else:
        thesis.append("Below 200DMA")

    if m["mom"] > 5:
        score += 25
        thesis.append("Strong momentum")
    elif m["mom"] > 0:
        score += 10
        thesis.append("Mild momentum")
    else:
        thesis.append("Negative momentum")

    if 50 < m["rsi"] < 70:
        score += 20
        thesis.append("Healthy RSI")
    elif m["rsi"] >= 70:
        thesis.append("Overbought")
    else:
        thesis.append("Weak RSI")

    if m["rs"] > 5:
        score += 35
        thesis.append("Outperforming")
    elif m["rs"] > 0:
        score += 15
        thesis.append("Slightly outperforming")
    else:
        thesis.append("Underperforming")

    if score >= 70:
        rec = "BUY"
    elif score >= 45:
        rec = "HOLD"
    else:
        rec = "AVOID"

    return score, rec, " | ".join(thesis)

# ==============================
# MARKET FILTER
# ==============================

def get_market_series(benchmark_df):
    df = benchmark_df.copy()
    df["SMA200"] = df["Close"].rolling(200).mean()
    return (df["Close"] > df["SMA200"]).astype(int)

# ==============================
# SCREENER
# ==============================

if mode == "📊 Screener":

    if st.button("Run Screener"):

        benchmark_df = fetch_data(benchmark_symbol)
        market_series = get_market_series(benchmark_df)
        market_ok = bool(market_series.iloc[-1])

        rows = []

        for t in tickers:
            df = fetch_data(t)
            m = compute_metrics(df, benchmark_df)

            if m is None:
                continue

            score, rec, thesis = score_stock(m)

            if not market_ok:
                rec = "AVOID (Market Weak)"

            rows.append({
                "Ticker": t,
                "Price": m["price"],
                "Score": score,
                "Recommendation": rec,
                "RSI": m["rsi"],
                "Momentum %": m["mom"],
                "Rel Strength %": m["rs"],
                "Thesis": thesis
            })

        df_out = pd.DataFrame(rows)

        if not df_out.empty:
            st.dataframe(df_out.sort_values(by="Score", ascending=False))
        else:
            st.warning("No valid stocks")

# ==============================
# SINGLE STOCK
# ==============================

elif mode == "🔍 Single Stock":

    if st.button("Analyze Stock"):

        ticker = tickers[0]
        df = fetch_data(ticker)
        benchmark_df = fetch_data(benchmark_symbol)

        m = compute_metrics(df, benchmark_df)

        if m is None:
            st.error("Not enough data")
        else:
            score, rec, thesis = score_stock(m)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Price", m["price"])
            col2.metric("RSI", m["rsi"])
            col3.metric("Momentum %", m["mom"])
            col4.metric("Rel Strength %", m["rs"])

            st.subheader(f"Recommendation: {rec}")
            st.write(thesis)

# ==============================
# BACKTEST
# ==============================

elif mode == "📈 Backtest":

    if st.button("Run Backtest"):

        benchmark_df = fetch_data(benchmark_symbol)
        benchmark_df["Returns"] = benchmark_df["Close"].pct_change()

        market_series = get_market_series(benchmark_df)

        portfolio = []

        for date in benchmark_df.index:

            if market_series.loc[date] == 0:
                portfolio.append(0)
                continue

            buy_flag = False

            for t in tickers:
                df = fetch_data(t)

                if df is None or date not in df.index:
                    continue

                sub_df = df[df.index <= date]

                m = compute_metrics(sub_df, benchmark_df)

                if m is None:
                    continue

                score, rec, _ = score_stock(m)

                if rec == "BUY":
                    buy_flag = True
                    break

            portfolio.append(1 if buy_flag else 0)

        portfolio = pd.Series(portfolio, index=benchmark_df.index)

        strategy_returns = portfolio.shift(1) * benchmark_df["Returns"]

        strategy_curve = (1 + strategy_returns.fillna(0)).cumprod()
        benchmark_curve = (1 + benchmark_df["Returns"].fillna(0)).cumprod()

        st.subheader("Strategy vs Benchmark")

        chart_df = pd.DataFrame({
            "Strategy": strategy_curve,
            benchmark_choice: benchmark_curve
        })

        st.line_chart(chart_df)

        st.metric("Strategy Return", f"{(strategy_curve.iloc[-1]-1)*100:.2f}%")
        st.metric(f"{benchmark_choice} Return", f"{(benchmark_curve.iloc[-1]-1)*100:.2f}%")
