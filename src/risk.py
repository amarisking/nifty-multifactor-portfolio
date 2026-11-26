"""Risk layer: VaR/CVaR (historical, parametric, GARCH-t), VaR backtesting
(Kupiec test), volatility targeting + drawdown de-risking, stress tests."""
import numpy as np
import pandas as pd
from scipy.stats import chi2, norm
from scipy.stats import t as t_dist

from . import config


def hist_var_cvar(r, alpha=config.VAR_ALPHA):
    q = r.quantile(alpha)
    return q, r[r <= q].mean()


def rolling_var(r, method, alpha=config.VAR_ALPHA, window=252):
    """One-day VaR forecast for day t using only data up to t-1."""
    if method == "historical":
        v = r.rolling(window).quantile(alpha)
    elif method == "parametric":
        v = r.rolling(window).mean() + norm.ppf(alpha) * r.rolling(window).std()
    else:
        raise ValueError(method)
    return v.shift(1)


def garch_var(r, alpha=config.VAR_ALPHA, min_obs=500, refit_every=63):
    """GARCH(1,1) with Student-t errors. Parameters re-estimated every
    `refit_every` days; the volatility filter is updated every day."""
    from arch import arch_model
    x = r.dropna() * 100
    out = pd.Series(np.nan, index=x.index)
    params = None
    for t in range(min_obs, len(x)):
        try:
            am = arch_model(x.iloc[:t], mean="Constant", vol="GARCH",
                            p=1, q=1, dist="t")
            if params is None or (t - min_obs) % refit_every == 0:
                res = am.fit(disp="off")
                params = res.params
            else:
                res = am.fix(params)
            f = res.forecast(horizon=1)
            mu = f.mean.iloc[-1, 0]
            sig = np.sqrt(f.variance.iloc[-1, 0])
            nu = params["nu"]
            q = t_dist.ppf(alpha, nu) * np.sqrt((nu - 2) / nu)
            out.iloc[t] = (mu + sig * q) / 100
        except Exception:
            continue
    return out


def kupiec_pvalue(breaches, n, alpha):
    """Kupiec proportion-of-failures test: H0 = breach rate equals alpha."""
    x, p = breaches, alpha
    if n == 0:
        return np.nan
    ll_null = (n - x) * np.log(1 - p) + x * np.log(p)
    ph = x / n
    ll_alt = 0.0
    if 0 < x < n:
        ll_alt = (n - x) * np.log(1 - ph) + x * np.log(ph)
    return float(1 - chi2.cdf(-2 * (ll_null - ll_alt), 1))


def var_backtest(r, var_dict, alpha=config.VAR_ALPHA):
    rows = {}
    for name, v in var_dict.items():
        d = pd.concat([r, v], axis=1).dropna()
        n = len(d)
        b = int((d.iloc[:, 0] < d.iloc[:, 1]).sum())
        rows[name] = {"Days": n, "Breaches": b,
                      "Breach rate": b / n if n else np.nan,
                      "Expected rate": alpha,
                      "Kupiec p-value": kupiec_pvalue(b, n, alpha)}
    return pd.DataFrame(rows).T


def risk_overlay(r, rf=config.RISK_FREE_RATE, vol_target=config.VOL_TARGET,
                 vol_window=60, dd_trigger=config.DD_TRIGGER,
                 dd_reset=config.DD_RESET, dd_exposure=config.DD_EXPOSURE,
                 cost_bps=config.COST_BPS):
    """Scale exposure to the strategy: (1) volatility targeting from trailing
    realised vol, (2) halve exposure after a drawdown trigger until recovery.
    Both use information up to the previous day. Max exposure 1.0 (no
    leverage); the rest sits in cash earning rf; exposure changes pay costs."""
    rf_d = (1 + rf) ** (1 / config.TRADING_DAYS) - 1
    realised = r.rolling(vol_window, min_periods=20).std() * np.sqrt(config.TRADING_DAYS)
    vol_exp = (vol_target / realised).clip(upper=1.0).shift(1).fillna(1.0)

    eq = peak = 1.0
    derisk = False
    dd_exp = np.ones(len(r))
    for i, x in enumerate(r.values):
        dd_exp[i] = dd_exposure if derisk else 1.0     # state from yesterday
        eq *= 1 + x
        peak = max(peak, eq)
        dd = eq / peak - 1
        if derisk and dd > -dd_reset:
            derisk = False
        elif (not derisk) and dd < -dd_trigger:
            derisk = True
    exposure = np.minimum(vol_exp, pd.Series(dd_exp, index=r.index))
    cost = exposure.diff().abs().fillna(0) * cost_bps / 1e4
    return exposure * r + (1 - exposure) * rf_d - cost, exposure


def stress_table(df, windows=config.STRESS_WINDOWS):
    rows = {}
    for name, (a, b) in windows.items():
        sub = df.loc[a:b]
        if len(sub) < 10:
            continue
        rows[name] = (1 + sub).prod() - 1
    worst = df.min().rename("Worst single day")
    out = pd.DataFrame(rows).T
    return pd.concat([out, worst.to_frame().T])
