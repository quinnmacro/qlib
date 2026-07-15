# FORK_SURFACE.md —— qlib fork 改动面与操作坑清单

> 给"上下文被 clear 之后的我"看的 fork 改动面操作手册。不是介绍文。
> 规则：每条论断可追溯到 `路径:行号`；`[已自核]` = 本轮亲自开文件核对；`[已自核-上轮]` = 上一轮侦察自核、本轮未重开但同 session 无 rebase 故行号有效；`[未验证]` = 仍待核，不可当事实。
> 阅读顺序：本文件从最危险项排到最次要项。**第 1 条是 fork 改算子实现时最高危、且不报错**——先读它。

---

## 0. 方法论

每条 fork-surface 项给出四要素：

- **触发条件**：什么操作会踩到。
- **影响半径**：改了波及哪些路径/全部表达式/全部回测。
- **rebase 风险**：`git log --oneline -- <path> | head -20` 的近期改动密度与近一次改动（截至 2026-07-15，main = d5379c52）。commit 总数越低、近一次越久远 → rebase 痛苦越低。
- **能否绕过及代价**：不改源能否达成；改源的代价是什么。

### 0.1 rebase 风险总表（本轮 `git log --oneline -- <path> | head -20` 实测）

| 路径 | 总 commit | 近一次改动 | 判定 |
|---|---|---|---|
| `qlib/utils/__init__.py` | 101 | `a0cef033`(#1868 python 版本) / parse_field 自身最近 `3c4f4bfd`(#1012 中文标点) | 高频但 parse_field 本体**稳定**（最近真改动在 2022 前后） |
| `qlib/backtest/exchange.py` | 66 | `1b426503`(#1966 parquet) / `be4646b4`(#1594 rolling api) | **中高**，活跃区 |
| `qlib/contrib/evaluate.py` | 34 | `c38e799c`(#1938 加 mode=product) / `3097dcc9`(#2153 安全) | **中**，且 `c38e799c` 正是加 product 模式的提交——口径仍在动 |
| `qlib/workflow/record_temp.py` | 89 | `3097dcc9`(#2153) / `2fb9380b`(#2127) / `05d67b38`(#1546 multi-pass) | **高**，活跃 |
| `qlib/contrib/evaluate_portfolio.py` | 4 | `144e1e24`(#888 pylint) / `99ebd87c`(init) | **极低**——legacy 冻结，rebase 几乎无痛 |
| `qlib/data/storage/file_storage.py` | 19 | `7ccf3f76`(#2195，**main 最新提交之一**) | **中高**，近期仍动 |
| `qlib/data/data.py` | 89 | `37b90879`(#1809 typo) / `2ae4be42`(#1732) | **中** |
| `qlib/data/cache.py` | 32 | `39634b21`(#2099 安全 pickle) / `fbba7680`(#1917) | **中**，近期以安全为主 |
| `qlib/data/base.py` | 15 | `b51e881b`(docs) / `9dd5e078`(#1000 PRef) | **低**，稳定 |
| `qlib/data/ops.py` | 49 | `5b73b802`(docs) / `4001a5d1`(#1228 Rank/WMA fix) | **中** |
| `qlib/data/dataset/handler.py` | 72 | `de86e46e`(#1958 **BaseDataHandler 重构**) / `38f02d25`(#1960) | **高**，正在重构 |
| `qlib/model/trainer.py` | 59 | `de86e46e`(#1958 重构) / `3a348aec`(#1811 typo) | **中高**，跟随 handler 重构 |

**结论**：`evaluate_portfolio.py`(4) 与 `base.py`(15) rebase 几乎无痛；`handler.py`/`record_temp.py`/`exchange.py`/`file_storage.py` 是 patch 冲突高发区，fork 改动尽量**子类化/配置化**而非 inline patch。

---

## 1. 缓存静默 stale（改算子实现而 `__str__` 不变 = 跑旧 bin）—— **最高危，不报错**

> 这是 fork 场景下最危险的坑。它不抛异常、不警告，只静默返回旧数据，让你对新算子实现产生错误信心。

### 1.1 机制（全 `[已自核]`）

**(a) 内存缓存键** —— `qlib/data/base.py:187`：
```python
cache_key = str(self), instrument, start_index, end_index, *args
```
`base.py:188-189` 命中 `H["f"]` 直接返；`:193` miss 才调 `self._load_internal(...)`；`:202` 写回。**key 中唯一表达式身份信号是 `str(self)`**；`*args` 带 `freq`（基础引擎）或 `(cur_pit, period)`（PIT）。key **不含算子 class 身份、不含实现 hash、不含 qlib/算子版本**。

**(b) 磁盘缓存键** —— `qlib/data/cache.py:502-505` `DiskExpressionCache._uri`：
```python
def _uri(self, instrument, field, start_time, end_time, freq):
    field = remove_fields_space(field)
    instrument = str(instrument).lower()
    return hash_args(instrument, field, freq)
```
`hash_args` = `md5(json.dumps((instrument, field, freq), sort_keys=True, default=str))`（`qlib/utils/__init__.py:271-274` [未验证-上轮，子 agent 核中]）。**磁盘 key = `hash_args(instrument, field, freq)`**。`start_time`/`end_time` **在签名里但函数体丢弃**——全量 series 缓存一次，读时切片。

**(c) 磁盘读分支** —— `qlib/data/cache.py:518-533`：
```python
if self.check_cache_exists(cache_path, suffix_list=[".meta"]):
    ...
    series = read_bin(cache_path, start_index, end_index)
    return series
```
`.meta` 存在 → 直接 `read_bin` 返旧 series，**`_load_internal` / `provider.expression` 根本不被调用**。新算子实现不执行。

**(d) meta 无版本字段** —— `qlib/data/cache.py:570-573` `gen_expression_cache`：
```python
meta = {
    "info": {"instrument": instrument, "field": field, "freq": freq, "last_update": last_update},
    "meta": {"last_visit": time.time(), "visits": 1},
}
```
**无 operator-version / code-hash / class-identity 字段可 bump。** `update`(`cache.py:586-644`) 经 `ExpressionD.get_expression_instance(field)`(`:625`) 重解析算子——**信任 field 串解析成同一算子语义，不检测实现漂移**。

**(e) `qlib.init` 只清内存不清磁盘** —— `qlib/__init__.py:54-56` `[已自核-上轮]`：
```python
clear_mem_cache = kwargs.pop("clear_mem_cache", True)
if clear_mem_cache:
    H.clear()
```
`H.clear()` 只清 `H["f"]/H["c"]/H["i"]` 内存；**不碰磁盘 `<provider_uri>/features_cache/`**。重跑 `qlib.init` 仍命中 stale 磁盘文件。

**(f) `str(self)` 跨实现变化稳定——这就是 bug 的根** —— 各 `__str__` 纯结构（类名 + 子表达式串 + 构造参数），**绝不编码 `_load_internal` 体**：`Expression.__str__`=`type(self).__name__`(`base.py:26-27`)、`Feature.__str__`=`"$"+name`(`base.py:250-251`)、`Rolling.__str__`=`"{}({},{})".format(type(self).__name__, self.feature, self.N)`(`ops.py:739-740`)。故编辑 `Mean._load_internal` 不改 `Mean.__str__`=`"Mean($close,5)"` → key byte-identical → 旧 bin 返。`__str__` 行号 `[未验证-上轮，子 agent 核中]`。

**(g) 仅复合表达式落磁盘；裸 Feature 不落磁盘** —— `qlib/data/cache.py:562-564`：
```python
else:
    # If the expression is a raw feature(such as $close, $open)
    return self.provider.expression(instrument, field, start_time, end_time, freq)
```
`$close` 等裸 Feature **不写磁盘缓存**（每次走 provider）。故 stale 坑**精确咬在改复合算子 `_load_internal`（如 `Mean`/`Std`/`Ref`/`Rank`）时**；改 `$close` 的 load 只命中内存（被 `qlib.init` 清）。

### 1.2 触发条件（全满足才 stale）

1. `qlib.init(expression_cache=<非None>)` 配置了磁盘表达式缓存；
2. `<provider_uri>/features_cache/<instrument>/<hash>` 存在且 `.meta` 有效（`C.features_cache_dir_name` 默认 `"features_cache"`，`qlib/config.py:177` `[已自核]`）；
3. DSL `field` 与 `(instrument, freq)` 不变——即只改了 `_load_internal` 体（fork 改算子实现的最常见情形）。

### 1.3 影响半径

- **内存** `H["f"]`(`base.py:187`)：单进程内直到 `qlib.init`/LRU 驱逐；`qlib.init` 清之（`__init__.py:56`）。
- **磁盘** `DiskExpressionCache`(`cache.py:505`)：**不被 `qlib.init` 清**，跨进程持久；改实现后任何命中 `.meta` 的 load 都返旧值。
- **dataset 缓存** 同病：`DiskDatasetCache._uri`(`cache.py:655-657`) key = `hash_args(norm_inst, norm_fields, freq, disk_cache, inst_processors)`，`fields` 是 DSL 串列表——改算子实现同样 stale。dataset 缓存有 per-call `disk_cache=0` bypass（`cache.py:402-406` 等 `[已核实-子agent]`），**表达式缓存无此等价物**。

### 1.4 rebase 风险

`qlib/data/cache.py`(32 commit，近 `39634b21`(#2099) 安全 pickle)、`qlib/data/base.py`(15 commit，近 `b51e881b` docs)——**低**。stale 机制是设计而非近改，fork 不需 patch 此二文件即可触发；只需在 fork 侧加"改算子后清缓存"的纪律/脚本。

### 1.5 能否绕过及代价

- **无 API flag** 强制重算：无 `recompute`/`disable_cache`/`refresh`/版本 bump（meta 无版本列，`cache.py:570-573` `[已自核]`）。
- **手动删磁盘**：删 `<provider_uri>/features_cache/`（整树）或具体 `<instrument>/<hash>` + `.meta`。`BaseProviderCache.clear_cache`(`cache.py:313-321` `[已核实-子agent]`) 删单条但未接 user-facing refresh 调用——须手动 `rm -rf` 或手动调。删后 `check_cache_exists` 返 False → `gen_expression_cache`(`cache.py:551,:566`) 用新实现重算。
- **整体禁用（旁路，非清除）** `[已自核]`：`qlib.init(expression_cache=None)` → `data.py:1320` 为 False → `DiskExpressionCache` **根本不实例化**（不是 `ExpressionCache.expression`(`cache.py:343-346`) 抛 `NotImplementedError` 回退 `provider.expression`——那是缓存实例已存在但 `_expression` 未实现时的回退路径，禁用时不触发）。原始 `LocalExpressionProvider` 直连，本次 session 不读不写磁盘、当场重算。**但 stale `.bin` 原样留存**：唯一删文件的代码 `clear_cache`(`cache.py:313-321`) 只在 `gen_expression_cache`(`cache.py:575`) 内调用，而后者只在缓存**已启用**的 miss 分支(`cache.py:538/551`)执行——禁用时整段不跑。故"跑一遍重算后再开缓存"**不安全**：再开即 `cache.py:518` 命中旧 `.meta` 静默复用。要恢复缓存须**先删 `features_cache/`**。
- **dataset bypass**：`disk_cache=0` 或 `qlib.init(dataset_cache=None)`；**表达式缓存无 `disk_cache=0` 等价物**。
- **`qlib.init()` 单独不够**：只清内存不清磁盘（`__init__.py:56` `[已自核-上轮]`）。
- **代价**：纪律成本——每次改复合算子 `_load_internal` 后必须手动清 `features_cache/`，否则新代码不执行且无任何告警。建议在 fork 的开发流程里加 pre-run hook 或 wrapper 强制清。

### 1.6 行动守则（红线）

> 改任何**复合算子** `_load_internal`（或 DSL 串不捕获的代码）后：
> 1. 手动删 `<provider_uri>/features_cache/`（用 dataset 缓存则还有 `<C.dataset_cache_dir_name>/`，默认见 `qlib/config.py`）——**唯一可靠清除**；
> 2. `qlib.init(expression_cache=None, dataset_cache=None)` 仅**旁路本次 session**（`data.py:1320` False → 不实例化 `DiskExpressionCache`），**不删** stale `.bin`；仅在删过 `features_cache/` 之后、或永不再开缓存时才安全，**不能代替删文件**；
> 3. **`qlib.init()` 单独不清磁盘**——不要以为重 init 就够了。
> 4. 裸 `$close` 改 load 不咬磁盘（只咬内存，`qlib.init` 清），但复合算子（`Mean`/`Std`/`Ref`/`Rank`/...）改实现必清。

---

## 2. parse_field —— 新词法语法必改核心

### 2.1 位置与机制（`[已自核-上轮]`）

`qlib/utils/__init__.py:277-302` `def parse_field(field):`——三条 `re.sub` 顺序遍历（`for pattern, new in [...]`，`:293`）：
1. `rf"\$\$([\w{chinese_punctuation_regex}]+)"` → `r'PFeature("\1")'`（`:295-297`，注释 `$$ must be before $`）
2. `rf"\$([\w{chinese_punctuation_regex}]+)"` → `r'Feature("\1")'`（`:298`）
3. `r"(\w+\s*)\("` → `r"Operators.\1("`（`:299`）

中文标点 regex `chinese_punctuation_regex = r"、：（）"`（`:292`）。非 str 先 `str(field)`（`:285-286`），返回重写后字符串（`:302`）。`:282-283` TODO：`$close@5min` 频率语法**未实现**。

eval 点：`qlib/data/data.py:397` `expression = eval(parse_field(field))`、`qlib/data/cache.py:543` `eval(parse_field(field))`——`[未验证-上轮，子 agent 核中]`。parse_field 不是 parser，是 regex 重写 + Python `eval`。

### 2.2 触发条件

- 需要**新词法**（新前缀如 `#field`、`$close@5min`、新分隔符）——**必须改此函数**，无插件钩子。
- 加**新算子名**——**不需改**（`custom_ops` 即可，见 §2.5）。

### 2.3 影响半径

所有表达式解析入口经此。改了影响全部 field 串解析；`eval` 作用域（`data.py:397`、`cache.py:543`）须同步——DSL 顶层新 callable 须注册算子或加进 eval 命名空间。

### 2.4 rebase 风险

`qlib/utils/__init__.py` 总 101 commit，但 parse_field 本体最近真改动在 `3c4f4bfd`(#1012 中文标点)/`e229b567`(#1003)——**parse_field 函数本身稳定**，近期 `__init__.py` 改动多为版本/redis/windows 等无关项。inline patch 此函数冲突概率**中低**。

### 2.5 能否绕过及代价

- 加新算子名——能绕过：`custom_ops`（`qlib/config.py:282-285` `[已核实-子agent]`）或 `qlib.init(custom_ops=[...])`，子类 `ExpressionOps` 并实现四方法 + override `__str__`，不改源。
- 加新词法——**不能绕过**，必须改 regex。fork 须 patch `qlib/utils/__init__.py:277-302`，并同步 `data.py:397`/`cache.py:543` 的 eval 作用域。
- **安全红线**：eval 字段串 = 可执行 Python，任意 Python 会在 field 字符串里执行（仅 `NameError`/`SyntaxError` 是 parse 错）。**外部/模型生成的字段串不许直接喂 `D.features`**。

---

## 3. T+1 引擎级缺钩子

> `[已核实-子agent]` 本轮架构子 agent 已读 `qlib/backtest/exchange.py` 逐行核实。grep `t+1|t1|today|bought|holding|day_count|settle` 仅两条无关 log(`exchange.py:152,254`)。

### 3.1 位置（`[已核实-子agent]`）

`qlib/backtest/exchange.py`：
- `check_order(order)`(`:417-419`) → `is_stock_tradable(stock_id,start,end,direction)`(`:404-414`) = `not(check_stock_suspended(...) or check_stock_limit(...))`(`:412-414`)——仅查停牌+涨跌停，无时序持仓约束。
- `deal_order`(`:421-463`) 与 `_calc_trade_info_by_order`(`:859-952`) 无 T+1 钩子。
- SELL 分支(`:894-917`) 持仓 clip `:899-909`（`order.deal_amount` clip 到 `position` 当前总持仓），不区分当日买入 vs 之前——当日买入可立即在 `deal_order` 内全卖。

### 3.2 触发条件

要 A 股 T+1 **引擎级强制**（而非策略层 `hold_thresh` 近似）。

### 3.3 影响半径

改 `deal_order`/`_calc_trade_info_by_order`/`check_order` 影响全部策略回测撮合。Exchange **不维护 per-share acquisition-time ledger**——子类 override 须自建此状态。

### 3.4 rebase 风险

`qlib/backtest/exchange.py` 总 66 commit，近 `1b426503`(#1966 parquet)/`be4646b4`(#1594 rolling api)——**中高**活跃区，inline patch 冲突概率高。fork 尽量**子类化 override** 而非改源。

### 3.5 能否绕过及代价

- 策略层 `hold_thresh` 近似（`qlib/contrib/strategy/signal_strategy.py:75` `TopkDropoutStrategy`，`hold_thresh=1` `:81`/`:134`，卖闸 `:242-244` `[已核实-子agent]`）——代价：只对用该策略的路径生效；RL/WeightStrategy/rule_strategy 路径无 T+1。
- 引擎级强制——**fork-required / 越界**：须子类 override `deal_order`/`_calc_trade_info_by_order`/`check_order` 注入持仓年龄逻辑（需 per-share acquisition-time ledger，Exchange 不维护），或改源/在 Account 层包。

---

## 4. 三套年化口径（238 / 252 / 250）

> `[已核实-子agent]` 本轮回测子 agent 已逐行核实 `record_temp.py`/`evaluate_portfolio.py`/`evaluate.py`。`evaluate.py` 主 agent 上轮 `[已自核]`。

### 4.1 位置
- `qlib/contrib/evaluate.py:52` `[已自核]` —— 日频年化常量 **238**（`cal_risk_analysis_scaler`，`:48-56`，dict `:50-55`）。docstring `:39` 写 "day: 252" 与实现 `:52` `238` **打架**——以 238 为准。
- `qlib/workflow/record_temp.py:304` `[已核实-子agent]` —— `SigAnaRecord.__init__(... ann_scaler=252 ...)` 默认 **252**。
- `qlib/contrib/evaluate_portfolio.py:138,154,173` `[已核实-子agent]` —— 全用 **250**。

### 4.2 触发条件

任何回测收益数字进结论/报告。

### 4.3 影响半径

跨三个模块；改一处不动他处 → 同一报告里数字口径不一。**不报错，只让数字错配**。另：`ICIR = ic.mean()/ic.std()` 无 √N(`record_temp.py:326` `[已核实-子agent]`) vs `information_ratio = mean/std*sqrt(N)` 有 √N(`evaluate.py:84` `[已自核]`)——同名不同口径，放同一页是事故。

### 4.4 rebase 风险

- `evaluate.py`(34 commit，近 `c38e799c`(#1938) **正是加 mode=product 的提交**)——口径仍在动，inline patch 须盯上游。
- `record_temp.py`(89 commit)——高活跃。
- `evaluate_portfolio.py`(4 commit，legacy 冻结)——**极低**，改它无痛但它是并行遗留集，建议**不动**。

### 4.5 能否绕过及代价

- **文档记录差异，不改 upstream**（红线：不在 `evaluate.py` 顺手把 238 改 252——会与上游 `c38e799c` 口径演进冲突）。
- 代价：须在 `BACKTEST_SPEC.md` 裁决表 + `CLAUDE.md` 红线写死"回测数字必须标是哪个函数算的、用哪个常量"。
- 详见 `BACKTEST_SPEC.md` 口径裁决表。

---

## 5. bin dtype 硬编码 float32 + 强制 cast

> 写侧 `[已核实-子agent]`（dump_bin + file_storage）；读侧 cast `[已核实-子agent]`（FIXME 注释 `data.py:868-870`，实际 cast `series.astype(np.float32)` 在 `:872`，try/except 吞 `ValueError`/`TypeError`）。

### 5.1 位置

- `qlib/data/storage/file_storage.py` `[已核实-子agent]`：`FileFeatureStorage.__getitem__`(`:346-375`) 经 `:372` `np.frombuffer` 读裸 `<f` float32 字节返 `pd.Series`；`FileFeatureStorage.write`(`:299-329`) 写裸值。**读侧硬编码 float32，无 dtype 配置。**
- `scripts/dump_bin.py:269` `[已自核]` `np.hstack([date_index, _df[field]]).astype("<f").tofile(...)`——dump 侧 float32。
- `qlib/data/data.py:868-870` FIXME（实际 cast `series.astype(np.float32)` 在 `:872`，try/except 吞 `ValueError`/`TypeError`）`[已核实-子agent]`——`LocalExpressionProvider.expression` 读侧强 cast float32。`expression` 本体定义在 `:843` `[已核实-子agent]`。

### 5.2 触发条件

需要非 float 特征（int categorical、离散编码等）。

### 5.3 影响半径

改 bin dtype 须**同时**改 `FileFeatureStorage` 读写与 `LocalExpressionProvider` cast 与 `dump_bin.py` cast——**只改一处不够**（`data.py:868-870` FIXME 承认，实际 cast 在 `:872` `[已核实-子agent]`）。

### 5.4 rebase 风险

`file_storage.py`(19 commit，近 `7ccf3f76`(#2195) **main 最新提交之一**)——**中高**，近期仍动。`data.py`(89 commit)——中。`dump_bin.py`——待查。

### 5.5 能否绕过及代价

- dump_bin 已无 schema（全列 dump），但**读侧强 cast float32**——非 float 数据须 fork 两处（`file_storage.py` + `data.py`），外加 dump 侧。
- 代价：dtype 在写侧（file_storage/dump_bin）与读侧（data.py cast）双重硬编码，无单一配置开关。

---

## 附录：非"必动核心"但需记的操作坑

- **`min_cost` 对称/全局**：`exchange.py` 单标量同施买卖(`:912,925,929,948` `[已核实-子agent]`)，无 open/close min_cost。
- **`deal_price` 静默回退 `$close`** `[已核实-子agent]`：`exchange.py:510-513`，触发条件 `deal_price is None or np.isnan(deal_price) or deal_price <= 1e-08`（比"NaN"宽——含 `None` 与近零）→ warn 后回退 `get_close`(`$close`)——可掩盖缺数据。
- **`trade_w_adj_price` 在 `$factor` NaN 时静默变** `[已核实-子agent]`：`exchange.py:222-232`，是**布尔实例属性**（非方法，`:225`/`:232` 赋值）；`$factor` 含 NaN 而 `$close` 非空 → True，整手 rounding 静默禁用。
- **`return_rate` gross of cost vs `earning` net** `[已核实-子agent]`：rtn/earning docstring `account.py:18-31`（rtn 不含成本；`earning = rtn - cost`）；`return_rate=(now_earning+now_cost)/last_account_value`(`account.py:283`，gross of cost 加回成本)——读回报数字须分清 rtn/earning/return_rate。
- **`generate_order_for_target_amount_position`** `random.seed(0)` 硬编码 `[已核实-子agent]`(`exchange.py:638-639`)。
