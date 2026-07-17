"""Produce FX visualization set for USDCNH & USDCNY."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

BASE = 'c:/Users/Q/Code/qlib/fork-docs/fx_research'
OUT = BASE + '/charts'

# Palette: CNH = teal, CNY = amber
CNH_COLOR = '#1f77b4'  # blue
CNY_COLOR = '#d62728'  # red

# Load
cnh = pd.read_csv(BASE + '/usdcnh.csv', index_col=0, parse_dates=True)
cny = pd.read_csv(BASE + '/usdcny.csv', index_col=0, parse_dates=True)

cnh_last = cnh['last']
cny_last = cny['last']

# Align on common dates for basis calc
both = pd.concat({'CNH': cnh_last, 'CNY': cny_last}, axis=1)
both = both.dropna(how='any')
basis = both['CNH'] - both['CNY']  # CNH - CNY

# Log returns
cnh_ret = np.log(cnh_last / cnh_last.shift(1)).dropna()
cny_ret = np.log(cny_last / cny_last.shift(1)).dropna()

# Event dates
events = {
    '2015-08-11': '2015-08 depeg',
    '2022-10-24': '2022-10',
    '2025-08-01': '2025-08',
}

plt.rcParams.update({
    'figure.autolayout': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'font.size': 10,
})

def add_events(ax):
    for d, lab in events.items():
        dt = pd.Timestamp(d)
        ax.axvline(dt, color='grey', ls='--', lw=0.9, alpha=0.8)
        # text near top
        ymin, ymax = ax.get_ylim()
        ax.text(dt, ymax*0.97 if ymax>0 else ymax*0.03, ' ' + lab,
                rotation=90, va='top', ha='left', fontsize=8, color='dimgray')


# 1. price_overlay.png
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(cnh_last.index, cnh_last.values, color=CNH_COLOR, lw=0.9, label='USDCNH')
ax.plot(cny_last.index, cny_last.values, color=CNY_COLOR, lw=0.9, label='USDCNY', alpha=0.85)
ax.set_yscale('log')
ax.set_title('USDCNH vs USDCNY last price (log scale), 2015-2026')
ax.set_ylabel('Price (CNY per USD, log)')
ax.set_xlabel('Date')
ax.legend(loc='best')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax.xaxis.set_major_locator(mdates.YearLocator())
add_events(ax)
plt.tight_layout()
plt.savefig(OUT + '/price_overlay.png', dpi=120)
plt.close()

# 2. basis_spread.png — top: basis; bottom: 252d z-score
basis_z = (basis - basis.rolling(252).mean()) / basis.rolling(252).std()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
ax1.plot(basis.index, basis.values, color='#2ca02c', lw=0.9)
ax1.axhline(0, color='black', lw=0.5, alpha=0.5)
ax1.set_title('CNH - CNY basis (USDCNH.last - USDCNY.last)')
ax1.set_ylabel('Basis (CNY/CNH)')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax1.xaxis.set_major_locator(mdates.YearLocator())
add_events(ax1)
ax2.plot(basis_z.index, basis_z.values, color='#9467bd', lw=0.9)
ax2.axhline(0, color='black', lw=0.5, alpha=0.5)
ax2.axhline(2, color='red', lw=0.5, ls='--', alpha=0.5)
ax2.axhline(-2, color='red', lw=0.5, ls='--', alpha=0.5)
ax2.set_title('CNH-CNY basis z-score (rolling 252d)')
ax2.set_ylabel('z-score')
ax2.set_xlabel('Date')
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax2.xaxis.set_major_locator(mdates.YearLocator())
add_events(ax2)
plt.tight_layout()
plt.savefig(OUT + '/basis_spread.png', dpi=120)
plt.close()

# 3. returns_hist.png — overlaid histograms
fig, ax = plt.subplots(figsize=(10, 6))
bins = np.linspace(min(cnh_ret.min(), cny_ret.min()),
                   max(cnh_ret.max(), cny_ret.max()), 80)
ax.hist(cnh_ret, bins=bins, alpha=0.55, color=CNH_COLOR, label=f'USDCNH', density=True)
ax.hist(cny_ret, bins=bins, alpha=0.55, color=CNY_COLOR, label=f'USDCNY', density=True)
ax.set_title('Daily log-return distributions')
ax.set_xlabel('Daily log return')
ax.set_ylabel('Density')
ax.set_yscale('log')
cstats = f'CNH:  mean={cnh_ret.mean()*100:.4f}%  std={cnh_ret.std()*100:.4f}%'
nstats = f'CNY:  mean={cny_ret.mean()*100:.4f}%  std={cny_ret.std()*100:.4f}%'
ax.legend(loc='upper right')
ax.text(0.02, 0.98, cstats + '\n' + nstats, transform=ax.transAxes,
        va='top', ha='left', fontsize=9, family='monospace',
        bbox=dict(boxstyle='round', fc='white', alpha=0.8))
plt.tight_layout()
plt.savefig(OUT + '/returns_hist.png', dpi=120)
plt.close()

# 4. drawdown.png — underwater series
cnh_dd = cnh_last / cnh_last.cummax() - 1
cny_dd = cny_last / cny_last.cummax() - 1
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(cnh_dd.index, cnh_dd.values*100, color=CNH_COLOR, lw=0.9, label='USDCNH')
ax.plot(cny_dd.index, cny_dd.values*100, color=CNY_COLOR, lw=0.9, label='USDCNY', alpha=0.85)
ax.fill_between(cnh_dd.index, cnh_dd.values*100, 0, color=CNH_COLOR, alpha=0.12)
ax.fill_between(cny_dd.index, cny_dd.values*100, 0, color=CNY_COLOR, alpha=0.12)
ax.set_title('Underwater drawdown (price / cummax - 1)')
ax.set_ylabel('Drawdown (%)')
ax.set_xlabel('Date')
ax.legend(loc='best')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax.xaxis.set_major_locator(mdates.YearLocator())
plt.tight_layout()
plt.savefig(OUT + '/drawdown.png', dpi=120)
plt.close()

# 5. rolling_vol.png — 21d & 63d rolling std of log returns
cnh_vol21 = cnh_ret.rolling(21).std() * np.sqrt(252) * 100
cnh_vol63 = cnh_ret.rolling(63).std() * np.sqrt(252) * 100
cny_vol21 = cny_ret.rolling(21).std() * np.sqrt(252) * 100
cny_vol63 = cny_ret.rolling(63).std() * np.sqrt(252) * 100

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
ax1.plot(cnh_vol21.index, cnh_vol21.values, color=CNH_COLOR, lw=0.9, label='USDCNH 21d')
ax1.plot(cny_vol21.index, cny_vol21.values, color=CNY_COLOR, lw=0.9, label='USDCNY 21d', alpha=0.85)
ax1.set_title('Rolling annualized volatility (21d window, sqrt-252)')
ax1.set_ylabel('Annualized vol (%)')
ax1.legend(loc='best')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax1.xaxis.set_major_locator(mdates.YearLocator())
ax2.plot(cnh_vol63.index, cnh_vol63.values, color=CNH_COLOR, lw=0.9, label='USDCNH 63d')
ax2.plot(cny_vol63.index, cny_vol63.values, color=CNY_COLOR, lw=0.9, label='USDCNY 63d', alpha=0.85)
ax2.set_title('Rolling annualized volatility (63d window, sqrt-252)')
ax2.set_ylabel('Annualized vol (%)')
ax2.set_xlabel('Date')
ax2.legend(loc='best')
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax2.xaxis.set_major_locator(mdates.YearLocator())
plt.tight_layout()
plt.savefig(OUT + '/rolling_vol.png', dpi=120)
plt.close()

print('done')
print('cnh rows', len(cnh), 'cny rows', len(cny))
print('cnh_ret mean', cnh_ret.mean(), 'std', cnh_ret.std())
print('cny_ret mean', cny_ret.mean(), 'std', cny_ret.std())
print('basis mean', basis.mean(), 'std', basis.std())
