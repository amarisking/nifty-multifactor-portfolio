"""Download, cache and clean price data."""
import numpy as np
import pandas as pd

from . import config


def download_prices(tickers=None, start=None, end=None, use_cache=True):
    """Adjusted close for the universe + benchmarks. Cached to data/prices.csv."""
    cache = config.DATA_DIR / "prices.csv"
    if use_cache and cache.exists():
        df = pd.read_csv(cache, index_col=0, parse_dates=True)
        if config.BENCHMARK_ETF in df.columns:
            return df
        print("Cache has no benchmark ETF column; downloading again...")

    import yfinance as yf  # imported here so the rest works offline

    tickers = tickers or config.TICKERS
    symbols = ([f"{t}.NS" for t in tickers]
               + [f"{config.BENCHMARK_ETF}.NS", config.INDEX_TICKER])
    raw = yf.download(symbols, start=start or config.START_DATE,
                      end=end or config.END_DATE, auto_adjust=True,
                      progress=False)["Close"]
    raw.columns = [c.replace(".NS", "") for c in raw.columns]
    config.DATA_DIR.mkdir(exist_ok=True)
    raw.to_csv(cache)
    return raw


def _repair_benchmark(prices, bench_name, max_gap=0.05, max_move=0.15):
    """Yahoo ETF data sometimes contains bad ticks or unadjusted splits
    (e.g. a one-day -90% move). Where the benchmark's daily return differs
    from the Nifty index return by more than `max_gap`, use the index return
    instead. Without the index, flag |return| > `max_move` and set it to 0."""
    px = prices[bench_name].dropna()
    ret = px.pct_change()
    if config.INDEX_TICKER in prices and bench_name != config.INDEX_TICKER:
        idx_ret = prices[config.INDEX_TICKER].pct_change().reindex(ret.index)
        bad = ((ret - idx_ret).abs() > max_gap) | (ret.abs() > max_move)
        ret[bad] = idx_ret[bad].fillna(0.0)
    else:
        bad = ret.abs() > max_move
        ret[bad] = 0.0
    if bad.any():
        print(f"WARNING: repaired {int(bad.sum())} bad benchmark day(s): "
              f"{[d.date().isoformat() for d in ret.index[bad]][:10]}")
    return (1 + ret.fillna(0.0)).cumprod() * px.iloc[0]


def clean_prices(prices, max_missing=0.30, ffill_limit=5):
    """Returns (stock_prices, benchmark_prices, benchmark_name).

    - benchmark = NIFTYBEES (dividend-adjusted) if available, else ^NSEI
    - drop stocks with too much missing history
    - forward-fill short gaps (holidays) only; never backfill (that is lookahead)
    """
    prices = prices.sort_index()
    prices = prices[~prices.index.duplicated()]
    prices = prices.replace(0, np.nan)

    etf_ok = (config.BENCHMARK_ETF in prices
              and prices[config.BENCHMARK_ETF].notna().sum() > 500)
    bench_name = config.BENCHMARK_ETF if etf_ok else config.INDEX_TICKER
    if not etf_ok:
        print("WARNING: using price-only ^NSEI as benchmark (no dividends).")
    bench = _repair_benchmark(prices, bench_name)

    stocks = prices.drop(columns=[config.INDEX_TICKER, config.BENCHMARK_ETF],
                         errors="ignore")
    keep = stocks.columns[stocks.isna().mean() <= max_missing]
    dropped = sorted(set(stocks.columns) - set(keep))
    if dropped:
        print(f"Dropped (too much missing data): {dropped}")
    stocks = stocks[keep].ffill(limit=ffill_limit).dropna(how="all")
    return stocks, bench, bench_name


def synthetic_prices(n_stocks=30, years=9, seed=42):
    """Fake prices with a market factor, only to test the pipeline offline."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2016-01-01", periods=years * 252)
    market = rng.normal(0.0004, 0.01, len(idx))
    betas = rng.uniform(0.5, 1.3, n_stocks)
    rets = market[:, None] * betas + rng.normal(0.0002, 0.012, (len(idx), n_stocks))
    px = pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=idx,
                      columns=[f"STK{i:02d}" for i in range(n_stocks)])
    px[config.INDEX_TICKER] = 100 * np.exp(np.cumsum(market))
    px[config.BENCHMARK_ETF] = 100 * np.exp(np.cumsum(market + 0.00005))
    return px
