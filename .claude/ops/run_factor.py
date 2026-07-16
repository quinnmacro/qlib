"""Stage 4.2 — compute + hand-verify + IC/ICIR for RollingZScore, following
factor-research SKILL.md Steps 3-5.
"""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.getcwd(), ".claude", "ops"))

import qlib
from qlib.data import D
from qlib.contrib.eva.alpha import calc_ic
from rolling_zscore import RollingZScore

# Step 3: register custom_ops. Step 4: expression_cache=None for dev (no cache side-effects)
qlib.init(provider_uri="~/.qlib/qlib_data/cn_data", expression_cache=None, custom_ops=[RollingZScore],
          kernels=1)  # kernels=1: D.features over multiple instruments uses joblib multiprocessing;
                       # on Windows spawn re-imports main module -> hang. Sequential avoids it.

FIELD = "RollingZScore($close,20)"
ST, EN = "2019-01-01", "2020-08-01"
SYM = "sh600000"

# ---- Step 4: compute ----
print("="*70); print("Step 4: compute RollingZScore($close,20)"); print("="*70)
df = D.features(instruments=[SYM], fields=[FIELD, "$close"], start_time=ST, end_time=EN, freq="day")
print(df.head(25))
print(f"shape={df.shape}, nan count in op col={df[FIELD].isna().sum()} (first 19 should be NaN)")

# ---- hand-verify: INDEPENDENT explicit windowed zscore (numpy, not pandas rolling) ----
print("\n" + "="*70); print("HAND-VERIFY: independent explicit 20-day windowed zscore (numpy)"); print("="*70)
# index is MultiIndex (instrument, datetime). For k>=19 the 20-day window lies fully
# within df's $close range, so numpy zscore of df["$close"].iloc[k-19:k+1] must match op.
close = df["$close"].dropna()
op = df[FIELD].reindex(close.index)
print(f"{'date':12}{'close':>10}{'op_val':>12}{'indep_numpy':>12}{'match':>7}")
checks = [19, 20, 50, 100, 200, len(close)-2]
for k in checks:
    if k >= len(close) or k < 19: continue
    w = close.iloc[k-19:k+1].values  # 20 values ending at k (inclusive)
    m = w.mean(); sd = w.std(ddof=1); indep = (w[-1]-m)/sd
    opv = op.iloc[k]
    match = abs(indep-opv) < 1e-5
    print(f"{str(close.index[k][1].date()):12}{w[-1]:10.4f}{opv:12.6f}{indep:12.6f}{str(match):>7}")
# NOTE: op has 0 NaN at start because the engine pre-extends the window (get_extended_window_size)
# and fetches 2018 data to compute the 2019-01-02 value. So skill坑#4's "boundary NaN" only
# bites when there is NO prior history at all.
print(f"\nop NaN count in requested range = {df[FIELD].isna().sum()} (0 => engine pre-fetched left context)")

# ---- Step 5: IC/ICIR via calc_ic (same fn SigAnaRecord uses, alpha.py:178) ----
print("\n" + "="*70); print("Step 5: IC/ICIR across csi300 (label = next-day return Ref($close,-1)/$close-1)"); print("="*70)
LABEL = "Ref($close,-1)/$close-1"
fields = [FIELD, LABEL]
# Explicit symbols (D.instruments("csi300") default filter returns too few on this data)
insts = ["sh600000","sh600009","sh600010","sh600011","sh600015","sh600016","sh600019",
        "sh600025","sh600028","sh600029","sh600030","sh600036","sh600048","sh600050","sh600061"]
print(f"computing factor + label across {len(insts)} symbols (2019)...")
ful = D.features(instruments=insts, fields=fields, start_time="2019-01-01", end_time="2019-12-31", freq="day")
print(f"full shape={ful.shape}")
pred = ful[[FIELD]]
label = ful[[LABEL]]
# calc_ic expects pred, label as single-column DataFrames with MultiIndex (datetime,instrument)
ic, ric = calc_ic(pred.iloc[:,0], label.iloc[:,0])
print(f"\nIC        = {ic.mean():.6f}   (alpha.py:178 daily cross-section Pearson)")
print(f"Rank IC   = {ric.mean():.6f}   (alpha.py:179 daily cross-section Spearman)")
print(f"ICIR      = {ic.mean()/ic.std():.6f}   (record_temp.py:326, NO sqrt(N))")
print(f"Rank ICIR = {ric.mean()/ric.std():.6f}   (no sqrt(N))")
print(f"(contrast: ic.mean()/ic.std()*sqrt(238) = {ic.mean()/ic.std()*np.sqrt(238):.6f} -- NOT what's logged)")
print(f"n_days IC series = {len(ic)}")
