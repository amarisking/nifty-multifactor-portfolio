# Systematic Multi-Factor Portfolio Framework for Indian Equities (Nifty 50)

An end-to-end research framework: signals -> portfolio construction -> risk
layer -> validation. Built to answer one question honestly: *does a
multi-factor, risk-managed portfolio add value over a Nifty 50 index fund
after costs, and how much of that can be trusted?*

## Quick start
```bash
python -m venv venv && venv\Scripts\activate      # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python run.py --synthetic --quick   # 1-minute offline pipeline test
python run.py                       # real NSE data (needs internet; ~5-10 min with GARCH)
python -m pytest tests              # unit tests (no-lookahead, weights, costs)
```
Outputs: `results/REPORT.md` (tables + figures), `results/tables/*.csv`, `results/figures/*.png`.
If you ran an earlier version, delete `data/prices.csv` so the benchmark ETF downloads.

## What is inside
| Layer | Module | Contents |
|---|---|---|
| Data | `src/data.py` | yfinance download, caching, cleaning (no backfill), dividend-adjusted benchmark (NIFTYBEES) |
| Signals | `src/signals.py` | 12-1 momentum, low volatility, short-term reversal, trend filter, z-scored multi-factor composite |
| Construction | `src/portfolio.py` | Equal weight, minimum variance, max-Sharpe (shrunk returns), risk parity, Hierarchical Risk Parity; Ledoit-Wolf covariance; long-only with position caps |
| Engine | `src/backtest.py` | Next-day execution, drifting weights, cost on actual turnover, cash earns risk-free |
| Risk | `src/risk.py` | Historical / parametric / GARCH-t VaR and CVaR, Kupiec backtest, volatility targeting, drawdown de-risking, stress windows |
| Validation | `src/validation.py` | Parameter heatmap, cost sensitivity, walk-forward test, block-bootstrap Sharpe intervals |
| Analytics | `src/metrics.py` | CAGR, Sharpe, Sortino, Calmar, CAPM alpha/beta (HAC errors), information ratio, capture ratios |

## Design decisions (be ready to defend these)
- **No lookahead:** signals use data up to month-end; trades earn returns from the next day. Tests enforce this.
- **Shrinkage:** sample covariance is noisy with 20 assets, so Ledoit-Wolf is used. Expected returns in max-Sharpe are shrunk 50% toward their mean.
- **HRP is the pre-specified "final" construction** (no return forecasts, no matrix inversion). Choosing it before seeing results limits data snooping.
- **Risk overlay has no leverage:** exposure is capped at 100%, remainder in cash.
- **Benchmark is a total-return proxy** (NIFTYBEES), because ^NSEI excludes dividends.

## Limitations (keep this honest)
- **Survivorship bias:** today's Nifty members over the whole history flatter stock-selection results. Fix: point-in-time constituents.
- Multiple strategies were compared on one sample, so the best one is optimistic. Bootstrap intervals and walk-forward results are the more credible evidence.
- Costs are a flat bps assumption; no taxes, market impact, or liquidity limits.
- Stress-window dates are approximate.
- One market, ~10 years, one regime sequence.

## Findings
Sample: Feb 2015 to Nov 2026, 46 Nifty stocks, net of 10 bps trading costs, benchmark NIFTYBEES (dividend-adjusted ETF).

1. **No signal or optimizer beat equal-weight of the same stocks.** Sharpe ratios: equal-weight 0.74, risk parity 0.74, HRP 0.71, momentum 0.68, multi-factor (top 10) 0.67. Bootstrap 90% intervals overlap heavily (equal-weight: 0.22 to 1.29), so the strategies cannot be ranked statistically.
2. **Apparent outperformance over the index is mostly survivorship bias.** Equal-weighting today's index members earned 17.9% CAGR vs 10.8% for the ETF, with no stock-picking skill involved.
3. **Mean-variance (max-Sharpe) was the worst weighting method** (Sharpe 0.53), consistent with the known sensitivity of optimizers to noisy return estimates.
4. **The risk overlay (volatility target + drawdown rule) worked as crash insurance but cost returns.** Max drawdown fell from -32.9% to -24.7% and the COVID-crash loss from -31.9% to -23.7%, but CAGR dropped from 16.7% to 13.1%.
5. **Costs matter.** HRP's Sharpe falls from 0.78 at 0 bps to 0.46 at 50 bps because turnover is about 930% a year.
6. **VaR:** historical and parametric 95% VaR were well calibrated (breach rates 5.3% and 5.0%). GARCH-t VaR breached 6.1% of days (Kupiec p = 0.01).
7. **Walk-forward test:** momentum with parameters chosen on past data earned an out-of-sample Sharpe of 0.51 vs 0.74 for equal-weight.

### What did not work
- Momentum added no value and had a deeper drawdown (-41.6%). It was weakest in 2024-25 (-21.3% vs -12.0% for equal-weight).
- Max-Sharpe optimization underperformed simple weighting.
- GARCH-t VaR was less well calibrated than simple methods. I have not diagnosed why.
- The reversal strategy shows the best Sharpe (0.93) but turns over about 20x a year, so I do not trust it under realistic costs.
- The benchmark ETF data contained bad prices (265% volatility), which broke the first results. The pipeline now detects and repairs such days.

## Roadmap
- Point-in-time index constituents; mid-cap universe
- Regime filters (volatility / trend of the index)
- Black-Litterman, transaction-cost-aware optimization
- Paper-trading via a broker API
