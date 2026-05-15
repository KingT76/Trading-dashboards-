import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from strategy import run_backtest, fetch_historical_data, get_live_positions, get_account_info

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="APEX Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom dark theme CSS
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .win { color: #3fb950; }
    .loss { color: #f85149; }
    .neutral { color: #8b949e; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

st.sidebar.image("https://img.icons8.com/color/96/combo-chart.png", width=60)
st.sidebar.title("APEX Trading")
st.sidebar.markdown("---")

page = st.sidebar.radio("Navigation", [
    "📊 Backtest",
    "🔴 Live Positions",
    "📈 Metrics",
    "⚙️ Settings"
])

st.sidebar.markdown("---")
st.sidebar.subheader("Strategy Parameters")
symbol = st.sidebar.text_input("Symbol", value="AAPL")
fast_ma = st.sidebar.slider("Fast MA Period", 5, 50, 10)
slow_ma = st.sidebar.slider("Slow MA Period", 20, 200, 50)
initial_capital = st.sidebar.number_input("Starting Capital ($)", value=10000, step=1000)

col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start", value=datetime.now() - timedelta(days=365))
end_date = col2.date_input("End", value=datetime.now())

run_btn = st.sidebar.button("▶ Run Backtest", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("Built by APEX System")

# ─────────────────────────────────────────────
# STATE MANAGEMENT
# ─────────────────────────────────────────────

if "backtest_run" not in st.session_state:
    st.session_state.backtest_run = False
    st.session_state.df = None
    st.session_state.trade_log = None
    st.session_state.metrics = None

# ─────────────────────────────────────────────
# PAGE: BACKTEST
# ─────────────────────────────────────────────

if page == "📊 Backtest":
    st.title("📊 Backtest Engine")
    st.caption(f"Strategy: MA Crossover ({fast_ma}/{slow_ma}) | Symbol: {symbol}")

    if run_btn:
        with st.spinner("Fetching data and running backtest..."):
            try:
                df_raw = fetch_historical_data(
                    symbol,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
                df, trade_log, metrics = run_backtest(df_raw, fast_ma, slow_ma, initial_capital)
                st.session_state.df = df
                st.session_state.trade_log = trade_log
                st.session_state.metrics = metrics
                st.session_state.backtest_run = True
            except Exception as e:
                st.error(f"Error: {e}")

    if st.session_state.backtest_run:
        m = st.session_state.metrics
        df = st.session_state.df
        trade_log = st.session_state.trade_log

        # Metric Cards
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total Return", f"{m['total_return']}%",
                  delta=f"{m['total_return']}%")
        c2.metric("Win Rate", f"{m['win_rate']}%")
        c3.metric("Sharpe Ratio", f"{m['sharpe_ratio']}")
        c4.metric("Max Drawdown", f"{m['max_drawdown']}%")
        c5.metric("Total Trades", f"{m['total_trades']}")
        c6.metric("Final Equity", f"${m['final_equity']:,.2f}")

        st.markdown("---")

        # Equity Curve Chart
        st.subheader("Equity Curve")
        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(
            x=df.index,
            y=df["equity"],
            mode="lines",
            name="Portfolio Value",
            line=dict(color="#3fb950", width=2),
            fill="tozeroy",
            fillcolor="rgba(63,185,80,0.1)"
        ))
        fig_equity.update_layout(
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
            font=dict(color="#e6edf3"),
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(gridcolor="#21262d", title="Portfolio Value ($)"),
            height=350,
            margin=dict(l=0, r=0, t=20, b=0)
        )
        st.plotly_chart(fig_equity, use_container_width=True)

        # Price + MA Chart
        st.subheader("Price & Moving Averages")
        fig_price = go.Figure()
        fig_price.add_trace(go.Candlestick(
            x=df.index,
            open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            name="Price",
            increasing_line_color="#3fb950",
            decreasing_line_color="#f85149"
        ))
        fig_price.add_trace(go.Scatter(
            x=df.index, y=df["fast_ma"],
            name=f"Fast MA ({fast_ma})",
            line=dict(color="#58a6ff", width=1.5)
        ))
        fig_price.add_trace(go.Scatter(
            x=df.index, y=df["slow_ma"],
            name=f"Slow MA ({slow_ma})",
            line=dict(color="#f0883e", width=1.5)
        ))
        fig_price.update_layout(
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
            font=dict(color="#e6edf3"),
            xaxis=dict(gridcolor="#21262d", rangeslider=dict(visible=False)),
            yaxis=dict(gridcolor="#21262d"),
            height=350,
            margin=dict(l=0, r=0, t=20, b=0)
        )
        st.plotly_chart(fig_price, use_container_width=True)

        # Trade Log
        st.subheader("Trade Log")
        if not trade_log.empty:
            def color_result(val):
                color = "#3fb950" if val == "WIN" else "#f85149"
                return f"color: {color}"

            styled = trade_log.style.applymap(color_result, subset=["result"])
            st.dataframe(styled, use_container_width=True, height=300)
        else:
            st.info("No completed trades in the selected period.")

    else:
        st.info("👈 Configure your strategy in the sidebar and click **Run Backtest**")

# ─────────────────────────────────────────────
# PAGE: LIVE POSITIONS
# ─────────────────────────────────────────────

elif page == "🔴 Live Positions":
    st.title("🔴 Live Positions")
    st.caption("Connected to Alpaca Paper Trading")

    auto_refresh = st.toggle("Auto-refresh every 30s", value=True)

    # Account Summary
    try:
        account = get_account_info()
        a1, a2, a3 = st.columns(3)
        a1.metric("Portfolio Equity", f"${account['equity']:,.2f}")
        a2.metric("Cash Available", f"${account['cash']:,.2f}")
        a3.metric("Buying Power", f"${account['buying_power']:,.2f}")
    except Exception as e:
        st.warning(f"Could not load account info: {e}")

    st.markdown("---")

    # Positions Table
    st.subheader("Open Positions")
    try:
        positions = get_live_positions()
        if not positions.empty:
            def color_pl(val):
                try:
                    return "color: #3fb950" if float(val) >= 0 else "color: #f85149"
                except:
                    return ""

            styled_pos = positions.style\
                .applymap(color_pl, subset=["unrealized_pl", "unrealized_plpc"])
            st.dataframe(styled_pos, use_container_width=True)
        else:
            st.info("No open positions.")
    except Exception as e:
        st.error(f"Error loading positions: {e}")

    # Auto refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()

# ─────────────────────────────────────────────
# PAGE: METRICS
# ─────────────────────────────────────────────

elif page == "📈 Metrics":
    st.title("📈 Performance Metrics")

    if not st.session_state.backtest_run:
        st.info("Run a backtest first to see detailed metrics.")
    else:
        m = st.session_state.metrics
        df = st.session_state.df
        trade_log = st.session_state.trade_log

        # Win/Loss Breakdown
        st.subheader("Win / Loss Breakdown")
        if not trade_log.empty:
            wins = len(trade_log[trade_log["result"] == "WIN"])
            losses = len(trade_log[trade_log["result"] == "LOSS"])
            fig_pie = go.Figure(go.Pie(
                labels=["Wins", "Losses"],
                values=[wins, losses],
                marker_colors=["#3fb950", "#f85149"],
                hole=0.4
            ))
            fig_pie.update_layout(
                paper_bgcolor="#0d1117",
                font=dict(color="#e6edf3"),
                height=300
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # Monthly Returns Heatmap Data
        st.subheader("Monthly Returns")
        df["month"] = df.index.to_series().dt.strftime("%Y-%m")
        monthly = df.groupby("month")["strategy_return"].sum() * 100
        monthly_df = monthly.reset_index()
        monthly_df.columns = ["Month", "Return (%)"]

        fig_bar = go.Figure(go.Bar(
            x=monthly_df["Month"],
            y=monthly_df["Return (%)"],
            marker_color=monthly_df["Return (%)"].apply(
                lambda x: "#3fb950" if x >= 0 else "#f85149"
            )
        ))
        fig_bar.update_layout(
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
            font=dict(color="#e6edf3"),
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(gridcolor="#21262d", title="Return (%)"),
            height=300,
            margin=dict(l=0, r=0, t=20, b=0)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Drawdown Chart
        st.subheader("Drawdown Over Time")
        rolling_max = df["equity"].cummax()
        drawdown_series = (df["equity"] - rolling_max) / rolling_max * 100
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(
            x=df.index,
            y=drawdown_series,
            fill="tozeroy",
            fillcolor="rgba(248,81,73,0.15)",
            line=dict(color="#f85149", width=1.5),
            name="Drawdown"
        ))
        fig_dd.update_layout(
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
            font=dict(color="#e6edf3"),
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(gridcolor="#21262d", title="Drawdown (%)"),
            height=250,
            margin=dict(l=0, r=0, t=20, b=0)
        )
        st.plotly_chart(fig_dd, use_container_width=True)

# ─────────────────────────────────────────────
# PAGE: SETTINGS
# ─────────────────────────────────────────────

elif page == "⚙️ Settings":
    st.title("⚙️ Settings")
    st.subheader("API Configuration")

    st.info("""
    **How to add your Alpaca API keys:**

    1. Go to **railway.app** → Your Project → **Variables** tab
    2. Add these two variables:
       - `ALPACA_API_KEY` → paste your key
       - `ALPACA_SECRET_KEY` → paste your secret
    3. Railway auto-redeploys with new variables

    Your keys are stored securely and never shown in the dashboard.
    """)

    st.subheader("Strategy Info")
    st.markdown("""
    **Current Strategy: Moving Average Crossover**

    - **Entry:** Fast MA crosses above Slow MA → BUY
    - **Exit:** Fast MA crosses below Slow MA → SELL
    - **Data Source:** Alpaca Markets (paper trading)
    - **Supported Symbols:** Any US stock (AAPL, TSLA, SPY, QQQ, etc.)

    **To add a new strategy:**
    Edit `strategy.py` on GitHub → push → Railway auto-redeploys in ~60 seconds.
    """)
