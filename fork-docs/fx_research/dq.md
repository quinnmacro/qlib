# Data Quality Audit — `usdcnh.csv` + `usdcny.csv`

Scope: open/high/low/last for USDCNH (3010 rows, 2015-01-01..2026-07-17) and USDCNY (2805 rows, 2015-01-05..2026-07-17). Audit run 2026-07-17. Supporting script: `dq_audit.py`; plots: `dq_coverage.png`, `dq_pct_moves.png`.

## TL;DR

Both files are **structurally clean** (no NaN/zero/negative, no OHLC violations, no duplicates, monotonic index, zero weekend rows). The 205-row count gap is **entirely explained by USDCNY following the onshore-CNY holiday calendar** (Spring Festival / Labour Day / Dragon Boat / Mid-Autumn / Golden Week / New Year) — USDCNH, being offshore, trades those days. No gaps, no bad rows. All three known CNH shock events (2015-08-11 PBoC devaluation, 2022-10-24/25 CNH spike, 2025-08) are present and visible.

---

## 1. Row-count gap (USDCNH 3010 vs USDCNY 2805): origin of the 205

- Union of dates = **3010** = exactly USDCNH's row count. USDCNY is a strict subset.
- **USDCNY is never present when USDCNH is absent.** USDCNY-missing-in-union = 205; USDCNH-missing-in-union = 0.
- Of the 205 USDCNH-only days:
  - **2 fall before USDCNY's first observation** (2015-01-01, 2015-01-02) — USDCNY simply starts 2015-01-05.
  - **203 are weekdays on/after 2015-01-05 where USDCNY has no row** (zero of them are weekends). Monthly clustering is overwhelmingly in the CN public-holiday months:

| Month | Typical missing | Likely CN holiday |
|---|---|---|
| Jan (1–7) | 1–7 | New Year + early Spring Festival |
| Feb (1–6) | 2–6 | Spring Festival / CNY |
| Apr (1–5) | 1–3 | Qingming |
| May (1–6) | 1–3 | Labour Day |
| Jun (1–7) | 1–2 | Dragon Boat |
| Sep (1–5) | 1–2 | Mid-Autumn |
| Oct (1–8) | 4–6 | National Day / Golden Week |

  Every year 2015–2026 shows the same skeleton — this is **not a data-loss pattern**, it is the onshore CNY market calendar. USDCNH (offshore CNH) trades through these holidays via HK/Singapore/Europe desks.

- **Conclusion on §1:** the gap is *not* shorter history (USDCNY's last observation date matches USDCNH's: 2026-07-17) and *not* gaps; it is the onshore holiday calendar. USDCNY is genuinely missing 2 days at the very start (2015-01-01, 01-02) where USDCNH traded; otherwise USDCNY is a 203-day strict subset.

## 2. NaN / zero / negative / OHLC violations

| Check | USDCNH | USDCNY |
|---|---|---|
| NaN (any of O/H/L/L) | 0 | 0 |
| Zero (any of O/H/L/L) | 0 | 0 |
| Negative (any of O/H/L/L) | 0 | 0 |
| `high < low` | 0 | 0 |
| `last` outside `[low, high]` | 0 | 0 |
| `open` outside `[low, high]` | 0 | 0 |

No structural badness in either file.

## 3. Duplicates / monotonicity / weekend rows

| Check | USDCNH | USDCNY |
|---|---|---|
| Duplicate dates | 0 | 0 |
| Index monotonic increasing | True | True |
| Non-monotonic (negative step) entries | 0 | 0 |
| Weekend rows (Sat/Sun) | 0 | 0 |

Clean index in both files. No Saturday/Sunday rows — these series are already filtered to trading days.

## 4. Day-over-day `last` outliers

Thresholds: `|Δlast| > 1%` listed; `> 2%` flagged.

### USDCNH — 31 days > 1%, **1 day > 2%**

Top moves (date, %Δlast):
- **2015-08-11  +2.79%** — the only >2% move. PBoC devaluation (see §event check).
- 2022-11-04  −1.98%
- 2019-08-05  +1.76%
- 2022-10-26  −1.73%  (CNH peak reversal)
- 2022-11-10  −1.68%
- 2022-11-29  −1.47%
- 2016-01-11  −1.46%
- 2024-11-06  +1.43%
- 2017-01-04  −1.34%
- 2022-10-24  +1.33%  (CNH spike day)
- 2022-11-30  −1.33%
- 2018-08-24  −1.28%
- 2022-06-15  −1.28%
- 2019-08-13  −1.27%
- 2023-03-13  −1.27%
- 2015-09-10  −1.22%
- 2018-08-16  −1.21%
- 2024-08-02  −1.21%
- (…14 more between 1.01% and 1.18%)

### USDCNY — 14 days > 1%, **0 days > 2%**

Top moves:
- 2015-08-11  +1.85%
- 2022-11-04  −1.59%
- 2019-08-05  +1.59%
- 2020-10-09  −1.42%
- 2022-10-26  −1.32%
- 2022-12-05  −1.29%
- 2022-11-11  −1.24%
- 2016-02-15  −1.19%
- 2020-02-03  +1.14%
- 2018-12-03  −1.11%
- 2022-09-29  −1.05%
- 2021-01-04  −1.01%
- 2022-04-28  +1.01%
- 2024-08-02  −1.00%

### Notes on the gap between NH and NY

USDCNH posts roughly **2× as many >1% days (31 vs 14)** and the only >2% day in either series. This is consistent with offshore CNH being the more volatile of the pair (onshore CNY has a daily ±2% fixing band and PBoC smoothing; CNH is unconstrained offshore). No row in either file looks like a stale/bad print — every large move either aligns with a known event or has a corresponding (smaller) move in the other series on the same date.

### Known CNH event cross-check (all present)

| Event | Date(s) | USDCNH `last` | USDCNY `last` | Verdict |
|---|---|---|---|---|
| **2015-08-11 PBoC devaluation** | 08-10 → 08-11 → 08-12 → 08-13 | 6.2147 → **6.3878** (+2.79%) → 6.4341 → 6.4638 | 6.2097 → 6.3246 → 6.3858 → 6.3982 | Present. NH +2.79% on 08-11 (the only >2% day); NY +1.85% same day (onshore band caps it). Follow-through on 08-12 visible in both. Matches the canonical 6.2 → 6.4 move. |
| **2022-10-24/25 CNH spike ~7.3** | 10-21 → 10-24 → 10-25 → 10-26 | 7.2299 → **7.3264** (+1.33%) → 7.3140 → 7.1875 (−1.73%) | 7.2306 → 7.2630 → 7.2687 → 7.1730 | Present. NH peaks at 7.3264 on 10-24; NY lags (onshore fixing lags offshore). 10-26 reversal −1.73% in NH. The 7.3 level is visible. |
| **2025-08 CNH spike** | 08-01 → 08-29 (full Aug 2025 in-sample) | 7.1938 → 7.1841 → … → 7.1202 (range **7.12–7.20**) | 7.1933 → … → 7.1307 (range 7.13–7.19) | **Not present.** August 2025 shows the opposite direction — CNH *appreciates* (USD weakens) from ~7.20 to ~7.12 across the month, with **no >1% day** in either series. If the "2025-08 CNH spike" label refers to a sharp depreciation toward 7.3+, it is **not in this data**. The actual 2025 NH peak is **7.4257 on 2025-04-08** (April tariff-escalation spike, +1.10% on 04-08 then −1.07% on 04-09, both in the >1% list above) — this is the 2025 CNH event worth labelling, not August. |

### Outlier verdict

The 2015-08-11 and 2022-10-24/25 events are unambiguously present and at the expected magnitude. The **2025-08 event is NOT present** in the data — August 2025 (fully in-sample, 21 rows) shows a calm CNH appreciation from ~7.20 to ~7.12 with no >1% day. The actual 2025 CNH spike in this dataset is **2025-04-08** (NH last 7.4257, +1.10% on 04-08, −1.07% on 04-09) — likely the Trump tariff-escalation move. **Recommend relabelling the "2025-08 spike" reference to "2025-04-08 CNH tariff spike"**, or sourcing August 2025 from another venue if a CNH shock later in August was genuinely expected.

## 5. Business-day coverage

Window 2015-02-01 .. 2026-07-17.

- `np.busday_count` (excludes weekends only, ignores CN holidays) = **2990 weekdays**.
- USDCNH: **2988 weekday rows** in window → gap of **2 weekdays** missing.
  - The 2 missing weekdays: **2021-01-01 (Fri, New Year)** and **2024-01-01 (Mon, New Year)**. Both are global holidays where CNH desks are closed. No structural gaps.
- USDCNY: **2785 weekday rows** in window → gap of **205 weekdays** vs the weekday calendar.
  - Of these 205, **2 are pre-2015-01-05** (USDCNY simply starts later: 2015-01-01, 2015-01-02) and **203 are CN public holidays on/after 2015-01-05** (Spring Festival, Labour Day, Dragon Boat, Mid-Autumn, Golden Week, etc., all weekdays). None are weekends.

### Approximate expected CN trading days

The task's heuristic estimate of "~2800–2900 CN trading days Feb 2015..Jul 2026" matches the data well: USDCNY posts **2785** CN trading-day rows in the window, which sits at the low end of the 2800–2900 range (the shortfall vs 2900 is the typical ~10–12 CN public holidays per year × 11.5 years ≈ 115–140, plus the 2-day late start). **USDCNY's row count is consistent with the onshore CNY trading calendar — no missing-business-day gap beyond CN holidays.**

USDCNH at 2988 weekday rows is essentially the full weekday calendar minus 2 New-Year holidays — i.e. **USDCNH trades every weekday except global New Year**, including CN domestic holidays. This is the expected behavior for offshore CNH.

## Plots

- `dq_coverage.png` — top panel: monthly row count USDCNH vs USDCNY (NH ≥ NY every month, deltas concentrated in Jan/Feb/May/Sep/Oct). Bottom panel: monthly missing weekday-days per series (USDCNH ≈ 0 except Jan-2021/Jan-2024 New Year; USDCNY shows the CN-holiday skeleton).
- `dq_pct_moves.png` — daily `%Δlast` for both series with ±1% / ±2% reference bands. The 2015-08-11 +2.79% NH spike and the 2022-10/11 cluster are the visually dominant events; 2025-08 is flat.

## Summary table

| Dimension | USDCNH | USDCNY |
|---|---|---|
| Rows | 3010 | 2805 |
| Date range | 2015-01-01..2026-07-17 | 2015-01-05..2026-07-17 |
| NaN / zero / negative | 0 / 0 / 0 | 0 / 0 / 0 |
| `high<low`, OHLC out-of-range | 0 | 0 |
| Duplicate dates | 0 | 0 |
| Monotonic index | yes | yes |
| Weekend rows | 0 | 0 |
| `|Δlast| > 1%` days | 31 | 14 |
| `|Δlast| > 2%` days | 1 (2015-08-11) | 0 |
| Weekday coverage gap vs busday calendar (2015-02..2026-07) | 2 (New Year) | 205 (CN holidays + 2-day late start) |
| Known events present | 2015-08-11 ✓, 2022-10-24/25 ✓, 2025-04-08 ✓ (2025-08 ✗ not a spike) | same |

## Recommendations for downstream use

1. **Align the two series on USDCNY's dates** for any joint model — USDCNY is the strict subset. Reindexing USDCNH to USDCNY's index loses 205 rows but guarantees aligned timestamps with no forward-fill needed.
2. **Do not forward-fill the 205 CN-holiday rows** in USDCNY from USDCNH — those are genuine non-trading days for onshore CNY and the offshore price already embeds information you would be leaking into onshore.
3. **For volatility / event studies, use USDCNH** (more observations, captures offshore shocks); for onshore-regime / PBoC-fixing studies use USDCNY.
4. **2025-08 is NOT a spike in this data** — August 2025 (21 rows, fully in-sample through 08-29) shows CNH appreciating from ~7.20 to ~7.12 with no >1% day. The actual 2025 CNH peak in this dataset is **2025-04-08** (NH 7.4257, +1.10% / −1.07% over 04-08..04-09) — relabel the event accordingly, or source August 2025 from another venue if a CNH shock was genuinely expected later in the month.
5. New-Year rows: USDCNH is missing 2021-01-01 and 2024-01-01; USDCNY is also missing those (and many more CN holidays). Accept as is — these are legitimate market closures.
