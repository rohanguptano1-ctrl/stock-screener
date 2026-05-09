# V12.5 AI Equity Research Platform (app.py)

```python
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="AI Equity Research Platform V12.5", layout="wide")

# =====================================================
# CONFIG
# =====================================================

BENCHMARKS = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "S&P 500": "^GSPC"
}

# =====================================================
# SIDEBAR
# =====================================================

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
    list(BENCHMARKS.keys())
)

years = st.sidebar.slider(
    "Years",
    1,
    10,
    3
)

top_n = st.sidebar.slider(
    "Top N Stocks",
    1,
    10,
    5
)

benchmark_ticker = BENCHMARKS[benchmark_name]

tickers = [
    x.strip().upper()
    for x in ticker_input.split(",")
    if x.strip()
]

st.title("🚀 AI Equity Research Platform V12.5")

# =====================================================
# TOOLTIP TEXT
# =====================================================

TOOLTIPS = {
    "RSI": "Relative Strength Index. Measures momentum. 50-70 is generally bullish.",
    "Momentum": "20-day price momentum percentage.",
    "Relative Strength": "Performance vs benchmark over recent period.",
    "Sharpe": "Risk-adjusted return metric. Higher is better.",
    "Drawdown": "Largest peak-to-trough decline.",
    "CAGR": "Compounded annual growth rate.",
    "Score": "Composite factor score based on trend, momentum, RSI and relative strength."
}

# =====================================================
# DATA FETCH
# =====================================================

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

        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df.dropna(inplace=True)

        if len(df) < 220:
            return None

        return df

    except:
        return None

# =====================================================
# FACTOR ENGINE
# =====================================================

def compute_factors(df, benchmark_df):

    try:

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

        df["Momentum20"] = (
            (df["Close"] / df["Close"].shift(20)) - 1
        ) * 100

        df["Returns"] = df["Close"].pct_change()

        volatility = (
            df["Returns"]
            .rolling(20)
            .std()
            .iloc[-1]
        )

        stock_return = (
            (df["Close"].iloc[-1] / df["Close"].iloc[-60]) - 1
        )

        benchmark_return = (
            (benchmark_df["Close"].iloc[-1] / benchmark_df["Close"].iloc[-60]) - 1
        )

        rel_strength = (stock_return - benchmark_return) * 100

        latest = df.iloc[-1]

        price = float(latest["Close"])
        sma50 = float(latest["SMA50"])
        sma200 = float(latest["SMA200"])
        rsi = float(latest["RSI"])
        momentum = float(latest["Momentum20"])

        score = 0

        if rel_strength > 10:
            score += 35
        elif rel_strength > 0:
            score += 20

        if price > sma200:
            score += 25

        if momentum > 10:
            score += 20
        elif momentum > 0:
            score += 10

        if 50 <= rsi <= 70:
            score += 10

        if volatility < 0.025:
            score += 10

        if score >= 70:
            recommendation = "🟢 BUY"
        elif score >= 50:
            recommendation = "🟡 HOLD"
        else:
            recommendation = "🔴 AVOID"

        return {
            "Price": round(price, 2),
            "SMA50": round(sma50, 2),
            "SMA200": round(sma200, 2),
            "RSI": round(rsi, 2),
            "Momentum": round(momentum, 2),
            "RelStrength": round(rel_strength, 2),
            "Volatility": round(volatility * 100, 2),
            "Score": score,
            "Recommendation": recommendation,
            "Returns": df["Returns"].fillna(0),
            "Data": df
        }

    except:
        return None

# =====================================================
# THESIS ENGINE
# =====================================================

def generate_thesis(metrics):

    thesis = []
    risks = []

    if metrics["Price"] > metrics["SMA200"]:
        thesis.append("Stock remains above 200DMA indicating long-term uptrend.")
    else:
        risks.append("Price below 200DMA indicates weak long-term trend.")

    if metrics["Momentum"] > 5:
        thesis.append("Momentum remains strong over recent sessions.")
    else:
        risks.append("Momentum remains weak.")

    if metrics["RelStrength"] > 0:
        thesis.append("Stock is outperforming benchmark.")
    else:
        risks.append("Stock underperforming benchmark.")

    if metrics["RSI"] > 70:
        risks.append("RSI indicates overbought conditions.")
    elif metrics["RSI"] < 40:
        risks.append("RSI remains weak.")
    else:
        thesis.append("RSI remains in healthy bullish zone.")

    return thesis, risks

# =====================================================
# BENCHMARK
# =====================================================

benchmark_df = fetch_data(benchmark_ticker, years)

if benchmark_df is None:
    st.error("Benchmark failed")
    st.stop()

# =====================================================
# SCREENER
# =====================================================

if mode == "📊 Screener":

    st.subheader("📊 Screener")

    if st.button("Run Screener"):

        rows = []

        for ticker in tickers:

            df = fetch_data(ticker, years)

            if df is None:
                continue

            metrics = compute_factors(df, benchmark_df)

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
                "Volatility %": metrics["Volatility"]
            })

        if len(rows) == 0:
            st.warning("No valid stocks")
        else:
            result_df = pd.DataFrame(rows)
            result_df = result_df.sort_values(by="Score", ascending=False)

            st.caption(TOOLTIPS["Score"])
            st.dataframe(result_df, use_container_width=True)

# =====================================================
# SINGLE STOCK
# =====================================================

elif mode == "🔍 Single Stock":

    st.subheader("🔍 Single Stock")

    if st.button("Analyze Stock"):

        ticker = tickers[0]

        df = fetch_data(ticker, years)

        if df is None:
            st.error("Invalid stock")
            st.stop()

        metrics = compute_factors(df, benchmark_df)

        if metrics is None:
            st.error("Factor computation failed")
            st.stop()

        thesis, risks = generate_thesis(metrics)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Price",
            metrics["Price"],
            help="Current stock price"
        )

        c2.metric(
            "RSI",
            metrics["RSI"],
            help=TOOLTIPS["RSI"]
        )

        c3.metric(
            "Momentum %",
            metrics["Momentum"],
            help=TOOLTIPS["Momentum"]
        )

        c4.metric(
            "Relative Strength %",
            metrics["RelStrength"],
            help=TOOLTIPS["Relative Strength"]
        )

        st.markdown(f"## Recommendation: {metrics['Recommendation']}")

        # CHART

        chart_df = metrics["Data"][["Close", "SMA50", "SMA200"]]

        st.subheader("📈 Price Chart")
        st.line_chart(chart_df)

        # CHART ANALYSIS

        st.subheader("🧠 Chart Analysis")

        chart_analysis = []

        if metrics["Price"] > metrics["SMA200"]:
            chart_analysis.append(
                "Price trading above 200DMA indicates long-term bullish structure."
            )

        if metrics["SMA50"] > metrics["SMA200"]:
            chart_analysis.append(
                "50DMA above 200DMA suggests positive trend continuation."
            )

        if metrics["Momentum"] > 5:
            chart_analysis.append(
                "Momentum expansion suggests institutional accumulation."
            )

        if metrics["RSI"] > 70:
            chart_analysis.append(
                "RSI entering overbought zone may indicate short-term consolidation risk."
            )

        for line in chart_analysis:
            st.write(f"- {line}")

        # THESIS

        st.subheader("📋 Investment Thesis")

        for item in thesis:
            st.write(f"✅ {item}")

        # RISKS

        st.subheader("⚠️ Risk Factors")

        for item in risks:
            st.write(f"⚠️ {item}")

# =====================================================
# BACKTEST
# =====================================================

elif mode == "📈 Portfolio Backtest":

    st.subheader("📈 Portfolio Backtest")

    if st.button("Run Portfolio Backtest"):

        benchmark_returns = (
            benchmark_df["Close"]
            .pct_change()
            .fillna(0)
        )

        benchmark_curve = (1 + benchmark_returns).cumprod()

        all_stock_returns = []

        for ticker in tickers:

            df = fetch_data(ticker, years)

            if df is None:
                continue

            metrics = compute_factors(df, benchmark_df)

            if metrics is None:
                continue

            all_stock_returns.append({
                "Ticker": ticker,
                "Score": metrics["Score"],
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
            [x["Returns"] for x in selected],
            axis=1
        ).mean(axis=1)

        strategy_returns = strategy_returns.fillna(0)

        strategy_curve = (1 + strategy_returns).cumprod()

        common_index = strategy_curve.index.intersection(
            benchmark_curve.index
        )

        strategy_curve = strategy_curve.loc[common_index]
        benchmark_curve = benchmark_curve.loc[common_index]

        st.line_chart(pd.DataFrame({
            "Strategy": strategy_curve,
            benchmark_name: benchmark_curve
        }))

        strategy_return = ((strategy_curve.iloc[-1] - 1) * 100)
        benchmark_return = ((benchmark_curve.iloc[-1] - 1) * 100)

        cagr = (
            (strategy_curve.iloc[-1]) ** (1 / years) - 1
        ) * 100

        drawdown = (
            strategy_curve / strategy_curve.cummax() - 1
        )

        max_drawdown = drawdown.min() * 100

        sharpe = (
            strategy_returns.mean()
            /
            strategy_returns.std()
        ) * np.sqrt(252)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Strategy Return",
            f"{strategy_return:.2f}%",
            help="Total portfolio return"
        )

        c2.metric(
            "Benchmark Return",
            f"{benchmark_return:.2f}%",
            help="Benchmark performance"
        )

        c3.metric(
            "CAGR",
            f"{cagr:.2f}%",
            help=TOOLTIPS["CAGR"]
        )

        c4.metric(
            "Sharpe Ratio",
            f"{sharpe:.2f}",
            help=TOOLTIPS["Sharpe"]
        )

        st.metric(
            "Max Drawdown",
            f"{max_drawdown:.2f}%",
            help=TOOLTIPS["Drawdown"]
        )

        selected_df = pd.DataFrame([
            {
                "Ticker": x["Ticker"],
                "Score": x["Score"]
            }
            for x in selected
        ])

        st.subheader("Selected Portfolio")
        st.dataframe(selected_df, use_container_width=True)
```
