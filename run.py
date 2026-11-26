"""Full pipeline.
    python run.py              real NSE data via yfinance (needs internet)
    python run.py --synthetic  offline test with fake data
    python run.py --quick      lighter run (skips GARCH, smaller grids)
Outputs: results/REPORT.md, results/tables/*.csv, results/figures/*.png"""
import argparse
import warnings

import pandas as pd

from src import (backtest, config, data, metrics, plots, risk, signals,
                 strategies, validation)
from src.report import Report

warnings.filterwarnings("ignore")


def main(synthetic=False, quick=False):
    tdir = config.RESULTS_DIR / "tables"
    fdir = config.RESULTS_DIR / "figures"
    tdir.mkdir(parents=True, exist_ok=True)
    fdir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- data
    raw = data.synthetic_prices() if synthetic else data.download_prices()
    P, bench_px, bname = data.clean_prices(raw)
    bench = bench_px.pct_change()
    print(f"Universe: {P.shape[1]} stocks | {P.index[0].date()} to "
          f"{P.index[-1].date()} | benchmark: {bname}")

    # ----------------------------------------------- strategies (all net of costs)
    comp = signals.composite(P)
    W = {
        "Equal-weight (all)": backtest.equal_weight_all(P),
        "Momentum": strategies.weights_from_score(P, signals.momentum(P)),
        "Low volatility": strategies.weights_from_score(P, signals.low_volatility(P)),
        "Reversal": strategies.weights_from_score(P, signals.reversal(P)),
        "Trend-filtered momentum": strategies.weights_from_score(
            P, signals.momentum(P), eligible=signals.trend_filter(P)),
        "Multi-factor (top 10)": strategies.weights_from_score(P, comp),
    }
    methods = [("EW", "equal"), ("MinVar", "minvar"), ("MaxSharpe", "maxsharpe"),
               ("RiskParity", "riskparity"), ("HRP", "hrp")]
    for label, m in methods:
        print(f"  building multi-factor top {config.TOP_N_OPT} / {label} ...")
        W[f"MF-20 {label}"] = strategies.weights_from_score(
            P, comp, top_n=config.TOP_N_OPT, method=m)

    rets, turns = {}, {}
    for name, w in W.items():
        rets[name], turns[name] = backtest.run_backtest(P, w)

    FINAL = "MF-20 HRP"                      # chosen a priori (robust, no return forecasts)
    overlay, exposure = risk.risk_overlay(rets[FINAL])
    OVL = f"{FINAL} + risk overlay"
    rets[OVL] = overlay

    df = pd.DataFrame(rets)
    df[bname] = bench
    df = df.dropna()                          # common sample for every strategy
    years = len(df) / config.TRADING_DAYS
    print(f"Common evaluation sample: {df.index[0].date()} to {df.index[-1].date()}")

    perf = pd.DataFrame({c: metrics.summary(df[c]) for c in df}).T
    perf["Annual turnover"] = [turns[c].reindex(df.index).sum() / years
                               if c in turns else float("nan") for c in perf.index]
    perf.loc[OVL, "Annual turnover"] = perf.loc[FINAL, "Annual turnover"]
    ab = pd.DataFrame({c: metrics.alpha_beta(df[c], df[bname])
                       for c in df if c != bname}).T
    perf.to_csv(tdir / "performance.csv")
    ab.to_csv(tdir / "alpha_beta.csv")

    singles = ["Equal-weight (all)", "Momentum", "Low volatility", "Reversal",
               "Trend-filtered momentum", "Multi-factor (top 10)", bname]
    constr = [f"MF-20 {l}" for l, _ in methods] + [bname]
    plots.equity_and_drawdown(df[singles], fdir / "01_single_factors.png",
                              "Single-factor and multi-factor portfolios")
    plots.equity_and_drawdown(df[constr], fdir / "02_construction_methods.png",
                              "Portfolio construction methods (multi-factor, top 20)")

    # ------------------------------------------------------------ risk layer
    plots.overlay_chart(df[FINAL], df[OVL], exposure.reindex(df.index),
                        fdir / "03_risk_overlay.png")
    r_final = df[FINAL]
    vh, ch = risk.hist_var_cvar(r_final)
    vars_ = {"historical": risk.rolling_var(r_final, "historical"),
             "parametric": risk.rolling_var(r_final, "parametric")}
    if not quick:
        print("  fitting rolling GARCH-t VaR (takes a minute) ...")
        vars_["GARCH-t"] = risk.garch_var(r_final)
    var_bt = risk.var_backtest(r_final, vars_)
    plots.var_chart(r_final, vars_, fdir / "04_var.png")
    var_bt.to_csv(tdir / "var_backtest.csv")
    stress_cols = [bname, "Equal-weight (all)", "Momentum",
                   "Multi-factor (top 10)", FINAL, OVL]
    stress = risk.stress_table(df[stress_cols])
    stress.to_csv(tdir / "stress.csv")

    # ------------------------------------------------------------ validation
    lbs, ns = ([126, 252], [10, 20]) if quick else ([126, 189, 252], [5, 10, 15, 20])
    grid = validation.momentum_returns_grid(P, lbs, ns)
    sh_tab, cg_tab = validation.sensitivity_tables(grid, lbs, ns, df.index[0])
    plots.heatmap(sh_tab, fdir / "05_momentum_sharpe_heatmap.png",
                  "Momentum Sharpe: lookback vs. portfolio size")
    sh_tab.to_csv(tdir / "momentum_sensitivity_sharpe.csv")

    cost_tab = pd.concat({
        "Momentum": validation.cost_sensitivity(P, W["Momentum"], start=df.index[0]),
        FINAL: validation.cost_sensitivity(P, W[FINAL], start=df.index[0]),
    })
    cost_tab.to_csv(tdir / "cost_sensitivity.csv")

    oos, picks = validation.walk_forward(grid, df.index[0])
    fixed = grid[f"252d/top10"] if "252d/top10" in grid else grid[next(iter(grid))]
    wf = pd.DataFrame({
        "Walk-forward momentum (OOS)": oos,
        "Fixed 252d/top10 momentum": fixed.reindex(oos.index),
        "Equal-weight (all)": df["Equal-weight (all)"].reindex(oos.index),
        bname: df[bname].reindex(oos.index)}).dropna()
    wf_tab = pd.DataFrame({c: metrics.summary(wf[c]) for c in wf}).T
    wf_tab.to_csv(tdir / "walk_forward.csv")
    picks.to_csv(tdir / "walk_forward_picks.csv", index=False)

    boot_cols = [bname, "Equal-weight (all)", "Momentum",
                 "Multi-factor (top 10)", FINAL, OVL]
    boot = validation.block_bootstrap_sharpe(df[boot_cols], bname,
                                             n_boot=300 if quick else 2000)
    boot.to_csv(tdir / "bootstrap_sharpe.csv")

    yearly = metrics.calendar_year_returns(df[[bname, "Momentum", FINAL, OVL]])
    plots.yearly_bars(yearly, fdir / "06_calendar_years.png")
    yearly.to_csv(tdir / "calendar_year_returns.csv")

    # ---------------------------------------------------------------- report
    R = Report()
    R.h("Systematic Multi-Factor Portfolio Framework: Nifty 50", 1)
    R.p(f"*Auto-generated. Sample: {df.index[0].date()} to {df.index[-1].date()} "
        f"({years:.1f} years), {P.shape[1]} stocks, benchmark {bname}. "
        f"Costs: {config.COST_BPS} bps per unit of turnover. Risk-free rate "
        f"{config.RISK_FREE_RATE:.0%}."
        f"{' **SYNTHETIC DATA: numbers are meaningless.**' if synthetic else ''}*")

    R.h("1. Performance (net of costs)")
    R.table(perf[["CAGR", "Volatility", "Sharpe", "Sortino", "Max Drawdown",
                  "Calmar", "Annual turnover"]])
    R.img("figures/01_single_factors.png", "single factors")
    R.h("2. Portfolio construction: same stock picks, different weighting")
    R.table(perf.loc[constr[:-1] + [OVL, bname],
                     ["CAGR", "Volatility", "Sharpe", "Max Drawdown", "Calmar"]])
    R.img("figures/02_construction_methods.png", "construction methods")
    R.h("3. Benchmark-relative statistics (CAPM regression)")
    R.table(ab)
    R.h("4. Risk layer")
    R.p(f"Full-sample one-day 95% VaR of {FINAL}: {vh:.2%}; CVaR: {ch:.2%}.")
    R.p("**VaR forecast backtest** (95% VaR should be breached on about 5% of days; "
        "a small Kupiec p-value means the model's breach rate is statistically off):")
    R.table(var_bt)
    R.img("figures/04_var.png", "VaR")
    R.p("**Volatility targeting and drawdown de-risking:**")
    R.img("figures/03_risk_overlay.png", "overlay")
    R.p("**Stress windows** (cumulative return; windows are approximate):")
    R.table(stress, pct_all=True)
    R.h("5. Validation")
    R.p("**Parameter sensitivity** (momentum Sharpe). A trustworthy signal works across "
        "neighbouring settings rather than at one lucky point.")
    R.img("figures/05_momentum_sharpe_heatmap.png", "heatmap")
    R.p("**Transaction-cost sensitivity:**")
    R.table(cost_tab)
    R.p("**Walk-forward test** (parameters chosen on past data only, then traded on "
        "the next unseen year):")
    R.table(wf_tab[["CAGR", "Volatility", "Sharpe", "Max Drawdown"]])
    R.table(picks)
    R.p("**Block-bootstrap Sharpe ratios** (90% interval; P = chance the strategy's "
        "Sharpe beats the benchmark's across resampled histories):")
    R.table(boot)
    R.p("**Calendar-year returns:**")
    R.img("figures/06_calendar_years.png", "yearly")

    best = perf.drop(index=[bname])["Sharpe"].idxmax()
    beat = [c for c in perf.index if c != bname and perf.loc[c, "Sharpe"] > perf.loc[bname, "Sharpe"]]
    sig = [c for c in ab.index if abs(ab.loc[c, "Alpha t-stat"]) > 2]
    R.h("6. Automatic observations (read critically)")
    R.p(f"- Highest full-sample Sharpe: **{best}** ({perf.loc[best, 'Sharpe']:.2f}) "
        f"vs benchmark {perf.loc[bname, 'Sharpe']:.2f}. Picking the best of many "
        f"strategies in-sample overstates its true skill (multiple testing).")
    R.p(f"- Strategies with higher Sharpe than the benchmark: {len(beat)} of "
        f"{len(perf) - 1}.")
    R.p(f"- Strategies with |alpha t-stat| > 2: {', '.join(sig) if sig else 'none'}.")
    R.p("- Survivorship bias is present: the universe is today's index members, which "
        "flatters every stock-picking result relative to the benchmark.")
    R.save(config.RESULTS_DIR / "REPORT.md")
    pd.set_option("display.width", 220, "display.float_format", "{:.3f}".format)
    print(perf[["CAGR", "Volatility", "Sharpe", "Max Drawdown", "Annual turnover"]])
    print(f"\nFull report: {config.RESULTS_DIR / 'REPORT.md'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    main(a.synthetic, a.quick)
