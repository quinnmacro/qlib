"""Data Quality audit for usdcnh.csv + usdcny.csv."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

NH = pd.read_csv('c:/Users/Q/Code/qlib/fork-docs/fx_research/usdcnh.csv', index_col=0, parse_dates=True)
NY = pd.read_csv('c:/Users/Q/Code/qlib/fork-docs/fx_research/usdcny.csv', index_col=0, parse_dates=True)

print("=" * 70)
print("BASIC SHAPE")
print("=" * 70)
print(f"USDCNH: {NH.shape}  index range {NH.index.min().date()}..{NH.index.max().date()}")
print(f"USDCNY: {NY.shape}  index range {NY.index.min().date()}..{NY.index.max().date()}")
print(f"USDCNH dtypes:\n{NH.dtypes}")
print(f"USDCNY dtypes:\n{NY.dtypes}")

# ---- 1. Row-count gap / coverage gap ----
print("\n" + "=" * 70)
print("1. COVERAGE / MISSING-DAYS MATRIX")
print("=" * 70)
union = NH.index.union(NY.index)
print(f"Union of dates: {len(union)}")
nh_missing = union.difference(NH.index)
ny_missing = union.difference(NY.index)
print(f"Days in union but NOT in USDCNH: {len(nh_missing)}")
print(f"Days in union but NOT in USDCNY: {len(ny_missing)}")
print(f"Days in BOTH: {len(NH.index.intersection(NY.index))}")
print(f"USDCNH-only days: {len(NH.index.difference(NY.index))}")
print(f"USDCNY-only days: {len(NY.index.difference(NH.index))}")

# show start/end overlap
nh_start, nh_end = NH.index.min(), NH.index.max()
ny_start, ny_end = NY.index.min(), NY.index.max()
print(f"\nUSDCNH starts {nh_start.date()}, USDCNY starts {ny_start.date()}")
print(f"Pre-USDCNY window ({nh_start.date()}..{ny_start.date()}): USDCNH has "
      f"{((NH.index < ny_start)).sum()} days USDCNY lacks entirely.")
print(f"USDCNH ends {nh_end.date()}, USDCNY ends {ny_end.date()}")

# monthly missing heatmap matrix
def monthly_missing(df, label, union_idx):
    # reindex to union, mark present
    present = pd.Series(True, index=df.index).reindex(union_idx, fill_value=False)
    # group by year-month, count missing
    miss = ~present
    monthly = miss.groupby([union_idx.year, union_idx.month]).sum()
    return monthly

m_nh = monthly_missing(NH, "NH", union)
m_ny = monthly_missing(NY, "NY", union)

# print monthly missing counts where any missing
print("\nMonth-by-month missing days (year,month): NH / NY")
combined = pd.DataFrame({'NH_missing': m_nh, 'NY_missing': m_ny})
combined = combined[combined.sum(axis=1) > 0]
print(combined.to_string())

# ---- 2. NaN / zero / negative / OHLC violations ----
print("\n" + "=" * 70)
print("2. NaN / ZERO / NEGATIVE / OHLC VIOLATIONS")
print("=" * 70)
for name, df in [("USDCNH", NH), ("USDCNY", NY)]:
    print(f"\n--- {name} ---")
    nan_cnt = df.isna().sum()
    print(f"NaN counts:\n{nan_cnt.to_string()}")
    zero_cnt = (df == 0).sum()
    print(f"Zero counts:\n{zero_cnt.to_string()}")
    neg_cnt = (df < 0).sum()
    print(f"Negative counts:\n{neg_cnt.to_string()}")
    hl_viol = df[df['high'] < df['low']]
    print(f"high<low violations: {len(hl_viol)}")
    if len(hl_viol):
        print(hl_viol.head())
    # last outside [low, high]
    out_of_range = df[(df['last'] < df['low']) | (df['last'] > df['high'])]
    print(f"last outside [low,high]: {len(out_of_range)}")
    if len(out_of_range):
        print(out_of_range.head())
    # open outside [low,high]
    open_out = df[(df['open'] < df['low']) | (df['open'] > df['high'])]
    print(f"open outside [low,high]: {len(open_out)}")
    if len(open_out):
        print(open_out.head())

# ---- 3. Duplicate / monotonic / weekend ----
print("\n" + "=" * 70)
print("3. DUPLICATES / NON-MONOTONIC / WEEKEND ROWS")
print("=" * 70)
for name, df in [("USDCNH", NH), ("USDCNY", NY)]:
    print(f"\n--- {name} ---")
    dup = df.index.duplicated()
    print(f"Duplicate dates: {dup.sum()}")
    mono = df.index.is_monotonic_increasing
    print(f"Index monotonic increasing: {mono}")
    diffs = pd.Series(df.index).diff()
    non_incr = (diffs.dt.total_seconds() < 0).sum()
    print(f"Non-monotonic (negative step) entries: {non_incr}")
    weekend = df[df.index.dayofweek >= 5]
    print(f"Weekend rows (Sat/Sun): {len(weekend)}")
    if len(weekend):
        print(weekend.head(10))

# ---- 4. Outlier day-over-day moves ----
print("\n" + "=" * 70)
print("4. DAY-OVER-DAY |Δlast| OUTLIERS")
print("=" * 70)
for name, df in [("USDCNH", NH), ("USDCNY", NY)]:
    print(f"\n--- {name} ---")
    last = df['last']
    pct = last.pct_change() * 100.0
    big1 = pct.abs() > 1.0
    big2 = pct.abs() > 2.0
    print(f"|Δ| > 1%: {big1.sum()}   |Δ| > 2%: {big2.sum()}")
    sub = pct[big1].sort_values(key=lambda s: s.abs(), ascending=False)
    print("All >1% moves (date, pct%):")
    print(sub.to_string())

# ---- 5. Business-day coverage ----
print("\n" + "=" * 70)
print("5. BUSINESS-DAY COVERAGE")
print("=" * 70)
# CN business days from 2015-02-01 to 2026-07-17 (approx)
start = pd.Timestamp('2015-02-01')
end = pd.Timestamp('2026-07-17')
# Use numpy busday (excludes weekends only, not CN holidays - rough lower bound)
bdays = np.busday_count(start.date(), (end + pd.Timedelta(days=1)).date())
print(f"Approx weekday count {start.date()}..{end.date()} (np busday, excludes weekends only): {bdays}")
for name, df in [("USDCNH", NH), ("USDCNY", NY)]:
    sub = df[(df.index >= start) & (df.index <= end)]
    n_weekday = (sub.index.dayofweek < 5).sum()
    n_weekend = (sub.index.dayofweek >= 5).sum()
    print(f"{name}: total in window = {len(sub)}, weekdays = {n_weekday}, weekend = {n_weekend}")
    print(f"  gap vs weekday count = {bdays - n_weekday} (negative => extra weekdays present)")

# CN-specific known events cross check
print("\n" + "=" * 70)
print("CNH EVENT CROSS-CHECK")
print("=" * 70)
events = {
    "2015-08-11 PBoC devaluation": ["2015-08-10", "2015-08-11", "2015-08-12", "2015-08-13"],
    "2022-10-24/25 CNH spike ~7.3": ["2022-10-21", "2022-10-24", "2022-10-25", "2022-10-26"],
    "2025-08 CNH spike": ["2025-07-31", "2025-08-01", "2025-08-04", "2025-08-05",
                         "2025-08-06", "2025-08-07", "2025-08-08", "2025-08-11"],
}
for ev, dates in events.items():
    print(f"\n{ev}")
    for d in dates:
        ts = pd.Timestamp(d)
        nh_row = NH.loc[NH.index == ts]
        ny_row = NY.loc[NY.index == ts]
        nh_last = nh_row['last'].iloc[0] if len(nh_row) else "MISSING"
        ny_last = ny_row['last'].iloc[0] if len(ny_row) else "MISSING"
        print(f"  {d}: USDCNH last={nh_last}  USDCNY last={ny_last}")

# also min/max of last
print("\nRange of `last`:")
print(f"USDCNH: min={NH['last'].min()} max={NH['last'].max()}")
print(f"USDCNY: min={NY['last'].min()} max={NY['last'].max()}")

# ---- Plot: missing coverage matrix ----
# build daily present/absent over union, resample monthly
present_nh = pd.Series(1, index=NH.index).reindex(union, fill_value=0)
present_ny = pd.Series(1, index=NY.index).reindex(union, fill_value=0)
m_nh = present_nh.resample('MS').sum()
m_ny = present_ny.resample('MS').sum()
# expected business days per month (approx)
def expected_bd(s, e):
    return np.busday_count(s.date(), (e + pd.Timedelta(days=1)).date())
exp = pd.Series({m: expected_bd(m, (m + pd.Timedelta(days=31)).replace(day=1) - pd.Timedelta(days=1))
                 for m in m_nh.index})
# simpler: count weekdays in each month from union
all_cal = pd.date_range(union.min(), union.max(), freq='D')
wd_mask = pd.Series(all_cal.dayofweek < 5, index=all_cal)
wd_per_month = wd_mask.resample('MS').sum().reindex(m_nh.index, fill_value=0)

fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
ax = axes[0]
ax.bar(m_nh.index, m_nh.values, width=20, color='steelblue', label='USDCNH present')
ax.bar(m_ny.index, m_ny.values, width=12, color='orange', alpha=0.6, label='USDCNY present')
ax.set_ylabel('Rows per month')
ax.set_title('Monthly row count: USDCNH vs USDCNY')
ax.legend()
ax.grid(True, alpha=0.3)

ax = axes[1]
miss_nh = (wd_per_month - m_nh).clip(lower=0)
miss_ny = (wd_per_month - m_ny).clip(lower=0)
ax.bar(miss_nh.index, miss_nh.values, width=20, color='crimson', alpha=0.6, label='USDCNH missing weekdays')
ax.bar(miss_ny.index, miss_ny.values, width=12, color='darkgreen', alpha=0.6, label='USDCNY missing weekdays')
ax.set_ylabel('Missing weekday-days per month')
ax.set_title('Monthly missing weekday days (lower bound; ignores CN holidays)')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('c:/Users/Q/Code/qlib/fork-docs/fx_research/dq_coverage.png', dpi=110, bbox_inches='tight')
print("\nSaved plot: dq_coverage.png")

# Day-over-day pct plot for both
fig, ax = plt.subplots(figsize=(14, 5))
pct_nh = NH['last'].pct_change() * 100
pct_ny = NY['last'].pct_change() * 100
ax.plot(pct_nh.index, pct_nh.values, label='USDCNH %Δlast', color='steelblue', lw=0.6)
ax.plot(pct_ny.index, pct_ny.values, label='USDCNY %Δlast', color='orange', lw=0.6, alpha=0.7)
ax.axhline(2, color='red', ls='--', lw=0.8)
ax.axhline(-2, color='red', ls='--', lw=0.8)
ax.axhline(1, color='gray', ls=':', lw=0.6)
ax.axhline(-1, color='gray', ls=':', lw=0.6)
ax.set_title('Day-over-day % move of `last` (red=±2%, gray=±1%)')
ax.set_ylabel('%')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('c:/Users/Q/Code/qlib/fork-docs/fx_research/dq_pct_moves.png', dpi=110, bbox_inches='tight')
print("Saved plot: dq_pct_moves.png")

print("\nDONE")
