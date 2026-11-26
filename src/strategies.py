"""Turn a signal (score table) into target weights on monthly rebalance dates."""
import pandas as pd

from . import config, portfolio
from .backtest import month_end_dates


def weights_from_score(prices, score, top_n=config.TOP_N, method="equal",
                       eligible=None, cov_window=config.COV_WINDOW,
                       max_w=config.MAX_WEIGHT):
    rets = prices.pct_change()
    dates = month_end_dates(prices.index)
    W = pd.DataFrame(0.0, index=dates, columns=prices.columns)
    for d in dates:
        s = score.loc[d].dropna()
        if eligible is not None:
            ok = eligible.loc[d].reindex(s.index).fillna(0) > 0
            s = s[ok]
        if len(s) < min(top_n, 5):
            continue                      # not enough candidates: stay in cash
        sel = s.nlargest(top_n).index
        if method == "equal":
            w = pd.Series(1.0 / len(sel), index=sel)
        else:
            win = rets.loc[:d].tail(cov_window)[sel]
            good = win.columns[win.isna().mean() < 0.05]
            if len(good) < 5:
                w = pd.Series(1.0 / len(sel), index=sel)
            else:
                w = portfolio.optimize(method, win[good].fillna(0.0), max_w)
        W.loc[d, w.index] = w.values
    return W
