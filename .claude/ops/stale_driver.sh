#!/usr/bin/env bash
# Stage 4.3 — stale expression-cache reproduction driver.
# 5 phases, each a FRESH python process (empty MemCache -> forces disk reads).
# Toggles RollingZScore SCALE 1<->2 via sed; __str__ is unchanged so cache key is unchanged.
set -u
PY='C:/Users/Q/miniconda3/envs/qlib/python.exe'
OP='.claude/ops/rolling_zscore.py'
FC=~/.qlib/qlib_data/cn_data/features_cache
export MLFLOW_ALLOW_FILE_STORE=true

run() { "$PY" .claude/ops/stale_probe.py "$1" "$2" 2>&1 | grep "^RESULT"; }

echo "=== Phase 1: SCALE=1, cache ON (write fresh bin, record V1) ==="
sed -i 's/^SCALE = .*/SCALE = 1.0/' "$OP"
run phase1 on

echo "=== Phase 2: SCALE=2, cache ON (expect STALE V1, not 2xV1) ==="
sed -i 's/^SCALE = .*/SCALE = 2.0/' "$OP"
run phase2 on

echo "=== Phase 3: SCALE=2, cache OFF (bypass -> fresh 2xV1; bin still on disk) ==="
run phase3 off

echo "=== Phase 4: SCALE=2, cache ON again (stale REPRODUCES -> V1, decisive bypass!=clear) ==="
run phase4 on

echo "=== Phase 5: SCALE=2, cache ON after rm -rf features_cache (fresh 2xV1) ==="
rm -rf "$FC"
run phase5 on

echo "=== restore SCALE=1 ==="
sed -i 's/^SCALE = .*/SCALE = 1.0/' "$OP"
echo "done"
