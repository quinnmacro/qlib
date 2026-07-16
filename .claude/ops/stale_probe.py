"""Stage 4.3 stale-cache probe. Run as a FRESH process per phase (so in-memory
MemCache H is empty, forcing disk reads). Args: <phase_label> <cache_on|cache_off>.
Reports the RollingZScore($close,20) value at the last date of the queried range,
plus how many .bin files live in features_cache/.
"""
import os, sys, glob
sys.path.insert(0, os.path.join(os.getcwd(), ".claude", "ops"))
import qlib
from qlib.data import D
from rolling_zscore import RollingZScore, SCALE  # SCALE is read from file at import

phase = sys.argv[1]
cache_mode = sys.argv[2]
kwargs = dict(provider_uri="~/.qlib/qlib_data/cn_data", custom_ops=[RollingZScore])
# NOTE: client mode defaults expression_cache to None (config.py:156 + client block has no
# expression_cache key). To actually enable the disk cache we must set it explicitly.
if cache_mode == "on":
    kwargs["expression_cache"] = "DiskExpressionCache"
elif cache_mode == "off":
    kwargs["expression_cache"] = None
qlib.init(**kwargs)

SYM = "sh600000"
ST, EN = "2020-06-01", "2020-07-31"
df = D.features(instruments=[SYM], fields=["RollingZScore($close,20)"],
                start_time=ST, end_time=EN, freq="day")
val = float(df["RollingZScore($close,20)"].iloc[-1])

fc = os.path.expanduser("~/.qlib/qlib_data/cn_data/features_cache")
bins = glob.glob(f"{fc}/**/*.bin", recursive=True) if os.path.isdir(fc) else []
print(f"RESULT phase={phase} scale={SCALE} cache={cache_mode} value={val:.10f} bin_count={len(bins)}", flush=True)
