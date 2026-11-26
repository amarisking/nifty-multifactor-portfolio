"""Cross-sectional signals. Higher score = more attractive. Each score at
date t uses only prices up to and including t."""
import numpy as np
import pandas as pd

from . import config


def momentum(prices, lookback=config.LOOKBACK_DAYS, skip=config.SKIP_DAYS):
    """Return from t-lookback to t-skip (skips the most recent month)."""
    return prices.shift(skip) / prices.shift(lookback) - 1


def low_volatility(prices, window=126):
    """Negative trailing volatility: calmer stocks score higher."""
    r = prices.pct_change()
    return -r.rolling(window, min_periods=int(window * 0.9)).std()


def reversal(prices, window=21):
    """Short-term reversal: last month's losers score higher."""
    return -(prices / prices.shift(window) - 1)


def trend_filter(prices, window=200):
    """1.0 where price is above its moving average (eligibility flag)."""
    ma = prices.rolling(window, min_periods=window).mean()
    return (prices > ma).astype(float)


def zscore(df):
    sd = df.std(axis=1).replace(0, np.nan)
    return df.sub(df.mean(axis=1), axis=0).div(sd, axis=0)


def composite(prices, weights=None):
    """Weighted sum of cross-sectional z-scores (momentum, low vol, reversal)."""
    weights = weights or config.FACTOR_WEIGHTS
    parts = {"mom": zscore(momentum(prices)),
             "lowvol": zscore(low_volatility(prices)),
             "rev": zscore(reversal(prices))}
    return sum(weights[k] * parts[k] for k in weights)
