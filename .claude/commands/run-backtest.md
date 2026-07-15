---
description: Run a qlib backtest from a workflow config and attribute results.
argument: workflow-yaml
---

# /run-backtest

用户要用 workflow 配置跑回测：**$ARGUMENTS**

按 `backtest-analysis` skill 全流程执行（用 Skill 工具加载它）：

1. **配置核验**：读该 workflow yaml，定位 `task.model` / `task.dataset`（handler+segments）/ `task.record`（`SignalRecord`→`SigAnaRecord`→`PortAnaRecord` 顺序，`trainer.py:61-71` 字面顺序无容错）/ `PortAnaRecord` 默认 strategy=`TopkDropoutStrategy` benchmark=`SH000300`（`record_temp.py:399-419`）。
2. **执行**：`qrun <yaml>` 或 `workflow(config_path=...)`。回测链路见 `fork-docs/ARCHITECTURE.md` 链路 2（`backtest/__init__.py:217`→`backtest.py:25`→`executor.py:227`→`exchange.py:421`）。
3. **归因**：`PortAnaRecord._generate` 出两份超额——无成本 `risk_analysis(return-bench)` 与有成本 `risk_analysis(return-bench-cost)`，默认 `mode="sum"`（`record_temp.py:507-512`）。

**读数字前必查 `fork-docs/BACKTEST_SPEC.md §0 裁决表`**：
- `annualized_return`=mean*238 单利（`evaluate.py:68/52`）；`max_drawdown`=cumsum 加性回撤（`:69`）；`information_ratio`=mean/std*sqrt(238) 有 √N（`:84`）；`ICIR`=ic.mean()/ic.std() 无 √N（`record_temp.py:326`）；long-short 用 252（`:304/335`）。
- 任何年化 / IR / ICIR 数字进结论**必须标来源函数 + scaler**。ICIR ≠ IR 同页标注。`evaluate_portfolio.py`（250）弃用。

异常排查：
- 数字没变 / 可疑 → 先查缓存（改过算子？清 `features_cache/` 或 `qlib.init(expression_cache=None)`，见 `qlib-data-ops` skill）。
- T+1 仅策略层近似（`fork-docs/FORK_SURFACE.md §3`），引擎级不强制——若策略非 TopkDropout 要注意当日买卖。
- `deal_price` 静默回退 `$close`（`exchange.py:510-513`）可掩盖缺数据。

完成后给：回测是否跑通、关键指标表（每个数字标来源函数 + scaler）、超额有/无成本两列、踩到的坑。
