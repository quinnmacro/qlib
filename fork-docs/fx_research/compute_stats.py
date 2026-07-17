"""Descriptive statistics for USDCNH and USDCNY. Descriptive only, no backtest.

Annualization convention: 252 trading days. This is NOT qlib risk_analysis
(which uses 238, sum mode). Sharpe-like ratio is a raw mean-vol ratio,
NOT qlib IR/ICIR (ICIR has no sqrt(N); IR has sqrt(N)).
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DIR = r'c:/Users/Q/Code/qlib/fork-docs/fx_research'
CHARTS = os.path.join(DIR, 'charts')
os.makedirs(CHARTS, exist_ok=True)

cnh = pd.read_csv(os.path.join(DIR, 'usdcnh.csv'), index_col=0, parse_dates=True)
cny = pd.read_csv(os.path.join(DIR, 'usdcny.csv'), index_col=0, parse_dates=True)

# use 'last' as close
cnh_close = cnh['last']
cny_close = cny['last']

TRADING_DAYS = 252

def per_series_stats(name, close):
    first = close.iloc[0]
    last = close.iloc[-1]
    mn = close.min()
    mx = close.max()
    total_ret = last / first - 1.0
    n_years = (close.index[-1] - close.index[0]).days / 365.25
    cagr = (last / first) ** (1.0 / n_years) - 1.0 if n_years > 0 else float('nan')
    # daily log returns
    logr = np.log(close / close.shift(1)).dropna()
    # daily simple returns (for skew/kurt/max gain-loss)
    simpr = (close / close.shift(1) - 1.0).dropna()
    mean_log = logr.mean()
    std_log = logr.std(ddof=1)
    ann_vol = std_log * np.sqrt(TRADING_DAYS)
    # annualized return (geo mean of daily log return * 252)
    ann_ret = mean_log * TRADING_DAYS
    # also simple annualized return via CAGR for cross-check
    sharpe = ann_ret / ann_vol if ann_vol > 0 else float('nan')
    skew = simpr.skew()
    kurt = simpr.kurtosis()  # pandas: excess kurtosis (Fisher)
    max_gain = simpr.max()
    max_loss = simpr.min()
    pct_gt1 = (simpr.abs() > 0.01).mean() * 100.0
    max_gain_date = simpr.idxmax()
    max_loss_date = simpr.idxmin()
    return {
        'series': name,
        'n_obs': int(len(close)),
        'first_date': close.index[0].strftime('%Y-%m-%d'),
        'last_date': close.index[-1].strftime('%Y-%m-%d'),
        'first_close': first,
        'last_close': last,
        'min_close': mn,
        'max_close': mx,
        'total_return_pct': total_ret * 100.0,
        'CAGR_pct': cagr * 100.0,
        'years_span': n_years,
        'daily_logret_mean': mean_log,
        'daily_logret_std': std_log,
        'annualized_vol_252d_pct': ann_vol * 100.0,
        'annualized_return_252d_geo_pct': ann_ret * 100.0,
        'sharpe_like_mean_vol_ratio': sharpe,
        'daily_ret_skew': skew,
        'daily_ret_excess_kurtosis': kurt,
        'max_one_day_gain_pct': max_gain * 100.0,
        'max_one_day_gain_date': max_gain_date.strftime('%Y-%m-%d'),
        'max_one_day_loss_pct': max_loss * 100.0,
        'max_one_day_loss_date': max_loss_date.strftime('%Y-%m-%d'),
        'pct_days_abs_ret_gt_1pct': pct_gt1,
    }

cnh_stats = per_series_stats('USDCNH', cnh_close)
cny_stats = per_series_stats('USDCNY', cny_close)

# --- Cross-series: align on common dates ---
common = cnh_close.index.intersection(cny_close.index)
cnh_c = cnh_close.reindex(common)
cny_c = cny_close.reindex(common)
cnh_r = np.log(cnh_c / cnh_c.shift(1)).dropna()
cny_r = np.log(cny_c / cny_c.shift(1)).dropna()
# align returns
rcommon = cnh_r.index.intersection(cny_r.index)
cnh_r = cnh_r.reindex(rcommon)
cny_r = cny_r.reindex(rcommon)

corr = cnh_r.corr(cny_r)
# beta CNH ~ CNY OLS
beta = np.cov(cnh_r, cny_r, ddof=1)[0, 1] / np.var(cny_r, ddof=1)
alpha = cnh_r.mean() - beta * cny_r.mean()

# basis = USDCNH - USDCNY (in price units), aligned
basis = cnh_c - cny_c
basis = basis.dropna()
basis_mean = basis.mean()
basis_std = basis.std(ddof=1)
basis_min = basis.min()
basis_max = basis.max()
# basis>0 => CNH more expensive (weaker CNY offshore) = CNH weaker than CNY => CNH premium (weaker)
max_premium_date = basis.idxmax()
max_discount_date = basis.idxmin()

cross = {
    'common_obs': int(len(common)),
    'return_corr_daily': corr,
    'beta_CNH_on_CNY': beta,
    'alpha_CNH_on_CNY_daily': alpha,
    'basis_mean': basis_mean,
    'basis_std': basis_std,
    'basis_min': basis_min,
    'basis_max': basis_max,
    'max_CNH_premium_date (basis max, CNH weaker)': max_premium_date.strftime('%Y-%m-%d'),
    'max_CNH_premium_value': basis_max,
    'max_CNH_discount_date (basis min, CNH stronger)': max_discount_date.strftime('%Y-%m-%d'),
    'max_CNH_discount_value': basis_min,
}

# --- Rolling realized vol ---
# realized vol = std of daily log returns over window * sqrt(252), annualized
def rolling_vol(close, window):
    r = np.log(close / close.shift(1))
    return r.rolling(window).std(ddof=1) * np.sqrt(TRADING_DAYS)

rv21_cnh = rolling_vol(cnh_close, 21)
rv63_cnh = rolling_vol(cnh_close, 63)
rv21_cny = rolling_vol(cny_close, 21)
rv63_cny = rolling_vol(cny_close, 63)

fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
axes[0].plot(rv21_cnh.index, rv21_cnh.values, label='USDCNH 21d', color='#1f77b4', lw=1)
axes[0].plot(rv21_cny.index, rv21_cny.values, label='USDCNY 21d', color='#ff7f0e', lw=1)
axes[0].set_ylabel('Annualized realized vol\n(252d conv.)')
axes[0].set_title('Rolling 21-day realized volatility (annualized, 252d conv.)')
axes[0].legend(loc='best')
axes[0].grid(True, alpha=0.3)

axes[1].plot(rv63_cnh.index, rv63_cnh.values, label='USDCNH 63d', color='#1f77b4', lw=1)
axes[1].plot(rv63_cny.index, rv63_cny.values, label='USDCNY 63d', color='#ff7f0e', lw=1)
axes[1].set_ylabel('Annualized realized vol\n(252d conv.)')
axes[1].set_title('Rolling 63-day realized volatility (annualized, 252d conv.)')
axes[1].legend(loc='best')
axes[1].grid(True, alpha=0.3)

fig.tight_layout()
png = os.path.join(CHARTS, 'rolling_vol.png')
fig.savefig(png, dpi=110)
plt.close(fig)

# Basis histogram
fig2, ax2 = plt.subplots(figsize=(8, 4.5))
ax2.hist(basis.values, bins=60, color='#4c78a8', edgecolor='white', alpha=0.85)
ax2.axvline(basis_mean, color='red', ls='--', lw=1.2, label=f'mean={basis_mean:.4f}')
ax2.set_xlabel('Basis = USDCNH - USDCNY (price units)')
ax2.set_ylabel('Frequency')
ax2.set_title('Histogram of USDCNH-USDCNY basis (aligned common dates)')
ax2.legend()
ax2.grid(True, alpha=0.3)
fig2.tight_layout()
png2 = os.path.join(CHARTS, 'basis_hist.png')
fig2.savefig(png2, dpi=110)
plt.close(fig2)

# --- Build markdown + CSV ---
rows = []
def add(section, metric, value, note=''):
    rows.append({'section': section, 'metric': metric, 'value': value, 'note': note})

# Per-series
for label, s in [('USDCNH', cnh_stats), ('USDCNY', cny_stats)]:
    add(label, 'n_obs (close rows)', s['n_obs'])
    add(label, 'first_date', s['first_date'])
    add(label, 'last_date', s['last_date'])
    add(label, 'years_span (calendar)', f"{s['years_span']:.3f}")
    add(label, 'first_close', f"{s['first_close']:.4f}")
    add(label, 'last_close', f"{s['last_close']:.4f}")
    add(label, 'min_close', f"{s['min_close']:.4f}")
    add(label, 'max_close', f"{s['max_close']:.4f}")
    add(label, 'total_return_pct', f"{s['total_return_pct']:.4f}")
    add(label, 'CAGR_pct (calendar-year basis)', f"{s['CAGR_pct']:.4f}")
    add(label, 'daily_logret_mean', f"{s['daily_logret_mean']:.6e}")
    add(label, 'daily_logret_std (ddof=1)', f"{s['daily_logret_std']:.6e}")
    add(label, 'annualized_vol_252d_pct (std*sqrt(252))', f"{s['annualized_vol_252d_pct']:.4f}",
         'NOT qlib risk_analysis (which uses 238, sum mode)')
    add(label, 'annualized_return_252d_geo_pct (mean_log*252)', f"{s['annualized_return_252d_geo_pct']:.4f}",
         'annualization convention: 252 trading days')
    add(label, 'sharpe_like_mean_vol_ratio (rf=0)', f"{s['sharpe_like_mean_vol_ratio']:.4f}",
         'raw mean-vol ratio, NOT qlib IR/ICIR')
    add(label, 'daily_ret_skew', f"{s['daily_ret_skew']:.4f}")
    add(label, 'daily_ret_excess_kurtosis (Fisher)', f"{s['daily_ret_excess_kurtosis']:.4f}")
    add(label, 'max_one_day_gain_pct', f"{s['max_one_day_gain_pct']:.4f}",
         f"date={s['max_one_day_gain_date']}")
    add(label, 'max_one_day_loss_pct', f"{s['max_one_day_loss_pct']:.4f}",
         f"date={s['max_one_day_loss_date']}")
    add(label, 'pct_days_abs_ret_gt_1pct', f"{s['pct_days_abs_ret_gt_1pct']:.4f}")

# Cross
add('CROSS (USDCNH vs USDCNY)', 'common_obs (aligned dates)', cross['common_obs'])
add('CROSS (USDCNH vs USDCNY)', 'daily_logret_corr', f"{cross['return_corr_daily']:.4f}")
add('CROSS (USDCNH vs USDCNY)', 'beta_CNH_on_CNY (OLS)', f"{cross['beta_CNH_on_CNY']:.4f}")
add('CROSS (USDCNH vs USDCNY)', 'alpha_CNH_on_CNY_daily (logret)', f"{cross['alpha_CNH_on_CNY_daily']:.6e}")
add('CROSS (USDCNH vs USDCNY)', 'basis_mean (USDCNH-USDCNY)', f"{cross['basis_mean']:.4f}")
add('CROSS (USDCNH vs USDCNY)', 'basis_std (ddof=1)', f"{cross['basis_std']:.4f}")
add('CROSS (USDCNH vs USDCNY)', 'basis_min', f"{cross['basis_min']:.4f}",
    f"max CNH discount (CNH stronger) date={cross['max_CNH_discount_date (basis min, CNH stronger)']}")
add('CROSS (USDCNH vs USDCNY)', 'basis_max', f"{cross['basis_max']:.4f}",
    f"max CNH premium (CNH weaker than CNY) date={cross['max_CNH_premium_date (basis max, CNH weaker)']}")

df = pd.DataFrame(rows)
df.to_csv(os.path.join(DIR, 'stats.csv'), index=False)

# Markdown
lines = []
lines.append('# Descriptive Statistics: USDCNH & USDCNY\n')
lines.append('All annualization uses **252 trading days** convention. '
             'The `annualized_vol_252d` here is **NOT** qlib `risk_analysis` '
             '(which annualizes by 238 in sum mode — see `fork-docs/BACKTEST_SPEC.md`). '
             'The `sharpe_like_mean_vol_ratio` is a raw mean/vol ratio (rf=0) and is **NOT** '
             'qlib IR (which has sqrt(N)) or ICIR (no sqrt(N)). Descriptive only — no backtest.\n')
lines.append(f"- USDCNH: {cnh_stats['first_date']} → {cnh_stats['last_date']} ({cnh_stats['n_obs']} obs)")
lines.append(f"- USDCNY: {cny_stats['first_date']} → {cny_stats['last_date']} ({cny_stats['n_obs']} obs)")
lines.append(f"- Aligned common dates for cross-stats: {cross['common_obs']}\n")

# per-series table
per_cols = ['metric', 'USDCNH', 'USDCNY']
per_rows = []
metrics_order = [
    'n_obs (close rows)', 'first_date', 'last_date', 'years_span (calendar)',
    'first_close', 'last_close', 'min_close', 'max_close',
    'total_return_pct', 'CAGR_pct (calendar-year basis)',
    'daily_logret_mean', 'daily_logret_std (ddof=1)',
    'annualized_vol_252d_pct (std*sqrt(252))',
    'annualized_return_252d_geo_pct (mean_log*252)',
    'sharpe_like_mean_vol_ratio (rf=0)',
    'daily_ret_skew', 'daily_ret_excess_kurtosis (Fisher)',
    'max_one_day_gain_pct', 'max_one_day_loss_pct',
    'pct_days_abs_ret_gt_1pct',
]
# build value lookup per series
def get_val(label, metric):
    for r in rows:
        if r['section'] == label and r['metric'] == metric:
            return r['value']
    return ''

# add date annotations under gain/loss rows in note column inline
lines.append('## Per-series statistics\n')
lines.append('| metric | USDCNH | USDCNY |')
lines.append('|---|---|---|')
for m in metrics_order:
    v_cnh = get_val('USDCNH', m)
    v_cny = get_val('USDCNY', m)
    # add date notes for gain/loss
    if m == 'max_one_day_gain_pct':
        v_cnh = f"{v_cnh} ({cnh_stats['max_one_day_gain_date']})"
        v_cny = f"{v_cny} ({cny_stats['max_one_day_gain_date']})"
    elif m == 'max_one_day_loss_pct':
        v_cnh = f"{v_cnh} ({cnh_stats['max_one_day_loss_date']})"
        v_cny = f"{v_cny} ({cny_stats['max_one_day_loss_date']})"
    lines.append(f"| {m} | {v_cnh} | {v_cny} |")

lines.append('\n## Cross-series (USDCNH vs USDCNY, aligned common dates)\n')
lines.append('| metric | value |')
lines.append('|---|---|')
for r in rows:
    if r['section'].startswith('CROSS'):
        note = f" — {r['note']}" if r['note'] else ''
        lines.append(f"| {r['metric']} | {r['value']}{note} |")

lines.append('\n## Notes & conventions\n')
lines.append('- **Close**: `last` column from each CSV.')
lines.append('- **Daily returns**: log returns `ln(P_t / P_{t-1})` on the `last` series; '
             'skew/kurtosis/max gain-loss computed on simple returns `(P_t/P_{t-1} - 1)` '
             '(kurtosis is Fisher excess, `pandas.Series.kurtosis`).')
lines.append('- **Annualized vol (252d)**: `std(daily logret, ddof=1) * sqrt(252)` — '
             'labeled explicitly as **NOT qlib `risk_analysis`** (which uses 238, sum mode).')
lines.append('- **Annualized return (252d geo)**: `mean(daily logret) * 252` (geometric mean × trading days). '
             'CAGR is reported separately on a calendar-year basis `(last/first)^(365.25/days)-1` for cross-check.')
lines.append('- **Sharpe-like ratio**: `ann_return / ann_vol` (rf=0). Labeled as **raw mean-vol ratio, '
             'NOT qlib IR/ICIR** (IR uses sqrt(N); ICIR has no sqrt(N) — see `fork-docs/BACKTEST_SPEC.md`).')
lines.append('- **Beta**: OLS slope of CNH daily log-return on CNY daily log-return '
             '(cov/var, ddof=1). Alpha is the OLS intercept (daily, log-return).')
lines.append('- **Basis** = `USDCNH - USDCNY` in price units. Basis > 0 ⇒ CNH quotes higher (weaker CNY offshore) '
             '⇒ "CNH weaker than CNY" / CNH premium. Basis < 0 ⇒ CNH stronger than CNY / CNH discount.')
lines.append('- All figures are **descriptive**; no backtest, no qlib backtest engine invoked.')

lines.append('\n## Charts\n')
lines.append(f"- Rolling 21d & 63d realized vol (annualized, 252d): `charts/rolling_vol.png`")
lines.append(f"- Basis histogram: `charts/basis_hist.png`")

with open(os.path.join(DIR, 'stats.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

# print summary to stdout for verification
print("=== USDCNH stats ===")
for k, v in cnh_stats.items():
    print(f"  {k}: {v}")
print("\n=== USDCNY stats ===")
for k, v in cny_stats.items():
    print(f"  {k}: {v}")
print("\n=== CROSS ===")
for k, v in cross.items():
    print(f"  {k}: {v}")
print("\nWrote: stats.md, stats.csv, charts/rolling_vol.png, charts/basis_hist.png")
