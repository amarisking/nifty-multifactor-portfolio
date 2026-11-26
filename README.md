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
*Fill this in after running on real data (see CAREER_KIT.md for the template).*

## Roadmap
- Point-in-time index constituents; mid-cap universe
- Regime filters (volatility / trend of the index)
- Black-Litterman, transaction-cost-aware optimization
- Paper-trading via a broker API
