"""Backtest engine.

Timing: weights are decided with data up to the close of a rebalance date and
earn returns starting the NEXT trading day (no lookahead).
Weights drift with prices between rebalances; trading cost is charged on the
actual turnover (target weights vs drifted weights). Unallocated weight is
held in cash earning the risk-free rate.
"""
import numpy as np
import pandas as pd

from . import config


def month_end_dates(index):
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby([index.year, index.month]).max().values)


def run_backtest(prices, target_weights, cost_bps=config.COST_BPS,
                 rf=config.RISK_FREE_RATE):
    """Returns (net daily returns, turnover charged on each rebalance day)."""
    rets = prices.pct_change().fillna(0.0)
    idx = rets.index
    tw = target_weights.sort_index().reindex(columns=prices.columns,
                                             fill_value=0.0)
    invested = tw.sum(axis=1) > 0
    if invested.any():
        tw = tw.loc[invested.idxmax():]          # drop leading all-cash rows
    dates = list(tw.index)
    pos = idx.get_indexer(dates)
    rf_d = (1 + rf) ** (1 / config.TRADING_DAYS) - 1

    pieces, turnover = [], {}
    w_prev = pd.Series(0.0, index=prices.columns)
    for k, (d, p) in enumerate(zip(dates, pos)):
        start = p + 1
        end = pos[k + 1] if k + 1 < len(pos) else len(idx) - 1
        if start > end:
            continue
        w0 = tw.loc[d]
        seg = rets.iloc[start:end + 1]
        stock_val = (1 + seg).cumprod().mul(w0, axis=1)
        cash_val = max(0.0, 1 - w0.sum()) * (1 + rf_d) ** np.arange(1, len(seg) + 1)
        pv = stock_val.sum(axis=1) + cash_val
        r = pv.pct_change()
        r.iloc[0] = pv.iloc[0] - 1.0
        trade = (w0 - w_prev).abs().sum()
        r.iloc[0] -= trade * cost_bps / 1e4
        turnover[seg.index[0]] = trade
        w_prev = stock_val.iloc[-1] / pv.iloc[-1]   # drifted weights
        pieces.append(r)
    return pd.concat(pieces), pd.Series(turnover)


def equal_weight_all(prices):
    """Monthly rebalanced equal weight of every stock that has a price."""
    dates = month_end_dates(prices.index)
    avail = prices.loc[dates].notna().astype(float)
    return avail.div(avail.sum(axis=1), axis=0).fillna(0.0)
