import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

def fetch_historical_data(symbol, start_date, end_date, timeframe="1Day"):
    """
    Fetches historical OHLCV data from Alpaca.
    Returns a pandas DataFrame.
    """
    import alpaca_trade_api as tradeapi
    import os

    api_key = os.getenv("ALPACA_API_KEY", "")
    api_secret = os.getenv("ALPACA_SECRET_KEY", "")
    base_url = "https://paper-api.alpaca.markets"

    if not api_key:
        # Return sample data if no API key set yet
        dates = pd.date_range(start=start_date, end=end_date, freq="B")
        np.random.seed(42)
        price = 100 + np.cumsum(np.random.randn(len(dates)) * 2)
        df = pd.DataFrame({
            "open": price * 0.99,
            "high": price * 1.02,
            "low": price * 0.98,
            "close": price,
            "volume": np.random.randint(1000000, 5000000, len(dates))
        }, index=dates)
        return df

    api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')
    bars = api.get_bars(symbol, timeframe, start=start_date, end=end_date).df
    return bars


# ─────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────

def add_indicators(df, fast_ma=10, slow_ma=50, rsi_period=14):
    """Adds moving averages and RSI to the dataframe."""
    df = df.copy()
    df["fast_ma"] = df["close"].rolling(fast_ma).mean()
    df["slow_ma"] = df["close"].rolling(slow_ma).mean()

    # RSI calculation
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(rsi_period).mean()
    loss = (-delta.clip(upper=0)).rolling(rsi_period).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    return df


# ─────────────────────────────────────────────
# BACKTEST ENGINE
# ─────────────────────────────────────────────

def run_backtest(df, fast_ma=10, slow_ma=50, initial_capital=10000):
    """
    Runs a moving average crossover backtest.
    Returns a dict of metrics and the trade log.
    """
    df = add_indicators(df, fast_ma, slow_ma)
    df = df.dropna()

    # Generate signals: 1 = buy, -1 = sell
    df["signal"] = 0
    df.loc[df["fast_ma"] > df["slow_ma"], "signal"] = 1
    df.loc[df["fast_ma"] < df["slow_ma"], "signal"] = -1

    # Detect crossovers
    df["position"] = df["signal"].diff()

    # Calculate returns
    df["strategy_return"] = df["signal"].shift(1) * df["close"].pct_change()
    df["equity"] = initial_capital * (1 + df["strategy_return"]).cumprod()

    # Trade log
    trades = []
    position = None
    entry_price = 0
    entry_date = None

    for date, row in df.iterrows():
        if row["position"] == 2 and position is None:   # Buy signal
            position = "LONG"
            entry_price = row["close"]
            entry_date = date
        elif row["position"] == -2 and position == "LONG":  # Sell signal
            exit_price = row["close"]
            pnl = exit_price - entry_price
            pnl_pct = (pnl / entry_price) * 100
            trades.append({
                "entry_date": entry_date,
                "exit_date": date,
                "entry_price": round(entry_price, 2),
                "exit_price": round(exit_price, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "result": "WIN" if pnl > 0 else "LOSS"
            })
            position = None

    trade_log = pd.DataFrame(trades)

    # Metrics
    returns = df["strategy_return"].dropna()
    total_return = ((df["equity"].iloc[-1] / initial_capital) - 1) * 100
    win_rate = (len(trade_log[trade_log["result"] == "WIN"]) / len(trade_log) * 100) if len(trade_log) > 0 else 0

    # Sharpe ratio (annualized)
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

    # Max drawdown
    rolling_max = df["equity"].cummax()
    drawdown = (df["equity"] - rolling_max) / rolling_max * 100
    max_drawdown = drawdown.min()

    metrics = {
        "total_return": round(total_return, 2),
        "win_rate": round(win_rate, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_drawdown, 2),
        "total_trades": len(trade_log),
        "final_equity": round(df["equity"].iloc[-1], 2),
    }

    return df, trade_log, metrics


# ─────────────────────────────────────────────
# LIVE TRADING
# ─────────────────────────────────────────────

def get_live_positions():
    """Returns current open positions from Alpaca."""
    import alpaca_trade_api as tradeapi
    import os

    api_key = os.getenv("ALPACA_API_KEY", "")
    api_secret = os.getenv("ALPACA_SECRET_KEY", "")
    base_url = "https://paper-api.alpaca.markets"

    if not api_key:
        return pd.DataFrame([{
            "symbol": "DEMO",
            "qty": 10,
            "avg_entry_price": 150.00,
            "current_price": 155.50,
            "unrealized_pl": 55.00,
            "unrealized_plpc": 3.33
        }])

    api = tradeapi.REST(api_key, api_secret, base_url)
    positions = api.list_positions()

    if not positions:
        return pd.DataFrame()

    data = [{
        "symbol": p.symbol,
        "qty": float(p.qty),
        "avg_entry_price": float(p.avg_entry_price),
        "current_price": float(p.current_price),
        "unrealized_pl": round(float(p.unrealized_pl), 2),
        "unrealized_plpc": round(float(p.unrealized_plpc) * 100, 2)
    } for p in positions]

    return pd.DataFrame(data)


def get_account_info():
    """Returns account cash, equity, and buying power."""
    import alpaca_trade_api as tradeapi
    import os

    api_key = os.getenv("ALPACA_API_KEY", "")
    api_secret = os.getenv("ALPACA_SECRET_KEY", "")
    base_url = "https://paper-api.alpaca.markets"

    if not api_key:
        return {"equity": 10000.00, "cash": 7500.00, "buying_power": 15000.00}

    api = tradeapi.REST(api_key, api_secret, base_url)
    account = api.get_account()

    return {
        "equity": round(float(account.equity), 2),
        "cash": round(float(account.cash), 2),
        "buying_power": round(float(account.buying_power), 2)
  }
