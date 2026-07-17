# Descriptive Statistics: USDCNH & USDCNY

All annualization uses **252 trading days** convention. The `annualized_vol_252d` here is **NOT** qlib `risk_analysis` (which annualizes by 238 in sum mode — see `fork-docs/BACKTEST_SPEC.md`). The `sharpe_like_mean_vol_ratio` is a raw mean/vol ratio (rf=0) and is **NOT** qlib IR (which has sqrt(N)) or ICIR (no sqrt(N)). Descriptive only — no backtest.

- USDCNH: 2015-01-01 → 2026-07-17 (3010 obs)
- USDCNY: 2015-01-05 → 2026-07-17 (2805 obs)
- Aligned common dates for cross-stats: 2805

## Per-series statistics

| metric | USDCNH | USDCNY |
|---|---|---|
| n_obs (close rows) | 3010 | 2805 |
| first_date | 2015-01-01 | 2015-01-05 |
| last_date | 2026-07-17 | 2026-07-17 |
| years_span (calendar) | 11.540 | 11.529 |
| first_close | 6.2190 | 6.2199 |
| last_close | 6.7794 | 6.7779 |
| min_close | 6.1884 | 6.1884 |
| max_close | 7.4257 | 7.3463 |
| total_return_pct | 9.0111 | 8.9712 |
| CAGR_pct (calendar-year basis) | 0.7505 | 0.7480 |
| daily_logret_mean | 2.867381e-05 | 3.063962e-05 |
| daily_logret_std (ddof=1) | 2.928423e-03 | 2.492614e-03 |
| annualized_vol_252d_pct (std*sqrt(252)) | 4.6487 | 3.9569 |
| annualized_return_252d_geo_pct (mean_log*252) | 0.7226 | 0.7721 |
| sharpe_like_mean_vol_ratio (rf=0) | 0.1554 | 0.1951 |
| daily_ret_skew | -0.0762 | -0.0353 |
| daily_ret_excess_kurtosis (Fisher) | 7.0038 | 5.5155 |
| max_one_day_gain_pct | 2.7853 (2015-08-11) | 1.8503 (2015-08-11) |
| max_one_day_loss_pct | -1.9804 (2022-11-04) | -1.5942 (2022-11-04) |
| pct_days_abs_ret_gt_1pct | 1.0302 | 0.4993 |

## Cross-series (USDCNH vs USDCNY, aligned common dates)

| metric | value |
|---|---|
| common_obs (aligned dates) | 2805 |
| daily_logret_corr | 0.8269 |
| beta_CNH_on_CNY (OLS) | 1.0009 |
| alpha_CNH_on_CNY_daily (logret) | -4.082024e-07 |
| basis_mean (USDCNH-USDCNY) | 0.0053 |
| basis_std (ddof=1) | 0.0162 |
| basis_min | -0.0877 — max CNH discount (CNH stronger) date=2017-01-05 |
| basis_max | 0.1405 — max CNH premium (CNH weaker than CNY) date=2016-01-06 |

## Notes & conventions

- **Close**: `last` column from each CSV.
- **Daily returns**: log returns `ln(P_t / P_{t-1})` on the `last` series; skew/kurtosis/max gain-loss computed on simple returns `(P_t/P_{t-1} - 1)` (kurtosis is Fisher excess, `pandas.Series.kurtosis`).
- **Annualized vol (252d)**: `std(daily logret, ddof=1) * sqrt(252)` — labeled explicitly as **NOT qlib `risk_analysis`** (which uses 238, sum mode).
- **Annualized return (252d geo)**: `mean(daily logret) * 252` (geometric mean × trading days). CAGR is reported separately on a calendar-year basis `(last/first)^(365.25/days)-1` for cross-check.
- **Sharpe-like ratio**: `ann_return / ann_vol` (rf=0). Labeled as **raw mean-vol ratio, NOT qlib IR/ICIR** (IR uses sqrt(N); ICIR has no sqrt(N) — see `fork-docs/BACKTEST_SPEC.md`).
- **Beta**: OLS slope of CNH daily log-return on CNY daily log-return (cov/var, ddof=1). Alpha is the OLS intercept (daily, log-return).
- **Basis** = `USDCNH - USDCNY` in price units. Basis > 0 ⇒ CNH quotes higher (weaker CNY offshore) ⇒ "CNH weaker than CNY" / CNH premium. Basis < 0 ⇒ CNH stronger than CNY / CNH discount.
- All figures are **descriptive**; no backtest, no qlib backtest engine invoked.

## Charts

- Rolling 21d & 63d realized vol (annualized, 252d): `charts/rolling_vol.png`
- Basis histogram: `charts/basis_hist.png`