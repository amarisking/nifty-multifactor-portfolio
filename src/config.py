"""Central settings. Change things here, not inside the code."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

START_DATE = "2014-01-01"
END_DATE = None  # None = today

# Approximate Nifty 50 list (Yahoo Finance tickers). Constituents change over
# time and some tickers get renamed or delisted, so verify this list.
# Using TODAY's constituents for a historical test causes SURVIVORSHIP BIAS.
TICKERS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT",
    "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO", "BAJFINANCE", "NESTLEIND",
    "WIPRO", "HCLTECH", "TECHM", "POWERGRID", "NTPC", "ONGC", "TATASTEEL",
    "JSWSTEEL", "M&M", "BAJAJFINSV", "ADANIPORTS", "COALINDIA", "DRREDDY",
    "CIPLA", "EICHERMOT", "GRASIM", "HEROMOTOCO", "HINDALCO", "INDUSINDBK",
    "BRITANNIA", "APOLLOHOSP", "DIVISLAB", "BPCL", "TATACONSUM", "SBILIFE",
    "HDFCLIFE", "BAJAJ-AUTO", "ADANIENT",
]
INDEX_TICKER = "^NSEI"        # Nifty 50 price index (no dividends)
BENCHMARK_ETF = "NIFTYBEES"   # Nifty 50 ETF: dividend-adjusted proxy for total return

# Backtest assumptions
RISK_FREE_RATE = 0.06
COST_BPS = 10            # one-way cost per unit of turnover (basis points)
TRADING_DAYS = 252

# Signals / portfolio
LOOKBACK_DAYS = 252
SKIP_DAYS = 21
TOP_N = 10               # names in single-factor portfolios
TOP_N_OPT = 20           # names in the multi-factor portfolios that get optimized
COV_WINDOW = 252         # days of history for covariance estimation
MAX_WEIGHT = 0.15        # position cap for constrained optimizers
FACTOR_WEIGHTS = {"mom": 0.5, "lowvol": 0.3, "rev": 0.2}

# Risk layer
VOL_TARGET = 0.15
DD_TRIGGER = 0.15
DD_RESET = 0.07
DD_EXPOSURE = 0.5
VAR_ALPHA = 0.05

# Approximate stress windows (verify dates against index data before quoting)
STRESS_WINDOWS = {
    "2018 Aug-Oct selloff": ("2018-08-28", "2018-10-26"),
    "COVID crash": ("2020-02-19", "2020-03-23"),
    "2021-22 rate-hike selloff": ("2021-10-19", "2022-06-17"),
    "2024-25 drawdown": ("2024-09-27", "2025-03-28"),
}
