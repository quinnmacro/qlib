# ARCHITECTURE.md —— qlib 两条核心链路函数级调用序列 + 扩展点

> 给"上下文被 clear 之后的我"看的架构地图。不是介绍文。
> 规则：每步可追溯 `路径:行号`。`[已自核]` = 主 agent 亲开文件核对；`[已核实-子agent]` = 本轮架构子 agent 亲读逐字引用。
> 两条链路：**链路 1 训练/推理 + record 生成**（qrun → task_train → model.fit → records → D.features → Expression.load）；**链路 2 回测执行**（strategy → executor → exchange → account）。

---

## 链路 1：训练 / 推理 / record 生成

### 1.1 CLI 入口 —— `qlib/cli/run.py` `[已核实-子agent]`
- `:86` `def workflow(config_path, experiment_name="workflow", uri_folder="mlruns")`——渲染 YAML(`:106`)、merge BASE_CONFIG(`:111-133`)、`sys_config`(`:136`)、`qlib.init(...)`(`:139`/`:143`)。
- `:147` `recorder = task_train(config.get("task"), experiment_name=experiment_name)`——**用 `config.get("task")`（None-safe），非 `config["task"]`**。
- `:148` `recorder.save_objects(config=config)`。
- `:152` `def run():` → `:153` `fire.Fire(workflow)`。

### 1.2 task_train —— `qlib/model/trainer.py` `[已核实-子agent]`
`:108` `def task_train(task_config, experiment_name, recorder_name=None) -> Recorder:`：
1. `:125` `with R.start(experiment_name=experiment_name, recorder_name=recorder_name):`
2. `:126` `_log_task_info(task_config)`
3. `:127` `_exe_task(task_config)`
4. `:128` `return R.get_recorder()`
5. context exit 隐式（`with` 块末），无显式 `R.end_recorder()`。

### 1.3 _exe_task —— `qlib/model/trainer.py:42-71` `[已核实-子agent]`
`:42` `def _exe_task(task_config):`
1. `:43` `rec = R.get_recorder()`
2. `:45` `model = init_instance_by_config(task_config["model"], accept_types=Model)`
3. `:46` `dataset = init_instance_by_config(task_config["dataset"], accept_types=Dataset)`
4. `:47` `reweighter = task_config.get("reweighter", None)`
5. `:49` `auto_filter_kwargs(model.fit)(dataset, reweighter=reweighter)`——**reweighter 总被传**，`auto_filter_kwargs` 在 `model.fit` 不接受时丢弃
6. `:50` `R.save_objects(**{"params.pkl": model})`
7. `:52` `dataset.config(dump_all=False, recursive=True)`
8. `:53` `R.save_objects(**{"dataset": dataset})`
9. `:55-56` `task_config = fill_placeholder(task_config, {"<MODEL>": model, "<DATASET>": dataset})`
10. `:58` `records = task_config.get("record", [])`；`:59-60` dict→list 规范化
11. `:61` `for record in records:`
12. `:65-70` `r = init_instance_by_config(record, recorder=rec, default_module="qlib.workflow.record_temp", try_kwargs={"model": model, "dataset": dataset})`
13. `:71` `r.generate()`

**record 循环**：顺序 = config["record"] 字面顺序，plain `for`，**无重排无 try/except**。任一 record 异常中断剩余并传播。fork 容错须包 `:65-71` 于 try/except。

### 1.4 init_instance_by_config —— `qlib/utils/mod.py` `[已核实-子agent]`
- `:122` `def init_instance_by_config(config, default_module=None, accept_types=(), try_kwargs={}, **kwargs) -> Any:`（import 进 `qlib.utils.__init__`，**不在 `__init__.py` 本体**）。
- `:156-157` `isinstance(config, accept_types)` 短路返。
- `:176` `klass, cls_kwargs = get_callable_kwargs(config, default_module=default_module)`。
- `:178-184` `try: return klass(**cls_kwargs, **try_kwargs, **kwargs)` except TypeError → `return klass(**cls_kwargs, **kwargs)`（`try_kwargs` 冲突时 fallback）。
- `get_callable_kwargs` `:67`：`:92` key=`"class"` 若有 else `"func"`；`:97` `split_module_path`（dotted 串 `a.b.c.Class` 直用，否则 `:99` `m_path=config.get("module_path", default_module)`）；`:100` `get_module_by_module_path(m_path)`；`:103` `getattr(module, cls)`；`:106` `kwargs=config.get("kwargs", {})`。

### 1.5 record 生成 —— `qlib/workflow/record_temp.py` `[已核实-子agent]`
- `SignalRecord`(`:161`) `generate`(`:190`)：`:192` `pred = self.model.predict(self.dataset)`；`:195` `self.save(**{"pred.pkl": pred})`；`:204-206` `generate_label` → 存 `label.pkl`。
- `SigAnaRecord`(`:295`, `ACRecordTemp` 子类) 继承 `ACRecordTemp.generate`(`:219`) → `:235` 调 `self._generate`；`:310` `_generate` → `:323` `ic, ric = calc_ic(...)`；`:347` `log_metrics`。
- `PortAnaRecord`(`:358`) `_generate`(`:465`)：`:466` load pred；`:470-471` `fill_placeholder` 注 `<PRED>`；`:488-490` `normal_backtest(executor=self.executor_config, strategy=self.strategy_config, **self.backtest_config)`；`:507-512` 两次 `risk_analysis`；`:517` `log_metrics`。`risk_analysis` 从 `qlib.contrib.evaluate` import(`:13`)。

### 1.6 DataHandlerLP fit 路径 —— `qlib/data/dataset/handler.py` `[已核实-子agent]`
- `:510` `get_all_processors()` = `shared_processors + infer_processors + learn_processors`。
- `:513` `def fit(self):` → `:517` `for proc in self.get_all_processors():` `:519` `proc.fit(self._data)`。**fit 在整个 raw `self._data` 上调，不是 train 切片**（泄漏边界见下）。
- `:521` `fit_process_data()` → `:527` `self.process_data(with_fit=True)`。
- `:530` `def _run_proc_l(df, proc_l, with_fit, check_for_infer):`（`:529` 是 `@staticmethod` 装饰器）：`:537-538` `if with_fit: proc.fit(df)`；`:539` `df = proc(df)`——**fit 输入是前一 processor 输出**（链式）。
- `:552` `process_data(with_fit=False)`。
- `:633` `setup_data(init_type=IT_FIT_SEQ, **kwargs)`：`:650` `super().setup_data`；`:652-661` dispatch：`IT_FIT_IND`→`fit()`+`process_data()`；`IT_LS`→`process_data()`；`IT_FIT_SEQ`→`fit_process_data()`。`IT_*` 常量 `:629-631`。

**泄漏边界**：`proc.fit(self._data)` 收全时间范围。防泄漏逐 processor 经 `fit_start_time`/`fit_end_time`，仅时序归一器遵守：`MinMaxNorm.fit`/`ZScoreNorm.fit`/`RobustZScoreNorm.fit`（`processor.py:204-218/238-252/281-288` `[已自核]`）。自定义带状态 `fit()` 且不切片 → 泄漏。

### 1.7 Dataset 切片 —— `qlib/data/dataset/__init__.py` + handler `[已核实-子agent]`
- `:185` `DatasetH.prepare(segments, col_set=CS_ALL, data_key=DK_I, **kwargs)`：`:229-230` 建 `seg_kwargs`；`:240` `return self._prepare_seg(self.segments[segments], **seg_kwargs)`；`:244` 多 seg list；`:247` pass-through slice。
- `:171` `_prepare_seg(slc, **kwargs)`：`:180-181` `return self.handler.fetch(slc, **kwargs, **self.fetch_kwargs)`（有 `fetch_kwargs`）else `:183` `self.handler.fetch(slc, **kwargs)`。
- `handler.py:197` `DataHandler.fetch(selector=..., level="datetime", col_set=..., data_key=..., ...)` → `:307`/`:312` `fetch_df_by_index(data_df, selector, level, fetch_orig=self.fetch_orig)`。**processor 此处不跑**（已在 `setup_data` 跑过）。segmentation 是预处理后 `_infer`/`_learn` 的纯 index 切片。

### 1.8 loader → provider → expression —— `qlib/data/dataset/loader.py` + `qlib/data/data.py` `[已核实-子agent]`
- `loader.py:153` `class QlibDataLoader(DLWParser):`。`.load` 继承自 `DLWParser.load`(`loader.py:138`) → `:142`/`:149` `load_group_df`。
- `loader.py:202` `QlibDataLoader.load_group_df(...)` → `:223` `df = D.features(instruments, exprs, start_time, end_time, freq=freq, inst_processors=inst_processors)`。
- `data.py:843` `LocalExpressionProvider.expression(instrument, field, start_time, end_time, freq="day")`：
  - `:844` `get_expression_instance(field)`
  - `:852` `_, _, start_index, end_index = Cal.locate_index(start_time, end_time, freq=freq, future=False)`
  - `:853` `lft_etd, rght_etd = expression.get_extended_window_size()`
  - `:854` `query_start, query_end = max(0, start_index - lft_etd), end_index + rght_etd`
  - `:859` `series = expression.load(instrument, query_start, query_end, freq)`
  - `:877-878` `if not series.empty: series = series.loc[start_index:end_index]`——扩张部分 trim 丢弃。

### 1.9 Expression.load 缓存键 —— `qlib/data/base.py:142` `[已自核]` body `:184-203`
- `:142` `def load(self, instrument, start_index, end_index, *args):`
- `:187` `cache_key = str(self), instrument, start_index, end_index, *args`
- `:188-189` `if cache_key in H["f"]: return H["f"][cache_key]`
- `:193` `series = self._load_internal(instrument, start_index, end_index, *args)`
- `:201` `series.name = str(self)`
- `:202` `H["f"][cache_key] = series`；`:203` `return series`

**key 不含算子实现 hash / class 身份 / 版本**——这是缓存静默 stale 的根（详见 `FORK_SURFACE.md` §1）。磁盘侧 `DiskExpressionCache._uri`(`qlib/data/cache.py:502-505` `[已自核]`) = `hash_args(instrument, field, freq)`，同样只看 DSL 串。

---

## 链路 2：回测执行

### 2.1 PortAnaRecord → backtest 入口 `[已核实-子agent]`
- `record_temp.py:465` `PortAnaRecord._generate`：`:470-471` `fill_placeholder` 注 `<PRED>`；`:488-490` `normal_backtest(executor=..., strategy=..., **self.backtest_config)`。
- `record_temp.py:17` `from ..backtest import backtest as normal_backtest`——**`normal_backtest` 是 `backtest` 的 import 别名**，无 `normal_backstrategist` 函数。
- `qlib/backtest/__init__.py:217` `def backtest(start_time, end_time, strategy, executor, benchmark="SH000300", account=1e9, exchange_kwargs={}, pos_type="Position"):` → `:266` `trade_strategy, trade_executor = get_strategy_executor(...)`；`:275` `return backtest_loop(start_time, end_time, trade_strategy, trade_executor)`。
- `qlib/backtest/backtest.py:25` `def backtest_loop(...):` → `:43` `for _decision in collect_data_loop(...): pass`；`:46-47` 取 `portfolio_dict`/`indicator_dict`。
- `qlib/backtest/backtest.py:52` `def collect_data_loop(...):` → `:82` `trade_executor.reset(...)`；`:83` `trade_strategy.reset(level_infra=...)`；`:87` `while not trade_executor.finished():`；`:88` `trade_strategy.generate_trade_decision(_execute_result)`；`:89` `yield from trade_executor.collect_data(_trade_decision, level=0)`。

### 2.2 BaseExecutor / SimulatorExecutor —— `qlib/backtest/executor.py` `[已核实-子agent]`
`BaseExecutor.collect_data`(`:227`)：
- `:262-263` `if self.track_data: yield trade_decision`
- `:265` `atomic = not issubclass(self.__class__, NestedExecutor)`
- `:270-271` `if self._settle_type != BasePosition.ST_NO: self.trade_account.current_position.settle_start(self._settle_type)`——**T+1 引擎层默认 OFF**（`ST_NO`），同 bar 卖出现金立即可买；`ST_CASH` 须显式开。
- `:273` `obj = self._collect_data(trade_decision=trade_decision, level=level)`
- `:275-281` yield-from if GeneratorType else unpack
- `:283-293` `self.trade_account.update_bar_end(...)`
- `:295` `self.trade_calendar.step()`
- `:297-298` `if self._settle_type != ST_NO: self.trade_account.current_position.settle_commit()`

`SimulatorExecutor`(`:513`)：`:520` `TT_SERIAL="serial"`；`:523` `TT_PARAL="parallel"`；`:528` `__init__(..., trade_type=TT_SERIAL, ...)`。
- `:561` `_get_order_iterator(trade_decision)` → `:574` `_retrieve_orders_from_decision`；`:576` TT_SERIAL→`order_it=orders`；`:579-585` **TT_PARAL: `order_it = sorted(orders, key=lambda order: -order.direction)`——BUY-first**（`Order.SELL=0, Order.BUY=1`(`qlib/backtest/decision.py:32-33`)，`-direction` 升序 ⇒ BUY(-1) 先；`:583` 注释 "make the buying go first"）。**注意：非 SELL-first，上轮笔记此处错。**
- `:590` `_collect_data(trade_decision, level=0)` → `:594` `for order in self._get_order_iterator(trade_decision):`；`:597-600` 每新日 reset `dealt_order_amount`；`:604-608` `trade_val, trade_cost, trade_price = self.trade_exchange.deal_order(order, trade_account=self.trade_account, dealt_order_amount=self.dealt_order_amount)`；`:611` `self.dealt_order_amount[order.stock_id] += order.deal_amount`；`:628` `return execute_result, {"trade_info": execute_result}`。

### 2.3 NestedExecutor —— `qlib/backtest/executor.py:310` `[已核实-子agent]`
- `:349-358` `self.inner_executor = init_instance_by_config(inner_executor, common_infra=..., accept_types=BaseExecutor)`；`self.inner_strategy = init_instance_by_config(inner_strategy, ..., accept_types=BaseStrategy)`。
- `:389` `_init_sub_trading(trade_decision)`：`:390` `trade_start_time, trade_end_time = self.trade_calendar.get_step_time()`；`:391` `self.inner_executor.reset(start_time=trade_start_time, end_time=trade_end_time)`（内 executor calendar 重置到外步 `[start,end]`）；`:392-393` 设 sub_level_infra；`:394` `self.inner_strategy.reset(level_infra=sub_level_infra, outer_trade_decision=trade_decision)`。
- `:406` `_collect_data(trade_decision, level=0)`：`:417` `self._init_sub_trading(trade_decision)`；`:420` `while not self.inner_executor.finished():`；`:436` `res = self.inner_strategy.generate_trade_decision(_inner_execute_result)`。

### 2.4 策略层 `[已核实-子agent]`
- `qlib/strategy/base.py:23` `class BaseStrategy:`；`:132-146` `@abstractmethod def generate_trade_decision(self, execute_result=None)`。
- **`TopkDropoutStrategy` 在 `qlib/contrib/strategy/signal_strategy.py:75`**（`qlib/strategy/signal_strategy.py` 不存在——上轮笔记路径错）。
  - `:81` `__init__(*, topk, n_drop, method_sell="bottom", method_buy="top", hold_thresh=1, ...)`；`:88` `hold_thresh=1`；`:134` `self.hold_thresh = hold_thresh`。
  - `:138` `generate_trade_decision(execute_result=None)`：`:140` `trade_step = self.trade_calendar.get_trade_step()`；`:142` `pred_start_time, pred_end_time = self.trade_calendar.get_step_time(trade_step, shift=1)`——**信号 shift=1**（今日决策用早一 bar 预测，T+1 信息边界）。
  - `:242-244` 卖出闸：`time_per_step = self.trade_calendar.get_freq()`；`if current_temp.get_stock_count(code, bar=time_per_step) < self.hold_thresh: continue`——count 在 bar 末 `Account.update_current_position`→`add_count_all` 增。**T+1 仅此策略层近似，非核心引擎规则。**

### 2.5 Exchange.deal_order —— `qlib/backtest/exchange.py:421-463` `[已核实-子agent]`
`:421` `def deal_order(self, order, trade_account=None, position=None, dealt_order_amount=defaultdict(float))`：
- `:438` `if not self.check_order(order):` → `:439-442` `order.deal_amount = 0.0; return 0.0, 0.0, np.nan`
- `:448-452` `trade_price, trade_val, trade_cost = self._calc_trade_info_by_order(order, trade_account.current_position if trade_account else position, dealt_order_amount)`
- `:453-461` `if trade_val > 1e-5:` → `:459` `trade_account.update_order(...)`（有 account）OR `:461` `position.update_order(...)`（elif position）
- `:463` `return trade_val, trade_cost, trade_price`

### 2.6 check_order / is_stock_tradable `[已核实-子agent]`
- `:417` `check_order(order) -> bool` → `:419` `return self.is_stock_tradable(order.stock_id, order.start_time, order.end_time, order.direction)`。
- `:404` `is_stock_tradable(stock_id, start_time, end_time, direction=None)` → `:412-414` `return not (self.check_stock_suspended(...) or self.check_stock_limit(...))`。**仅查停牌+涨跌停，无时序持仓约束。**

### 2.7 _calc_trade_info_by_order —— `exchange.py:859-952` `[已核实-子agent]`
`:859` `def _calc_trade_info_by_order(self, order, position, dealt_order_amount)`：
1. `:873-876` `trade_price = self.get_deal_price(order.stock_id, order.start_time, order.end_time, direction=order.direction)`
2. `:877` `total_trade_val = self.get_volume(...) * trade_price`
3. `:878` `order.factor = self.get_factor(...)`；`:879` `order.deal_amount = order.amount`
4. `:884` `self._clip_amount_by_volume(order, dealt_order_amount)`（def `:786-832`，in-place 改 `order.deal_amount`；`:828` `order.deal_amount = max(min(vol_limit_min, orig_deal_amount), 0)`）
5. `:887` `trade_val = order.deal_amount * trade_price`
6. impact：`:890` `adj_cost_ratio = self.impact_cost`（`not total_trade_val or isnan`）；`:892` `adj_cost_ratio = self.impact_cost * (trade_val/total_trade_val)**2`
7. `:894-917` **SELL**：`:895` `cost_ratio = self.close_cost + adj_cost_ratio`；持仓 clip `:899-909`；cash guard `:912-916`→`order.deal_amount=0`
8. `:919-942` **BUY**：`:920` `cost_ratio = self.open_cost + adj_cost_ratio`；cash check `:923-928`；partial `:929-936`；full `:937-939`；no-position `:941-942`
9. `:948` `trade_cost = max(trade_val * cost_ratio, self.min_cost)`
10. `:949-951` `if trade_val <= 1e-5: trade_cost = 0`
11. `:952` `return trade_price, trade_val, trade_cost`

### 2.8 T+1 确认 —— Exchange 不强制 `[已核实-子agent]`
grep `exchange.py` for `t+1|t1|today|bought|holding|day_count|settle` 仅两条无关 log(`:152,254`)。**无持仓期、无"当日买入"、无 day-count、无结算逻辑**。SELL 分支 clip 仅到总持仓(`:899-909`)，不区分当日 vs 之前。唯一持仓闸在策略层 `TopkDropoutStrategy`(`qlib/contrib/strategy/signal_strategy.py:243` `hold_thresh`)。T+1 引擎级强制 = fork-required（详见 `FORK_SURFACE.md` §3）。

---

## 扩展点

| 扩展 | 基类/钩子（file:line） | 如何接入 | 注册机制 |
|---|---|---|---|
| **custom_ops（自定义算子）** | `ExpressionOps`(`qlib/data/base.py`)；注册 `qlib/data/ops.py:1670` `register_all_ops`→`:1679-1680` `Operators.register(C.custom_ops)`；config `qlib/config.py:285` `"custom_ops": []`；触发 `qlib/config.py:490` `register_all_ops(self)` | 子类 `ExpressionOps`，实现 `_load_internal`/`get_longest_back_rolling`/`get_extended_window_size` + override `__str__`，传 `qlib.init(custom_ops=[YourOp])`。示例 `qlib/rl/data/integration.py:54` | `OpsWrapper.__getattr__`(`ops.py:1661` `[已自核]`) |
| **processor** | `Processor`(`qlib/data/dataset/processor.py:35`) | 子类实现 `__call__`/`fit`/`is_for_infer`/`readonly`，在 `DataHandlerLP` `shared/infer/learn_processors`(`handler.py:510`) 用 `{"class":..,"module_path":..,"kwargs":..}` 引用 | `init_instance_by_config`(`qlib/utils/mod.py:122`) name-only 解析（须可从 `qlib.data.dataset.processor` import，否则给 `module_path`） |
| **model** | `Model`(`qlib/model/base.py:22`，`fit :25`/`predict :62-63`)；`ModelFT`(`:81`，`finetune :84-85`) | 子类 `Model`/`ModelFT`，放 `{"class":..,"module_path":..}` 于 `task["model"]`；`_exe_task`(`trainer.py:45`) 用 `accept_types=Model` 实例化 | config 引用，无中央注册 |
| **RecordTemp** | `RecordTemp`(`record_temp.py:28`，`generate`)；`ACRecordTemp`(`:212`，`_generate :240` abstract，`generate :219` 自动 check→_generate→save) | 子类实现 `generate`（或 `ACRecordTemp._generate` 返 artifact dict），加 config 到 `task["record"]` | `_exe_task`(`trainer.py:65-70`) `default_module="qlib.workflow.record_temp"` + `try_kwargs={"model","dataset"}` |
| **data handler** | `DataHandlerLP`(`handler.py:382`)；`DataHandler`(`:67`)；`DataHandlerABC`(`:25`) | 子类 `DataHandlerLP`，override `default_data_loader`/processors/`_maybe_append_processor`，设 `segments`，放 `task["dataset"]`；`_exe_task`(`trainer.py:46`) `accept_types=Dataset` | config 引用 |
| **strategy** | `BaseStrategy`(`qlib/strategy/base.py:23`，`generate_trade_decision :132-146`) | 子类实现 `generate_trade_decision(execute_result)`，放 `{"class":..}` 于 `PortAnaRecord.strategy_config`(`record_temp.py:470-471`) 或 `backtest(strategy=...)` | `get_strategy_executor`(`qlib/backtest/__init__.py:266`) 解析 |
| **exchange 行为** | `Exchange`(`qlib/backtest/exchange.py:28`)；可 override：`_update_limit :273`、`check_stock_limit :338`、`check_stock_suspended :378`、`is_stock_tradable :404`、`check_order :417`、`deal_order :421`、`get_deal_price :494`、`get_factor :516`、`round_amount_by_trade_unit :761`、`_clip_amount_by_volume :786`、`_calc_trade_info_by_order :859` | 子类 `Exchange` override 相关方法，传 `{"class":..,"module_path":..,"kwargs":..}` 为 `exchange_kwargs`（`backtest(...)` / `PortAnaRecord.backtest_config`） | `get_strategy_executor` 构造 Exchange 挂到 `executor.trade_exchange` |

**扩展共性**：qlib 扩展靠**继承 + 配置引用**（非装饰器/钩子/composition）。算子注册靠 `OpsWrapper`；processor/model/strategy/handler/exchange 靠 `init_instance_by_config` 从 config dict 解析 class path——**无中央注册表**（除算子）。`init_instance_by_config`(`qlib/utils/mod.py:122`) 是所有 config→instance 的统一漏斗。
