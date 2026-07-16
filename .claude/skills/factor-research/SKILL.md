---
name: factor-research
description: Use when defining a new factor/alpha expression, implementing a custom qlib operator, computing factor values across instruments via D.features, or evaluating a factor via IC/ICIR/Rank-IC. Use before writing any custom operator or running factor IC analysis.
---

# factor-research

## 概述
新因子全流程：**定义 → 注册 custom_ops → 计算 → IC/ICIR 评估**。本 skill 给步骤 + 四方法签名 + 坑；口径细节见 `fork-docs/BACKTEST_SPEC.md`，算子扩展点见 `fork-docs/ARCHITECTURE.md` 扩展点表，缓存坑见 `fork-docs/FORK_SURFACE.md §1`。

## 何时使用
- 要写一个 qlib 里没有的因子表达式 / 算子。
- 已有因子要算 IC / ICIR / Rank IC / long-short。
- 复合算子改实现后重跑因子（先看缓存坑）。

## 全流程

### Step 1 定义因子表达式
DSL 串，例 `"Mean($close, 5)"`、`"Ref($close, -1)/$close - 1"`。`$` 前缀 = 裸特征（`$close` → bin 文件 `close.day.bin`，见 `fork-docs/DATA_SPEC.md §6`）。
- 内置算子足够 → 直接用 DSL，跳到 Step 4。
- 内置不够 → Step 2/3 写 custom_ops。

### Step 2 自定义算子（如需）—— 四方法实现要求
子类 `ExpressionOps`（`qlib/data/base.py`），实现下表四方法（签名逐字取自 `qlib/data/ops.py` 的 `ElemOperator` 基类）：

| 方法 | 签名 | 作用 |
|---|---|---|
| `_load_internal` | `(self, instrument, start_index, end_index, *args) -> pd.Series` | 实际计算体；`Expression.load`（`qlib/data/base.py:193`）在 cache miss 时调它。`*args` 带 `freq` |
| `get_extended_window_size` | `(self) -> (left:int, right:int)` | 告诉引擎向左/右扩张多少 calendar index 取数；引擎据此 `query_start = max(0, start_index - left)`（`data.py:853-854`）扩张取数后 trim |
| `get_longest_back_rolling` | `(self) -> int` | 最长回看窗口，rolling 对齐用 |
| `__str__` | `(self) -> str` | **双重职责**：(1) 是内存 cache key 的一部分（`base.py:187` `cache_key=str(self),...`）；(2) 必须能被 `parse_field`→`eval`（`data.py:397`）解析回等价表达式。纯结构：`"ClassName(subexpr, params)"` |

骨架（参照 `qlib/rl/data/integration.py:54` 示例）：
```python
from qlib.data.base import ExpressionOps
import pandas as pd

class MyOp(ExpressionOps):
    def __init__(self, feature, N):
        self.feature = feature
        self.N = N
    def __str__(self):
        return "{}({},{})".format(type(self).__name__, self.feature, self.N)
    def get_longest_back_rolling(self):
        return self.feature.get_longest_back_rolling() + self.N - 1
    def get_extended_window_size(self):
        lft, rght = self.feature.get_extended_window_size()
        return lft + self.N - 1, rght
    def _load_internal(self, instrument, start_index, end_index, *args):
        s = self.feature.load(instrument, start_index, end_index, *args)
        return s.rolling(self.N).mean()
```

### Step 3 注册 custom_ops
两选一（机制：`register_all_ops` → `Operators.register(C.custom_ops)`，`qlib/config.py:490`；config 默认 `"custom_ops": []`，`qlib/config.py:285`）：
```python
qlib.init(provider_uri=..., expression_cache=..., custom_ops=[MyOp])
# 或写进 config: qlib.init(...) 后 Operators 里已注册
```
注册后 DSL 串 `MyOp($close, 5)` 经 `parse_field` 第三条 regex（`__init__.py:299`）重写成 `Operators.MyOp(Feature("close"))` → `eval` 解析（`data.py:397`）。

### Step 4 计算
```python
import qlib
from qlib.data import D
qlib.init(provider_uri="~/.qlib/qlib_data/cn_data", expression_cache=None)  # 开发期建议关磁盘缓存
df = D.features(instruments=D.instruments("csi300"), fields=["MyOp($close,5)"],
                start_time="2018-01-01", end_time="2024-12-31", freq="day")
```
**cache 默认与启用（经验 2026-07，见 `fork-docs/FORK_SURFACE.md §1.7`）**：client 模式（默认 `default_conf="client"`）下 `expression_cache` 基线已 `None`（`config.py:156`+client 块无该键）→ **cache 默认 OFF**，无需显式传 `None`。要**启用**磁盘缓存须 `expression_cache="DiskExpressionCache"`，且 `DiskExpressionCache` 写锁**依赖 redis**（`config.py:478`：redis 连不上则带 WARNING 静默禁用，cache 不生效、不写 bin）；`DiskDatasetCache` 依赖 `pytables`（`pip install tables`，core 不含）。启用前先起 `redis-server`。
**Windows 多标的 hang**：`D.features` 跨多 instrument 用 joblib `multiprocessing`（`config.py:168`），Windows spawn 重导入主模块 → hang。脚本须 `if __name__=="__main__":` 守卫 + `freeze_support()`，或 `qlib.init(..., kernels=1)` 强制串行（多标的 IC 评估推荐 `kernels=1`）。

### Step 5 IC / ICIR 评估
经 `SigAnaRecord`（`qlib/workflow/record_temp.py`）→ `calc_ic`（`qlib/contrib/eva/alpha.py:160-183`）。口径**必查** `fork-docs/BACKTEST_SPEC.md §0 裁决表 + §3`：
- **IC** = 按日截面 Pearson（`alpha.py:178`）；**Rank IC** = 按日截面 Spearman（`alpha.py:179`）。
- **ICIR** = `ic.mean() / ic.std()`（`record_temp.py:326`）——**无 √N，不年化**。
- 组合 `information_ratio` = `mean/std*sqrt(238)`（`evaluate.py:84`）——**有 √N**。两者**同名不同口径**，同页必须标注。

**轻量评估（不走 full workflow）**：快速因子筛选可直接调 `calc_ic(pred, label)`（`qlib/contrib/eva/alpha.py`）——`pred`/`label` 为单列 `DataFrame`（MultiIndex `(datetime, instrument)`），返 `(ic, ric)` 两按日 Series；`ic.mean()`/`ic.std()` 即 IC/ICIR（与 `SigAnaRecord` 同函数同口径）。label 常用 `Ref($close,-1)/$close-1`（次日收益）。Windows 多标的记得 `kernels=1`（见 Step 4）。

## 常见坑
- **改算子实现不清缓存 → 静默跑旧 bin**：`__str__` 不变 → cache key 不变（`base.py:187`），新 `_load_internal` 不执行。**唯一可靠修复 = 手动删 `features_cache/`**；`qlib.init(expression_cache=None)` 只旁路本次 session、不删 stale `.bin`（`data.py:1320` 为 False → `DiskExpressionCache` 不实例化），重启用即复现——**不等价**于删文件。详见 `qlib-data-ops` skill 的 checklist / `fork-docs/FORK_SURFACE.md §1`。
- **`__str__` 不稳定或不往返** → cache key 漂移 / `parse_field`→`eval` 解析失败。`__str__` 必须纯结构、可重解析。
- **field 串经 `parse_field` → `eval()` = 可执行 Python**（`data.py:397`）：外部 / 模型生成的 field 串**不许直接进 `D.features`**（安全红线，`fork-docs/FORK_SURFACE.md §2.5`）。
- **rolling 在样本边界 min_periods=1 静默错值**：见 factor-reviewer 清单第 2 条——pandas `.rolling(N).mean()/.std()` 默认 `min_periods=window`（**不是** 1，默认即在窗口不足处产 NaN，正确）；坑在显式传 `min_periods=1` 偷渡错值。**注意 qlib 引擎按 `get_extended_window_size` 预扩张左窗取数后 trim**——故请求范围内**通常 0 边界 NaN**（NaN 在请求起点之前，被扩张取数消化）；边界 NaN 只在该 symbol **无更早历史**时出现。算子 `_load_internal` 不应显式设 `min_periods=1`。
- **复权**：要原始价用 `$close/$factor`，qlib 读层不自动复权（`fork-docs/DATA_SPEC.md §7`）。

## 红线
- 复合算子改实现后未清 `features_cache` → 结果无效。
- 任何因子 IC/ICIR 数字进结论前必标是 `calc_ic`/`record_temp.py:326`（无 √N）还是 `risk_analysis` IR（有 √N）。
- 外部 field 串不直接进 `D.features`。
