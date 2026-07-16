#!/usr/bin/env bash
# Stage 4.3 — stale DATASET cache reproduction driver. Same 5-phase protocol as
# stale_driver.sh but for dataset_cache (DiskDatasetCache), expression_cache=None
# to isolate. Key = hash_args(instruments, fields, freq, disk_cache, inst_processors)
# -- field strings only, so SCALE change with field string unchanged -> stale.
set -u
PY='C:/Users/Q/miniconda3/envs/qlib/python.exe'
OP='.claude/ops/rolling_zscore.py'
DC=~/.qlib/qlib_data/cn_data/dataset_cache
export MLFLOW_ALLOW_FILE_STORE=true

run() { "$PY" .claude/ops/stale_probe_ds.py "$1" "$2" 2>&1 | grep "^RESULT"; }

echo "=== Phase 1: SCALE=1, dcache ON (write fresh dataset, record V1) ==="
sed -i 's/^SCALE = .*/SCALE = 1.0/' "$OP"; rm -rf "$DC" 2>/dev/null
run ds_phase1 on

echo "=== Phase 2: SCALE=2, dcache ON (expect STALE V1, not 2xV1) ==="
sed -i 's/^SCALE = .*/SCALE = 2.0/' "$OP"
run ds_phase2 on

echo "=== Phase 3: SCALE=2, dcache OFF (bypass -> fresh 2xV1; dataset still on disk) ==="
run ds_phase3 off

echo "=== Phase 4: SCALE=2, dcache ON again (stale REPRODUCES -> V1) ==="
run ds_phase4 on

echo "=== Phase 5: SCALE=2, dcache ON after rm -rf dataset_cache (fresh 2xV1) ==="
rm -rf "$DC"
run ds_phase5 on

echo "=== restore SCALE=1 ==="
sed -i 's/^SCALE = .*/SCALE = 1.0/' "$OP"
echo done
