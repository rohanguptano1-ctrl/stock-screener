# =========================================
# AI EQUITY RESEARCH PLATFORM V16.1
# FULL app.py
# Fixed Portfolio Backtest Button
# Added Institutional Pattern Analysis
# =========================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(layout="wide")

# =========================================
# TITLE
# =========================================

st.title("🚀 AI Equity Research Platform V16.1")

# =========================================
# DATA FETCH
# =========================================

@st.cache_data
def fetch_data(ticker, period="10y"):

    df = yf.download(
        ticker,
        period=period,
        auto_adjust=True,
        progress=False
    )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()

    return df


# =========================================
# RSI
# =========================================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi


# =========================================
# METRICS ENGINE
# =========================================

def compute_metrics(df, benchmark_df):

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()

    df["RSI"] = calculate_rsi(df["Close"])

    df["Momentum"] = (
        (df["Close"] / df["Close"].shift(63)) - 1
    ) * 100

    benchmark_return = (
        benchmark_df["Close"] / benchmark_df["Close"].iloc[0]
    )

    stock_return = (
        df["Close"] / df["Close"].iloc[0]
    )

    relative_strength = (
        (stock_return.iloc[-1] / benchmark_return.iloc[-1]) - 1
    ) * 100

    volatility = (
        df["Close"]
        .pct_change()
        .rolling(21)
        .std()
        .iloc[-1]
    ) * np.sqrt(252) * 100

    latest = df.iloc[-1]

    score = 0

    if latest["Close"] > latest["SMA200"]:
        score += 30

    if latest["SMA50"] > latest["SMA200"]:
        score += 20

    if latest["RSI"] > 55:
        score += 20

    if latest["Momentum"] > 0:
        score += 20

    if relative_strength > 0:
        score += 10

    # =====================================
    # RECOMMENDATION
    # =====================================

    if score >= 70:
        recommendation = "🟢 Buy"

    elif score >= 40:
        recommendation = "🟠 Watch"

    else:
        recommendation = "🔴 Avoid"

    # =====================================
    # STRUCTURE
    # =====================================

    if (
        latest["Close"] > latest["SMA200"]
        and latest["SMA50"] > latest["SMA200"]
    ):
        structure = "Bullish Trend Structure"

    elif (
        latest["Close"] > latest["SMA200"]
        and latest["SMA50"] < latest["SMA200"]
    ):
        structure = "Early Accumulation"

    elif (
        latest["Close"] < latest["SMA200"]
        and latest["SMA50"] < latest["SMA200"]
    ):
        structure = "Bearish Structure"

    else:
        structure = "Sideways Consolidation"

    return {
        "Price": round(latest["Close"], 2),
        "RSI": round(latest["RSI"], 2),
        "Momentum": round(latest["Momentum"], 2),
        "RelativeStrength": round(relative_strength, 2),
        "Volatility": round(volatility, 2),
        "Score": score,
        "Recommendation": recommendation,
        "Structure": structure,
        "SMA50": round(latest["SMA50"], 2),
        "SMA200": round(latest["SMA200"], 2),
    }


# =========================================
# CHART ANALYSIS
# =========================================

def generate_chart_analysis(metrics):

    points = []

    if metrics["Price"] > metrics["SMA200"]:

        points.append(
            "Price continues trading above the 200DMA, indicating the long-term institutional trend remains constructive."
        )

    else:

        points.append(
            "Price remains below the 200DMA, suggesting long-term structure remains weak."
        )

    if metrics["Momentum"] > 5:

        points.append(
            "Momentum expansion suggests buyers remain in control and trend continuation probability is improving."
        )

    elif metrics["Momentum"] > 0:

        points.append(
            "Momentum remains mildly positive, indicating gradual accumulation behavior."
        )

    else:

        points.append(
            "Negative momentum suggests near-term selling pressure is still present."
        )

    if metrics["RSI"] > 70:

        points.append(
            "RSI has entered overbought territory, increasing probability of near-term consolidation."
        )

    elif metrics["RSI"] > 55:

        points.append(
            "RSI remains in a healthy bullish range, supporting trend continuation."
        )

    else:

        points.append(
            "Weak RSI indicates momentum participation remains limited."
        )

    if metrics["RelativeStrength"] > 0:

        points.append(
            "The stock continues outperforming the benchmark index, often signaling institutional accumulation."
        )

    else:

        points.append(
            "Underperformance versus benchmark suggests capital rotation toward stronger sectors or names."
        )

    return points


# =========================================
# PATTERN ANALYSIS
# =========================================

def generate_pattern_analysis(metrics):

    patterns = []

    if metrics["SMA50"] > metrics["SMA200"]:

        patterns.append(
            "🟢 SMA50 remains above SMA200, reflecting bullish trend alignment often associated with sustained uptrends."
        )

    else:

        patterns.append(
            "🔴 SMA50 remains below SMA200, indicating recent momentum remains weaker than the long-term trend."
        )

    if metrics["Momentum"] > 10:

        patterns.append(
            "📈 Strong momentum expansion suggests the stock may be entering a breakout continuation phase."
        )

    elif metrics["Momentum"] > 0:

        patterns.append(
            "📊 Current setup resembles gradual accumulation rather than aggressive breakout behavior."
        )

    else:

        patterns.append(
            "⚠️ Price action currently reflects consolidation or corrective behavior."
        )

    return patterns


# =========================================
# PROBABILITY ENGINE
# =========================================

def generate_probability_view(metrics):

    bullish = 50
    sideways = 30
    bearish = 20

    if metrics["Recommendation"] == "🟢 Buy":
        bullish += 20

    if metrics["Momentum"] < 0:
        bearish += 10

    if metrics["RelativeStrength"] > 0:
        bullish += 10

    total = bullish + sideways + bearish

    bullish = round((bullish / total) * 100)
    sideways = round((sideways / total) * 100)
    bearish = round((bearish / total) * 100)

    return bullish, sideways, bearish


# =========================================
# SCREENER
# =========================================

st.header("📊 Screener")

ticker_input = st.text_input(
    "Enter Tickers",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"
)

if st.button("Run Screener"):

    benchmark_df = fetch_data("^NSEI")

    results = []

    tickers = [
        t.strip()
        for t in ticker_input.split(",")
    ]

    for ticker in tickers:

        try:

            df = fetch_data(ticker)

            metrics = compute_metrics(df, benchmark_df)

            results.append({
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

    screener_df = pd.DataFrame(results)

    screener_df = screener_df.sort_values(
        by="Score",
        ascending=False
    )

    st.dataframe(
        screener_df,
        use_container_width=True
    )


# =========================================
# SINGLE STOCK ANALYSIS
# =========================================

st.header("🔎 Single Stock")

ticker = st.text_input(
    "Ticker",
    "RELIANCE.NS"
)

if st.button("Analyze Stock"):

    benchmark_df = fetch_data("^NSEI")

    df = fetch_data(ticker)

    metrics = compute_metrics(df, benchmark_df)

    st.subheader(
        f"Recommendation: {metrics['Recommendation']}"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "RSI",
        metrics["RSI"],
        help="RSI measures momentum strength. 45-70 is generally considered healthy."
    )

    col2.metric(
        "Momentum %",
        metrics["Momentum"],
        help="Measures price acceleration over last 3 months."
    )

    col3.metric(
        "Relative Strength %",
        metrics["RelativeStrength"],
        help="Measures stock outperformance vs benchmark index."
    )

    col4.metric(
        "Volatility %",
        metrics["Volatility"],
        help="Measures annualized price fluctuations and risk."
    )

    st.divider()

    # =====================================
    # PRICE CHART
    # =====================================

    st.subheader("📉 Price Chart")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            name="Close"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA50"],
            name="SMA50"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SMA200"],
            name="SMA200"
        )
    )

    fig.update_layout(
        height=500,
        template="plotly_white"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =====================================
    # MOVING AVERAGE GUIDE
    # =====================================

    st.subheader("ℹ️ Moving Average Guide")

    st.markdown("""
- **SMA50** = Average stock price over last 50 trading days  
→ Tracks short/medium-term trend

- **SMA200** = Average stock price over last 200 trading days  
→ Tracks long-term trend

Institutional investors often use these levels to judge trend strength and market structure.
""")

    st.divider()

    # =====================================
    # PATTERN ANALYSIS
    # =====================================

    st.subheader("📈 Chart Pattern Analysis")

    patterns = generate_pattern_analysis(metrics)

    for p in patterns:
        st.markdown(f"- {p}")

    st.divider()

    # =====================================
    # WRITEUP
    # =====================================

    st.subheader("🧠 AI Investment Writeup")

    st.info(
        f"""
The stock currently exhibits a **{metrics['Structure']}** setup.

Overall technical structure suggests institutional positioning remains constructive.

Current recommendation framework classifies the stock as:
{metrics['Recommendation']}
"""
    )

    st.subheader("✅ Bullish Factors")

    bullish_points = generate_chart_analysis(metrics)

    for p in bullish_points:
        st.markdown(f"- {p}")

    # =====================================
    # PROBABILITY VIEW
    # =====================================

    st.subheader("🎯 Probability Scenarios")

    bullish_prob, sideways_prob, bearish_prob = generate_probability_view(metrics)

    prob_df = pd.DataFrame({
        "Scenario": [
            "Bullish Continuation",
            "Sideways Consolidation",
            "Bearish Breakdown"
        ],
        "Probability": [
            f"{bullish_prob}%",
            f"{sideways_prob}%",
            f"{bearish_prob}%"
        ]
    })

    st.dataframe(
        prob_df,
        use_container_width=True
    )

    # =====================================
    # WHAT TO WATCH
    # =====================================

    st.subheader("👀 What To Watch Next")

    watchlist = []

    if metrics["Momentum"] < 0:
        watchlist.append(
            "Watch whether momentum turns positive over coming weeks."
        )

    if metrics["SMA50"] < metrics["SMA200"]:
        watchlist.append(
            "Watch for SMA50 crossing above SMA200, which would strengthen bullish structure."
        )

    if metrics["RSI"] > 70:
        watchlist.append(
            "Monitor whether RSI cools off without significant price breakdown."
        )

    if metrics["RelativeStrength"] < 0:
        watchlist.append(
            "Watch whether relative strength improves versus benchmark index."
        )

    if len(watchlist) == 0:
        watchlist.append(
            "Current technical structure remains stable without immediate warning signals."
        )

    for item in watchlist:
        st.markdown(f"- {item}")


# =========================================
# PORTFOLIO BACKTEST
# =========================================

st.header("📉 Portfolio Backtest")

portfolio_input = st.text_input(
    "Portfolio Tickers",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS",
    key="portfolio_tickers"
)

years = st.slider(
    "Backtest Years",
    1,
    10,
    5,
    key="backtest_years"
)

run_backtest = st.button(
    "Run Portfolio Backtest",
    key="run_portfolio_backtest"
)

if run_backtest:

    with st.spinner("Running portfolio backtest..."):

        benchmark_df = fetch_data(
            "^NSEI",
            period=f"{years}y"
        )

        benchmark_returns = (
            benchmark_df["Close"]
            .pct_change()
            .fillna(0)
        )

        strategy_returns = None

        selected = []

        tickers = [
            t.strip()
            for t in portfolio_input.split(",")
        ]

        for ticker in tickers:

            try:

                df = fetch_data(
                    ticker,
                    period=f"{years}y"
                )

                if len(df) < 250:
                    continue

                metrics = compute_metrics(df, benchmark_df)

                if (
                    metrics["Recommendation"] == "🟢 Buy"
                    or metrics["Recommendation"] == "🟠 Watch"
                ):

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

            except:
                pass

        if len(selected) == 0:

            st.error(
                "No stocks qualified for portfolio construction."
            )

        else:

            strategy_returns = strategy_returns / len(selected)

            strategy_curve = (
                1 + strategy_returns
            ).cumprod()

            benchmark_curve = (
                1 + benchmark_returns
            ).cumprod()

            # =====================================
            # CHART
            # =====================================

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

            fig.update_layout(
                height=500,
                template="plotly_white"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            # =====================================
            # METRICS
            # =====================================

            strategy_total = (
                strategy_curve.iloc[-1] - 1
            ) * 100

            benchmark_total = (
                benchmark_curve.iloc[-1] - 1
            ) * 100

            cagr = (
                (
                    strategy_curve.iloc[-1]
                ) ** (1 / years) - 1
            ) * 100

            rolling_max = strategy_curve.cummax()

            drawdown = (
                strategy_curve / rolling_max - 1
            )

            max_drawdown = drawdown.min() * 100

            sharpe = (
                strategy_returns.mean()
                / strategy_returns.std()
            ) * np.sqrt(252)

            downside = strategy_returns[
                strategy_returns < 0
            ]

            if downside.std() != 0:

                sortino = (
                    strategy_returns.mean()
                    / downside.std()
                ) * np.sqrt(252)

            else:

                sortino = 0

            # =====================================
            # DISPLAY
            # =====================================

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Strategy Return",
                f"{strategy_total:.2f}%"
            )

            col2.metric(
                "Benchmark Return",
                f"{benchmark_total:.2f}%"
            )

            col3.metric(
                "Sharpe Ratio",
                round(sharpe, 2),
                help="Measures return generated per unit of risk."
            )

            col4, col5, col6 = st.columns(3)

            col4.metric(
                "CAGR",
                f"{cagr:.2f}%",
                help="Compounded annual growth rate."
            )

            col5.metric(
                "Max Drawdown",
                f"{max_drawdown:.2f}%",
                help="Largest peak-to-trough decline."
            )

            col6.metric(
                "Sortino Ratio",
                round(sortino, 2),
                help="Measures return relative to downside risk."
            )

            st.subheader("Selected Portfolio")

            selected_df = pd.DataFrame({
                "Ticker": selected
            })

            st.dataframe(
                selected_df,
                use_container_width=True
            )

            # =====================================
            # COMMENTARY
            # =====================================

            st.subheader("🧠 Portfolio Interpretation")

            if strategy_total > benchmark_total:

                st.success(
                    "The strategy outperformed the benchmark over the selected time period, suggesting the framework generated alpha."
                )

            else:

                st.warning(
                    "The strategy underperformed the benchmark, indicating current selection logic may require refinement."
                )

            if sharpe > 1:

                st.info(
                    "Risk-adjusted returns appear strong."
                )

            elif sharpe > 0.5:

                st.info(
                    "Risk-adjusted returns appear moderate."
                )

            else:

                st.info(
                    "Risk-adjusted returns remain relatively weak."
                )
