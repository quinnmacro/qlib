"""Stage 4.1 v2 — cleaner empirical adjustment characterization.
Detect corporate actions via FACTOR jumps (not price drops, since price fields are adjusted/continuous).
"""
import numpy as np, os

ROOT = os.path.expanduser("~/.qlib/qlib_data/cn_data")
FEAT = f"{ROOT}/features"
CAL = np.loadtxt(f"{ROOT}/calendars/day.txt", dtype=str)
SYMS = sorted(os.listdir(FEAT))

def read_bin(sym, field):
    p = f"{FEAT}/{sym}/{field}.day.bin"
    if not os.path.exists(p): return None
    a = np.fromfile(p, dtype="<f4")
    return a[1:] if len(a) >= 2 else None

print(f"symbols: {len(SYMS)}, calendar days: {len(CAL)}")

# ---- endpoint distributions: which field looks like real yuan prices? ----
def stats(name, arr):
    arr = arr[~np.isnan(arr)]
    if len(arr)==0: return
    qs = np.percentile(arr, [1,5,25,50,75,95,99])
    print(f"  {name:16} n={len(arr):5d}  p1={qs[0]:.4f} p5={qs[1]:.4f} p25={qs[2]:.4f} p50={qs[3]:.4f} p75={qs[4]:.4f} p95={qs[5]:.4f} p99={qs[6]:.4f}")

c0,cL,a0,aL = [],[],[],[]
for s in SYMS:
    cl=read_bin(s,"close"); ac=read_bin(s,"adjclose")
    if cl is None or ac is None: continue
    cl=cl[~np.isnan(cl)]; ac=ac[~np.isnan(ac)]
    if len(cl)<2 or len(ac)<2: continue
    c0.append(cl[0]); cL.append(cl[-1]); a0.append(ac[0]); aL.append(ac[-1])
print("\n=== endpoint distributions (real A-share prices are ~3-500 yuan) ===")
stats("close[0]",  np.array(c0))
stats("close[-1]", np.array(cL))
stats("adjclose[0]", np.array(a0))
stats("adjclose[-1]",np.array(aL))

# ---- detect FACTOR jumps (corporate actions) & volume behavior ----
# A factor jump day t: factor finite at t and t-1, and |f[t]-f[t-1]|>1e-6
jumps = []  # (sym, t, f_r, vo_r, cl_r, ac_r, vo_tm1, vo_t, ...)
detail = []
for s in SYMS:
    if not (s.startswith("sh6") or s.startswith("sz0") or s.startswith("sz3")): continue
    f=read_bin(s,"factor"); vo=read_bin(s,"volume"); cl=read_bin(s,"close"); ac=read_bin(s,"adjclose")
    if f is None or vo is None or cl is None or ac is None: continue
    n=min(len(f),len(vo),len(cl),len(ac))
    f,vo,cl,ac=f[:n],vo[:n],cl[:n],ac[:n]
    fin = ~(np.isnan(f)|np.isnan(vo)|np.isnan(cl)|np.isnan(ac))
    for t in range(1,n):
        if not (fin[t] and fin[t-1]): continue
        if abs(f[t]-f[t-1]) <= 1e-6: continue
        f_r = f[t]/f[t-1] if f[t-1]!=0 else np.nan
        vo_r = vo[t]/vo[t-1] if vo[t-1]!=0 else np.nan
        cl_r = cl[t]/cl[t-1] if cl[t-1]!=0 else np.nan
        ac_r = ac[t]/ac[t-1] if ac[t-1]!=0 else np.nan
        jumps.append((s,t,f_r,vo_r,cl_r,ac_r,vo[t-1],vo[t],f[t-1],f[t],cl[t-1],cl[t],ac[t-1],ac[t]))
        if len(detail) < 8 and abs(f_r-2.0)<0.3:  # ~10送10 split (f_r~2)
            detail.append((s,t,f_r,vo_r,cl_r,ac_r,vo[t-1],vo[t],f[t-1],f[t],cl[t-1],cl[t],ac[t-1],ac[t]))

print(f"\n=== factor-jump days (corporate actions) found: {len(jumps)} ===")
if jumps:
    fr = np.array([j[2] for j in jumps if not np.isnan(j[2])])
    vor = np.array([j[3] for j in jumps if not np.isnan(j[3])])
    clr = np.array([j[4] for j in jumps if not np.isnan(j[4])])
    acr = np.array([j[5] for j in jumps if not np.isnan(j[5])])
    print(f"  factor ratio  f[t]/f[t-1]:   median={np.median(fr):.4f} mean={fr.mean():.4f}  (>>1 => factor grows on corp action)")
    print(f"  volume ratio vo[t]/vo[t-1]:  median={np.median(vor):.4f} mean={vor.mean():.4f}")
    print(f"  close ratio  cl[t]/cl[t-1]:  median={np.median(clr):.4f} mean={clr.mean():.4f}  (~1 => close continuous => ADJUSTED)")
    print(f"  adjclose r   ac[t]/ac[t-1]:  median={np.median(acr):.4f} mean={acr.mean():.4f}")
    print("\n  VOLUME DIRECTION (median vo_r vs median f_r):")
    mfr, mvor = np.median(fr), np.median(vor)
    print(f"    median f_r={mfr:.4f}  median vo_r={mvor:.4f}")
    print(f"    if vo_r≈f_r   -> volume = raw * factor (adjusted WITH factor)")
    print(f"    if vo_r≈1     -> volume = raw (unadjusted)")
    print(f"    if vo_r≈1/f_r -> volume = raw / factor")

print("\n=== detail: ~10送10 split days (f_r≈2) ===")
print(f"{'sym':10}{'date':12}{'f_r':>8}{'vo_r':>10}{'cl_r':>8}{'ac_r':>8}{'vo_-1':>14}{'vo_+0':>14}{'f_-1':>9}{'f_+0':>9}{'cl_-1':>9}{'cl_+0':>9}{'ac_-1':>9}{'ac_+0':>9}")
for j in detail:
    s,t=j[0],j[1]; date=CAL[t] if t<len(CAL) else "?"
    print(f"{s:10}{date:12}{j[2]:8.4f}{j[3]:10.4f}{j[4]:8.4f}{j[5]:8.4f}{j[6]:14.1f}{j[7]:14.1f}{j[8]:9.5f}{j[9]:9.5f}{j[10]:9.4f}{j[11]:9.4f}{j[12]:9.4f}{j[13]:9.4f}")
