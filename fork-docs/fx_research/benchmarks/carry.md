# CARRY on USDCNH (offshore) — 1M forward points

**Window:** 2015-01-02 .. 2026-07-17, n=3005 trading days (USDCNH offshore calendar).
**Asset:** USDCNH offshore spot (`last`), 1M forward points `fwd_1m` from `carry_fwd.csv` (pips), merged on date.
**Notional:** 1 unit. Long CNH = +1, short CNH = -1. 1-day lag on signal (decide on close t-1, earn day-t move + carry accrued at t-1).

## Annualization convention (label verbatim)

- **252 trading days.** `ann_vol = daily_std * sqrt(252)`. `CAGR = (1+total)^(252/n_days)-1`.
- This is **NOT qlib `risk_analysis`** (which uses **238** in `sum` mode) and **NOT the 250 legacy figure**.
- The **Sharpe-like ratio = raw mean_daily / vol_daily (rf=0)**. This is **NOT qlib IR** (IR has `sqrt(N)`) and **NOT ICIR** (no `sqrt(N)`). Same page, different口径 — labeled.

## CIP sign derivation (re-derived; the draft formula's leading minus is INVERTED for this data)

USD/CNH spot `S = last` (CNH per 1 USD). 1M forward points `fwd_1m` in pips (1 pip = 1e-4).

CIP in log form, 1M horizon:  `ln(F/S) ≈ r_US − r_CN`  ⇒  `r_CN − r_US ≈ −(F−S)/S`.
Standard market forward points for USD/CNH = `(F − S)·1e4`, so with standard points the formula is `r_CN − r_US = −(fwd/1e4)/S·12`. That is the draft in the task.

**But `carry_fwd.csv` does NOT use the standard `(F−S)` convention.** Cross-check against the known rate regime:

| year | spot (avg) | fwd_1m (avg) | known yield regime | `r_CN − r_US` (reality) |
|---|---|---|---|---|
| 2015 | 6.305 | +211 | CN policy ~5%, Fed ~0.25% | **+** (~+4.5%) |
| 2018 | 6.617 | +79  | CN ~3.0%, US ~2.2% | + (~+0.8%) |
| 2020 | 6.902 | +104 | CN ~3.0%, US ~0.4% | + (~+2.6%) |
| 2022 | 6.741 | +15  | CN ~2.6%, US ~2.5% | ~0 |
| 2024 | 7.209 | −150 | CN ~2.0%, US ~5.3% | **−** (~−3.3%) |
| 2025 | 7.191 | −154 | CN ~2.0%, US ~4.5% | − (~−2.5%) |
| 2026 | 6.857 | −140 | CN ~2.0%, US ~4.4% | − (~−2.4%) |

`fwd_1m` is **positive exactly when `r_CN > r_US`**. So in this file `fwd_1m ≈ (r_CN − r_US)·(S·1e4)/12`, i.e. the series is the **negative** of standard market forward points (it equals `(S − F)·1e4`). The correct sign for this data is therefore:

```
r_CN − r_US  (annualized)  =  (fwd_1m / 10000) / spot_last * 12        # NO leading minus
```

The draft formula's leading minus would invert the trade (short CNH when CN yields more, paying carry). Verified: with the corrected sign the carry leg is a **positive** accrual on average and the full strategy is profitable (+21.66%); with the inverted sign it would be a steady bleed. **Sign documented and corrected.**

## Strategy spec

```
carry_signal_t   = (fwd_1m_t / 1e4) / last_t * 12           # annualized r_CN − r_US
position_t       = sign(carry_signal_t)                     # +1 long CNH if CN>US, −1 short CNH if US>CN
spot_ret_t       = last_{t-1}/last_t − 1  =  −pct_change(USD/CNH)   # long-CNH return in USD
PnL_full_t       = position_{t-1} * ( spot_ret_t + carry_signal_{t-1}/252 )   # spot + carry legs
PnL_spot_t       = position_{t-1} *   spot_ret_t                              # carry leg NOT booked
```

`spot_ret` is defined as the **long-CNH** return (USD/CNH up ⇒ CNH weak ⇒ long CNH loses ⇒ negative), so that B&H CNH = `cumprod(1+spot_ret)` is economically a long-CN-Holding position. This keeps the carry leg sign consistent: `position=+1` (long CNH, CN yields more) books `+carry/252` per day.

## Results (metric spec, identical computation for fair comparison)

| strategy | total_return | CAGR | ann_vol_252 | sharpe_like | max_drawdown | calmar | win_rate | turnover | n_flips | vs B&H CNH |
|---|---|---|---|---|---|---|---|---|---|---|
| **CARRY (spot+carry legs, 1M fwd)** | **+21.66%** | +1.66% | 4.65% | 0.024 | −11.73% | 0.141 | 52.31% | 0.0193 | 35 | −10.60% |
| CARRY spot-only (no carry leg) | −8.60% | −0.75% | 4.65% | −0.009 | −14.87% | −0.051 | 49.95% | 0.0193 | 35 | −10.60% |
| B&H CNH (same window) | −10.60% | −0.94% | 4.65% | −0.011 | −18.68% | −0.050 | 48.99% | 0.0000 | 0 | — |

B&H CNH total over the same window = **−10.60%** (CNH depreciated over 2015-2026; offshore USD/CNH went 6.22 → 6.78, i.e. CNH weakened, so holding CNH lost ~10.6% in USD terms).

## Commentary

### Which leg drives PnL — the carry leg, decisively

Daily mean / std of each leg (full variant, across the 3005-day window):

| leg | mean/day | std/day | mean/std (daily Sharpe-like of the leg) |
|---|---|---|---|
| spot leg (`pos·spot_ret`) | −2.57e-5 | 2.93e-3 | −0.009 |
| carry leg (`pos·carry/252`) | **+9.52e-5** | 5.97e-5 | **1.595** |

- The **carry leg is the entire source of alpha**: +9.5e-5/day × 3005 ≈ +28.6% gross carry harvest, while the spot leg nets **−7.7%** gross (the direction signal is a *poor spot timer* — being long CNH when CN yields more does not predict CNH appreciation; if anything CNH tends to depreciate when its yield is high, the classic FX carry "uncovered interest parity puzzle" working against you, though weakly here).
- Full strategy = +21.66%, spot-only = −8.60%. The **~30pp gap** between them is the carry leg, net of the spot leg's drag and the path-dependence of compounding.
- The carry leg's mean/std is ~1.6 (daily), far above the spot leg's −0.009 — the carry leg is small but very steady (std 6e-5 vs spot's 2.9e-3). The **full strategy's Sharpe-like (0.024) is dragged down by the spot leg's volatility**: the carry alpha is real but small in magnitude relative to the spot noise it rides on. This is the classic carry-trade Sharpe profile: steady small accrual, occasional spot drawdowns.
- Max drawdown: full −11.73% vs B&H −18.68% — the carry signal's regime-aware long/short stance *reduces* drawdown vs naive long CNH (notably by going short CNH in 2024-2026 when US yields exceeded CN, avoiding the CNH depreciation of those years).

### Signal flips — very infrequent, regime-persistent

- The carry signal flips sign **35 times** over 3005 days (~11.5 years) — roughly **3 flips per year**, i.e. the r_CN − r_US differential changes sign only at macro regime shifts (2015-2017 CN>US, 2018-2021 mostly CN>US but narrowing, 2022 near-flat, 2023-2026 US>CN).
- Position was **long CNH 62.1%** of days, **short CNH 37.7%** of days (a handful of zero-signal days where fwd_1m=0).
- Turnover (mean |Δposition|) = 0.0193 — tiny, consistent with the infrequent flips. This is a low-turnover macro carry strategy, not a fast-trading one.

### Why Sharpe-like is low despite positive carry

The carry leg earns ~+28.6% cumulatively but with a spot leg whose **std is 49x larger** than the carry leg's std, the combined daily Sharpe (mean_full/std_full ≈ 0.024) is modest. Annualized, the carry leg alone would Sharpe ≈ 1.6·√252/... — the leg itself is high-quality; the problem is we are forced to hold the spot exposure (the carry is only bookable by holding the FX position). A carry strategy that could shed the spot leg (e.g. delta-hedge the spot) would lift Sharpe dramatically — but that is a different product.

## Files

- `carry.py` — strategy + metric computation + plots.
- `carry_equity.png` — full CARRY (spot+carry) equity vs B&H CNH, log-y.
- `carry_equity_spotonly.png` — spot-only variant vs B&H CNH, log-y (for reference).

## Caveats

- `fwd_1m` is treated as a daily 1M forward series observed at each spot date; the CIP annualization (`*12`) treats it as a rolling 1M horizon repriced daily. This is the standard approximation; it ignores day-count and the small compounding gap between 1M and 1/252.
- No transaction costs modeled. Given turnover 0.0193 (≈3 sign-flips/year, mostly full ±1 swings), cost drag is small (~bps/flip) and would not change the conclusion that carry drives PnL.
- The 4 NaN `fwd_1m` rows (dropped on merge) and the leading NaN from `shift(1)` reduce the effective window by ~5 days at the start; B&H is computed on the identical post-drop window for fair comparison.
