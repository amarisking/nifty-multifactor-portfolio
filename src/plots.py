"""Figures saved to results/figures."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import metrics


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def equity_and_drawdown(df, path, title="Growth of 1 rupee (net of costs)"):
    fig, ax = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    for c in df:
        metrics.equity_curve(df[c]).plot(ax=ax[0], label=c, lw=1.3)
        metrics.drawdown(df[c]).plot(ax=ax[1], lw=1.0)
    ax[0].set_title(title)
    ax[0].set_yscale("log")
    ax[0].legend(fontsize=8)
    ax[1].set_title("Drawdown")
    _save(fig, path)


def heatmap(table, path, title):
    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(table.values.astype(float), cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(table.shape[1]), table.columns)
    ax.set_yticks(range(table.shape[0]), table.index)
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            ax.text(j, i, f"{table.values[i, j]:.2f}", ha="center", va="center")
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    _save(fig, path)


def var_chart(r, var_dict, path):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(r.index, r.values, lw=0.5, color="grey", label="Daily return")
    for name, v in var_dict.items():
        ax.plot(v.index, v.values, lw=1.1, label=f"VaR 95% {name}")
    ax.set_title("Daily returns vs one-day VaR forecasts")
    ax.legend(fontsize=8)
    _save(fig, path)


def overlay_chart(raw, overlay, exposure, path):
    fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    metrics.equity_curve(raw).plot(ax=ax[0], label="Without overlay")
    metrics.equity_curve(overlay).plot(ax=ax[0], label="With vol target + drawdown rule")
    ax[0].legend()
    ax[0].set_title("Effect of the risk overlay")
    exposure.plot(ax=ax[1], lw=0.8)
    ax[1].set_title("Equity exposure (rest in cash)")
    ax[1].set_ylim(0, 1.05)
    _save(fig, path)


def yearly_bars(table, path):
    ax = (table * 100).plot.bar(figsize=(11, 5), width=0.85)
    ax.set_ylabel("Return (%)")
    ax.set_title("Calendar-year returns")
    ax.legend(fontsize=7)
    _save(ax.get_figure(), path)
