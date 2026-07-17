"""Pull USDCNH / USDCNY daily OHLC from Bloomberg via xbbg/blpapi.

xbbg 1.0 returns a long-format pyarrow Table (cols: ticker, date, field, value[str]).
We pivot to wide (date index, open/high/low/last), cast to float, save CSV.

Output: fork-docs/fx_research/usdcnh.csv, usdcny.csv
"""
from __future__ import annotations
import pandas as pd
from xbbg import bdh
from pathlib import Path

OUT = Path(__file__).resolve().parent
TICKERS = {
    "USDCNH Curncy": "usdcnh",
    "USDCNY Curncy": "usdcny",
}
FIELDS = ["PX_OPEN", "PX_HIGH", "PX_LOW", "PX_LAST"]
START, END = "2015-01-01", pd.Timestamp.today().strftime("%Y-%m-%d")
FIELD_RENAME = {"PX_OPEN": "open", "PX_HIGH": "high", "PX_LOW": "low", "PX_LAST": "last"}


def to_pandas(obj):
    """Coerce xbbg's narwhals.DataFrame (-> pyarrow Table) to pandas."""
    if obj is None:
        return pd.DataFrame()
    if hasattr(obj, "to_native"):
        obj = obj.to_native()
    # pyarrow Table
    if hasattr(obj, "to_pandas"):
        try:
            return obj.to_pandas()  # pyarrow Table -> pandas
        except Exception:
            pass
    return pd.DataFrame(obj)


def pull(ticker: str, name: str) -> pd.DataFrame:
    raw = bdh(ticker, FIELDS, START, END)
    df = to_pandas(raw)
    if df.empty:
        return df
    # long -> wide
    df = df[["date", "field", "value"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    wide = df.pivot_table(index="date", columns="field", values="value", aggfunc="last")
    wide.columns = [FIELD_RENAME.get(c, c) for c in wide.columns]
    wide = wide[[c for c in ["open", "high", "low", "last"] if c in wide.columns]]
    wide = wide[~wide.index.duplicated(keep="last")].sort_index()
    wide = wide.astype(float)
    wide.to_csv(OUT / f"{name}.csv", date_format="%Y-%m-%d")
    return wide


def main():
    summary = []
    for ticker, name in TICKERS.items():
        df = pull(ticker, name)
        if df.empty:
            summary.append(f"{name}: EMPTY (ticker={ticker})")
            continue
        summary.append(
            f"{name} ({ticker}): {len(df)} rows, "
            f"{df.index.min().date()} -> {df.index.max().date()}, "
            f"cols={list(df.columns)}"
        )
    print("\n".join(summary))


if __name__ == "__main__":
    main()
