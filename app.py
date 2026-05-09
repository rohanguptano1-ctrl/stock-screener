import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Equity Research Platform V11.4",
    layout="wide"
)

st.title("🚀 AI Equity Research Platform V11.4")

# =========================================================
# BENCHMARK MAP
# =========================================================

BENCHMARKS = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "Bank Nifty": "^NSEBANK",
    "Nifty IT": "^CNXIT",
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC"
}

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("Controls")

mode = st.sidebar.radio(
    "Select Mode",
    ["📊 Screener", "🔍 Single Stock", "📈 Backtest"]
)

ticker_input = st.sidebar.text_input(
    "Tickers",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS"
)

benchmark_name = st.sidebar.selectbox(
    "Benchmark",
    list(BENCHMARKS.keys())
)

years = st.sidebar.slider(
    "Backtest Years",
    1,
    10,
    3
)

benchmark_ticker = BENCHMARKS[benchmark_name]

# =========================================================
# DATA FETCH
# =========================================================

@st.cache_data
def fetch_data(ticker, years=5):

    try:
        df = yf.download(
            ticker,
            period=f"{years}y",
            auto_adjust=True,
            progress=False
        )

        if df is None or len(df) == 0:
            return None

        # FIX MULTIINDEX
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.copy()

        # ENSURE NUMERIC
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df.dropna(inplace=True)

        if len(df) < 220:
            return None

        return df

    except:
        return None

# =========================================================
# METRICS ENGINE
# =========================================================

def compute_metrics(df, benchmark_df):

    try:

        df = df.copy()
        benchmark_df = benchmark_df.copy()

        # INDICATORS
        df["SMA50"] = df["Close"].rolling(50).mean()
        df["SMA200"] = df["Close"].rolling(200).mean()

        delta = df["Close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss

        df["RSI"] = 100 - (100 / (1 + rs))

        df["Momentum20"] = (
            (df["Close"] / df["Close"].shift(20)) - 1
        ) * 100

        # ALIGN BENCHMARK
        aligned_benchmark = benchmark_df.reindex(df.index)

        aligned_benchmark["Returns"] = (
            aligned_benchmark["Close"].pct_change()
        )

        df["Returns"] = df["Close"].pct_change()

        stock_ret = (
            (1 + df["Returns"].dropna()).prod() - 1
        )

        benchmark_ret = (
            (1 + aligned_benchmark["Returns"].dropna()).prod() - 1
        )

        rel_strength = (
            (stock_ret - benchmark_ret) * 100
        )

        latest = df.iloc[-1]

        price = round(float(latest["Close"]), 2)
        rsi = round(float(latest["RSI"]), 2)
        momentum = round(float(latest["Momentum20"]), 2)

        above_200dma = (
            float(latest["Close"]) > float(latest["SMA200"])
        )

        # SCORE
        score = 0
        thesis = []

        if above_200dma:
            score += 40
            thesis.append("Above 200DMA")
        else:
            thesis.append("Below 200DMA")

        if momentum > 5:
            score += 30
            thesis.append("Strong momentum")
        elif momentum > 0:
            score += 15
            thesis.append("Mild momentum")
        else:
            thesis.append("Negative momentum")

        if rsi > 55:
            score += 20
            thesis.append("Healthy RSI")
        elif rsi < 40:
            thesis.append("Weak RSI")

        if rel_strength > 0:
            score += 10
            thesis.append("Outperforming market")
        else:
            thesis.append("Underperforming market")

        # RECOMMENDATION
        if score >= 80:
            recommendation = "BUY"
        elif score >= 50:
            recommendation = "HOLD"
        else:
            recommendation = "AVOID"

        return {
            "Price": price,
            "RSI": rsi,
            "Momentum": momentum,
            "RelStrength": round(rel_strength, 2),
            "Score": score,
            "Recommendation": recommendation,
            "Thesis": " | ".join(thesis),
            "Returns": df["Returns"].fillna(0)
        }

    except:
        return None

# =========================================================
# MARKET FILTER
# =========================================================

def market_is_positive(benchmark_df):

    benchmark_df = benchmark_df.copy()

    benchmark_df["SMA200"] = (
        benchmark_df["Close"].rolling(200).mean()
    )

    latest = benchmark_df.iloc[-1]

    return float(latest["Close"]) > float(latest["SMA200"])

# =========================================================
# SCREENER MODE
# =========================================================

if mode == "📊 Screener":

    st.subheader("📊 Screener")

    if st.button("Run Screener"):

        tickers = [
            x.strip().upper()
            for x in ticker_input.split(",")
            if x.strip()
        ]

        benchmark_df = fetch_data(benchmark_ticker, years)

        if benchmark_df is None:
            st.error("Benchmark failed")
            st.stop()

        market_ok = market_is_positive(benchmark_df)

        rows = []

        for ticker in tickers:

            df = fetch_data(ticker, years)

            if df is None:
                continue

            metrics = compute_metrics(df, benchmark_df)

            if metrics is None:
                continue

            recommendation = metrics["Recommendation"]

            if not market_ok:
                if recommendation == "BUY":
                    recommendation = "HOLD (Market Weak)"
                elif recommendation == "HOLD":
                    recommendation = "AVOID (Market Weak)"

            rows.append({
                "Ticker": ticker,
                "Price": metrics["Price"],
                "Score": metrics["Score"],
                "Recommendation": recommendation,
                "RSI": metrics["RSI"],
                "Momentum %": metrics["Momentum"],
                "Rel Strength %": metrics["RelStrength"],
                "Thesis": metrics["Thesis"]
            })

        if len(rows) == 0:
            st.warning("No valid stocks found")

        else:

            result_df = pd.DataFrame(rows)

            result_df = result_df.sort_values(
                by="Score",
                ascending=False
            )

            st.dataframe(
                result_df,
                use_container_width=True
            )

# =========================================================
# SINGLE STOCK MODE
# =========================================================

elif mode == "🔍 Single Stock":

    st.subheader("🔍 Single Stock Analysis")

    if st.button("Analyze Stock"):

        ticker = ticker_input.split(",")[0].strip().upper()

        benchmark_df = fetch_data(benchmark_ticker, years)

        df = fetch_data(ticker, years)

        if df is None:
            st.error("Stock data unavailable")
            st.stop()

        if benchmark_df is None:
            st.error("Benchmark unavailable")
            st.stop()

        metrics = compute_metrics(df, benchmark_df)

        if metrics is None:
            st.error("Could not compute metrics")
            st.stop()

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Price", metrics["Price"])
        c2.metric("RSI", metrics["RSI"])
        c3.metric("Momentum %", metrics["Momentum"])
        c4.metric("Rel Strength %", metrics["RelStrength"])

        st.markdown(
            f"## Recommendation: {metrics['Recommendation']}"
        )

        st.write(metrics["Thesis"])

# =========================================================
# BACKTEST MODE
# =========================================================

elif mode == "📈 Backtest":

    st.subheader("📈 Strategy Backtest")

    if st.button("Run Backtest"):

        tickers = [
            x.strip().upper()
            for x in ticker_input.split(",")
            if x.strip()
        ]

        benchmark_df = fetch_data(benchmark_ticker, years)

        if benchmark_df is None:
            st.error("Benchmark unavailable")
            st.stop()

        benchmark_df["Returns"] = (
            benchmark_df["Close"].pct_change().fillna(0)
        )

        benchmark_df["SMA200"] = (
            benchmark_df["Close"].rolling(200).mean()
        )

        benchmark_df = benchmark_df.dropna()

        portfolio_returns = []

        for ticker in tickers:

            df = fetch_data(ticker, years)

            if df is None:
                continue

            metrics = compute_metrics(df, benchmark_df)

            if metrics is None:
                continue

            signal = 1 if metrics["Score"] >= 50 else 0

            strat_returns = (
                metrics["Returns"] * signal
            )

            portfolio_returns.append(strat_returns)

        if len(portfolio_returns) == 0:
            st.error("No valid stocks for backtest")
            st.stop()

        combined = pd.concat(
            portfolio_returns,
            axis=1
        ).mean(axis=1)

        combined = combined.fillna(0)

        strategy_curve = (
            1 + combined
        ).cumprod()

        benchmark_curve = (
            1 + benchmark_df["Returns"]
        ).cumprod()

        # ALIGN
        common_index = strategy_curve.index.intersection(
            benchmark_curve.index
        )

        strategy_curve = strategy_curve.loc[common_index]
        benchmark_curve = benchmark_curve.loc[common_index]

        # RETURNS
        strategy_return = (
            (strategy_curve.iloc[-1] - 1) * 100
        )

        benchmark_return = (
            (benchmark_curve.iloc[-1] - 1) * 100
        )

        # CHART
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=strategy_curve.index,
                y=strategy_curve.values,
                name="Strategy"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=benchmark_curve.index,
                y=benchmark_curve.values,
                name=benchmark_name
            )
        )

        fig.update_layout(
            title="Strategy vs Benchmark",
            height=600
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        c1, c2 = st.columns(2)

        c1.metric(
            "Strategy Return",
            f"{strategy_return:.2f}%"
        )

        c2.metric(
            f"{benchmark_name} Return",
            f"{benchmark_return:.2f}%"
        )
