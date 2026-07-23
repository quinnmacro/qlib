# Time-series Momentum on USDCNH (offshore)

## Annualization convention (applied identically to every variant)

- 252 trading days. `ann_vol = daily_std * sqrt(252)`.
- `CAGR = (1+total)^(252/n_days) - 1`.
- Sharpe-like = `mean_daily / vol_daily`, rf=0, **no sqrt(N)**.
- This is NOT qlib `risk_analysis` (238, sum mode) and NOT the 250 legacy figure. This is NOT qlib IR (has sqrt(N)) or ICIR (no sqrt(N)).

## Signal & execution lag

- Signal at close t: `sign(close_t / close_{t-L} - 1)` where L in {20, 60, 120}.
- 1-day execution lag applied: signal computed at close t is traded at close t+1 and earns the t+1 -> t+2 log return. `PnL_t = position_{t-1} * log_ret_t`, with `position_{t-1} = signal_{t-2}`.
- Each equity curve starts on the first day the lagged position is valid (warmup dropped). All strategies trade 1 unit notional (long CNH = +1, short CNH = -1).

## Results table

| Strategy | total_return | CAGR | ann_vol_252 | sharpe_like | max_drawdown | calmar | win_rate_daily_% | turnover | n_flips | n_days | B&H_same_window_total_return |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MOM20 | 0.4924 | 0.0343 | 0.0465 | 0.0472 | -0.0587 | 0.5846 | 51.6064 | 0.1935 | 291 | 2988 | 0.0675 |
| MOM60 | 0.4614 | 0.0330 | 0.0467 | 0.0452 | -0.0758 | 0.4346 | 51.4925 | 0.0882 | 130 | 2948 | 0.0781 |
| MOM120 | -0.0053 | -0.0005 | 0.0472 | 0.0009 | -0.2036 | -0.0023 | 52.0083 | 0.0596 | 86 | 2888 | 0.0789 |
| B&H_full | 0.0761 | 0.0062 | 0.0465 | 0.0098 | -0.1245 | 0.0495 | 50.5816 | 0 | 0 | 3009 | 0.0761 |

## Notes

- All variants apply the same 1-day execution lag and start their equity curves on their own first valid signal day, so cross-variant comparison is over slightly different windows (the B&H column matched to each variant's window makes the comparison fair).
- `max_drawdown` is peak-to-trough on the equity curve, as a fraction (e.g. -0.20 = -20%).
- `turnover` = mean of |delta position| per day; `n_flips` = count of position sign changes.
- Plot: `momentum_equity.png` shows each MOM strategy equity vs the buy-and-hold CNH equity on the same window, log y-axis.

## Which lookback wins?

By Sharpe-like ratio, **MOM20** wins (sharpe_like = 0.0472). See full numbers above; the verdict is on the risk-adjusted mean/vol (rf=0, no sqrt N) metric, NOT qlib IR/ICIR.