---
description: Scaffold a new factor — define expression, register custom operator if needed, compute, run IC/ICIR.
argument: factor-name
---

# /new-factor

用户要新建因子：**$ARGUMENTS**

按 `factor-research` skill 全流程执行（用 Skill 工具加载它）：

1. **定义**：先确认因子表达式 DSL。内置算子够用 → 直接用；不够 → 走自定义算子。
2. **自定义算子（如需）**：子类 `ExpressionOps`，逐字实现四方法 `_load_internal` / `get_extended_window_size` / `get_longest_back_rolling` / `__str__`（签名见 skill 表，锚点 `qlib/data/ops.py:54/57/60/93`）。`__str__` 必须可被 `parse_field`→`eval` 往返。
3. **注册**：`qlib.init(custom_ops=[YourOp])`（`qlib/config.py:490` `register_all_ops`）。
4. **计算**：`D.features(instruments, fields=[...], start_time, end_time)`。开发期建议 `expression_cache=None`。
5. **IC/ICIR 评估**：经 `SigAnaRecord` / `calc_ic`。数字口径查 `fork-docs/BACKTEST_SPEC.md §0/§3`：IC=按日截面 Pearson（`alpha.py:178`）、ICIR=`ic.mean()/ic.std()` 无 √N（`record_temp.py:326`）。

执行前过一遍 `factor-reviewer` 清单前三条：(1) 若涉及自定义 processor 有 fit → 必切 fit_start/end_time；(2) rolling 窗口边界别 min_periods=1 偷渡；(3) 改算子实现后清 `<provider_uri>/features_cache/`（`qlib-data-ops` skill checklist）。

完成后给：因子定义、四方法实现（若有）、IC/ICIR/Rank-IC 数字（**标来源函数**）、踩到的坑。
