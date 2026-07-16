"""Stage 4.3 — stale DATASET cache probe. Isolates dataset_cache by keeping
expression_cache=None. Args: <phase> <on|off>. Dataset cache stores D.features
DataFrame results keyed by hash_args(instruments, fields, freq, disk_cache,
inst_processors) -- field STRINGS only, so changing SCALE (impl) with the field
string unchanged -> stale.
"""
import os, sys, glob
sys.path.insert(0, os.path.join(os.getcwd(), ".claude", "ops"))
import qlib
from qlib.data import D
from rolling_zscore import RollingZScore, SCALE

phase = sys.argv[1]
mode = sys.argv[2]
kwargs = dict(provider_uri="~/.qlib/qlib_data/cn_data", custom_ops=[RollingZScore],
              expression_cache=None)  # isolate: only dataset cache under test
if mode == "on":
    kwargs["dataset_cache"] = "DiskDatasetCache"
else:
    kwargs["dataset_cache"] = None
qlib.init(**kwargs)

df = D.features(instruments=["sh600000"], fields=["RollingZScore($close,20)", "$close"],
               start_time="2020-06-01", end_time="2020-07-31", freq="day")
val = float(df["RollingZScore($close,20)"].iloc[-1])

dc = os.path.expanduser("~/.qlib/qlib_data/cn_data/dataset_cache")
files = glob.glob(f"{dc}/**/*", recursive=True) if os.path.isdir(dc) else []
datafiles = [f for f in files if os.path.isfile(f) and not f.endswith(".meta")]
print(f"RESULT phase={phase} scale={SCALE} dcache={mode} value={val:.10f} ds_files={len(datafiles)}", flush=True)
