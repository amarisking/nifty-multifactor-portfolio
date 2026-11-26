"""Tiny helpers to write the markdown report."""
import numpy as np
import pandas as pd

PCT = {"CAGR", "Volatility", "Max Drawdown", "VaR 95% (1d)", "CVaR 95% (1d)",
       "Alpha (ann.)", "Tracking error", "Breach rate", "Expected rate",
       "Annual turnover"}


def _fmt(col, v):
    if isinstance(v, (int, np.integer)):
        return str(v)
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if isinstance(v, float):
        return f"{v * 100:.1f}%" if col in PCT or "%" in str(col) else f"{v:.2f}"
    return str(v)


def md_table(df, pct_all=False):
    cols = list(df.columns)
    lines = ["| |" + "|".join(str(c) for c in cols) + "|",
             "|---|" + "|".join("---" for _ in cols) + "|"]
    for idx, row in df.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            if pct_all and isinstance(v, (float, np.floating)) and not np.isnan(v):
                cells.append(f"{v * 100:.1f}%")
            else:
                cells.append(_fmt(c, v))
        lines.append(f"| {idx} |" + "|".join(cells) + "|")
    return "\n".join(lines)


class Report:
    def __init__(self):
        self.parts = []

    def h(self, text, level=2):
        self.parts.append(f"\n{'#' * level} {text}\n")

    def p(self, text):
        self.parts.append(text + "\n")

    def table(self, df, **kw):
        self.parts.append(md_table(df, **kw) + "\n")

    def img(self, rel_path, alt=""):
        self.parts.append(f"![{alt}]({rel_path})\n")

    def save(self, path):
        path.write_text("\n".join(self.parts), encoding="utf-8")
