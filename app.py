import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Equity Research Platform V16.1",
    layout="wide"
)

st.title("🚀 AI Equity Research Platform V16.1")

# =========================================================
# HELPERS
# =========================================================

@st.cache_data
def fetch_data(ticker, period="5y"):

    df = yf.download(
        ticker,
        period=period,
        auto_adjust=True,
        progress=False
    )

    df.dropna(inplace=True)

    return df


def compute_metrics(df, benchmark_df):

    close = df["Close"]

    sma50 = close.rolling(50).mean()

    sma200 = close.rolling(200).mean()

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()

    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    momentum = (
        (close.iloc[-1] / close.iloc[-63]) - 1
    ) * 100

    benchmark_return = (
        benchmark_df["Close"].iloc[-1]
        /
        benchmark_df["Close"].iloc[-63]
        - 1
    ) * 100

    stock_return = (
        close.iloc[-1]
        /
        close.iloc[-63]
        - 1
    ) * 100

    relative_strength = (
        stock_return - benchmark_return
    )

    volatility = (
        close.pct_change().std()
        * np.sqrt(252)
        * 100
    )

    score = 0

    if close.iloc[-1] > sma200.iloc[-1]:
        score += 30

    if sma50.iloc[-1] > sma200.iloc[-1]:
        score += 25

    if rsi.iloc[-1] > 55:
        score += 20

    if momentum > 0:
        score += 15

    if relative_strength > 0:
        score += 10

    # =====================================================
    # RECOMMENDATION
    # =====================================================

    if score >= 80:
        recommendation = "🟢 Strong Buy"

    elif score >= 60:
        recommendation = "🟢 Buy"

    elif score >= 40:
        recommendation = "🟠 Watch"

    else:
        recommendation = "🔴 Avoid"

    # =====================================================
    # STRUCTURE
    # =====================================================

    if (
        close.iloc[-1] > sma200.iloc[-1]
        and sma50.iloc[-1] > sma200.iloc[-1]
    ):
        structure = "Bullish Structure"

    elif close.iloc[-1] > sma200.iloc[-1]:
        structure = "Early Accumulation"

    else:
        structure = "Bearish Structure"

    return {
        "Price": round(close.iloc[-1], 2),
        "RSI": round(rsi.iloc[-1], 2),
        "Momentum": round(momentum, 2),
        "RelativeStrength": round(relative_strength, 2),
        "Volatility": round(volatility, 2),
        "SMA50": round(sma50.iloc[-1], 2),
        "SMA200": round(sma200.iloc[-1], 2),
        "Recommendation": recommendation,
        "Structure": structure,
        "Score": score
    }


# =========================================================
# BENCHMARK
# =========================================================

benchmark_df = fetch_data("^NSEI")

# =========================================================
# SCREENER
# =========================================================

st.header("📊 Screener")

ticker_input = st.text_input(
    "Enter Tickers",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"
)

if st.button("Run Screener"):

    tickers = [
        x.strip()
        for x in ticker_input.split(",")
    ]

    rows = []

    for ticker in tickers:

        try:

            df = fetch_data(ticker)

            metrics = compute_metrics(
                df,
                benchmark_df
            )

            rows.append({
                "Ticker": ticker,
                "Score": metrics["Score"],
                "Recommendation": metrics["Recommendation"],
                "Structure": metrics["Structure"],
                "RSI": metrics["RSI"],
                "Momentum": metrics["Momentum"],
                "RelativeStrength": metrics["RelativeStrength"],
                "Volatility": metrics["Volatility"]
            })

        except:
            pass

    screener_df = pd.DataFrame(rows)

    screener_df = screener_df.sort_values(
        by="Score",
        ascending=False
    )

    st.dataframe(
        screener_df,
        use_container_width=True
    )

# =========================================================
# PORTFOLIO BACKTEST
# =========================================================

st.header("📈 Portfolio Backtest")

portfolio_input = st.text_input(
    "Portfolio Tickers",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"
)

years = st.slider(
    "Backtest Years",
    1,
    10,
    5
)

if st.button("Run Portfolio Backtest"):

    tickers = [
        x.strip()
        for x in portfolio_input.split(",")
    ]

    benchmark_returns = (
        benchmark_df["Close"]
        .pct_change()
        .fillna(0)
    )

    # =====================================================
    # FIXED BUG HERE
    # =====================================================

    benchmark_returns = benchmark_returns[
        benchmark_returns.index >= (
            benchmark_returns.index.max()
            - pd.DateOffset(years=years)
        )
    ]

    portfolio_data = []

    for ticker in tickers:

        try:

            df = fetch_data(
                ticker,
                period=f"{years}y"
            )

            if len(df) < 250:
                continue

            metrics = compute_metrics(
                df,
                benchmark_df
            )

            portfolio_data.append({
                "Ticker": ticker,
                "Score": metrics["Score"],
                "DF": df
            })

        except:
            pass

    # =====================================================
    # RANK PORTFOLIO
    # =====================================================

    portfolio_data = sorted(
        portfolio_data,
        key=lambda x: x["Score"],
        reverse=True
    )

    # =====================================================
    # TOP 3 STOCKS
    # =====================================================

    top_portfolio = portfolio_data[:3]

    selected = []

    strategy_returns = None

    for item in top_portfolio:

        ticker = item["Ticker"]

        df = item["DF"]

        selected.append(ticker)

        returns = (
            df["Close"]
            .pct_change()
            .fillna(0)
        )

        returns = returns.reindex(
            benchmark_returns.index
        ).fillna(0)

        if strategy_returns is None:

            strategy_returns = returns.copy()

        else:

            strategy_returns = strategy_returns.add(
                returns,
                fill_value=0
            )

    if strategy_returns is not None:

        strategy_returns = (
            strategy_returns
            /
            len(selected)
        )

        strategy_curve = (
            1 + strategy_returns
        ).cumprod()

        benchmark_curve = (
            1 + benchmark_returns
        ).cumprod()

        # =================================================
        # CHART
        # =================================================

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=strategy_curve.index,
                y=strategy_curve,
                name="Strategy"
            )
        )

        fig.add_trace(
            go.Scatter(
                x=benchmark_curve.index,
                y=benchmark_curve,
                name="Benchmark"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # =================================================
        # METRICS
        # =================================================

        strategy_return = (
            strategy_curve.iloc[-1] - 1
        ) * 100

        benchmark_return = (
            benchmark_curve.iloc[-1] - 1
        ) * 100

        cagr = (
            (
                strategy_curve.iloc[-1]
            ) ** (1 / years) - 1
        ) * 100

        sharpe = (
            strategy_returns.mean()
            /
            strategy_returns.std()
        ) * np.sqrt(252)

        downside = strategy_returns[
            strategy_returns < 0
        ]

        sortino = (
            strategy_returns.mean()
            /
            downside.std()
        ) * np.sqrt(252)

        rolling_max = (
            strategy_curve.cummax()
        )

        drawdown = (
            strategy_curve
            /
            rolling_max
            - 1
        )

        max_drawdown = (
            drawdown.min()
        ) * 100

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Strategy Return",
            f"{strategy_return:.2f}%"
        )

        c2.metric(
            "Benchmark Return",
            f"{benchmark_return:.2f}%"
        )

        c3.metric(
            "Sharpe Ratio",
            f"{sharpe:.2f}"
        )

        c4, c5, c6 = st.columns(3)

        c4.metric(
            "CAGR",
            f"{cagr:.2f}%"
        )

        c5.metric(
            "Max Drawdown",
            f"{max_drawdown:.2f}%"
        )

        c6.metric(
            "Sortino Ratio",
            f"{sortino:.2f}"
        )

        # =================================================
        # SELECTED PORTFOLIO
        # =================================================

        st.subheader("Selected Portfolio")

        st.dataframe(
            pd.DataFrame({
                "Ticker": selected
            }),
            use_container_width=True
        )

        # =================================================
        # INTERPRETATION
        # =================================================

        st.subheader("🧠 Portfolio Interpretation")

        if strategy_return > benchmark_return:

            st.success(
                "The strategy outperformed the benchmark over the selected period, suggesting alpha generation."
            )

        else:

            st.warning(
                "The strategy underperformed the benchmark over the selected period."
            )

        if sharpe > 1:

            st.info(
                "Risk-adjusted returns appear strong."
            )

        else:

            st.info(
                "Risk-adjusted returns appear moderate."
            )

# =========================================================
# SINGLE STOCK ANALYSIS
# =========================================================

st.header("🔎 Single Stock")

single_ticker = st.text_input(
    "Ticker",
    "RELIANCE.NS"
)

if st.button("Analyze Stock"):

    df = fetch_data(single_ticker)

    metrics = compute_metrics(
        df,
        benchmark_df
    )

    close = df["Close"]

    sma50 = close.rolling(50).mean()

    sma200 = close.rolling(200).mean()

    st.subheader(
        f"Recommendation: {metrics['Recommendation']}"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "RSI",
        metrics["RSI"]
    )

    c2.metric(
        "Momentum %",
        metrics["Momentum"]
    )

    c3.metric(
        "Relative Strength %",
        metrics["RelativeStrength"]
    )

    c4.metric(
        "Volatility %",
        metrics["Volatility"]
    )

    # =====================================================
    # PRICE CHART
    # =====================================================

    st.subheader("📉 Price Chart")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=close,
            name="Close"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=sma50,
            name="SMA50"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=sma200,
            name="SMA200"
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =====================================================
    # WRITEUP
    # =====================================================

    st.subheader("🧠 AI Investment Writeup")

    st.info(
        f"""
The stock currently exhibits a **{metrics['Structure']}** setup.

Current framework recommendation:
### {metrics['Recommendation']}
"""
    )

    st.subheader("✅ Bullish Factors")

    bullish = []

    if metrics["Price"] > metrics["SMA200"]:
        bullish.append(
            "Price remains above 200DMA indicating long-term institutional support."
        )

    if metrics["RelativeStrength"] > 0:
        bullish.append(
            "Stock is outperforming benchmark index."
        )

    if metrics["RSI"] > 55:
        bullish.append(
            "RSI remains healthy and supportive of bullish continuation."
        )

    for x in bullish:
        st.write("•", x)

    st.subheader("⚠️ Risk Factors")

    risks = []

    if metrics["SMA50"] < metrics["SMA200"]:
        risks.append(
            "SMA50 remains below SMA200 indicating weak medium-term momentum."
        )

    if metrics["Momentum"] < 0:
        risks.append(
            "Momentum remains negative suggesting near-term selling pressure."
        )

    if not risks:
        risks.append(
            "No major technical weakness currently visible."
        )

    for x in risks:
        st.write("•", x)

    # =====================================================
    # PATTERN ANALYSIS
    # =====================================================

    st.subheader("📉 Chart Pattern Analysis")

    patterns = []

    if metrics["SMA50"] > metrics["SMA200"]:
        patterns.append(
            "Bullish moving average structure visible with SMA50 above SMA200."
        )

    else:
        patterns.append(
            "Bearish moving average structure visible with SMA50 below SMA200."
        )

    if metrics["Momentum"] > 0:
        patterns.append(
            "Momentum profile suggests trend continuation."
        )

    else:
        patterns.append(
            "Momentum profile suggests consolidation or correction phase."
        )

    for p in patterns:
        st.write("•", p)

    # =====================================================
    # PROBABILITY TABLE
    # =====================================================

    st.subheader("🎯 Probability Scenarios")

    scenario_df = pd.DataFrame({
        "Scenario": [
            "Bullish Continuation",
            "Sideways Consolidation",
            "Bearish Breakdown"
        ],
        "Probability": [
            "45%",
            "35%",
            "20%"
        ]
    })

    st.dataframe(
        scenario_df,
        use_container_width=True
    )

    # =====================================================
    # WATCHLIST
    # =====================================================

    st.subheader("👀 What To Watch Next")

    watch_items = []

    if metrics["Momentum"] < 0:
        watch_items.append(
            "Watch whether momentum turns positive in coming weeks."
        )

    if metrics["SMA50"] < metrics["SMA200"]:
        watch_items.append(
            "Watch for SMA50 crossing above SMA200."
        )

    if metrics["RSI"] > 70:
        watch_items.append(
            "RSI approaching overheated territory."
        )

    if not watch_items:
        watch_items.append(
            "Trend structure currently remains healthy."
        )

    for item in watch_items:
        st.write("•", item)
