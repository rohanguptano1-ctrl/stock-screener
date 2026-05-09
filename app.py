# app.py

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(
    page_title="AI Equity Research Platform V15",
    layout="wide"
)

# =========================================================
# HELPERS
# =========================================================

def fetch_data(ticker, period="5y"):
    df = yf.download(ticker, period=period, auto_adjust=True)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()

    return df


def calculate_rsi(series, period=14):
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi


def compute_metrics(df, benchmark_df):

    df = df.copy()

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()

    df["RSI"] = calculate_rsi(df["Close"])

    df["Momentum"] = (
        (df["Close"] / df["Close"].shift(60)) - 1
    ) * 100

    benchmark_return = (
        benchmark_df["Close"].pct_change().rolling(60).sum()
    )

    stock_return = (
        df["Close"].pct_change().rolling(60).sum()
    )

    df["RelativeStrength"] = (
        (stock_return - benchmark_return) * 100
    )

    df["Volatility"] = (
        df["Close"].pct_change().rolling(20).std()
    ) * np.sqrt(252) * 100

    latest = df.iloc[-1]

    price = float(latest["Close"])
    sma50 = float(latest["SMA50"])
    sma200 = float(latest["SMA200"])
    rsi = float(latest["RSI"])
    momentum = float(latest["Momentum"])
    rs = float(latest["RelativeStrength"])
    volatility = float(latest["Volatility"])

    # =====================================================
    # WEIGHTED SCORING MODEL
    # =====================================================

    score = 0

    # Market Structure
    if price > sma200:
        score += 40

    # SMA Trend Structure
    if sma50 > sma200:
        score += 20

    # Momentum
    if momentum > 5:
        score += 20
    elif momentum > 0:
        score += 10

    # Relative Strength
    if rs > 5:
        score += 10
    elif rs > 0:
        score += 5

    # RSI Confirmation
    if 45 <= rsi <= 70:
        score += 10

    # =====================================================
    # RECOMMENDATION ENGINE
    # =====================================================

    if score >= 70:
        recommendation = "🟢 Strong Buy"
    elif score >= 50:
        recommendation = "🟢 Buy"
    elif score >= 35:
        recommendation = "🟡 Watchlist"
    else:
        recommendation = "🔴 Avoid"

    # =====================================================
    # MARKET STRUCTURE
    # =====================================================

    if price > sma200 and sma50 > sma200:
        structure = "Strong Bullish Trend"
    elif price > sma200:
        structure = "Early Accumulation"
    elif price < sma200 and momentum > 0:
        structure = "Weak Recovery"
    else:
        structure = "Bearish Structure"

    return {
        "Price": round(price, 2),
        "SMA50": round(sma50, 2),
        "SMA200": round(sma200, 2),
        "RSI": round(rsi, 2),
        "Momentum": round(momentum, 2),
        "RelativeStrength": round(rs, 2),
        "Volatility": round(volatility, 2),
        "Score": score,
        "Recommendation": recommendation,
        "Structure": structure,
        "Data": df
    }


def generate_writeup(ticker, metrics):

    bullish = []
    risks = []

    if metrics["Price"] > metrics["SMA200"]:
        bullish.append(
            f"{ticker} continues to trade above its 200-day moving average, suggesting long-term institutional trend support remains intact."
        )
    else:
        risks.append(
            f"{ticker} remains below its 200-day moving average, indicating long-term market structure remains weak."
        )

    if metrics["SMA50"] > metrics["SMA200"]:
        bullish.append(
            "The shorter-term moving average remains above the long-term trend line, supporting continued bullish momentum."
        )
    else:
        risks.append(
            "The 50-day moving average remains below the 200-day average, indicating recent momentum remains fragile."
        )

    if metrics["Momentum"] > 5:
        bullish.append(
            "Price momentum remains strong, suggesting buyers continue to accumulate positions."
        )
    elif metrics["Momentum"] > 0:
        bullish.append(
            "Momentum remains positive, although upside acceleration has moderated."
        )
    else:
        risks.append(
            "Momentum has turned negative, which may indicate near-term selling pressure."
        )

    if metrics["RelativeStrength"] > 0:
        bullish.append(
            "The stock continues to outperform the benchmark index, often a sign of underlying institutional demand."
        )
    else:
        risks.append(
            "The stock is underperforming the benchmark index, reflecting weaker relative market participation."
        )

    if 45 <= metrics["RSI"] <= 70:
        bullish.append(
            "RSI remains in a healthy range, supporting bullish continuation without extreme overheating."
        )
    elif metrics["RSI"] > 75:
        risks.append(
            "RSI is entering overheated territory, increasing probability of short-term consolidation."
        )

    summary = f"""
The stock currently exhibits a **{metrics["Structure"]}** setup.

Overall technical structure suggests that institutional positioning remains
{'constructive' if metrics["Score"] >= 50 else 'cautious'}.

Current recommendation framework classifies the stock as:
**{metrics["Recommendation"]}**
"""

    return summary, bullish, risks


# =========================================================
# UI
# =========================================================

st.title("🚀 AI Equity Research Platform V15")

mode = st.sidebar.radio(
    "Select Mode",
    [
        "Screener",
        "Single Stock",
        "Portfolio Backtest"
    ]
)

benchmark = st.sidebar.selectbox(
    "Benchmark",
    ["^NSEI"]
)

benchmark_df = fetch_data(benchmark)

# =========================================================
# SCREENER
# =========================================================

if mode == "Screener":

    st.header("📊 Screener")

    tickers_input = st.text_input(
        "Enter Tickers",
        "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"
    )

    tickers = [
        x.strip()
        for x in tickers_input.split(",")
    ]

    if st.button("Run Screener"):

        results = []

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

# =========================================================
# SINGLE STOCK
# =========================================================

elif mode == "Single Stock":

    st.header("🔎 Single Stock")

    ticker = st.text_input(
        "Ticker",
        "RELIANCE.NS"
    )

    if st.button("Analyze Stock"):

        df = fetch_data(ticker)

        metrics = compute_metrics(df, benchmark_df)

        summary, bullish, risks = generate_writeup(
            ticker,
            metrics
        )

        # =================================================
        # RECOMMENDATION
        # =================================================

        st.subheader(
            f"Recommendation: {metrics['Recommendation']}"
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "RSI",
                metrics["RSI"],
                help="RSI measures momentum strength. 45-70 is typically considered healthy."
            )

        with col2:
            st.metric(
                "Momentum %",
                metrics["Momentum"],
                help="Measures price acceleration over recent months."
            )

        with col3:
            st.metric(
                "Relative Strength %",
                metrics["RelativeStrength"],
                help="Measures stock performance relative to benchmark."
            )

        with col4:
            st.metric(
                "Volatility %",
                metrics["Volatility"],
                help="Higher volatility implies larger price swings and higher risk."
            )

        # =================================================
        # PRICE CHART
        # =================================================

        st.markdown("---")

        st.subheader("📉 Price Chart")

        chart_df = metrics["Data"].copy()

        st.line_chart(
            chart_df[
                [
                    "Close",
                    "SMA50",
                    "SMA200"
                ]
            ]
        )

        # =================================================
        # SMA GUIDE
        # =================================================

        st.markdown("---")

        st.subheader("ℹ️ Moving Average Guide")

        st.markdown("""
- **SMA50** = Average stock price over last 50 trading days  
  → Tracks short/medium-term trend

- **SMA200** = Average stock price over last 200 trading days  
  → Tracks long-term trend

Institutional investors often use these levels to judge market structure and trend strength.
""")

        # =================================================
        # AI WRITEUP
        # =================================================

        st.markdown("---")

        st.subheader("🧠 AI Investment Writeup")

        st.info(summary)

        st.markdown("## ✅ Bullish Factors")

        for point in bullish:
            st.markdown(f"- {point}")

        st.markdown("## ⚠️ Risk Factors")

        if len(risks) == 0:
            st.markdown(
                "- No major technical risk factors currently detected."
            )

        for point in risks:
            st.markdown(f"- {point}")

# =========================================================
# PORTFOLIO BACKTEST
# =========================================================

elif mode == "Portfolio Backtest":

    st.header("📈 Portfolio Backtest")

    tickers_input = st.text_input(
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
            for x in tickers_input.split(",")
        ]

        selected = []

        for ticker in tickers:

            try:

                df = fetch_data(
                    ticker,
                    period=f"{years}y"
                )

                metrics = compute_metrics(
                    df,
                    benchmark_df
                )

                if metrics["Score"] >= 50:

                    returns = (
                        df["Close"].pct_change()
                    )

                    selected.append(returns)

            except:
                pass

        if len(selected) > 0:

            strategy_returns = pd.concat(
                selected,
                axis=1
            ).mean(axis=1)

            strategy_curve = (
                1 + strategy_returns.fillna(0)
            ).cumprod()

            benchmark_returns = (
                benchmark_df["Close"].pct_change()
            )

            benchmark_curve = (
                1 + benchmark_returns.fillna(0)
            ).cumprod()

            chart_df = pd.DataFrame({
                "Strategy": strategy_curve,
                "Benchmark": benchmark_curve
            }).dropna()

            st.line_chart(chart_df)

            strategy_total = (
                strategy_curve.iloc[-1] - 1
            ) * 100

            benchmark_total = (
                benchmark_curve.iloc[-1] - 1
            ) * 100

            sharpe = (
                strategy_returns.mean()
                / strategy_returns.std()
            ) * np.sqrt(252)

            drawdown = (
                strategy_curve
                / strategy_curve.cummax()
                - 1
            ).min() * 100

            cagr = (
                (
                    strategy_curve.iloc[-1]
                ) ** (1 / years) - 1
            ) * 100

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Strategy Return",
                    f"{strategy_total:.2f}%"
                )

            with col2:
                st.metric(
                    "Benchmark Return",
                    f"{benchmark_total:.2f}%"
                )

            with col3:
                st.metric(
                    "Sharpe Ratio",
                    round(sharpe, 2),
                    help="Measures risk-adjusted returns. Higher is better."
                )

            with col4:
                st.metric(
                    "Max Drawdown",
                    f"{drawdown:.2f}%",
                    help="Largest historical portfolio decline."
                )

            st.metric(
                "CAGR",
                f"{cagr:.2f}%",
                help="Annualized compounded growth rate."
            )

        else:

            st.warning(
                "No qualifying stocks passed the scoring filter."
            )
