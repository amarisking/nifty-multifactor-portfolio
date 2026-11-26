"""Robustness checks: parameter sensitivity, cost sensitivity, walk-forward
testing, and block-bootstrap confidence intervals for Sharpe ratios."""
import numpy as np
import pandas as pd

from . import config, metrics, signals, strategies
from .backtest import run_backtest


def momentum_returns_grid(prices, lookbacks, top_ns, cost_bps=config.COST_BPS):
    """Daily net returns for every (lookback, top_n) combination."""
    out = {}
    for lb in lookbacks:
        score = signals.momentum(prices, lb, config.SKIP_DAYS)
        for n in top_ns:
            W = strategies.weights_from_score(prices, score, top_n=n)
            out[f"{lb}d/top{n}"], _ = run_backtest(prices, W, cost_bps)
    return out


def sensitivity_tables(grid_returns, lookbacks, top_ns, start):
    sh = pd.DataFrame(index=[f"top{n}" for n in top_ns],
                      columns=[f"{lb}d" for lb in lookbacks], dtype=float)
    cg = sh.copy()
    for lb in lookbacks:
        for n in top_ns:
            r = grid_returns[f"{lb}d/top{n}"].loc[start:]
            sh.loc[f"top{n}", f"{lb}d"] = metrics.sharpe(r)
            cg.loc[f"top{n}", f"{lb}d"] = metrics.summary(r)["CAGR"]
    return sh, cg


def cost_sensitivity(prices, weights, costs=(0, 10, 20, 30, 50), start=None):
    rows = {}
    for c in costs:
        r, _ = run_backtest(prices, weights, c)
        r = r.loc[start:] if start is not None else r
        s = metrics.summary(r)
        rows[f"{c} bps"] = {"CAGR": s["CAGR"], "Sharpe": s["Sharpe"]}
    return pd.DataFrame(rows).T


def walk_forward(grid_returns, start, train_years=3, test_years=1):
    """Expanding-window walk-forward: pick the best (lookback, top_n) on the
    training data only, then trade it on the next unseen year."""
    df = pd.DataFrame(grid_returns).dropna().loc[start:]
    first, last = df.index[0], df.index[-1]
    test_start = first + pd.DateOffset(years=train_years)
    oos, picks = [], []
    while test_start < last:
        test_end = test_start + pd.DateOffset(years=test_years)
        train = df.loc[first:test_start - pd.Timedelta(days=1)]
        test = df.loc[test_start:test_end - pd.Timedelta(days=1)]
        if len(test) < 20:
            break
        score = train.mean() / train.std()
        best = score.idxmax()
        oos.append(test[best])
        picks.append({"Test period start": test_start.date(),
                      "Chosen params": best, "Train Sharpe (daily)": score.max()})
        test_start = test_end
    return pd.concat(oos), pd.DataFrame(picks)


def block_bootstrap_sharpe(df, benchmark_col, n_boot=2000, block=21, seed=0,
                           rf=config.RISK_FREE_RATE):
    """Circular block bootstrap of annualised Sharpe ratios (columns of df).
    Returns point estimate, 90% interval and P(Sharpe > benchmark)."""
    X = df.values
    T, k = X.shape
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(T / block))
    starts = rng.integers(0, T, size=(n_boot, n_blocks))
    idx = ((starts[:, :, None] + np.arange(block)) % T).reshape(n_boot, -1)[:, :T]
    rf_d = rf / config.TRADING_DAYS
    sims = np.empty((n_boot, k))
    for b in range(n_boot):
        s = X[idx[b]]
        sims[b] = (s.mean(axis=0) - rf_d) / s.std(axis=0) * np.sqrt(config.TRADING_DAYS)
    bi = list(df.columns).index(benchmark_col)
    rows = {}
    for j, c in enumerate(df.columns):
        rows[c] = {"Sharpe": metrics.sharpe(df[c]),
                   "5th pct": np.percentile(sims[:, j], 5),
                   "95th pct": np.percentile(sims[:, j], 95),
                   "P(Sharpe > benchmark)": float((sims[:, j] > sims[:, bi]).mean())
                   if c != benchmark_col else np.nan}
    return pd.DataFrame(rows).T
