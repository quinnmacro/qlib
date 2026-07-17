# FX Visualization Set — USDCNH & USDCNY

Charts for the CNH/CNY pair, 2015-01 → 2026-07. Source CSVs: `usdcnh.csv` (3010 rows), `usdcny.csv` (2805 rows). All saved at dpi=120 under `charts/`. Palette: **CNH = blue (#1f77b4)**, **CNY = red (#d62728)**; basis/z-score series use green and purple.

Common event markers (vertical dashed grey lines) on multi-series charts: 2015-08 depeg, 2022-10, 2025-08.

| File | Caption |
|---|---|
| `charts/price_overlay.png` | USDCNH & USDCNY `last` time series on log-y, 2015–2026, with event lines at 2015-08 depeg, 2022-10, 2025-08. CNH (blue) trades at a slight premium/discount vs onshore CNY (red). |
| `charts/basis_spread.png` | Top: USDCNH − USDCNY basis over time (mean ≈ +0.0053, std ≈ 0.0162). Bottom: same basis as a 252-day rolling z-score with ±2σ guides — flags regime episodes (2015 depeg widening, 2022-10 spike, 2025-08 dislocation). |
| `charts/returns_hist.png` | Daily log-return histograms overlaid (log-density y), with annotated mean/std — CNH mean ≈ 2.87e-5, std ≈ 0.293%; CNY mean ≈ 3.06e-5, std ≈ 0.249%. CNH shows fatter tails / higher dispersion as expected for the offshore rate. |
| `charts/drawdown.png` | Underwater series (price/cummax − 1) for both series, in %. Filled to zero; the 2015 depeg, 2022 selloff, and 2025-08 episodes show as the deepest troughs. |
| `charts/rolling_vol.png` | Two-panel rolling annualized vol (√252 scaling): top = 21-day window, bottom = 63-day window, both series. CNH vol consistently above CNY; spikes align with the marked events. |

## Notes on construction
- Log returns computed as `log(P_t / P_{t-1})`; series aligned on common dates only for the basis (dropna both).
- Basis z-score uses a 252-day rolling mean/std; ±2 guide lines for visual reference.
- Annualized vol uses √252 scaling — note this convention for any cross-comparison.
- Log-y on price overlay and log-density on histograms both chosen because daily-return distributions are sharply peaked near zero.
- Script: `viz_build.py` (re-runnable).
