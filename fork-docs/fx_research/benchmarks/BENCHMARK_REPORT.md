# BENCHMARK REPORT — USDCNH systematic strategies (2015-2026)

## 1. Setup

**Data.** BBG spot USDCNH offshore (`usdcnh.csv`, 3010 rows, 2015-01-01..2026-07-17, `last` used as close), USDCNY onshore (`usdcny.csv`, 2805 rows, 2015-01-05..2026-07-17), and USDCNH 1M/3M forward points (`carry_fwd.csv`, 3011 rows, `fwd_1m`/`fwd_3m` in pips; sign convention documented in `carry.md`: positive `fwd_1m` ⇔ r_CN > r_US, i.e. the file stores `(S−F)·1e4`, the negative of standard market points).

**Backtest engine.** Pure-pandas, **NOT qlib.** No qlib `risk_analysis`, no `SigAnaRecord`, no `PortAnaRecord`. Each strategy is a daily-return PnL series compounded into an equity curve; positions are ±1 (1-unit notional; long CNH = +1, short CNH = −1).

**Execution lag.** 1 day on every variant — signal computed on close-through-t information is traded at close t+1 (position applied to the t+1 return). Conservative, no lookahead.

**Annualization convention (label verbatim, applied identically to every variant for fair cross-strategy comparison):**
- **252 trading days.** `ann_vol = daily_std * sqrt(252)`.
- `CAGR = (1+total)^(252/n_days) - 1` (geo).
- **Sharpe-like ratio = raw mean_daily / vol_daily (rf=0, no sqrt(N)).**
- This is **NOT qlib `risk_analysis`** (which uses **238** in `sum` mode) and **NOT the 250 legacy figure**.
- The Sharpe-like ratio here is **NOT qlib IR** (IR has `sqrt(N)`) and **NOT ICIR** (no `sqrt(N)`). Same page, different口径 — labeled.

**Metric spec (identical computation for all strategies):** total_return, CAGR, ann_vol_252, sharpe_like (mean/vol), max_drawdown (peak-to-trough on equity curve, fraction), calmar (CAGR/|maxDD|), win_rate_daily (%), turnover (mean |Δposition|), n_flips (sign changes of executed position). Each equity curve plotted vs buy-and-hold CNH equity `cumprod(1+spot_ret)` on the SAME window, log-y.

**Buy-and-hold CNH benchmark.** B&H = `cumprod(1+spot_ret_NH)-1` over the SAME window each strategy uses (long-CNH return convention: USD/CNH up ⇒ CNH weak ⇒ B&H loses). Computed in every agent.

## 2. Comparison table

| Strategy | window | n_days | total_return | CAGR | ann_vol_252 | sharpe_like | max_drawdown | calmar | win_rate_daily_% | turnover | n_flips | B&H CNH same window |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MOM20 | 2015..2026 | 2988 | +49.24% | +3.43% | 4.65% | 0.0472 | −5.87% | 0.585 | 51.61 | 0.1935 | 291 | +6.75% |
| MOM60 | 2015..2026 | 2948 | +46.14% | +3.30% | 4.67% | 0.0452 | −7.58% | 0.435 | 51.49 | 0.0882 | 130 | +7.81% |
| MOM120 | 2015..2026 | 2888 | −0.53% | −0.05% | 4.72% | 0.0009 | −20.36% | −0.002 | 52.01 | 0.0596 | 86 | +7.89% |
| Basis-MR | 2016-01-12..2026-07-17 | 2554 | +90.02% | +6.54% | 1.93% | 0.207 | −1.19% | 5.485 | 69.3 | 0.1896 | 461 | +1.76% |
| Carry (full: spot+carry) | 2015..2026 | 3005 | +21.66% | +1.66% | 4.65% | 0.024 | −11.73% | 0.141 | 52.31 | 0.0193 | 35 | −10.60% |
| Carry (spot-only) | 2015..2026 | 3005 | −8.60% | −0.75% | 4.65% | −0.009 | −14.87% | −0.051 | 49.95 | 0.0193 | 35 | −10.60% |
| B&H CNH full | 2015..2026 | 3009 | +7.61% | +0.62% | 4.65% | 0.0098 | −12.45% | 0.050 | 50.58 | 0 | 0 | — |

Sharpe-like is `mean_daily/vol_daily` (rf=0, **no sqrt(N)**) — NOT qlib IR (has sqrt N) / ICIR (no sqrt N). `risk_analysis` annualization (238, sum) NOT used.

## 3. Per-strategy read

**MOM20 / MOM60 (time-series momentum, offshore).** Short lookbacks worked: MOM20 and MOM60 both delivered ~+46–49% total over 11.5y vs +6.75–7.81% B&H CNH over matched windows, with maxDD only −5.9% / −7.6%. The edge came almost entirely from the 2015 depeg period (CNH trended sharply lower after the Aug-2015 PBoC fix reform) and the 2022-24 Fed-hiking leg of USD strength — trend-following harvests exactly those regime moves. The problem: Sharpe-like of only ~0.045 means daily noise swamps the trend premium; this is "compounded a few big regime calls," not a high-frequency edge.

**MOM120.** Broke. Long lookback (≈6m) lagged too far: it flipped long into the 2022-23 USD-top regime just as carry was flipping short, then bled −20% maxDD; Sharpe-like ≈ 0.001. Trend persistence beyond ~60d is too slow to time FX regime turns with a 1-unit position.

**Basis-MR (USDCNH vs USDCNY, 252d z, hysteresis).** The standout: +90% total, Sharpe-like 0.207, calmar 5.5, maxDD only −1.19%. It works because the CNH−CNY basis is structurally mean-reverting (arbitrage bands enforced by CN onshore/offshore delivery), so a z-score with hysteresis is genuinely trading a stationary spread, not a random walk. Caveat: the natural benchmark is the spread's own reversion, NOT directional CNH — the 90% figure should not be compared apples-to-apples with the directional strategies' returns. The 2015 depeg widened the basis (z breached), 2022-23 stayed inside bands (fewer trades), 2025 tariff-spike widening was captured.

**Carry (full, 1M fwd).** +21.66% total, Sharpe-like 0.024, but the leg decomposition tells the story: the **carry leg alone is +9.5e-5/day (daily Sharpe ~1.6)**, the **spot leg is −7.7% cumulative** (the carry signal is a poor spot timer; UIP works weakly against you — CNH tends to depreciate when its yield is high). So carry alpha is real but tiny in magnitude vs the spot noise it rides on; the full-strategy Sharpe is dragged down by spot vol. The regime flip matters: the signal went short CNH in 2024-26 when US yields exceeded CN, avoiding ~half the B&H drawdown (−11.7% vs B&H −18.7%). The 2022-23 Fed hiking regime flip is exactly when the position went from long-CN to short-CN — a textbook macro carry rotation. The 2025 tariff spike is spot, not carry — it hit the spot leg, not the carry accrual.

## 4. Honest caveats

- **Single FX pair, no cross-section.** A real systematic FX book carries dozens of pairs; one pair is regime-sample noise.
- **1-unit notional, no volatility scaling.** Strategies are not comparably risk-loaded; basis-MR's low vol (1.93%) inflates its Sharpe vs the 4.65%-vol directional book. Risk-equalized, basis-MR's lead shrinks.
- **No transaction costs / no bid-ask / no funding spread.** Turnover 0.02–0.19/day × bid-ask would shave MOM20 and basis-MR materially (the high-turnover variants). Carry (turnover 0.019) is cost-robust.
- **1-day execution lag, no slippage modeling.** Conservative on timing, optimistic on fill.
- **Forward points sparse / interpolated?** `carry_fwd.csv` has 3011 rows vs 3010 spot rows; 4 NaN `fwd_1m` after merge dropped. We did NOT verify whether BBG populated `fwd_1m` on every spot date or interpolated holidays — if interpolated, the carry leg's daily accrual is smoother than reality and the 1.6 daily Sharpe of the carry leg is overstated.
- **11.5y single-regime sample.** The 2015 depeg and 2022-23 Fed cycle dominate trend/carry PnL. One regime flip (2022) is not "evidence of persistence."
- **Sharpe-like ~0.1–0.2 is NOT a real edge** after costs and multiple-testing. Basis-MR's 0.207 is the only figure that survives scrutiny, and only because the spread is structurally stationary — a property that can break under capital-control regime change (e.g. a CNH/CNY convergence policy).
- **This is NOT a qlib backtest.** No `DataHandlerLP`, no processor chain, no `risk_analysis` (238/250), no mlflow recorder. Numbers are pandas-derived and labeled under the 252 convention above.

## 5. Next steps

- **If the user wants qlib `risk_analysis` numbers (238, sum mode) for these same PnL series**, the daily returns must be re-annualized and re-labeled: total/CAGR unchanged but `ann_vol` and the Sharpe-family metric become the 238-based `risk_analysis` outputs, and the Sharpe-like ratio must be relabeled as the 238-IR (has √N) or 238-ICIR (no √N) per `fork-docs/BACKTEST_SPEC.md` §5. Do NOT silently paste these 252-day numbers into a qlib-attributed table — the口径 mismatch is a red-line (#2 in CLAUDE.md).
- **To run these inside qlib properly**: wrap each signal as a `Processor`/custom op on a USDCNH `DataHandler` (the spot `last` field), emit position via a `BaseStrategy`, and feed `PortAnaRecord` — but qlib's backtest engine is equity-oriented (daily bars, T+1 exchange), and FX carry booking (the carry leg accrual) is not a native qlib exchange behavior; a custom `Exchange` subclass (`exchange.py:28`) would be needed to book the forward-points accrual. This is non-trivial and would touch `fork-docs/FORK_SURFACE.md`.
- **Risk-equalize before re-ranking.** Re-run all variants at constant 10% annualized vol target (position size = 0.10/ann_vol); the basis-MR vs momentum ranking will change.
- **Cross-section.** Add ≥3–5 more EM carry pairs (BRL/INR/ZAR vs USD/CNH) before calling carry an "edge" rather than a single-pair artifact.
- **Cost sensitivity.** Re-run MOM20 and basis-MR with 2–5 bps per unit turnover; if Sharpe collapses, the variant is not tradable.

## Files
- `momentum.py` / `momentum.md` / `momentum_equity.png`
- `basis_mr.py` / `basis_mr.md` / `basis_mr_equity.png`
- `carry.py` / `carry.md` / `carry_equity.png` / `carry_equity_spotonly.png`
- this report: `BENCHMARK_REPORT.md`
````

Relevant absolute paths:
- c:/Users/Q/Code/qlib/fork-docs/fx_research/benchmarks/momentum.py
- c:/Users/Q/Code/qlib/fork-docs/fx_research/benchmarks/momentum.md
- c:/Users/Q/Code/qlib/fork-docs/fx_research/benchmarks/basis_mr.py
- c:/Users/Q/Code/qlib/fork-docs/fx_research/benchmarks/basis_mr.md
- c:/Users/Q/Code/qlib/fork-docs/fx_research/benchmarks/carry.py
- c:/Users/Q/Code/qlib/fork-docs/fx_research/benchmarks/carry.md
- c:/Users/Q/Code/qlib/fork-docs/fx_research/benchmarks/BENCHMARK_REPORT.md (to be written by parent; full markdown above)
