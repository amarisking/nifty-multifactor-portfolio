"""Performance and benchmark-relative metrics for daily return series."""
import numpy as np
import pandas as pd

from . import config


def equity_curve(returns):
    return (1 + returns.fillna(0)).cumprod()


def drawdown(returns):
    eq = equity_curve(returns)
    return eq / eq.cummax() - 1


def sharpe(r, rf=config.RISK_FREE_RATE, periods=config.TRADING_DAYS):
    r = r.dropna()
    return ((r - rf / periods).mean() / r.std() * np.sqrt(periods)
            if r.std() > 0 else np.nan)


def summary(returns, rf=config.RISK_FREE_RATE, periods=config.TRADING_DAYS):
    r = returns.dropna()
    years = len(r) / periods
    cagr = equity_curve(r).iloc[-1] ** (1 / years) - 1
    excess = r - rf / periods
    downside = np.sqrt((np.minimum(excess, 0) ** 2).mean()) * np.sqrt(periods)
    mdd = drawdown(r).min()
    q = r.quantile(config.VAR_ALPHA)
    return pd.Series({
        "CAGR": cagr,
        "Volatility": r.std() * np.sqrt(periods),
        "Sharpe": sharpe(r, rf, periods),
        "Sortino": excess.mean() * periods / downside if downside > 0 else np.nan,
        "Max Drawdown": mdd,
        "Calmar": cagr / abs(mdd) if mdd < 0 else np.nan,
        "VaR 95% (1d)": q,
        "CVaR 95% (1d)": r[r <= q].mean(),
    })


def alpha_beta(r, bench, rf=config.RISK_FREE_RATE, periods=config.TRADING_DAYS):
    """CAPM regression of excess returns (HAC standard errors) plus
    tracking error, information ratio and up/down capture."""
    import statsmodels.api as sm
    d = pd.concat([r, bench], axis=1).dropna()
    d.columns = ["r", "b"]
    ex = d - rf / periods
    m = sm.OLS(ex["r"], sm.add_constant(ex["b"])).fit(
        cov_type="HAC", cov_kwds={"maxlags": 5})
    active = d["r"] - d["b"]
    te = active.std() * np.sqrt(periods)
    up, down = d[d["b"] > 0], d[d["b"] < 0]
    return pd.Series({
        "Alpha (ann.)": m.params["const"] * periods,
        "Alpha t-stat": m.tvalues["const"],
        "Beta": m.params["b"],
        "Tracking error": te,
        "Information ratio": active.mean() * periods / te if te > 0 else np.nan,
        "Up capture": up["r"].mean() / up["b"].mean(),
        "Down capture": down["r"].mean() / down["b"].mean(),
    })


def calendar_year_returns(df):
    return (1 + df).groupby(df.index.year).prod() - 1
