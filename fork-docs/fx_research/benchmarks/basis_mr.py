"""Basis mean-reversion between USDCNH and USDCNY.

Strategy: basis = USDCNH_last - USDCNY_last (per common-day intersection,
NO forward fill). z = (basis - rolling_mean(basis,252)) / rolling_std(basis,252).
Entry |z|>1, exit |z|<0.5 (hysteresis), flat otherwise.
Convention: spread_return = log_ret(USDCNH) - log_ret(USDCNY).
  z>1  => CNH rich vs norm => basis expected to FALL => SHORT basis => pos=-1
          PnL = -1 * spread_return
  z<-1 => basis expected to RISE => LONG basis => pos=+1
          PnL = +1 * spread_return
1-day execution lag: z computed at close t, traded at t+1 (position applied
to spread_return at t+1).

Annualization convention (LABEL VERBATIM in outputs):
  - 252 trading days. ann_vol = daily_std * sqrt(252).
  - ann_ret (CAGR) = (1+total)^(252/n_days) - 1.
  - This is NOT qlib risk_analysis (238, sum mode) and NOT the 250 legacy.
  - Sharpe-like ratio = raw mean_daily / vol_daily (rf=0). NOT qlib IR
    (has sqrt(N)) / ICIR (no sqrt(N)).

Long/short 1-unit notional; long CNH = +1, short CNH = -1.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.dirname(BASE)
OUT = BASE

NH = pd.read_csv(os.path.join(DATA, "usdcnh.csv"), index_col=0, parse_dates=True)
NY = pd.read_csv(os.path.join(DATA, "usdcny.csv"), index_col=0, parse_dates=True)

# Use 'last' as close.
nh_close = NH["last"].rename("usdcnh")
ny_close = NY["last"].rename("usdcny")

# Intersection of dates (NO forward-fill). Gap days are non-trading for both.
common = nh_close.index.intersection(ny_close.index)
nh_c = nh_close.loc[common]
ny_c = ny_close.loc[common]
print(f"Common trading days: {len(common)}  range {common[0].date()}..{common[-1].date()}")

# Log returns per common day (consecutive common days).
nh_ret = np.log(nh_c / nh_c.shift(1))
ny_ret = np.log(ny_c / ny_c.shift(1))
spread_ret = nh_ret - ny_ret  # spread_return (log)

# Basis (price level) per common day.
basis = (nh_c - ny_c).rename("basis")

# Rolling z-score, 252-day window on basis levels.
roll = basis.rolling(252)
mu = roll.mean()
sd = roll.std()
z = (basis - mu) / sd

# Position signal with hysteresis. Compute on info-available basis (close t),
# then apply with 1-day lag (trade t+1).
entry_hi = 1.0   # z>1 enter short basis
entry_lo = -1.0  # z<-1 enter long basis
exit_hi = 0.5    # |z|<0.5 exit
exit_lo = -0.5

n = len(z)
pos_signal = pd.Series(0.0, index=z.index, dtype=float)
cur = 0.0
# Walk forward: state machine using z at time t (known at close t).
for i in range(n):
    zi = z.iloc[i]
    if np.isnan(zi):
        # not enough history; stay flat / carry forward
        pos_signal.iloc[i] = cur
        continue
    if cur == 0:
        if zi > entry_hi:
            cur = -1.0
        elif zi < entry_lo:
            cur = +1.0
        # else stay flat
    elif cur == -1.0:
        # short basis; exit when |z|<0.5 i.e. z>-0.5 (z rising back through band)
        if zi > exit_lo and zi < exit_hi:
            cur = 0.0
        # also flip side if opposite entry breaches
        elif zi < entry_lo:
            cur = +1.0
    elif cur == +1.0:
        if zi > exit_lo and zi < exit_hi:
            cur = 0.0
        elif zi > entry_hi:
            cur = -1.0
    pos_signal.iloc[i] = cur

# 1-day execution lag: position applied to spread_return at t+1.
pos = pos_signal.shift(1).fillna(0.0)

# Strategy daily PnL: pos * spread_return.
strat_ret = pos * spread_ret
# Drop warmup (first 252 days have NaN z) and first lag day.
valid = z.notna() & spread_ret.notna() & pos.notna()
# Enforce valid window starting where z first defined + lag.
first_valid = valid[valid].index[0]
strat_ret = strat_ret.loc[first_valid:]
pos_v = pos.loc[first_valid:]
spread_ret_v = spread_ret.loc[first_valid:]

# Equity curve.
equity = (1 + strat_ret).cumprod()
total_return = equity.iloc[-1] - 1
n_days = len(strat_ret)
cagr = (1 + total_return) ** (252 / n_days) - 1
ann_vol = strat_ret.std() * np.sqrt(252)
sharpe_like = strat_ret.mean() / strat_ret.std() if strat_ret.std() > 0 else np.nan
# Max drawdown on equity curve.
roll_max = equity.cummax()
dd = equity / roll_max - 1
max_dd = dd.min()
calmar = cagr / abs(max_dd) if max_dd != 0 else np.nan
win_rate = (strat_ret > 0).sum() / (strat_ret != 0).sum() * 100 if (strat_ret != 0).sum() else np.nan
turnover = pos_v.diff().abs().mean()
n_flips = int((np.sign(pos_v).diff().fillna(0) != 0).sum())

# Buy-and-hold CNH on the SAME window (directional reference only).
spot_ret = nh_ret.loc[first_valid:]
bh_equity = (1 + spot_ret).cumprod()
bh_total = bh_equity.iloc[-1] - 1
bh_cagr = (1 + bh_total) ** (252 / len(spot_ret)) - 1
bh_vol = spot_ret.std() * np.sqrt(252)
bh_sharpe = spot_ret.mean() / spot_ret.std() if spot_ret.std() > 0 else np.nan
bh_roll_max = bh_equity.cummax()
bh_dd = bh_equity / bh_roll_max - 1
bh_maxdd = bh_dd.min()
bh_calmar = bh_cagr / abs(bh_maxdd) if bh_maxdd != 0 else np.nan
bh_win = (spot_ret > 0).sum() / (spot_ret != 0).sum() * 100 if (spot_ret != 0).sum() else np.nan

print("\n=== METRICS (252-day annualization; NOT qlib 238/250) ===")
print(f"window: {first_valid.date()} .. {strat_ret.index[-1].date()}  ({n_days} days)")
print(f"BASIS MR:  total={total_return*100:.2f}%  CAGR={cagr*100:.2f}%  vol={ann_vol*100:.2f}%  sharpe_like={sharpe_like:.3f}  maxDD={max_dd*100:.2f}%  calmar={calmar:.3f}  win={win_rate:.1f}%  turnover={turnover:.3f}  flips={n_flips}")
print(f"B&H CNH :  total={bh_total*100:.2f}%  CAGR={bh_cagr*100:.2f}%  vol={bh_vol*100:.2f}%  sharpe_like={bh_sharpe:.3f}  maxDD={bh_maxdd*100:.2f}%  calmar={bh_calmar:.3f}  win={bh_win:.1f}%")

# Equity plot vs B&H CNH, log-y.
fig, ax = plt.subplots(figsize=(11, 6))
ax.plot(equity.index, equity.values, label="Basis MR (long/short)", lw=1.4)
ax.plot(bh_equity.index, bh_equity.values, label="Buy&Hold CNH (directional ref)", lw=1.0, alpha=0.7)
ax.set_yscale("log")
ax.set_title("Basis Mean-Reversion (USDCNH-USDCNY) vs Buy&Hold CNH\n252-day ann; equity = cumprod(1+ret); log-y")
ax.set_xlabel("date")
ax.set_ylabel("equity (log)")
ax.legend(loc="best")
ax.grid(True, which="both", alpha=0.3)
fig.tight_layout()
png = os.path.join(OUT, "basis_mr_equity.png")
fig.savefig(png, dpi=110)
plt.close(fig)
print(f"\nsaved: {png}")

# Write metrics table to md.
md = []
md.append("# Basis Mean-Reversion (USDCNH vs USDCNY)\n")
md.append("**Strategy**: relative-value long/short on the CNH-CNY basis. "
          "`basis = USDCNH_last - USDCNY_last` per common-day intersection "
          "(NO forward-fill; gap days non-trading for both). "
          "`z = (basis - mean_252(basis)) / std_252(basis)`. "
          "Entry `|z|>1`, exit `|z|<0.5` (hysteresis), flat otherwise. "
          "1-day execution lag (z at close t, traded t+1).\n")
md.append("**Convention**: `spread_return = log_ret(USDCNH) - log_ret(USDCNY)`. "
          "z>1 (CNH rich vs its norm) => basis expected to FALL => SHORT basis => pos=-1 => PnL = -1 * spread_return. "
          "z<-1 => pos=+1 => PnL = +1 * spread_return. 1 unit notional; long CNH=+1, short CNH=-1.\n")
md.append("**Annualization (VERBATIM labels)**: 252 trading days; "
          "`ann_vol = daily_std * sqrt(252)`; `CAGR = (1+total)^(252/n_days)-1`. "
          "This is NOT qlib `risk_analysis` (238, sum mode) and NOT the 250 legacy figure. "
          "Sharpe-like ratio = raw `mean_daily / vol_daily` (rf=0) — NOT qlib IR (has sqrt(N)) / ICIR (no sqrt(N)).\n")
md.append(f"\n**Window**: {first_valid.date()} .. {strat_ret.index[-1].date()} ({n_days} days; "
          f"first 252 used for z warmup, +1 lag).\n")
md.append(f"\n**Common-day intersection**: {len(common)} days "
          f"({common[0].date()}..{common[-1].date()}).\n")
md.append("\n## Metrics\n")
md.append("| strategy | total_return | CAGR | ann_vol_252 | sharpe_like | max_drawdown | calmar | win_rate_daily | turnover | n_flips | vs_B&H_CNH(total) |")
md.append("|---|---|---|---|---|---|---|---|---|---|---|")
md.append(f"| basis_mr | {total_return*100:.2f}% | {cagr*100:.2f}% | {ann_vol*100:.2f}% | {sharpe_like:.3f} | {max_dd*100:.2f}% | {calmar:.3f} | {win_rate:.1f}% | {turnover:.4f} | {n_flips} | {bh_total*100:.2f}% |")
md.append(f"| buy_hold_cnh | {bh_total*100:.2f}% | {bh_cagr*100:.2f}% | {bh_vol*100:.2f}% | {bh_sharpe:.3f} | {bh_maxdd*100:.2f}% | {bh_calmar:.3f} | {bh_win:.1f}% | — | — | — |")
md.append("\n## Notes\n")
md.append("- This is a **relative-value / long-short** strategy. Buy&Hold CNH is only a "
          "**directional reference**, not the natural benchmark. The natural performance "
          " Yardstick for a basis-reversion trade is the spread itself (mean-reverting by construction), "
          "so the equity plot's separation from B&H CNH reflects basis PnL, not directional CNH beta (which the strategy intentionally carries ~zero of).")
md.append("\n- Hysteresis bands (|z|>1 enter, |z|<0.5 exit) suppress churn at the band edge; "
          f"observed position flips (sign changes) = {n_flips} over {n_days} days, "
          f"mean turnover |Δpos| = {turnover:.4f}.")
md.append("\n- Execution lag of 1 day is conservative (no lookahead); z uses only close-through-t info.")
md.append("\n## Equity curve\n")
md.append(f"![equity](basis_mr_equity.png)")
md_path = os.path.join(OUT, "basis_mr.md")
with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print(f"saved: {md_path}")

# Persist machine-readable metrics for the orchestrator.
print("\n--- JSON-ish ---")
print(f"basis_mr: total={total_return} cagr={cagr} ann_vol_252={ann_vol} sharpe_like={sharpe_like} max_drawdown={max_dd} calmar={calmar} win_rate={win_rate} turnover={turnover} n_flips={n_flips}")
print(f"buy_hold_cnh: total={bh_total} cagr={bh_cagr} ann_vol_252={bh_vol} sharpe_like={bh_sharpe} max_drawdown={bh_maxdd}")
