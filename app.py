import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(layout="wide")

# =========================================================
# DATA FUNCTIONS
# =========================================================

@st.cache_data
def fetch_data(ticker):

    try:
        df = yf.download(
            ticker,
            period="5y",
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if df is None or df.empty:
            return None

        # FIX yfinance multi-index issue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required_cols = ["Close"]

        for col in required_cols:
            if col not in df.columns:
                return None

        df = df.dropna()

        if len(df) < 50:
            return None

        return df

    except:
        return None


# =========================================================
# METRIC ENGINE
# =========================================================

def compute_metrics(df, benchmark_df=None):

    if df is None or len(df) < 200:
        return None

    df = df.copy()

    # ------------------------
    # Indicators
    # ------------------------

    df["SMA200"] = df["Close"].rolling(200).mean()

    delta = df["Close"].diff()

    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()

    rs = gain / loss

    df["RSI"] = 100 - (100 / (1 + rs))

    df["Momentum20"] = df["Close"].pct_change(20)

    latest = df.iloc[-1]

    # ------------------------
    # Safety checks
    # ------------------------

    sma200 = float(latest["SMA200"])
    rsi = float(latest["RSI"])
    close = float(latest["Close"])
    momentum = float(latest["Momentum20"])

    if np.isnan(sma200) or np.isnan(rsi):
        return None

    # ------------------------
    # Relative strength
    # ------------------------

    rel_strength = 0

    if benchmark_df is not None:

        common_idx = df.index.intersection(benchmark_df.index)

        if len(common_idx) > 50:

            stock_return = (
                df.loc[common_idx, "Close"].pct_change().mean()
            )

            benchmark_return = (
                benchmark_df.loc[common_idx, "Close"].pct_change().mean()
            )

            rel_strength = (
                float(stock_return) - float(benchmark_return)
            ) * 100

    # ------------------------
    # Return metrics
    # ------------------------

    return {
        "price": close,
        "rsi": rsi,
        "momentum": momentum * 100,
        "above_200dma": close > sma200,
        "rel_strength": rel_strength
    }


# =========================================================
# SCORING ENGINE
# =========================================================

def score_stock(m):

    score = 0

    # Trend
    if m["above_200dma"]:
        score += 30

    # RSI
    if 45 <= m["rsi"] <= 70:
        score += 20

    # Momentum
    if m["momentum"] > 0:
        score += 20

    # Relative strength
    if m["rel_strength"] > 0:
        score += 30

    # Final recommendation
    if score >= 70:
        recommendation = "BUY"

    elif score >= 50:
        recommendation = "HOLD"

    else:
        recommendation = "AVOID"

    # Thesis
    thesis = []

    thesis.append(
        "Above 200DMA"
        if m["above_200dma"]
        else "Below 200DMA"
    )

    if m["momentum"] > 5:
        thesis.append("Strong momentum")

    elif m["momentum"] > 0:
        thesis.append("Positive momentum")

    else:
        thesis.append("Negative momentum")

    if m["rsi"] < 40:
        thesis.append("Weak RSI")

    elif m["rsi"] <= 70:
        thesis.append("Healthy RSI")

    else:
        thesis.append("Overbought")

    if m["rel_strength"] > 0:
        thesis.append("Outperforming market")
    else:
        thesis.append("Underperforming market")

    return score, recommendation, " | ".join(thesis)


# =========================================================
# MARKET FILTER
# =========================================================

def get_market_series(df):

    temp = df.copy()

    temp["SMA200"] = (
        temp["Close"]
        .rolling(200)
        .mean()
    )

    signal = (
        temp["Close"].astype(float)
        >
        temp["SMA200"].astype(float)
    )

    return signal.astype(int)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("Controls")

mode = st.sidebar.radio(
    "Select Mode",
    [
        "📊 Screener",
        "🔍 Single Stock",
        "📈 Backtest"
    ]
)

ticker_input = st.sidebar.text_input(
    "Tickers",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS"
)

tickers = [
    t.strip()
    for t in ticker_input.split(",")
    if t.strip()
]

benchmark_choice = st.sidebar.selectbox(
    "Benchmark",
    [
        "Nifty 50",
        "Sensex"
    ]
)

benchmark_map = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN"
}

benchmark_symbol = benchmark_map[benchmark_choice]

years = st.sidebar.slider(
    "Backtest Years",
    1,
    5,
    3
)

# =========================================================
# TITLE
# =========================================================

st.title("🚀 AI Equity Research Platform V11.3")

# =========================================================
# LOAD BENCHMARK
# =========================================================

benchmark_df = fetch_data(benchmark_symbol)

if benchmark_df is None:
    st.error("Failed to load benchmark data")
    st.stop()

# =========================================================
# MODE: SCREENER
# =========================================================

if mode == "📊 Screener":

    if st.button("Run Screener"):

        rows = []

        for ticker in tickers:

            df = fetch_data(ticker)

            if df is None:
                continue

            metrics = compute_metrics(df, benchmark_df)

            if metrics is None:
                continue

            score, recommendation, thesis = score_stock(metrics)

            rows.append({
                "Ticker": ticker,
                "Price": round(metrics["price"], 2),
                "Score": score,
                "Recommendation": recommendation,
                "RSI": round(metrics["rsi"], 2),
                "Momentum %": round(metrics["momentum"], 2),
                "Rel Strength %": round(metrics["rel_strength"], 2),
                "Thesis": thesis
            })

        if len(rows) == 0:
            st.warning("No valid stocks found")

        else:

            screener_df = (
                pd.DataFrame(rows)
                .sort_values(
                    by="Score",
                    ascending=False
                )
            )

            st.dataframe(
                screener_df,
                use_container_width=True
            )

# =========================================================
# MODE: SINGLE STOCK
# =========================================================

elif mode == "🔍 Single Stock":

    if len(tickers) != 1:
        st.warning(
            "Please enter ONLY ONE ticker in Single Stock mode"
        )
        st.stop()

    if st.button("Analyze Stock"):

        ticker = tickers[0]

        df = fetch_data(ticker)

        if df is None:
            st.error("Failed to fetch stock data")
            st.stop()

        metrics = compute_metrics(df, benchmark_df)

        if metrics is None:
            st.error("Not enough valid data")
            st.stop()

        score, recommendation, thesis = score_stock(metrics)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Price",
            round(metrics["price"], 2)
        )

        c2.metric(
            "RSI",
            round(metrics["rsi"], 2)
        )

        c3.metric(
            "Momentum %",
            round(metrics["momentum"], 2)
        )

        c4.metric(
            "Rel Strength %",
            round(metrics["rel_strength"], 2)
        )

        st.subheader(
            f"Recommendation: {recommendation}"
        )

        st.write(thesis)

# =========================================================
# MODE: BACKTEST
# =========================================================

elif mode == "📈 Backtest":

    if st.button("Run Backtest"):

        benchmark_df = benchmark_df.copy()

        benchmark_df = benchmark_df.last(
            f"{years}Y"
        )

        benchmark_df["Returns"] = (
            benchmark_df["Close"]
            .pct_change()
        )

        market_series = get_market_series(
            benchmark_df
        )

        portfolio_signal = []
        valid_dates = []

        for date in market_series.index:

            market_ok = int(
                market_series.loc[date]
            )

            if market_ok == 0:

                portfolio_signal.append(0)
                valid_dates.append(date)

                continue

            buy_flag = False

            for ticker in tickers:

                df = fetch_data(ticker)

                if df is None:
                    continue

                if date not in df.index:
                    continue

                sub_df = df.loc[:date]

                if len(sub_df) < 200:
                    continue

                metrics = compute_metrics(
                    sub_df,
                    benchmark_df
                )

                if metrics is None:
                    continue

                score, recommendation, thesis = (
                    score_stock(metrics)
                )

                if recommendation == "BUY":
                    buy_flag = True
                    break

            portfolio_signal.append(
                1 if buy_flag else 0
            )

            valid_dates.append(date)

        portfolio_signal = pd.Series(
            portfolio_signal,
            index=valid_dates
        )

        benchmark_returns = (
            benchmark_df.loc[
                portfolio_signal.index,
                "Returns"
            ]
            .fillna(0)
        )

        strategy_returns = (
            portfolio_signal.shift(1)
            .fillna(0)
            * benchmark_returns
        )

        if strategy_returns.abs().sum() == 0:

            st.warning(
                "No trades triggered. Strategy too strict."
            )

            st.stop()

        strategy_curve = (
            1 + strategy_returns
        ).cumprod()

        benchmark_curve = (
            1 + benchmark_returns
        ).cumprod()

        chart_df = pd.DataFrame({
            "Strategy": strategy_curve,
            benchmark_choice: benchmark_curve
        })

        st.subheader("Strategy vs Benchmark")

        st.line_chart(chart_df)

        c1, c2 = st.columns(2)

        c1.metric(
            "Strategy Return",
            f"{(strategy_curve.iloc[-1]-1)*100:.2f}%"
        )

        c2.metric(
            f"{benchmark_choice} Return",
            f"{(benchmark_curve.iloc[-1]-1)*100:.2f}%"
        )
