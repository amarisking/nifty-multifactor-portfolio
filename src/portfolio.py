"""Portfolio construction: equal weight, min-variance, max-Sharpe,
risk parity and Hierarchical Risk Parity (HRP). All long-only, fully invested.
Covariance is estimated with Ledoit-Wolf shrinkage."""
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.optimize import minimize
from scipy.spatial.distance import squareform
from sklearn.covariance import LedoitWolf

from . import config


def shrunk_cov(window, periods=config.TRADING_DAYS):
    lw = LedoitWolf().fit(window.values)
    return pd.DataFrame(lw.covariance_ * periods, index=window.columns,
                        columns=window.columns)


def _finish(w, index):
    w = np.clip(np.asarray(w, float), 0, None)
    return pd.Series(w / w.sum(), index=index)


def _cap(n, max_w):
    return max(max_w, 1.2 / n)  # cap must allow a feasible solution


def min_variance(cov, max_w=config.MAX_WEIGHT):
    n, S = len(cov), cov.values
    res = minimize(lambda w: 100 * w @ S @ w, np.full(n, 1 / n),
                   jac=lambda w: 200 * S @ w, method="SLSQP",
                   bounds=[(0, _cap(n, max_w))] * n,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
                   options={"maxiter": 300})
    return _finish(res.x if res.success else np.full(n, 1 / n), cov.index)


def max_sharpe(cov, mu, rf=config.RISK_FREE_RATE, max_w=config.MAX_WEIGHT):
    """Mean-variance with expected returns shrunk 50% toward their average
    (raw historical means are far too noisy to optimize on)."""
    n, S = len(cov), cov.values
    m = 0.5 * mu.values + 0.5 * mu.values.mean()

    def neg_sharpe(w):
        return -(w @ m - rf) / np.sqrt(max(w @ S @ w, 1e-12))

    res = minimize(neg_sharpe, np.full(n, 1 / n), method="SLSQP",
                   bounds=[(0, _cap(n, max_w))] * n,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
                   options={"maxiter": 300})
    return _finish(res.x if res.success else np.full(n, 1 / n), cov.index)


def risk_parity(cov):
    """Equal risk contribution via the convex formulation
    min 0.5 w'Sw - (1/n) sum(log w)."""
    n, S = len(cov), cov.values
    f = lambda w: 0.5 * w @ S @ w - np.log(w).sum() / n
    g = lambda w: S @ w - 1 / (n * w)
    res = minimize(f, np.full(n, 1 / n), jac=g, method="L-BFGS-B",
                   bounds=[(1e-10, None)] * n)
    return _finish(res.x if res.success else np.full(n, 1 / n), cov.index)


def _quasi_diag(link):
    link = link.astype(int)
    order = [link[-1, 0], link[-1, 1]]
    n_items = link[-1, 3]
    while max(order) >= n_items:
        new = []
        for item in order:
            if item >= n_items:
                row = link[item - n_items]
                new += [row[0], row[1]]
            else:
                new.append(item)
        order = new
    return order


def _cluster_var(S, items):
    sub = S[np.ix_(items, items)]
    ivp = 1.0 / np.diag(sub)
    ivp /= ivp.sum()
    return ivp @ sub @ ivp


def hrp(cov):
    """Hierarchical Risk Parity (Lopez de Prado, 2016)."""
    S = cov.values
    sd = np.sqrt(np.diag(S))
    corr = np.clip(S / np.outer(sd, sd), -1, 1)
    dist = np.sqrt(0.5 * (1 - corr))
    np.fill_diagonal(dist, 0)
    order = _quasi_diag(linkage(squareform(dist, checks=False), "single"))
    w = np.ones(len(S))
    clusters = [order]
    while clusters:
        clusters = [c[a:b] for c in clusters
                    for a, b in ((0, len(c) // 2), (len(c) // 2, len(c)))
                    if len(c) > 1]
        for i in range(0, len(clusters), 2):
            c0, c1 = clusters[i], clusters[i + 1]
            v0, v1 = _cluster_var(S, c0), _cluster_var(S, c1)
            alpha = 1 - v0 / (v0 + v1)
            w[c0] *= alpha
            w[c1] *= 1 - alpha
    return _finish(w, cov.index)


def optimize(method, window, max_w=config.MAX_WEIGHT):
    """window: DataFrame of daily returns (no NaN). Returns weights Series."""
    n = window.shape[1]
    if method == "equal":
        return pd.Series(1.0 / n, index=window.columns)
    cov = shrunk_cov(window)
    if method == "minvar":
        return min_variance(cov, max_w)
    if method == "maxsharpe":
        return max_sharpe(cov, window.mean() * config.TRADING_DAYS, max_w=max_w)
    if method == "riskparity":
        return risk_parity(cov)
    if method == "hrp":
        return hrp(cov)
    raise ValueError(f"unknown method {method}")
