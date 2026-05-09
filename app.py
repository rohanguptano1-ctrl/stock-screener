import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# ---------------- PAGE CONFIG ---------------- #

st.set_page_config(
    page_title="AI Equity Research Platform V14",
    layout="wide"
)

# ---------------- TITLE ---------------- #

st.title("🚀 AI Equity Research Platform V14")

# ---------------- SIDEBAR ---------------- #

st.sidebar.header("Controls")

mode = st.sidebar.radio(
    "Select Mode",
    ["📊 Screener", "🔍 Single Stock", "📈 Portfolio Backtest"]
)

tickers_input = st.sidebar.text_input(
    "Enter Tickers",
    "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS"
)

benchmark = st.sidebar.selectbox(
    "Benchmark",
    ["^NSEI", "^BSESN"]
)

years = st.sidebar.slider(
    "Backtest Years",
    1,
    10,
    5
)

# ---------------- DATA LOADER ---------------- #

@st.cache_data
def load_data(ticker, years=5):

    df = yf.download(
        ticker,
        period=f"{years}y",
        auto_adjust=True,
        progress=False
    )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()

    return df

# ---------------- METRICS ENGINE ---------------- #

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

    latest = df.iloc[-1]

    price = float(latest["Close"])
    sma50 = float(latest["SMA50"])
    sma200 = float(latest["SMA200"])
    rsi = float(latest["RSI"])

    momentum = (
        (
            price /
            float(df["Close"].iloc[-60])
        ) - 1
    ) * 100

    stock_return = (
        (
            price /
            float(df["Close"].iloc[0])
        ) - 1
    ) * 100

    benchmark_return = (
        (
            float(benchmark_df["Close"].iloc[-1]) /
            float(benchmark_df["Close"].iloc[0])
        ) - 1
    ) * 100

    rel_strength = stock_return - benchmark_return

    volatility = (
        df["Close"].pct_change().std()
        * np.sqrt(252)
        * 100
    )

    score = 0

    thesis = []

    # ---------------- TREND ---------------- #

    if price > sma200:
        score += 30
        thesis.append("Above 200DMA")
    else:
        thesis.append("Below 200DMA")

    # ---------------- SMA STRUCTURE ---------------- #

    if sma50 > sma200:
        score += 20
        thesis.append("Bullish SMA structure")
    else:
        thesis.append("Weak SMA structure")

    # ---------------- MOMENTUM ---------------- #

    if momentum > 5:
        score += 20
        thesis.append("Strong momentum")

    elif momentum > 0:
        score += 10
        thesis.append("Positive momentum")

    else:
        thesis.append("Weak momentum")

    # ---------------- RELATIVE STRENGTH ---------------- #

    if rel_strength > 0:
        score += 20
        thesis.append("Outperforming benchmark")

    else:
        thesis.append("Underperforming benchmark")

    # ---------------- RSI ---------------- #

    if 45 <= rsi <= 70:
        score += 10
        thesis.append("Healthy RSI")

    elif rsi > 70:
        thesis.append("Overbought RSI")

    else:
        thesis.append("Weak RSI")

    # ---------------- RECOMMENDATION ---------------- #

    if score >= 80:
        recommendation = "🟢 Strong Buy"

    elif score >= 60:
        recommendation = "🟢 Buy"

    elif score >= 40:
        recommendation = "🟡 Hold"

    elif score >= 20:
        recommendation = "🟠 Weak"

    else:
        recommendation = "🔴 Avoid"

    return {
        "Price": round(price, 2),
        "Score": score,
        "Recommendation": recommendation,
        "RSI": round(rsi, 2),
        "Momentum %": round(momentum, 2),
        "Relative Strength %": round(rel_strength, 2),
        "Volatility %": round(volatility, 2),
        "Thesis": " | ".join(thesis),
        "SMA50": round(sma50, 2),
        "SMA200": round(sma200, 2)
    }

# ---------------- AI WRITEUP ---------------- #

def generate_ai_writeup(metrics, ticker):

    bullish = []
    risks = []

    # ---------------- TREND ---------------- #

    if "Above 200DMA" in metrics["Thesis"]:

        bullish.append(
            f"{ticker} is trading above its 200-day moving average, which typically signals strong long-term institutional trend support."
        )

    else:

        risks.append(
            "The stock remains below its long-term moving average, indicating weak broader trend structure."
        )

    # ---------------- SMA STRUCTURE ---------------- #

    if "Bullish SMA structure" in metrics["Thesis"]:

        bullish.append(
            "The 50DMA remains above the 200DMA, indicating sustained medium-term bullish momentum."
        )

    else:

        risks.append(
            "The 50DMA remains below the 200DMA, suggesting recent momentum remains weak."
        )

    # ---------------- MOMENTUM ---------------- #

    if metrics["Momentum %"] > 5:

        bullish.append(
            "Recent momentum remains strong, indicating buyers continue to control price action."
        )

    elif metrics["Momentum %"] > 0:

        bullish.append(
            "Momentum remains mildly positive."
        )

    else:

        risks.append(
            "Momentum remains negative, which may indicate continued selling pressure."
        )

    # ---------------- RELATIVE STRENGTH ---------------- #

    if metrics["Relative Strength %"] > 0:

        bullish.append(
            "The stock is outperforming the benchmark index, often indicating institutional accumulation."
        )

    else:

        risks.append(
            "The stock continues to underperform the benchmark index."
        )

    # ---------------- RSI ---------------- #

    if 45 <= metrics["RSI"] <= 70:

        bullish.append(
            "RSI remains healthy without entering overheated territory."
        )

    elif metrics["RSI"] > 70:

        risks.append(
            "RSI is entering overbought territory, which may increase short-term correction risk."
        )

    else:

        risks.append(
            "RSI remains weak, reflecting lack of bullish momentum."
        )

    overall = (
        "Overall, the stock currently demonstrates favorable technical structure and improving trend characteristics."
    )

    return overall, bullish, risks

# ---------------- SCREENER ---------------- #

if mode == "📊 Screener":

    st.header("📊 Screener")

    if st.button("Run Screener"):

        tickers = [
            t.strip().upper()
            for t in tickers_input.split(",")
        ]

        benchmark_df = load_data(
            benchmark,
            years
        )

        results = []

        for ticker in tickers:

            try:

                df = load_data(
                    ticker,
                    years
                )

                if len(df) < 250:
                    continue

                metrics = compute_metrics(
                    df,
                    benchmark_df
                )

                results.append({
                    "Ticker": ticker,
                    **metrics
                })

            except:
                pass

        screener_df = pd.DataFrame(results)

        if not screener_df.empty:

            screener_df = screener_df.sort_values(
                by="Score",
                ascending=False
            )

            st.dataframe(
                screener_df,
                use_container_width=True
            )

# ---------------- SINGLE STOCK ---------------- #

elif mode == "🔍 Single Stock":

    st.header("🔍 Single Stock")

    ticker = (
        tickers_input
        .split(",")[0]
        .strip()
        .upper()
    )

    if st.button("Analyze Stock"):

        df = load_data(
            ticker,
            years
        )

        benchmark_df = load_data(
            benchmark,
            years
        )

        metrics = compute_metrics(
            df,
            benchmark_df
        )

        st.subheader(
            f"Recommendation: {metrics['Recommendation']}"
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "Price",
                metrics["Price"]
            )

        with col2:

            st.metric(
                "RSI",
                metrics["RSI"]
            )

            st.caption(
                "RSI measures momentum strength. 45-70 is generally considered healthy."
            )

        with col3:

            st.metric(
                "Momentum %",
                metrics["Momentum %"]
            )

            st.caption(
                "Measures recent price acceleration over last 3 months."
            )

        with col4:

            st.metric(
                "Relative Strength %",
                metrics["Relative Strength %"]
            )

            st.caption(
                "Measures stock outperformance vs benchmark index."
            )

        st.markdown("---")

        st.subheader("📉 Price Chart")

        chart_df = df.copy()

        chart_df["SMA50"] = (
            chart_df["Close"]
            .rolling(50)
            .mean()
        )

        chart_df["SMA200"] = (
            chart_df["Close"]
            .rolling(200)
            .mean()
        )

        st.line_chart(
            chart_df[
                ["Close", "SMA50", "SMA200"]
            ]
        )

        st.markdown("---")

        st.subheader("ℹ️ Moving Average Guide")

        st.markdown("""
        - **SMA50** = Average stock price over last 50 trading days  
          → Tracks short/medium-term trend

        - **SMA200** = Average stock price over last 200 trading days  
          → Tracks long-term trend

        Institutional investors often use these levels to judge trend strength and market structure.
        """)

        st.markdown("---")

        st.subheader("🧠 AI Investment Writeup")

        overall, bullish, risks = generate_ai_writeup(
            metrics,
            ticker
        )

        st.info(overall)

        st.markdown("### ✅ Bullish Factors")

        for item in bullish:

            st.markdown(
                f"- {item}"
            )

        st.markdown("### ⚠️ Risk Factors")

        if len(risks) == 0:

            st.success(
                "No major technical weakness visible currently."
            )

        for item in risks:

            st.markdown(
                f"- {item}"
            )

# ---------------- BACKTEST ---------------- #

elif mode == "📈 Portfolio Backtest":

    st.header("📈 Portfolio Backtest")

    if st.button("Run Portfolio Backtest"):

        tickers = [
            t.strip().upper()
            for t in tickers_input.split(",")
        ]

        benchmark_df = load_data(
            benchmark,
            years
        )

        selected = []

        for ticker in tickers:

            try:

                df = load_data(
                    ticker,
                    years
                )

                if len(df) < 250:
                    continue

                metrics = compute_metrics(
                    df,
                    benchmark_df
                )

                if metrics["Score"] >= 60:

                    selected.append(ticker)

            except:
                pass

        if len(selected) == 0:

            st.warning(
                "No qualifying portfolio generated."
            )

            st.stop()

        strategy_returns = pd.DataFrame()

        for ticker in selected:

            df = load_data(
                ticker,
                years
            )

            strategy_returns[ticker] = (
                df["Close"]
                .pct_change()
            )

        strategy_returns = (
            strategy_returns.mean(axis=1)
        )

        strategy_curve = (
            1 + strategy_returns
        ).cumprod()

        benchmark_returns = (
            benchmark_df["Close"]
            .pct_change()
        )

        benchmark_curve = (
            1 + benchmark_returns
        ).cumprod()

        chart_df = pd.DataFrame({
            "Strategy": strategy_curve,
            "Benchmark": benchmark_curve
        })

        st.line_chart(chart_df)

        strategy_total_return = (
            strategy_curve.iloc[-1] - 1
        ) * 100

        benchmark_total_return = (
            benchmark_curve.iloc[-1] - 1
        ) * 100

        cagr = (
            (
                strategy_curve.iloc[-1]
            ) ** (1 / years) - 1
        ) * 100

        running_max = (
            strategy_curve.cummax()
        )

        drawdown = (
            strategy_curve / running_max
        ) - 1

        max_drawdown = (
            drawdown.min()
        ) * 100

        sharpe = (
            strategy_returns.mean() /
            strategy_returns.std()
        ) * np.sqrt(252)

        downside_std = (
            strategy_returns[
                strategy_returns < 0
            ].std()
        )

        sortino = (
            strategy_returns.mean() /
            downside_std
        ) * np.sqrt(252)

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Strategy Return",
                f"{strategy_total_return:.2f}%"
            )

            st.metric(
                "CAGR",
                f"{cagr:.2f}%"
            )

        with col2:

            st.metric(
                "Benchmark Return",
                f"{benchmark_total_return:.2f}%"
            )

            st.metric(
                "Max Drawdown",
                f"{max_drawdown:.2f}%"
            )

        with col3:

            st.metric(
                "Sharpe Ratio",
                f"{sharpe:.2f}"
            )

            st.metric(
                "Sortino Ratio",
                f"{sortino:.2f}"
            )

        st.markdown("---")

        st.subheader("Selected Portfolio")

        portfolio_df = pd.DataFrame({
            "Ticker": selected
        })

        st.dataframe(
            portfolio_df,
            use_container_width=True
        )
