"""Pull USDCNH 1M + 3M forward points from Bloomberg for the carry benchmark.

USDCNH1M Curncy = 1M forward POINTS (quote in pips; e.g. -166 => 1M forward is
spot - 0.0166 => CNH trades at forward discount => CN yield > US yield, by CIP).

Output: fork-docs/fx_research/carry_fwd.csv  (date index, fwd_1m, fwd_3m)
"""
from __future__ import annotations
import pandas as pd
from xbbg import bdh
from pathlib import Path

OUT = Path(__file__).resolve().parent
TICKERS = {"USDCNH1M Curncy": "fwd_1m", "USDCNH3M Curncy": "fwd_3m"}
START, END = "2015-01-01", pd.Timestamp.today().strftime("%Y-%m-%d")


def to_pandas(obj):
    if obj is None:
        return pd.DataFrame()
    if hasattr(obj, "to_native"):
        obj = obj.to_native()
    if hasattr(obj, "to_pandas"):
        try:
            return obj.to_pandas()
        except Exception:
            pass
    return pd.DataFrame(obj)


def pull(ticker: str, col: str) -> pd.Series:
    raw = bdh(ticker, ["PX_LAST"], START, END)
    df = to_pandas(raw)
    if df.empty:
        return pd.Series(dtype=float, name=col)
    df = df[["date", "value"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    s = df.groupby("date")["value"].last().sort_index()
    s.name = col
    return s


def main():
    out = pd.DataFrame({col: pull(tk, col) for tk, col in TICKERS.items()})
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out = out.astype(float)
    out.to_csv(OUT / "carry_fwd.csv", date_format="%Y-%m-%d")
    print(f"carry_fwd: {len(out)} rows, {out.index.min().date()} -> {out.index.max().date()}")
    print(out.tail(3))
    print("fwd_1m NaN:", int(out['fwd_1m'].isna().sum()), "| fwd_3m NaN:", int(out['fwd_3m'].isna().sum()))
    print("fwd_1m range:", out['fwd_1m'].min(), "->", out['fwd_1m'].max())
    print("sign(fwd_1m) -> long CNH when fwd<0 (CN higher yield); pct fwd<0:",
          f"{(out['fwd_1m']<0).mean()*100:.1f}%")


if __name__ == "__main__":
    main()
