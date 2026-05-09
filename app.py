import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Equity Research Platform V12",
    layout="wide"
)

st.title("🚀 AI Equity Research Platform V12")

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("Controls")

mode = st.sidebar.radio(
    "Mode",
    [
        "📊 Screener",
        "🔍 Single Stock",
        "📈 Portfolio Backtest"
    ]
)

ticker_input = st.sidebar.text_area(
    "Tickers",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"
)

benchmark_name = st.sidebar.selectbox(
    "Benchmark",
    [
        "Nifty 50",
        "Sensex",
        "S&P 500"
    ]
)

top_n = st.sidebar.slider(
    "Top N Stocks",
    1,
    10,
    5
)

years = st.sidebar.slider(
    "Backtest Years",
    1,
    10,
    3
)

benchmark_map = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "S&P 500": "^GSPC"
}

benchmark_ticker = benchmark_map[benchmark_name]

tickers = [
    x.strip().upper()
    for x in ticker_input.split(",")
    if x.strip()
]

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

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.copy()

        for col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df.dropna(inplace=True)

        if len(df) < 220:
            return None

        return df

    except:
        return None

# =========================================================
# FACTOR ENGINE
# =========================================================

def compute_factors(df, benchmark_df):

    try:

        df = df.copy()

        # =====================
        # INDICATORS
        # =====================

        df["SMA200"] = (
            df["Close"]
            .rolling(200)
            .mean()
        )

        delta = df["Close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss

        df["RSI"] = 100 - (100 / (1 + rs))

        # =====================
        # MOMENTUM
        # =====================

        df["Momentum20"] = (
            (
                df["Close"]
                /
                df["Close"].shift(20)
            ) - 1
        ) * 100

        # =====================
        # VOLATILITY
        # =====================

        df["Returns"] = (
            df["Close"]
            .pct_change()
        )

        volatility = (
            df["Returns"]
            .rolling(20)
            .std()
            .iloc[-1]
        )

        # =====================
        # RELATIVE STRENGTH
        # =====================

        stock_return = (
            (
                df["Close"].iloc[-1]
                /
                df["Close"].iloc[-60]
            ) - 1
        )

        benchmark_return = (
            (
                benchmark_df["Close"].iloc[-1]
                /
                benchmark_df["Close"].iloc[-60]
            ) - 1
        )

        rel_strength = (
            stock_return - benchmark_return
        ) * 100

        latest = df.iloc[-1]

        price = float(latest["Close"])
        sma200 = float(latest["SMA200"])
        rsi = float(latest["RSI"])
        momentum = float(latest["Momentum20"])

        # =====================
        # SCORE
        # =====================

        score = 0

        # Relative strength
        if rel_strength > 10:
            score += 35
        elif rel_strength > 0:
            score += 20

        # Trend
        if price > sma200:
            score += 25

        # Momentum
        if momentum > 10:
            score += 20
        elif momentum > 0:
            score += 10

        # RSI
        if 50 <= rsi <= 70:
            score += 10

        # Volatility penalty
        if volatility < 0.025:
            score += 10

        # Recommendation
        if score >= 70:
            recommendation = "BUY"
        elif score >= 50:
            recommendation = "HOLD"
        else:
            recommendation = "AVOID"

        thesis = []

        thesis.append(
            "Above 200DMA"
            if price > sma200
            else "Below 200DMA"
        )

        thesis.append(
            "Strong momentum"
            if momentum > 0
            else "Weak momentum"
        )

        thesis.append(
            "Outperforming benchmark"
            if rel_strength > 0
            else "Underperforming benchmark"
        )

        return {
            "Price": round(price, 2),
            "RSI": round(rsi, 2),
            "Momentum": round(momentum, 2),
            "RelStrength": round(rel_strength, 2),
            "Volatility": round(volatility * 100, 2),
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

def market_ok(benchmark_df):

    benchmark_df = benchmark_df.copy()

    benchmark_df["SMA200"] = (
        benchmark_df["Close"]
        .rolling(200)
        .mean()
    )

    latest = benchmark_df.iloc[-1]

    return (
        float(latest["Close"])
        >
        float(latest["SMA200"])
    )

# =========================================================
# LOAD BENCHMARK
# =========================================================

benchmark_df = fetch_data(
    benchmark_ticker,
    years
)

if benchmark_df is None:
    st.error("Benchmark failed")
    st.stop()

# =========================================================
# SCREENER
# =========================================================

if mode == "📊 Screener":

    st.subheader("📊 Screener")

    if st.button("Run Screener"):

        rows = []

        for ticker in tickers:

            df = fetch_data(
                ticker,
                years
            )

            if df is None:
                continue

            metrics = compute_factors(
                df,
                benchmark_df
            )

            if metrics is None:
                continue

            rows.append({
                "Ticker": ticker,
                "Price": metrics["Price"],
                "Score": metrics["Score"],
                "Recommendation": metrics["Recommendation"],
                "RSI": metrics["RSI"],
                "Momentum %": metrics["Momentum"],
                "Rel Strength %": metrics["RelStrength"],
                "Volatility %": metrics["Volatility"],
                "Thesis": metrics["Thesis"]
            })

        if len(rows) == 0:

            st.warning("No valid stocks")

        else:

            result_df = pd.DataFrame(rows)

            result_df = (
                result_df
                .sort_values(
                    by="Score",
                    ascending=False
                )
            )

            st.dataframe(
                result_df,
                use_container_width=True
            )

# =========================================================
# SINGLE STOCK
# =========================================================

elif mode == "🔍 Single Stock":

    st.subheader("🔍 Single Stock")

    if st.button("Analyze Stock"):

        ticker = tickers[0]

        df = fetch_data(
            ticker,
            years
        )

        if df is None:
            st.error("Invalid stock")
            st.stop()

        metrics = compute_factors(
            df,
            benchmark_df
        )

        if metrics is None:
            st.error("Metrics failed")
            st.stop()

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Price",
            metrics["Price"]
        )

        c2.metric(
            "RSI",
            metrics["RSI"]
        )

        c3.metric(
            "Momentum %",
            metrics["Momentum"]
        )

        c4.metric(
            "Relative Strength %",
            metrics["RelStrength"]
        )

        st.markdown(
            f"## Recommendation: {metrics['Recommendation']}"
        )

        st.write(metrics["Thesis"])

# =========================================================
# PORTFOLIO BACKTEST
# =========================================================

elif mode == "📈 Portfolio Backtest":

    st.subheader("📈 Portfolio Backtest")

    if st.button("Run Portfolio Backtest"):

        benchmark_returns = (
            benchmark_df["Close"]
            .pct_change()
            .fillna(0)
        )

        benchmark_curve = (
            1 + benchmark_returns
        ).cumprod()

        all_stock_returns = []

        for ticker in tickers:

            df = fetch_data(
                ticker,
                years
            )

            if df is None:
                continue

            metrics = compute_factors(
                df,
                benchmark_df
            )

            if metrics is None:
                continue

            score = metrics["Score"]

            all_stock_returns.append({
                "Ticker": ticker,
                "Score": score,
                "Returns": metrics["Returns"]
            })

        if len(all_stock_returns) == 0:

            st.error("No valid stocks")
            st.stop()

        ranked = sorted(
            all_stock_returns,
            key=lambda x: x["Score"],
            reverse=True
        )

        selected = ranked[:top_n]

        strategy_returns = pd.concat(
            [
                x["Returns"]
                for x in selected
            ],
            axis=1
        ).mean(axis=1)

        strategy_returns = (
            strategy_returns
            .fillna(0)
        )

        strategy_curve = (
            1 + strategy_returns
        ).cumprod()

        common_index = (
            strategy_curve.index
            .intersection(
                benchmark_curve.index
            )
        )

        strategy_curve = (
            strategy_curve
            .loc[common_index]
        )

        benchmark_curve = (
            benchmark_curve
            .loc[common_index]
        )

        # =====================
        # PERFORMANCE METRICS
        # =====================

        strategy_return = (
            (
                strategy_curve.iloc[-1]
                - 1
            ) * 100
        )

        benchmark_return = (
            (
                benchmark_curve.iloc[-1]
                - 1
            ) * 100
        )

        cagr = (
            (
                strategy_curve.iloc[-1]
            ) ** (
                1 / years
            ) - 1
        ) * 100

        drawdown = (
            strategy_curve
            /
            strategy_curve.cummax()
            - 1
        )

        max_drawdown = (
            drawdown.min()
        ) * 100

        volatility = (
            strategy_returns.std()
            * np.sqrt(252)
            * 100
        )

        sharpe = (
            (
                strategy_returns.mean()
                /
                strategy_returns.std()
            ) * np.sqrt(252)
        )

        # =====================
        # DISPLAY
        # =====================

        chart_df = pd.DataFrame({
            "Strategy": strategy_curve,
            benchmark_name: benchmark_curve
        })

        st.line_chart(chart_df)

        m1, m2, m3, m4, m5 = st.columns(5)

        m1.metric(
            "Strategy Return",
            f"{strategy_return:.2f}%"
        )

        m2.metric(
            "Benchmark Return",
            f"{benchmark_return:.2f}%"
        )

        m3.metric(
            "CAGR",
            f"{cagr:.2f}%"
        )

        m4.metric(
            "Max Drawdown",
            f"{max_drawdown:.2f}%"
        )

        m5.metric(
            "Sharpe Ratio",
            f"{sharpe:.2f}"
        )

        selected_df = pd.DataFrame([
            {
                "Ticker": x["Ticker"],
                "Score": x["Score"]
            }
            for x in selected
        ])

        st.subheader("Selected Portfolio")

        st.dataframe(
            selected_df,
            use_container_width=True
        )
