"""Stage 4.1 v3 — strict-threshold corporate actions + single-stock window."""
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

# ---- single-stock window around a known 10送10 split ----
def window(sym, target_date, span=8):
    cl=read_bin(sym,"close"); ac=read_bin(sym,"adjclose"); vo=read_bin(sym,"volume"); f=read_bin(sym,"factor")
    if cl is None: return
    n=min(len(cl),len(ac),len(vo),len(f))
    cl,ac,vo,f=cl[:n],ac[:n],vo[:n],f[:n]
    t=int(np.where(CAL==target_date)[0][0])
    lo,hi=max(0,t-span),min(n,t+span+1)
    print(f"\n=== {sym} around {target_date} (10送10 split, f should ~double) ===")
    print(f"{'date':12}{'close':>10}{'adjclose':>12}{'volume':>16}{'factor':>10}")
    for i in range(lo,hi):
        mark = " <== SPLIT" if i==t else ""
        def fmt(x): return f"{x:.4f}" if (not np.isnan(x)) else "nan"
        print(f"{CAL[i] if i<len(CAL) else '?':12}{fmt(cl[i]):>10}{fmt(ac[i]):>12}{vo[i]:>16.1f}{fmt(f[i]):>10}{mark}")

for sym,dt in [("sh600005","2004-10-18"),("sh600011","2002-06-21"),("sh600010","2004-09-20")]:
    window(sym,dt)

# ---- strict aggregate: REAL corporate actions only (|f_r-1|>0.05) ----
# bucket by f_r to see volume response as a function of factor change
rows=[]
for s in SYMS:
    if not (s.startswith("sh6") or s.startswith("sz0") or s.startswith("sz3")): continue
    f=read_bin(s,"factor"); vo=read_bin(s,"volume"); cl=read_bin(s,"close"); ac=read_bin(s,"adjclose")
    if f is None or vo is None or cl is None or ac is None: continue
    n=min(len(f),len(vo),len(cl),len(ac))
    f,vo,cl,ac=f[:n],vo[:n],cl[:n],ac[:n]
    fin=~(np.isnan(f)|np.isnan(vo)|np.isnan(cl)|np.isnan(ac))
    fin = fin & np.r_[False, fin[:-1]]  # t and t-1 both valid
    idx = np.where(fin)[0]
    idx = idx[idx>0]
    if len(idx)==0: continue
    fr = f[idx]/f[idx-1]; vor = vo[idx]/vo[idx-1]; clr=cl[idx]/cl[idx-1]; acr=ac[idx]/ac[idx-1]
    real = np.abs(fr-1) > 0.05  # strict: real corp action
    rows.append((fr[real],vor[real],clr[real],acr[real]))
fr=np.concatenate([r[0] for r in rows if len(r[0])])
vor=np.concatenate([r[1] for r in rows if len(r[1])])
clr=np.concatenate([r[2] for r in rows if len(r[2])])
acr=np.concatenate([r[3] for r in rows if len(r[3])])
print(f"\n=== STRICT corporate-action days (|f_r-1|>0.05): {len(fr)} events ===")
print(f"  factor ratio f_r:     median={np.median(fr):.4f} mean={fr.mean():.4f}  p1={np.percentile(fr,1):.4f} p99={np.percentile(fr,99):.4f}")
print(f"  volume ratio vo_r:    median={np.median(vor):.4f} mean={vor.mean():.4f}")
print(f"  close ratio cl_r:     median={np.median(clr):.4f}  (close continuous? ~1 => adjusted)")
print(f"  adjclose ratio ac_r:  median={np.median(acr):.4f}  (adjclose continuous? ~1 => adjusted)")

# bucket by f_r magnitude (split-like f_r~2 vs cash-div f_r~1.0x small)
print("\n  volume response BY factor-ratio bucket:")
for lo,hi,label in [(1.0,1.02,"~cash div (f_r 1.00-1.02)"),(1.02,1.5,"small action (1.02-1.5)"),(1.5,2.5,"~10送10 split (1.5-2.5)"),(2.5,5.0,"bigger (>2.5)")]:
    m=(fr>=lo)&(fr<hi)
    if m.sum()>0:
        print(f"    {label:30} n={m.sum():6d}  med f_r={np.median(fr[m]):.4f}  med vo_r={np.median(vor[m]):.4f}  med cl_r={np.median(clr[m]):.4f}  med ac_r={np.median(acr[m]):.4f}")
