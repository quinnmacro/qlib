---
name: backtest-analysis
description: Use when configuring a qlib backtest (workflow yaml / PortAnaRecord / exchange_kwargs / strategy), executing a backtest run via qrun or task_train, or reading and attributing backtest results (annualized return, IR, IC, drawdown, long-short). Use before quoting any backtest number to pin down which function and scaler produced it.
---

# backtest-analysis

## 概述
回测全流程：**配置 → 执行 → 归因**。本 skill 给步骤 + 坑；**口径裁决**全在 `fork-docs/BACKTEST_SPEC.md §0 裁决表`——读任何回测数字前先查它，不在本 skill 复述。链路见 `fork-docs/ARCHITECTURE.md` 链路 2 + 扩展点表。

## 何时使用
- 写 / 改 workflow yaml（task / record / PortAnaRecord / strategy / exchange_kwargs）。
- 跑一次回测并出指标。
- 读回测结果数字（年化、IR、IC、回撤、long-short）写进结论 / 报告。
- 排查"为什么这次年化和上次对不上"——多半是口径错配。

## 全流程

### Step 1 配置
workflow yaml（CLI 入口 `qlib/cli/run.py:86` `workflow()`，`:147` `task_train(config.get("task"))`）关键段：
- `task.model` / `task.dataset`（handler + segments）——`_exe_task`（`trainer.py:42-71`）按 `accept_types=Model`/`Dataset` 实例化。
- `task.record`：list，**字面顺序** plain `for`，无重排无 try/except（`trainer.py:61-71`）。fork 容错须自己包 try/except。`SignalRecord`（`record_temp.py:161`）→ 存 pred/label；`SigAnaRecord`（`:295`）→ 算 IC/ICIR；`PortAnaRecord`（`:358`）→ 跑回测 + `risk_analysis`。
- `PortAnaRecord` 默认 A 股风味：strategy=`TopkDropoutStrategy` topk=50/n_drop=5，benchmark=`SH000300`（`record_temp.py:399-419`）。

### Step 2 执行
```bash
qrun <workflow.yaml>                       # CLI
# 或程序内
from qlib.cli.run import workflow
workflow(config_path="<workflow.yaml>", experiment_name="exp")
```
回测入口 `PortAnaRecord._generate`（`record_temp.py:465`）→ `normal_backtest`（= `qlib.backtest.backtest`，`backtest/__init__.py:217`）→ `backtest_loop`（`backtest.py:25`）→ `collect_data_loop`（`:52`）→ `trade_executor.collect_data`（`executor.py:227`）→ `Exchange.deal_order`（`exchange.py:421`）。

### Step 3 归因
`PortAnaRecord._generate` 出两份超额：`risk_analysis(return-bench)` 无成本、`risk_analysis(return-bench-cost)` 有成本（`record_temp.py:507-512`），默认 `mode="sum"`（不传 `mode=`）。指标→函数映射见 `fork-docs/BACKTEST_SPEC.md §0`。

## 读数字前必查口径裁决表（不在此复述）
查 `fork-docs/BACKTEST_SPEC.md §0`：每个数字问"哪个函数 + 哪个 scaler 算的"。一句话版：
- `annualized_return`（sum 模式）= `mean*238`，**单利不是复利**（`evaluate.py:68`/`:52`）。
- `max_drawdown`（sum 模式）= cumsum 上的加性回撤（`evaluate.py:69`）。
- `information_ratio` = `mean/std*sqrt(238)`，**有 √N**（`evaluate.py:84`）。
- `ICIR` = `ic.mean()/ic.std()`，**无 √N**（`record_temp.py:326`）。≠ IR。
- long-short 年化用 **252**（`record_temp.py:304/335`），与组合 238 不一致。
- `evaluate_portfolio.py` 全用 **250**，legacy 弃用（`fork-docs/BACKTEST_SPEC.md §0` 划掉行）。

## 常见坑
- **裸报"年化 X%"**——必须标来源函数 + scaler（238 / 252 / 250）。
- **ICIR 与 IR 同页不标**——同名不同口径（有/无 √N）。
- **`evaluate_portfolio.py` 的 250 指标误用**——除非显式从 position dict 算，否则别用；其 `get_normal_ic`/`get_rank_ic` 是整面板单相关，与 `calc_ic` 按日 groupby 不等价。
- **T+1 仅策略层 `hold_thresh` 近似**（`qlib/contrib/strategy/signal_strategy.py:242-244`），引擎级 `Exchange.deal_order` 不强制（`fork-docs/FORK_SURFACE.md §3`）——当日买入可立即全卖。要引擎级 T+1 须 fork 子类 override。
- **`deal_price` 静默回退 `$close`**（`exchange.py:510-513`，`fork-docs/FORK_SURFACE.md` 附录）——配置价 NaN 时 warn 后回退，可掩盖缺数据。
- **回报数字三层**：`rtn` 不含成本 / `earning` 含成本 / `return_rate` gross of cost（`account.py:18-31,283`，`fork-docs/BACKTEST_SPEC.md §4.2`）。读超额数字取无成本 / 有成本看问题。
- **改算子后回测数字没变？** 先查缓存（`qlib-data-ops` skill / `fork-docs/FORK_SURFACE.md §1`），不是口径问题。

## 红线（摘自 `fork-docs/BACKTEST_SPEC.md §5`）
- 回测收益数字必须标来源函数 + scaler。
- ICIR ≠ IR，同页标注。
- sum 模式 = 单利 + cumsum 加性回撤（默认）；改复利须显式传 `mode="product"`（qlib 自身不传，须 fork）。
- 不改 upstream 口径——不在 `evaluate.py` 顺手把 238 改 252（上游 `c38e799c` 口径仍演进）。
- `evaluate_portfolio.py` 弃用。
