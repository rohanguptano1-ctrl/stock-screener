import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(layout="wide")

# ---------------------------
# HELPERS
# ---------------------------

@st.cache_data
def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="5y", interval="1d", progress=False)

        if df is None or df.empty:
            return None

        df = df.dropna()
        return df
    except:
        return None


def compute_metrics(df, benchmark_df=None):

    if df is None or len(df) < 200:
        return None

    df = df.copy()

    df["SMA200"] = df["Close"].rolling(200).mean()
    df["Returns"] = df["Close"].pct_change()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["Momentum"] = df["Close"].pct_change(20)

    latest = df.iloc[-1]

    if pd.isna(latest["SMA200"]) or pd.isna(latest["RSI"]):
        return None

    rel_strength = 0
    if benchmark_df is not None:
        common = df.index.intersection(benchmark_df.index)
        if len(common) > 50:
            stock_ret = df.loc[common, "Close"].pct_change().mean()
            bench_ret = benchmark_df.loc[common, "Close"].pct_change().mean()
            rel_strength = stock_ret - bench_ret

    return {
        "price": float(latest["Close"]),
        "rsi": float(latest["RSI"]),
        "momentum": float(latest["Momentum"] * 100),
        "above_200dma": float(latest["Close"]) > float(latest["SMA200"]),
        "rel_strength": float(rel_strength * 100)
    }


def score_stock(m):

    score = 0

    if m["above_200dma"]:
        score += 30

    if 40 < m["rsi"] < 70:
        score += 20

    if m["momentum"] > 0:
        score += 20

    if m["rel_strength"] > 0:
        score += 30

    if score >= 70:
        rec = "BUY"
    elif score >= 50:
        rec = "HOLD"
    else:
        rec = "AVOID"

    thesis = f"{'Above' if m['above_200dma'] else 'Below'} 200DMA | Momentum {round(m['momentum'],2)}% | RSI {round(m['rsi'],1)}"

    return score, rec, thesis


def get_market_series(df):
    df = df.copy()
    df["SMA200"] = df["Close"].rolling(200).mean()
    return (df["Close"] > df["SMA200"]).astype(int)


# ---------------------------
# SIDEBAR
# ---------------------------

st.sidebar.title("Controls")

mode = st.sidebar.radio(
    "Select Mode",
    ["📊 Screener", "🔍 Single Stock", "📈 Backtest"]
)

ticker_input = st.sidebar.text_input(
    "Enter Tickers",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS"
)

tickers = [t.strip() for t in ticker_input.split(",") if t.strip()]

benchmark_choice = st.sidebar.selectbox(
    "Benchmark",
    ["Nifty 50", "Sensex"]
)

benchmark_map = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN"
}

benchmark_symbol = benchmark_map[benchmark_choice]

years = st.sidebar.slider("Backtest Years", 1, 5, 3)

st.title("🚀 AI Equity Research Platform V11.3")

# ---------------------------
# SCREENER
# ---------------------------

if mode == "📊 Screener":

    if st.button("Run Screener"):

        benchmark_df = fetch_data(benchmark_symbol)

        rows = []

        for t in tickers:

            df = fetch_data(t)

            m = compute_metrics(df, benchmark_df)

            if m is None:
                continue

            score, rec, thesis = score_stock(m)

            rows.append({
                "Ticker": t,
                "Price": m["price"],
                "Score": score,
                "Recommendation": rec,
                "RSI": round(m["rsi"], 2),
                "Momentum %": round(m["momentum"], 2),
                "Rel Strength %": round(m["rel_strength"], 2),
                "Thesis": thesis
            })

        if len(rows) == 0:
            st.warning("No valid stocks found")
        else:
            df = pd.DataFrame(rows).sort_values(by="Score", ascending=False)
            st.dataframe(df, use_container_width=True)


# ---------------------------
# SINGLE STOCK
# ---------------------------

elif mode == "🔍 Single Stock":

    if len(tickers) != 1:
        st.warning("Please enter ONLY ONE ticker")
        st.stop()

    if st.button("Analyze Stock"):

        ticker = tickers[0]

        df = fetch_data(ticker)
        benchmark_df = fetch_data(benchmark_symbol)

        m = compute_metrics(df, benchmark_df)

        if m is None:
            st.error("Not enough data")
            st.stop()

        score, rec, thesis = score_stock(m)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Price", round(m["price"], 2))
        c2.metric("RSI", round(m["rsi"], 2))
        c3.metric("Momentum %", round(m["momentum"], 2))
        c4.metric("Rel Strength %", round(m["rel_strength"], 2))

        st.subheader(f"Recommendation: {rec}")
        st.write(thesis)


# ---------------------------
# BACKTEST
# ---------------------------

elif mode == "📈 Backtest":

    if st.button("Run Backtest"):

        benchmark_df = fetch_data(benchmark_symbol)

        if benchmark_df is None or len(benchmark_df) < 200:
            st.error("Benchmark data insufficient")
            st.stop()

        benchmark_df["Returns"] = benchmark_df["Close"].pct_change()

        market_series = get_market_series(benchmark_df)

        portfolio = []
        valid_dates = []

        for date in market_series.index:

            if market_series.loc[date] == 0:
                portfolio.append(0)
                valid_dates.append(date)
                continue

            buy_flag = False

            for t in tickers:

                df = fetch_data(t)

                if df is None or date not in df.index:
                    continue

                sub_df = df.loc[:date]

                if len(sub_df) < 200:
                    continue

                m = compute_metrics(sub_df, benchmark_df)

                if m is None:
                    continue

                score, rec, _ = score_stock(m)

                if rec == "BUY":
                    buy_flag = True
                    break

            portfolio.append(1 if buy_flag else 0)
            valid_dates.append(date)

        portfolio = pd.Series(portfolio, index=valid_dates)

        benchmark_returns = benchmark_df.loc[portfolio.index, "Returns"].fillna(0)

        strategy_returns = portfolio.shift(1).fillna(0) * benchmark_returns

        if strategy_returns.sum() == 0:
            st.warning("No trades triggered — strategy too strict")
            st.stop()

        strategy_curve = (1 + strategy_returns).cumprod()
        benchmark_curve = (1 + benchmark_returns).cumprod()

        st.subheader("Strategy vs Benchmark")

        chart_df = pd.DataFrame({
            "Strategy": strategy_curve,
            benchmark_choice: benchmark_curve
        })

        st.line_chart(chart_df)

        st.metric("Strategy Return", f"{(strategy_curve.iloc[-1]-1)*100:.2f}%")
        st.metric(f"{benchmark_choice} Return", f"{(benchmark_curve.iloc[-1]-1)*100:.2f}%")
