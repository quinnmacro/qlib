"""Time-series MOMENTUM on USDCNH (offshore).

Three variants: MOM20, MOM60, MOM120.
signal_t = sign(spot_last_t / spot_last_{t-lookback} - 1), computed on info up to t.
1-day execution lag: signal at close t -> trade at close t+1, earns t+1->t+2 return.
PnL_t = position_{t-1} * spot_ret_t, where spot_ret = log(last/last.shift(1)).

Annualization convention (label verbatim in outputs):
  252 trading days. ann_vol = daily_std * sqrt(252).
  ann_ret (CAGR) = (1+total)^(252/n_days)-1.
  Sharpe-like = mean_daily/vol_daily (rf=0, no sqrt(N)).
  NOT qlib risk_analysis (238, sum) and NOT 250 legacy. NOT qlib IR (sqrt N) / ICIR.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.abspath(__file__))
NH_CSV = os.path.join(BASE, "..", "usdcnh.csv")
OUT_DIR = BASE
PNG = os.path.join(OUT_DIR, "momentum_equity.png")


def load_close():
    df = pd.read_csv(NH_CSV, index_col=0, parse_dates=True)
    close = df["last"].astype(float)
    close = close[~close.index.duplicated(keep="last")]
    close = close.sort_index()
    return close


def spot_logret(close):
    return np.log(close / close.shift(1))


def momentum_variant(close, lookback):
    """Return (equity_series, position_series) for a MOM{lookback} strategy.

    Execution lag = 1 day. signal at close t (uses [t-lookback, t]) -> position
    taken at close t+1 -> earns return from t+1 to t+2 (i.e. ret_{t+2}).
    """
    ret = spot_logret(close)
    # signal at t: sign of cumulative return over [t-lookback, t]
    cum = close / close.shift(lookback) - 1.0
    signal = np.sign(cum)  # NaN during warmup
    # position_held_during_return_t = signal_{t-1} (with extra 1-day exec lag =>
    # position that earns ret_t is signal_{t-2}).
    # PnL_t = position_{t-1} * ret_t ; here position_{t-1} = signal_{t-2} (1-day lag)
    pos = signal.shift(2)
    # warmup: drop rows until pos first valid
    first_valid = pos.first_valid_index()
    pos = pos.loc[first_valid:]
    ret = ret.loc[first_valid:]
    strat_ret = pos * ret
    strat_ret = strat_ret.dropna()
    equity = (1.0 + strat_ret).cumprod()
    return equity, pos, strat_ret


def metrics(equity, strat_ret, pos):
    n = len(strat_ret)
    total = equity.iloc[-1] - 1.0
    n_days = n
    cagr = (1.0 + total) ** (252.0 / n_days) - 1.0
    ann_vol = strat_ret.std() * np.sqrt(252.0)
    sharpe_like = strat_ret.mean() / strat_ret.std() if strat_ret.std() > 0 else np.nan
    # max drawdown on equity curve
    roll_max = equity.cummax()
    dd = (equity / roll_max - 1.0)
    max_dd = dd.min()  # negative
    calmar = cagr / abs(max_dd) if max_dd != 0 else np.nan
    win_rate = (strat_ret > 0).mean() * 100.0
    turnover = pos.diff().abs().mean()
    n_flips = int((np.sign(pos).diff().fillna(0) != 0).sum())
    return {
        "total_return": total,
        "CAGR": cagr,
        "ann_vol_252": ann_vol,
        "sharpe_like": sharpe_like,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "win_rate_daily_%": win_rate,
        "turnover": turnover,
        "n_flips": n_flips,
        "n_days": n_days,
    }


def buyhold_metrics(close, start_idx, end_idx):
    """B&H over [start_idx, end_idx]."""
    sub = close.loc[start_idx:end_idx].dropna()
    ret = np.log(sub / sub.shift(1)).dropna()
    equity = (1.0 + ret).cumprod()
    n = len(ret)
    total = equity.iloc[-1] - 1.0
    cagr = (1.0 + total) ** (252.0 / n) - 1.0 if n > 0 else np.nan
    ann_vol = ret.std() * np.sqrt(252.0)
    sharpe_like = ret.mean() / ret.std() if ret.std() > 0 else np.nan
    roll_max = equity.cummax()
    dd = equity / roll_max - 1.0
    max_dd = dd.min()
    calmar = cagr / abs(max_dd) if max_dd != 0 else np.nan
    win_rate = (ret > 0).mean() * 100.0
    return {
        "total_return": total,
        "CAGR": cagr,
        "ann_vol_252": ann_vol,
        "sharpe_like": sharpe_like,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "win_rate_daily_%": win_rate,
        "turnover": 0.0,
        "n_flips": 0,
        "n_days": n,
        "equity": equity,
    }


def main():
    close = load_close()
    lookbacks = [20, 60, 120]
    results = {}
    eqs = {}
    bh = {}
    for L in lookbacks:
        eq, pos, sret = momentum_variant(close, L)
        m = metrics(eq, sret, pos)
        results[f"MOM{L}"] = m
        eqs[f"MOM{L}"] = eq
        # B&H over same window
        bh_m = buyhold_metrics(close, eq.index[0], eq.index[-1])
        bh[f"MOM{L}"] = bh_m
        results[f"MOM{L}_BH_same_window"] = bh_m

    # also overall B&H for reference
    overall = buyhold_metrics(close, close.dropna().index[0], close.dropna().index[-1])
    results["B&H_full"] = overall

    # ---- print metrics ----
    print("=== MOMENTUM metrics (252 trading days; ann_vol=daily_std*sqrt(252); "
          "CAGR=(1+total)^(252/n)-1; sharpe_like=mean/vol, rf=0, NO sqrt(N); "
          "NOT qlib 238/250/IR/ICIR) ===\n")
    for k, v in results.items():
        print(f"--- {k} ---")
        for kk, vv in v.items():
            if isinstance(vv, float):
                print(f"  {kk}: {vv:.6f}")
            else:
                print(f"  {kk}: {vv}")
        print()

    # ---- plot ----
    fig, ax = plt.subplots(figsize=(11, 7))
    colors = {"MOM20": "#1f77b4", "MOM60": "#2ca02c", "MOM120": "#d62728"}
    for L in lookbacks:
        key = f"MOM{L}"
        ax.plot(eqs[key].index, eqs[key].values, label=f"{key} strategy",
                color=colors[key], linewidth=1.6)
        bh_eq = bh[key]["equity"]
        ax.plot(bh_eq.index, bh_eq.values, label=f"B&H CNH ({key} window)",
                color=colors[key], linewidth=1.0, alpha=0.45, linestyle="--")
    ax.set_yscale("log")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity (log scale, start=1)")
    ax.set_title("USDCNH time-series momentum vs buy-and-hold (log-y)\n"
                 "252-day ann; sharpe_like=mean/vol rf=0 (NOT qlib 238/250/IR/ICIR)")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(PNG, dpi=130)
    print(f"\nSaved plot: {PNG}")

    # ---- markdown report ----
    write_md(results, lookbacks)


def fmt(x, p=4):
    if x is None or (isinstance(x, float) and (np.isnan(x))):
        return "nan"
    if isinstance(x, float):
        return f"{x:.{p}f}"
    return str(x)


def write_md(results, lookbacks):
    md = []
    md.append("# Time-series Momentum on USDCNH (offshore)\n")
    md.append("## Annualization convention (applied identically to every variant)\n")
    md.append("- 252 trading days. `ann_vol = daily_std * sqrt(252)`.")
    md.append("- `CAGR = (1+total)^(252/n_days) - 1`.")
    md.append("- Sharpe-like = `mean_daily / vol_daily`, rf=0, **no sqrt(N)**.")
    md.append("- This is NOT qlib `risk_analysis` (238, sum mode) and NOT the 250 "
              "legacy figure. This is NOT qlib IR (has sqrt(N)) or ICIR (no sqrt(N)).\n")
    md.append("## Signal & execution lag\n")
    md.append("- Signal at close t: `sign(close_t / close_{t-L} - 1)` where "
              "L in {20, 60, 120}.")
    md.append("- 1-day execution lag applied: signal computed at close t is traded "
              "at close t+1 and earns the t+1 -> t+2 log return. "
              "`PnL_t = position_{t-1} * log_ret_t`, with `position_{t-1} = signal_{t-2}`.")
    md.append("- Each equity curve starts on the first day the lagged position is "
              "valid (warmup dropped). All strategies trade 1 unit notional "
              "(long CNH = +1, short CNH = -1).\n")
    md.append("## Results table\n")
    md.append("| Strategy | total_return | CAGR | ann_vol_252 | sharpe_like | "
              "max_drawdown | calmar | win_rate_daily_% | turnover | n_flips | n_days | "
              "B&H_same_window_total_return |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for L in lookbacks:
        m = results[f"MOM{L}"]
        bhm = results[f"MOM{L}_BH_same_window"]
        md.append(
            f"| MOM{L} | {fmt(m['total_return'])} | {fmt(m['CAGR'])} | "
            f"{fmt(m['ann_vol_252'])} | {fmt(m['sharpe_like'])} | "
            f"{fmt(m['max_drawdown'])} | {fmt(m['calmar'])} | "
            f"{fmt(m['win_rate_daily_%'])} | {fmt(m['turnover'])} | "
            f"{m['n_flips']} | {m['n_days']} | {fmt(bhm['total_return'])} |"
        )
    # overall B&H
    obh = results["B&H_full"]
    md.append(
        f"| B&H_full | {fmt(obh['total_return'])} | {fmt(obh['CAGR'])} | "
        f"{fmt(obh['ann_vol_252'])} | {fmt(obh['sharpe_like'])} | "
        f"{fmt(obh['max_drawdown'])} | {fmt(obh['calmar'])} | "
        f"{fmt(obh['win_rate_daily_%'])} | 0 | 0 | {obh['n_days']} | "
        f"{fmt(obh['total_return'])} |"
    )
    md.append("")
    md.append("## Notes\n")
    md.append("- All variants apply the same 1-day execution lag and start their "
              "equity curves on their own first valid signal day, so cross-variant "
              "comparison is over slightly different windows (the B&H column "
              "matched to each variant's window makes the comparison fair).")
    md.append("- `max_drawdown` is peak-to-trough on the equity curve, as a "
              "fraction (e.g. -0.20 = -20%).")
    md.append("- `turnover` = mean of |delta position| per day; `n_flips` = count "
              "of position sign changes.")
    md.append("- Plot: `momentum_equity.png` shows each MOM strategy equity vs "
              "the buy-and-hold CNH equity on the same window, log y-axis.\n")
    md.append("## Which lookback wins?\n")
    # pick winner by sharpe-like among MOM variants
    best = max(lookbacks, key=lambda L: results[f"MOM{L}"]["sharpe_like"]
               if not np.isnan(results[f"MOM{L}"]["sharpe_like"]) else -1e9)
    md.append(f"By Sharpe-like ratio, **MOM{best}** wins "
              f"(sharpe_like = {fmt(results[f'MOM{best}']['sharpe_like'])}). "
              f"See full numbers above; the verdict is on the risk-adjusted "
              f"mean/vol (rf=0, no sqrt N) metric, NOT qlib IR/ICIR.")
    with open(os.path.join(OUT_DIR, "momentum.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Saved report: {os.path.join(OUT_DIR, 'momentum.md')}")


if __name__ == "__main__":
    main()
