import numpy as np
import pandas as pd
import pytest

from src import backtest, data, portfolio, risk, signals, strategies


@pytest.fixture(scope="module")
def prices():
    raw = data.synthetic_prices(n_stocks=15, years=4)
    return data.clean_prices(raw)[0]


@pytest.mark.parametrize("method", ["equal", "minvar", "maxsharpe", "riskparity", "hrp"])
def test_weights_valid(prices, method):
    win = prices.pct_change().dropna().tail(252)
    w = portfolio.optimize(method, win)
    assert abs(w.sum() - 1) < 1e-6
    assert (w >= -1e-9).all()


def test_cost_is_charged_on_turnover(prices):
    d = backtest.month_end_dates(prices.index)[10]
    W = pd.DataFrame(0.0, index=[d], columns=prices.columns)
    W.iloc[0, 0] = 1.0
    r0, _ = backtest.run_backtest(prices, W, cost_bps=0)
    r1, t = backtest.run_backtest(prices, W, cost_bps=100)
    assert abs(t.iloc[0] - 1.0) < 1e-9
    assert abs((r0.iloc[0] - r1.iloc[0]) - 0.01) < 1e-9


def test_no_lookahead_in_signals(prices):
    """Changing FUTURE prices must not change a past signal."""
    t = prices.index[400]
    a = signals.composite(prices).loc[t]
    p2 = prices.copy()
    p2.iloc[401:] *= 3
    b = signals.composite(p2).loc[t]
    pd.testing.assert_series_equal(a, b)


def test_weights_use_only_past(prices):
    score = signals.momentum(prices)
    W1 = strategies.weights_from_score(prices, score)
    p2 = prices.copy()
    p2.iloc[-30:] *= 2
    W2 = strategies.weights_from_score(p2, signals.momentum(p2))
    early = W1.index[W1.index < prices.index[-60]]
    pd.testing.assert_frame_equal(W1.loc[early], W2.loc[early])


def test_overlay_never_levers(prices):
    r = prices.pct_change().mean(axis=1).dropna()
    _, exposure = risk.risk_overlay(r)
    assert exposure.max() <= 1.0 + 1e-12 and exposure.min() >= 0
