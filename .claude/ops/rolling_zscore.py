"""Stage 4.2 — first custom qlib operator, built by following
`.claude/skills/factor-research/SKILL.md` Step 2.

RollingZScore: (x - mean(x, N)) / std(x, N) over a trailing N-day window.
- has a lookback (exercises get_extended_window_size / get_longest_back_rolling)
- hand-verifiable against an explicit windowed mean/std
- produces NaN where the window is incomplete (no min_periods=1 silent-wrong-value)
"""
import numpy as np
import pandas as pd
from qlib.data.base import ExpressionOps

# Module-level coefficient. NOTE: __str__ below does NOT include SCALE, so changing
# SCALE changes _load_internal's output WITHOUT changing the cache key. This is the
# hook used by the stale-cache experiment in FORK_SURFACE §1 (toggles SCALE 1<->2).
SCALE = 1.0


class RollingZScore(ExpressionOps):
    def __init__(self, feature, N):
        self.feature = feature
        self.N = N

    def __str__(self):
        # pure structural, reparseable by parse_field -> eval
        return "{}({},{})".format(type(self).__name__, self.feature, self.N)

    def get_longest_back_rolling(self):
        return self.feature.get_longest_back_rolling() + self.N - 1

    def get_extended_window_size(self):
        lft, rght = self.feature.get_extended_window_size()
        return lft + self.N - 1, rght

    def _load_internal(self, instrument, start_index, end_index, *args):
        s = self.feature.load(instrument, start_index, end_index, *args)
        m = s.rolling(self.N).mean()           # pandas default min_periods=window -> NaN for first N-1
        sd = s.rolling(self.N).std(ddof=1)      # explicit ddof=1 (matches pandas default, matches risk_analysis std)
        return SCALE * (s - m) / sd
