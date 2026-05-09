import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="AI Equity Research Platform V13", layout="wide")

st.title("🚀 AI Equity Research Platform V13")

# =========================
# INPUTS
# =========================

mode = st.sidebar.radio(
    "Select Mode",
    ["📊 Screener", "🔍 Single Stock", "📈 Portfolio Backtest"]
)

tickers_input = st.sidebar.text_area(
    "Enter Tickers (.NS format)",
    value="RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"
)

benchmark = st.sidebar.selectbox(
    "Benchmark",
    ["^NSEI", "^BSESN"],
    format_func=lambda x: "Nifty 50" if x == "^NSEI" else "Sensex"
)

backtest_years = st.sidebar.slider(
    "Backtest Years",
    1,
    10,
    5
)

tickers = [x.strip().upper() for x in tickers_input.split(",") if x.strip()]

# =========================
# HELPERS
# =========================

@st.cache_data
def load_data(ticker, period="10y"):

    df = yf.download(
        ticker,
        period=period,
        auto_adjust=True,
        progress=False
    )

    if df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()

    return df


def compute_metrics(df, benchmark_df):

    df = df.copy()

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()

    delta = df["Close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    df["RSI"] = 100 - (100 / (1 + rs))

    df["Momentum"] = (
        (df["Close"] / df["Close"].shift(20)) - 1
    ) * 100

    df["Volatility"] = (
        df["Close"].pct_change().rolling(20).std()
    ) * 100

    stock_return = (
        df["Close"].pct_change().fillna(0)
    )

    benchmark_return = (
        benchmark_df["Close"].pct_change().fillna(0)
    )

    benchmark_return = benchmark_return.reindex(
        stock_return.index
    ).fillna(0)

    rel_strength = (
        (
            (1 + stock_return).cumprod().iloc[-1]
            /
            (1 + benchmark_return).cumprod().iloc[-1]
        ) - 1
    ) * 100

    latest = df.iloc[-1]

    score = 0

    if latest["Close"] > latest["SMA200"]:
        score += 30

    if latest["SMA50"] > latest["SMA200"]:
        score += 20

    if latest["Momentum"] > 0:
        score += 20

    if rel_strength > 0:
        score += 20

    if latest["RSI"] > 50:
        score += 10

    if score >= 70:
        recommendation = "BUY"

    elif score >= 50:
        recommendation = "HOLD"

    else:
        recommendation = "AVOID"

    return {
        "Price": round(float(latest["Close"]), 2),
        "SMA50": round(float(latest["SMA50"]), 2),
        "SMA200": round(float(latest["SMA200"]), 2),
        "RSI": round(float(latest["RSI"]), 2),
        "Momentum": round(float(latest["Momentum"]), 2),
        "Volatility": round(float(latest["Volatility"]), 2),
        "RelStrength": round(float(rel_strength), 2),
        "Score": score,
        "Recommendation": recommendation,
        "Data": df
    }


def generate_thesis(metrics, ticker):

    bull_points = []
    bear_points = []

    if metrics["Price"] > metrics["SMA200"]:

        bull_points.append(
            f"{ticker} is trading above its 200-day average, which generally signals a healthy long-term uptrend."
        )

    else:

        bear_points.append(
            f"{ticker} is trading below its 200-day average, which can indicate long-term weakness."
        )

    if metrics["SMA50"] > metrics["SMA200"]:

        bull_points.append(
            "The 50-day moving average remains above the 200-day moving average, suggesting medium-term trend strength."
        )

    else:

        bear_points.append(
            "The 50-day moving average remains below the 200-day moving average, indicating weaker recent momentum."
        )

    if metrics["Momentum"] > 8:

        bull_points.append(
            "Recent price momentum remains strong, meaning buyers continue pushing the stock higher."
        )

    elif metrics["Momentum"] > 0:

        bull_points.append(
            "Momentum remains positive, although not aggressively bullish."
        )

    else:

        bear_points.append(
            "Recent momentum has weakened in the short term."
        )

    if metrics["RelStrength"] > 5:

        bull_points.append(
            "The stock is outperforming the benchmark index, which often signals institutional buying interest."
        )

    elif metrics["RelStrength"] > 0:

        bull_points.append(
            "The stock is slightly outperforming the broader market."
        )

    else:

        bear_points.append(
            "The stock is underperforming the broader market."
        )

    if metrics["RSI"] >= 55 and metrics["RSI"] <= 70:

        bull_points.append(
            "RSI remains healthy, indicating bullish momentum without entering overheated territory."
        )

    elif metrics["RSI"] > 75:

        bear_points.append(
            "RSI appears elevated, meaning the stock may be overbought short term."
        )

    elif metrics["RSI"] < 40:

        bear_points.append(
            "Weak RSI suggests buyers currently lack conviction."
        )

    score = metrics["Score"]

    if score >= 70:

        summary = (
            "Overall, the stock shows strong technical strength, healthy momentum, and market outperformance."
        )

    elif score >= 50:

        summary = (
            "The stock shows mixed signals. Some indicators remain constructive, but conviction is moderate."
        )

    else:

        summary = (
            "Current technical indicators remain weak and risk-reward does not appear attractive."
        )

    return bull_points, bear_points, summary


def recommendation_emoji(rec):

    if rec == "BUY":
        return "🟢"

    elif rec == "HOLD":
        return "🟡"

    else:
        return "🔴"


# =========================
# LOAD BENCHMARK
# =========================

benchmark_df = load_data(benchmark)

# =========================
# SCREENER MODE
# =========================

if mode == "📊 Screener":

    st.header("📊 Screener")

    if st.button("Run Screener"):

        rows = []

        for ticker in tickers:

            try:

                df = load_data(ticker)

                if len(df) < 250:
                    continue

                metrics = compute_metrics(df, benchmark_df)

                thesis = []

                if metrics["Price"] > metrics["SMA200"]:
                    thesis.append("Above 200DMA")
                else:
                    thesis.append("Below 200DMA")

                if metrics["Momentum"] > 0:
                    thesis.append("Strong momentum")
                else:
                    thesis.append("Weak momentum")

                if metrics["RelStrength"] > 0:
                    thesis.append("Outperforming benchmark")
                else:
                    thesis.append("Underperforming benchmark")

                rows.append({
                    "Ticker": ticker,
                    "Price": metrics["Price"],
                    "Score": metrics["Score"],
                    "Recommendation":
                        recommendation_emoji(metrics["Recommendation"])
                        + " "
                        + metrics["Recommendation"],
                    "RSI": metrics["RSI"],
                    "Momentum %": metrics["Momentum"],
                    "Rel Strength %": metrics["RelStrength"],
                    "Volatility %": metrics["Volatility"],
                    "Thesis": " | ".join(thesis)
                })

            except:
                continue

        screener_df = pd.DataFrame(rows)

        if not screener_df.empty:

            screener_df = screener_df.sort_values(
                by="Score",
                ascending=False
            )

            st.dataframe(
                screener_df,
                use_container_width=True
            )

        else:

            st.warning("No valid stocks found.")

# =========================
# SINGLE STOCK MODE
# =========================

elif mode == "🔍 Single Stock":

    st.header("🔍 Single Stock")

    ticker = tickers[0]

    if st.button("Analyze Stock"):

        df = load_data(ticker)

        if len(df) < 250:

            st.error("Not enough data.")

        else:

            metrics = compute_metrics(df, benchmark_df)

            thesis, risks, summary = generate_thesis(
                metrics,
                ticker
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Price",
                metrics["Price"]
            )

            col2.metric(
                "RSI",
                metrics["RSI"],
                help="""
RSI = Relative Strength Index

Measures momentum on a scale of 0-100.

- Above 70 = potentially overbought
- Below 30 = potentially oversold
- 50-70 = healthy bullish momentum
"""
            )

            col3.metric(
                "Momentum %",
                metrics["Momentum"],
                help="""
Measures price strength over recent weeks.

Positive momentum usually means buyers are in control.
"""
            )

            col4.metric(
                "Relative Strength %",
                metrics["RelStrength"],
                help="""
Compares stock performance against benchmark index.

Positive = outperforming market
Negative = underperforming market
"""
            )

            st.markdown(
                f"## Recommendation: {recommendation_emoji(metrics['Recommendation'])} {metrics['Recommendation']}"
            )

            st.markdown("### 📈 Price Chart")

            chart_df = metrics["Data"].copy()

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=chart_df.index,
                    y=chart_df["Close"],
                    name="Close"
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=chart_df.index,
                    y=chart_df["SMA50"],
                    name="SMA50"
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=chart_df.index,
                    y=chart_df["SMA200"],
                    name="SMA200"
                )
            )

            fig.update_layout(
                height=500,
                xaxis_title="Date",
                yaxis_title="Price"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.markdown(
                """
### ℹ️ Moving Average Guide

- SMA50 = Average price over last 50 trading days  
  → Tracks short/medium-term trend

- SMA200 = Average price over last 200 trading days  
  → Tracks long-term trend

Institutional investors often use these levels to judge trend strength.
"""
            )

            st.markdown("## 🧠 AI Investment Writeup")

            st.info(summary)

            st.markdown("### ✅ Bullish Factors")

            for item in thesis:
                st.write(f"- {item}")

            st.markdown("### ⚠️ Risk Factors")

            if len(risks) == 0:
                st.write("- No major technical risks currently visible.")

            else:
                for item in risks:
                    st.write(f"- {item}")

# =========================
# BACKTEST MODE
# =========================

elif mode == "📈 Portfolio Backtest":

    st.header("📈 Portfolio Backtest")

    if st.button("Run Portfolio Backtest"):

        portfolio_returns = []

        selected = []

        for ticker in tickers:

            try:

                df = load_data(
                    ticker,
                    period=f"{backtest_years}y"
                )

                if len(df) < 250:
                    continue

                metrics = compute_metrics(df, benchmark_df)

                if metrics["Score"] >= 10:

                    selected.append({
                        "Ticker": ticker,
                        "Score": metrics["Score"]
                    })

                    returns = (
                        df["Close"].pct_change().fillna(0)
                    )

                    portfolio_returns.append(returns)

            except:
                continue

        if len(portfolio_returns) == 0:

            st.error("No valid portfolio generated.")

        else:

            portfolio_df = pd.concat(
                portfolio_returns,
                axis=1
            )

            strategy_curve = (
                (1 + portfolio_df.mean(axis=1)).cumprod()
            )

            benchmark_backtest = load_data(
                benchmark,
                period=f"{backtest_years}y"
            )

            benchmark_curve = (
                1 +
                benchmark_backtest["Close"].pct_change().fillna(0)
            ).cumprod()

            strategy_return = (
                strategy_curve.iloc[-1] - 1
            ) * 100

            benchmark_return = (
                benchmark_curve.iloc[-1] - 1
            ) * 100

            years = backtest_years

            cagr = (
                (
                    strategy_curve.iloc[-1]
                ) ** (1 / years) - 1
            ) * 100

            running_max = strategy_curve.cummax()

            drawdown = (
                strategy_curve / running_max - 1
            )

            max_drawdown = drawdown.min() * 100

            sharpe = (
                portfolio_df.mean(axis=1).mean()
                /
                portfolio_df.mean(axis=1).std()
            ) * np.sqrt(252)

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
                    name="Nifty 50"
                )
            )

            fig.update_layout(
                height=500
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            c1, c2, c3, c4, c5 = st.columns(5)

            c1.metric(
                "Strategy Return",
                f"{strategy_return:.2f}%"
            )

            c2.metric(
                "Benchmark Return",
                f"{benchmark_return:.2f}%"
            )

            c3.metric(
                "CAGR",
                f"{cagr:.2f}%",
                help="""
Compound Annual Growth Rate

Shows average yearly return over the backtest period.
"""
            )

            c4.metric(
                "Max Drawdown",
                f"{max_drawdown:.2f}%",
                help="""
Largest peak-to-bottom portfolio decline.

Measures downside risk.
"""
            )

            c5.metric(
                "Sharpe Ratio",
                round(sharpe, 2),
                help="""
Risk-adjusted return metric.

Higher Sharpe Ratio generally indicates better consistency.
"""
            )

            st.markdown("## Selected Portfolio")

            selected_df = pd.DataFrame(selected)

            st.dataframe(
                selected_df,
                use_container_width=True
            )
