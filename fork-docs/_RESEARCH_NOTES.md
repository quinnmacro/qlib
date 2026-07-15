# qlib 侦察笔记（阶段 0 + 0.5）

> 本文件是给"上下文被 clear 之后的我"看的操作底稿，不是给人看的介绍文。
> 规则：不压缩、不提炼、不省略。每条保留完整 `路径:行号`，逐字保留已核实的公式/默认值/常量。
> 重建时按本文件锚定，不要凭记忆。
>
> > ⚠️ **状态（2026-07-15 更新）：本文件已被 `docs/` 下四份正式文档（FORK_SURFACE.md / ARCHITECTURE.md / DATA_SPEC.md / BACKTEST_SPEC.md）取代。本文件仅作侦察过程留档。事实以四份文档为准，两者冲突时一律以文档为准。**
> > 本文件中带 `[已推翻 → 见 docs/XXX.md]` 的条目是已被四份文档推翻的结论，勿当事实；推翻原因见每条标注及 §11。

---

## 0. 本文件用途与可信度标记说明

每条论断前缀三类标记之一，**比内容本身更重要**：

- **[已自核]** = 我（主 agent）在阶段 0/0.5 亲自用 Read 打开过该 `文件:行号` 范围，亲眼核对过函数名/签名/常量/公式。clear 之后可直接信任，但行号可能因 rebase 漂移——以函数名为准回定位。
- **[未核实]** = 由我派出的只读子 agent（Explore 类型）打开并报告，主 agent 未亲自复核。子 agent 报告了具体 `文件:行号` 且自述已读，但主 agent 未二次开文件。**重建时应抽 1-2 条抽样复核**后再大面积采信。
- **[存疑]** = 源码与 docstring 打架，或多个来源口径冲突。已尽量标出冲突双方。

我（主 agent）阶段 0/0.5 **亲自开文件核对过**的 6 处（这些是 [已自核] 的核心锚点，优先级最高）：

1. `qlib/utils/__init__.py:277-302` —— `parse_field` 三条 regex。
2. `qlib/contrib/evaluate.py:26-93` —— `risk_analysis` 全函数体（含 238/252 docstring 冲突）。
3. `qlib/data/dataset/handler.py:505-564` —— `DataHandlerLP.fit` / `_run_proc_l` / `process_data`。
4. `qlib/data/base.py:182-203` —— `Expression.load` 的 `cache_key`。
5. `qlib/data/cache.py:498-509` —— `DiskExpressionCache._uri` / `_expression`。
6. `qlib/__init__.py:52-61` —— `init()` 的 `clear_mem_cache` / `H.clear()`。

其余为子 agent 报告（[未核实]），但子 agent 逐条给了 `文件:行号`，重建时可按行号快速复核。

---

## 1. 数据层与存储格式（dump_bin 契约、bin 布局、calendar/instruments、$ 前缀、复权）

来源：`scripts/dump_bin.py` 子 agent 报告。**整体标记 [未核实]**（主 agent 未开 dump_bin.py），但行号由子 agent 给出且自述已读，DATA_SPEC.md 落笔前必须抽样复核。

### 1.1 scripts/get_data.py 不是 CSV→bin 转换器
- [未核实] `scripts/get_data.py:8` 是 `fire.Fire(GetData)` 薄壳，包 `qlib.tests.data.GetData`。
- [未核实] `qlib/tests/data.py:18` `GetData` 仅从远端 release URL **下载预构建 zip 数据集**并解压（`data.py:44` download / `:72` download_data / `:120` unzip / `:153` qlib_data）。**不是** CSV→bin 转换器。所以 `scripts/dump_bin.py` 是 bin 产出的**唯一事实来源**。

### 1.2 输入 CSV 契约
- [未核实] `dump_bin.py:20-50` `read_as_df`；`pd.read_csv` 在 `:46`（CSV 分支）/ `:48`（parquet）。
- [未核实] `dump_bin.py:169-174` `_get_source_data`，传 `low_memory=False`。
- [未核实] `dump_bin.py:118` 文件发现：`glob *{file_suffix}` over `data_path`。
- [未核实] `dump_bin.py:76` 默认 `file_suffix=".csv"`。
- [未核实] `DumpDataBase.__init__` 在 `dump_bin.py:68-108`。
- [未核实] `dump_bin.py:75` `date_field_name` 默认 `"date"`——**必须存在**，`:172` coerce 成 datetime。
- [未核实] `dump_bin.py:77` `symbol_field_name` 默认 `"symbol"`。**关键坑**：`DumpDataAll` 的 symbol 取自**文件名**（`dump_bin.py:281` `get_symbol_from_file`），**不是 CSV 列**。`symbol` 列只有 `DumpDataUpdate._load_all_source_data`（`dump_bin.py:467-475`）用，缺失时从文件名合成（`:474`）。
- [未核实] `dump_bin.py:179-184` `get_dump_fields`：if `include_fields` → 用之；elif `exclude_fields` → 全列减 exclude；else → **全列**。**无固定 OHLCV schema**——CSV 有什么数值列就 dump 什么列。
- [未核实] 日期格式：读时 `pd.to_datetime`（`dump_bin.py:172`）灵活解析；输出 calendar 格式 `dump_bin.py:60-61`：day=`%Y-%m-%d`，intraday=`%Y-%m-%d %H:%M:%S`，于 `:146` 应用。
- [已核实-子agent] symbol 格式：文件名 stem → `fname_to_code`（`dump_bin.py:177`，`qlib/utils/__init__.py:925-936`）[已推翻 → 见 fork-docs/DATA_SPEC.md §1.7] ~~仅剥 `_qlib_` 前缀~~。**正确**：`str.lstrip(prefix)` 剥的是**字符集**（`_`,`q`,`l`,`i`,`b`）非字面前缀串；正常 symbol 行为等同剥前缀，边界 symbol（以这些字符开头）会多剥。**错因**：子 agent 把 `lstrip(prefix)` 行为描述为"剥前缀串"（未核 str.lstrip 语义）。instruments 文件将其大写（`dump_bin.py:221`）。
- [未核实] 输入排序不要求：`dump_bin.py:290` `drop_duplicates`，对齐靠 `:227-239` reindex。

### 1.3 calendar 生成 `calendars/<freq>.txt`
- [未核实] `dump_bin.py:306-326` `DumpDataAll._get_all_date`：`all_datetime = set union`（`:316`），逐文件收集 `:317-322`。
- [未核实] `dump_bin.py:328-332` `_dump_calendars`：`sorted(map(pd.Timestamp, ...))`（`:330`）。
- [未核实] `dump_bin.py:208-212` `save_calendars`：路径 `calendars/{freq}.txt`（`:210`），`np.savetxt(..., fmt="%s")`（`:212`），每行一个日期。
- [未核实] 更新路径 `DumpDataUpdate`：`dump_bin.py:458-460` 扩展 >旧末的日期，`:534` 重存全部。
- **重要**：calendar 是 **CSV 日期的 union**，**不与外部交易日历合并**。CSV 缺的上市日不会进 calendar；CSV 里的假期会留在 calendar。

### 1.4 instruments 生成 `instruments/<market>.txt`
- [未核实] `dump_bin.py:161-163` `_get_date(..., is_begin_end=True)` 返 `(df[date].min(), df[date].max())`。
- [未核实] **文件名恒为 `all.txt`**（常量 `INSTRUMENTS_FILE_NAME="all.txt"`，`dump_bin.py:63`），**不是 `<market>.txt`**——dump 时不分 market。
- [未核实] `dump_bin.py:214-225` `save_instruments`：TSV（`INSTRUMENTS_SEP="\t"`，`:62`），三列 `symbol\tstart_datetime\tend_datetime`，**无表头**（`:223`）。symbol 经 `fname_to_code(...).upper()`（`:221`）。
- [未核实] `DumpDataFix._dump_instruments` `dump_bin.py:357-378` 合并新 symbol 进既有 `all.txt`；`DumpDataUpdate.dump` `:533-538` 重写。

### 1.5 bin 写入 `features/<symbol>/<field>.<freq>.bin`
- [未核实] **手写 numpy dump，不用 `FileFeatureStorage.write`**。`dump_bin.py:245-269` `_data_to_bin`。
- [未核实] ALL_MODE 写：`dump_bin.py:269` `np.hstack([date_index, _df[field]]).astype("<f").tofile(...)`。即**头 4 字节 = `date_index` cast 成 float32**，后接数值列 cast float32。
- [未核实] `dump_bin.py:258` `start_index = get_datetime_index(_df, calendar_list)`；定义 `dump_bin.py:241-243` `calendar_list.index(df.index.min())`。即 **start_index = 该 symbol 首日在整个 calendar 中的位置索引**（数据先 reindex 到 calendar 切片 `[min,max]`，`dump_bin.py:227-239`，再写）。
- [未核实] dtype `"<f"` = little-endian float32（`dump_bin.py:269`、`:266`）。
- [未核实] 路径布局：`features_dir = features/<code_to_fname(code).lower()>`（`dump_bin.py:293`），文件 `{field.lower()}.{freq}.bin`（`:260`）。
- [未核实] UPDATE_MODE 写（append）：`"ab"` 打开，**只 append 数值不写头**（`dump_bin.py:263-266`），依赖既有 header。
- **坑**：`_df[field]` 无条件 cast float32（`:269`）；非数值/NaN 多的列静默成 NaN float。`data_merge_calendar` reindex 到 `[min,max]` 切片，bin 只跨 `[min,max]`。

### 1.6 `$` 前缀在哪一层
- [已自核] `$` 是**读取层 / 表达式引擎**约定，**不在 dump 层**。
- [未核实] dump 时文件名**无 `$`**：`dump_bin.py:260` `f"{field.lower()}.{self.freq}{DUMP_FILE_SUFFIX}"` → `close.day.bin`、`volume.day.bin`。
- [已自核] `qlib/data/base.py:250-251` `Feature.__str__` 返 `"$" + self._name`；`:267-268` `PFeature.__str__` 返 `"$$" + self._name`。`$close` 在 load 时解析成 bin 文件里名为 `close` 的字段。

### 1.7 复权（adjustment / adjfactor）
- [已核实-子agent] **`dump_bin.py` 从不应用前/后复权，从不引用 `adjfactor`/`factor` 列**（grep `adj|factor|adjust|forward|backward` 0 命中）。CSV 有什么数值列就原样写。
- [已核实-子agent] 结论：raw price 被 dump；复权是**数据源 / collector 的责任**（collector 产出 CSV 时归一价格 + 写 `factor` 列，见官方 `docs/component/data.rst:55-56,195`）。
- [已推翻 → 见 fork-docs/DATA_SPEC.md §7] ~~qlib 自身在 storage/expression 层用 `$factor` 字段做事后复权，不在 dump_bin~~。**正确**：`file_storage.py`/`data.py`/`dump_bin.py` grep `adj|factor|adjust` 全 0 命中——qlib 读层**从不自动施加复权**；`$factor` 是表达式语言字段引用（裸读名为 `factor` 的 bin 列），用户显式写 `$close/$factor` 取原始价。**错因**：子 agent 推断（无行号）被当成可能成立的结论写入 + 上轮未 grep 核实 storage/expression 层。错因分类：**推断当事实**。
- [已推翻 → 见 fork-docs/DATA_SPEC.md §7] ~~[存疑] qlib 在 load 时用 `$factor` 复权~~：同上，已证伪（非存疑，是错）。

### 1.8 freq 与变体
- [已核实-子agent] `dump_bin.py:73` `freq: str = "day"` 默认；`DumpDataUpdate.__init__` 重声明在 **`:398`** [已推翻 → 见 fork-docs/DATA_SPEC.md §1.2] ~~`:399`~~（错因：子 agent 行号 off-by-one，未开文件亲核）。
- [未核实] CLI 入口 `dump_bin.py:541-542`：`dump_all`→`DumpDataAll`(`:305`)；`dump_fix`→`DumpDataFix`(`:356`)；`dump_update`→`DumpDataUpdate`(`:392`)。
- [未核实] **无 `dump_baostock`**。baostock/yahoo 是独立 **collector**（下载器，产出 CSV，不是 bin dumper）：`scripts/data_collector/baostock_5min/collector.py:273`、`scripts/data_collector/yahoo/collector.py:755`。

### 1.9 自定义数据源会踩的坑（子 agent 判断）
- `DumpDataAll` 的 symbol 取自**文件名**（`dump_bin.py:281`），单个合并 CSV（所有 symbol、无分文件）不能走 `dump_all`；改用 `dump_update`（读 `symbol` 列，`:474`）或按 symbol 拆文件。
- 全列强 cast float32（`:269`），string/category 列成 NaN——用 `--exclude_fields` 排除。
- symbol 文件名须能经 `fname_to_code`/`code_to_fname`（`qlib/utils/__init__.py:905-936`）往返；Windows 保留名（CON/PRN/AUX/NUL/COMn/LPTn）写时加 `_qlib_` 前缀、读时剥。
- calendar 仅是 CSV 日期 union（`:316`/`:330`），无外部交易日历合并。
- `start_index`（头 4 字节）= symbol 首日 calendar 位置（`:243`/`:269`）；dump 与 load 间 calendar 不一致会让每个值错位。

---

## 2. 表达式引擎与算子（parse_field/eval、OpsWrapper、custom_ops 注册、四方法要求）

来源：表达式引擎子 agent + 我对 `parse_field` 的自核。`parse_field` 部分整体 [已自核]；OpsWrapper/custom_ops/OpsList 部分 [未核实]（子 agent 报告）。

### 2.1 parse_field —— 是 regex + eval，不是真 parser
- [已自核] `qlib/utils/__init__.py:277-302` `def parse_field(field):`。三条 `re.sub` 顺序遍历（`for pattern, new in [...]`，`:293`）：
  1. `rf"\$\$([\w{chinese_punctuation_regex}]+)"` → `r'PFeature("\1")'`（`:295-297`，注释 `$$ must be before $`）
  2. `rf"\$([\w{chinese_punctuation_regex}]+)"` → `r'Feature("\1")'`（`:298`）
  3. `r"(\w+\s*)\("` → `r"Operators.\1("`（`:299`）
- [已自核] 中文标点 regex `chinese_punctuation_regex = r"、：（）"`（`：292`，分别 、：（））。
- [已自核] 非 str 先 `str(field)`（`:285-286`），返回**重写后的字符串**（`:302` `return field`）。
- [已自核] `:282-283` TODO 注释：`$close@5min` 频率语法**未实现**。
- [未核实] eval 点：`qlib/data/data.py:397` `expression = eval(parse_field(field))`，缓存在 `self.expression_instance_cache`（`:390`/`:398`），`NameError`/`SyntaxError` 捕获重抛带 field 上下文（`:399-406`）。
- [未核实] 另一 eval 点 `qlib/data/cache.py:543` `eval(parse_field(field))`——判断 field 是裸 `Feature` 还是复合表达式（缓存决策用）。
- **结论**：`"Ref($close,1)/Mean($close,5)"` → 字符串 `"Operators.Ref(Feature("close"),1)/Operators.Mean(Feature("close"),5)"` → eval 成 Expression 树。`Operators.Ref`/`Operators.Mean` 经 `OpsWrapper.__getattr__` 解析，`Feature`/`PFeature` 经 eval 全局命名解析。
- **安全/正确性坑**：字段串 = 可执行 Python，任意 Python 会在 field 字符串里执行（仅 `NameError`/`SyntaxError` 是 parse 错）。

### 2.2 算子注册机制（无装饰器）
- [未核实] `qlib/data/ops.py:1619` `class OpsWrapper:`，持 `_ops: dict`（`:1623`）。
- [未核实] `qlib/data/ops.py:1628` `def register(self, ops_list)`：接受**算子类**或 **dict 配置** `{class, module_path}`（经 `get_callable_kwargs`，`:1648`）。key = `__name__`（`:1659`）。重注册只 warn 并覆盖（`:1655-1658`）。
- [未核实] `qlib/data/ops.py:1661` `def __getattr__(self, key):` 查 `_ops[key]`，缺则 `AttributeError("The operator [{0}] is not registered")`。这就是 `Operators.Mean(...)` 在 DSL 里能解析的原因。
- [未核实] `qlib/data/ops.py:1667` `Operators = OpsWrapper()`——模块级单例。
- [未核实] `qlib/data/ops.py:1566` `OpsList = [...]`——硬编码内置算子类列表（约 50 项，`:1566-1616`）+ `[TResample]`。
- [未核实] `qlib/data/ops.py:1670` `def register_all_ops(C):` reset 后注册 `OpsList + [P, PRef]`（`:1677`），再 append `C.custom_ops`（`:1679-1681`）。
- [未核实] `qlib/config.py:490` `register_all_ops(self)` 在 `Config.register()` 内调用。
- [未核实] `qlib/config.py:282-285` `custom_ops: []` 配置字段——**公开扩展钩子**。
- [未核实] 全仓库**无 `@register` 装饰器**（grep 确认）。

### 2.3 算子类别（均子类 `ExpressionOps`，行号为子 agent 报告）
- [未核实] Element-Wise：banner `:36`，`ElemOperator`(`:37`)，含 `ChangeInstrument`(`:64`)、`NpElemOperator`(`:97`)、`Abs`(`:122`)、`Log`(`:167`)、`Mask`(`:185`)、`Not`(`:212`)、`TResample`(`:1528`)。
- [未核实] Pair-Wise：banner `:230`，`PairOperator`(`:231`)，含 `Add/Sub/Mul/Div`(`:358-418`)、`Greater/Less/Gt/Ge/Lt/Le/Eq/Ne/And/Or`(`:438-618`)、`Power`(`:338`)。
- [未核实] Triple-wise：`If`(`:639`)。
- [未核实] Rolling：`:713`，含 `Ref`(`:781`)、`Mean`(`:827`)、`Sum`(`:847`)、`Std`(`:867`)、`Var`(`:887`)、`Skew`(`:907`)、`Kurt`(`:929`)、`Max`(`:951`)、`IdxMax`(`:971`)、`Min`(`:999`)、`IdxMin`(`:1019`)、`Quantile`(`:1047`)、`Med`(`:1079`)、`Mad`(`:1099`)、`Rank`(`:1133`)、`Count`(`:1171`)、`Delta`(`:1191`)、`Slope`(`:1221`)、`Rsquare`(`:1257`)、`Resi`(`:1286`)、`WMA`(`:1314`)、`EMA`(`:1349`)。
- [未核实] PairRolling：`:1387`，含 `Corr`(`:1467`)、`Cov`(`:1501`)。
- [未核实] `ExpressionOps` 在 `qlib/data/base.py:276`——空 marker 子类，注册目标类型。

### 2.4 base.py 的 Expression/Feature/PFeature
- [已自核] `qlib/data/base.py:182-203` `Expression.load`（见 §3）。
- [未核实] `qlib/data/base.py:13` `class Expression(abc.ABC)`。
- [未核实] `qlib/data/base.py:26-30` `__str__` 返 `type(self).__name__`，`__repr__` 委托 `__str__`。**这是 DSL 往返的关键**：每个算子须**override `__str__`** 才能重建 DSL 形态（默认只返类名，丢参数）。
- [未核实] `qlib/data/base.py:32-140` Python dunder 重载（`__gt__`/`__add__`/`__mul__`/`__truediv__`/`__pow__`/`__and__`/`__or__`），各惰性 import 构造对应 ops 类（如 `__add__`→`Add`，`:62-65`）。可写 `Feature("close")+Feature("open")` 直接得 `Add` 节点——绕过 DSL 的另一条建树路径。
- [已自核] `qlib/data/base.py:201` `series.name = str(self)`。
- [未核实] `qlib/data/base.py:205-207` `@abc.abstractmethod _load_internal`。
- [未核实] `qlib/data/base.py:209-220` `get_longest_back_rolling` abstract。
- [未核实] `qlib/data/base.py:222-235` `get_extended_window_size` abstract，返 `(lft_etd, rght_etd)`。
- [未核实] `qlib/data/base.py:238` `class Feature(Expression)`——"静态表达式"，从 provider load。`__init__(name)`(`:244`)；`_load_internal` 委托 `FeatureD.feature(...)`(`:253-257`)；窗口 `(0,0)`(`:262-263`)。
- [未核实] `qlib/data/base.py:266` `class PFeature(Feature)`——PIT 静态特征，`$$_name`(`:267-268`)，`_load_internal` 委托 `PITD.period_feature(...)` 带 `cur_time` 和可选 `period`(`:270-273`)。

### 2.5 加自定义算子的两种机制（均为 [未核实]，行号来自子 agent）
1. **class list in config**（文档化钩子）：子类 `ElemOperator`/`PairOperator`/`Rolling`/`PairRolling` 或直接 `ExpressionOps`（`qlib/data/base.py:276`）；实现 `_load_internal`、`get_longest_back_rolling`、`get_extended_window_size`；override `__str__`；append 到 `qlib/config.py:285` `custom_ops` 或传 `qlib.init(custom_ops=[...])`。示例 `qlib/rl/data/integration.py:54`、`qlib/contrib/data/highfreq_provider.py:110`。
2. **dict config**（惰性 import）：传 `{"class":"DayLast","module_path":"qlib.rl.data.integration"}`，经 `get_callable_kwargs`(`ops.py:1648`) 解析。
- 注册后经 `register_all_ops`(`ops.py:1680`) `Operators.register(C.custom_ops)` → `OpsWrapper.__getattr__`(`:1661`) 解析为 `Operators.YourOp(...)`。

### 2.6 `$field` 命名空间
- [已自核] `$` → `Feature("name")`：regex `qlib/utils/__init__.py:298`。
- [已自核] `$$` → `PFeature("name")`：regex `qlib/utils/__init__.py:295`（须先于 `$`）。
- [未核实] `Feature.__str__`=`"$"+name`(`base.py:251`)、`PFeature.__str__`=`"$$"+name`(`base.py:268`)——往返路径 string→tree→string。
- [未核实] `$close@5min` 频率形态 TODO 未实现（`qlib/utils/__init__.py:282-283`）。

### 2.7 FORK-REQUIRED（继承解决不了，子 agent 判断）
- **新词法语法**：`parse_field`(`qlib/utils/__init__.py:277-302`) 三条 regex 硬编码。加新**算子名**不需动；加新**词法**（新前缀如 `#field`、`$close@5min`）必须改此函数，无插件钩子。
- **eval 作用域**：`qlib/data/data.py:397`、`qlib/data/cache.py:543`——eval 见那些模块 import 进来的名字；`Feature`/`PFeature`/`Operators` 能用是因为 `Operators` 已 import 且 `Feature`/`PFeature` 在 `OpsList`。DSL 顶层新 callable 须注册算子或加进 eval 命名空间。
- **`OpsList` 硬编码**（`ops.py:1566-1616`）：内置不可删，只能覆盖（warn，`:1656`）。
- **Cython 算子** `rolling_slope`/`rolling_rsquare`/`rolling_resi`/`expanding_*`(`ops.py:18-19`)——`Slope`/`Rsquare`/`Resi` 用；扩 C 内循环需重编 `qlib/data/_libs/`。

### 2.8 与直觉不符（子 agent 判断）
- 算子既是 Python 类又经字符串 DSL 可序列化，桥是 regex 重写后 `eval`。"parser"不是 parser。
- 往返是手动的：`Expression.__str__` 默认只返类名（`base.py:27`），每个算子须 override `__str__` 重建 DSL 参数列表（`Rolling.__str__` `ops.py:739`、`PairRolling.__str__` `:1412`）。**忘 override 的自定义算子**计算正确但 cache key（`base.py:187` `str(self)`）与 DSL 输出错/冲突。
- `Ref` 是 `Rolling` 子类（`ops.py:781`）但完全 override `_load_internal`（用 `series.shift`，`:808`），不调 `rolling`。`func="ref"` 传给 `super().__init__`（`:798`）运行时未用，仅为基类契约。
- **`N=0` 是 expanding 不是"无窗口"**：`Rolling._load_internal` `ops.py:747-748` `if self.N == 0: series.expanding(...)`；`0<N<1`（float）是 **EWM** alpha=N（`:749-750`）——`N` 参数的隐藏第二语义。`get_longest_back_rolling` 对 `N==0` 返 `np.inf`（`:758-759`）。
- `Feature`/`PFeature` 在 `OpsList`（`ops.py:1614-1615`）虽非算子——为让 `Operators.Feature`/`Operators.PFeature` 可解析（但 DSL 发的是裸 `Feature(...)`，经 eval 全局解析，不经 `OpsWrapper`）。
- PIT `P` 算子显式拒未来引用：`qlib/data/pit.py:34-36` `end_ws > 0` 时 raise。
- cache key 含 `*args`（`base.py:187`），不同 `freq` 的 `Feature("close")` 分别缓存。

### 2.9 PIT（point-in-time）
- [未核实] `qlib/data/pit.py`（72 行，子 agent 全读）。`P`(`:24`) 是 `ElemOperator` 子类，collapse 算子，把 period-time 数据 collapse 成 observe-time。`P._load_internal`(`:25`) 遍历 `[start_index,end_index]`（`:29`），从 `Cal.calendar(freq)` 取 `cur_time`（`:26,30`），算扩展窗口（`:32`），`end_ws>0` raise（`:33-36`），调 `self._load_feature(instrument,-start_ws,0,cur_time)`(`:40`) 取**最后元素**为 collapse 值（`:41`）。`get_extended_window_size` 返 `(0,0)`(`:58-60`)——P 自行在 `_load_internal` 内部处理窗口，绕过 provider 扩张。
- [未核实] `PRef(P)`(`:63`) 加固定 `period`；`__str__` 追加 `[{period}]`(`:68-69`)；override `_load_feature` 传 `self.period`（`:71-72`）。
- [未核实] `P`/`PRef` 在 `register_all_ops` `ops.py:1674,1677` 注册。

---

## 3. 缓存机制（内存键 / 磁盘键 / 失效条件）—— 最高危项

来源：缓存子 agent + 我对 base.py:187 / cache.py:505 / __init__.py:56 的自核。**这一节是 fork 场景下最危险的坑**，比 T+1 危险得多：它不报错，只静默返旧数据。

### 3.1 Expression.load 内存缓存键（[已自核]）
- [已自核] `qlib/data/base.py:187`：
  ```python
  cache_key = str(self), instrument, start_index, end_index, *args
  ```
  `:188-189` 查 `H["f"]`，命中直接返；`:193` miss 调 `self._load_internal(...)`；`:202` `H["f"][cache_key] = series`。
- [已自核] `str(self)` 是 key 中**唯一**的表达式身份信号。`*args` 带 `freq`（基础引擎）或 `(cur_pit, period)`（PIT）。
- [已自核] **key 不含算子 class 身份、不含算子实现 hash、不含 qlib/算子版本**。两个不同算子类若 `str(self)` 相同会冲突（实际不会，因 `__str__` 嵌 `type(self).__name__`，但 key 本身不记录 class）。
- [已自核] `series.name = str(self)`（`:201`）。
- [未核实] 此内存路径**不用** `MemCacheExpire`（无 TTL）。对比 `DatasetURICache.dataset`(`cache.py:1155`)、`MemoryCalendarCache.calendar`(`:1187`) 用 `MemCacheExpire`。Expression 内存条目不自过期，靠 LRU 驱逐或 `H.clear()`。

### 3.2 MemCache（H["f"]）——内存，进程本地
- [未核实] `qlib/data/cache.py:137` `class MemCache`；三子缓存 `"c"`/`"i"`/`"f"` 在 `:161-163`。
- [已自核] `H` 是模块级单例：`qlib/data/cache.py:1199` `H = MemCache()`。进程本地，不跨进程共享；跨进程用 **redis 锁**（`CacheUtils.reader_lock`/`writer_lock`，`cache.py:525,550,728,738,779,784,944,961`）串行访问，**不共享缓存内容**。
- [未核实] `MemCache.clear()` `cache.py:175-178` 清三个 unit。
- [已自核] `qlib/__init__.py:54-56`：`clear_mem_cache = kwargs.pop("clear_mem_cache", True)`；`if clear_mem_cache: H.clear()`——在 `qlib.init` 内。**每次 `qlib.init(...)` 清内存缓存**，除非传 `clear_mem_cache=False`。
- [未核实] LRU 驱逐在 `__setitem__` 当 `self.limited`（`cache.py:63-66`），界 `C.mem_cache_size_limit`（`cache.py:151`）。

### 3.3 DiskExpressionCache —— 磁盘表达式缓存
- [已自核] `qlib/data/cache.py:502-505` `_uri`：
  ```python
  def _uri(self, instrument, field, start_time, end_time, freq):
      field = remove_fields_space(field)
      instrument = str(instrument).lower()
      return hash_args(instrument, field, freq)
  ```
  **磁盘 key = `hash_args(instrument, field, freq)`**。`start_time`/`end_time` **被传入但忽略**（签名留它们，函数体丢弃）——**全量 series 缓存一次，读取时切片**。
- [未核实] `hash_args` = `md5(json.dumps((instrument, field, freq), sort_keys=True, default=str))`（`qlib/utils/__init__.py:271-274`）。
- [未核实] `_expression` `cache.py:507-564`：`_uri` 用 `start_time=None, end_time=None` 算（`:508`）；`read_bin(cache_path, start_index, end_index)` 切片（`:532`）。
- [未核实] 磁盘位置：`get_cache_dir` `cache.py:499-500` `super().get_cache_dir(C.features_cache_dir_name, freq)`；`BaseProviderCache.get_cache_dir` `cache.py:323-327` `Path(C.dpm.get_data_uri(freq)).joinpath(dir_name)`。即 `<provider_uri>/<C.features_cache_dir_name>/<instrument>/<md5(instrument,field,freq)>`。
- [未核实] `_expression` 路径组装：`cache.py:508-510` `_cache_uri = self._uri(...)` → `cache_path = self.get_cache_dir(freq).joinpath(instrument.lower()).joinpath(_cache_uri)`。
- [未核实] meta 文件 `gen_expression_cache` `cache.py:566-584`，meta dict（`:570-573`）：
  ```python
  meta = {
      "info": {"instrument":..., "field":..., "freq":..., "last_update":...},
      "meta": {"last_visit": time.time(), "visits": 1},
  }
  ```
  **无 operator-version / code-hash / class-identity 字段**。`update()`(`cache.py:586-644`) 经 `ExpressionD.get_expression_instance(field)`(`:625`) 重算并 append——**信任 field 串解析成同一算子语义，不检测实现漂移**。
- [未核实] 命中判定 `check_cache_exists` `cache.py:305-311`；`.meta` 存在分支 `:518`。
- [未核实] **无 `recompute`/`disable_cache`/`refresh` flag**。绕过磁盘表达式缓存的唯一方式是**不配置它**（`qlib.init(expression_cache=None)`），此时 `ExpressionCache.expression` 走 `NotImplementedError` 回退 `self.provider.expression(...)`（`cache.py:343-346`）。无 per-call "force recompute" 参数。
- [未核实] **dataset 缓存有运行期 bypass**（expression 缓存无）：`disk_cache=0` 跳过（`cache.py:402-406`、`:699-703`、`:1133-1144`）。

### 3.4 DatasetCache / DiskDatasetCache
- [未核实] `cache.py:655-657` `DiskDatasetCache._uri`（static）：
  ```python
  def _uri(instruments, fields, start_time, end_time, freq, disk_cache=1, inst_processors=[], **kwargs):
      return hash_args(*DatasetCache.normalize_uri_args(instruments, fields, freq), disk_cache, inst_processors)
  ```
  key = `hash_args(norm_instruments, norm_fields, freq, disk_cache, inst_processors)`。`fields` 是**表达式 DSL 串列表**。`start_time`/`end_time` **同样被忽略**（全量缓存，读时切片 `:747`，`read_data_from_cache` `:662-694`）。
- [未核实] `normalize_uri_args` `cache.py:481` 规范化/排序 instruments 与 fields。
- [未核实] 磁盘位置 `cache.py:659-660`、`cache_path = self.get_cache_dir(freq).joinpath(_cache_uri)`(`:720`)，dir 名 `C.dataset_cache_dir_name`，存储 HDF5（`pd.HDFStore`，`:685-694`），`.index` 由 `IndexManager`(`:794+`) 管。
- [未核实] staleness 与表达式缓存**相同**：改算子实现、同 DSL 串、同 fields → 同 `_cache_uri` → `check_cache_exists`(`:725`) 返旧 HDF5，`gen_flag` 保持 `False`(`:733`) → 返旧数据(`:730`)。
- [未核实] `DatasetURICache`（client 路径）`cache.py:1118`，`_uri` `:1121-1122` 同 `hash_args(normalize_uri_args(...), disk_cache, inst_processors)`。叠加 `MemCacheExpire` 于 `H["f"]`(`:1155-1157,1169`)，内存 URI 缓存可经 `C.mem_cache_expire`(`cache.py:182,206`) 过期；磁盘文件存在性 `mnt_feature_uri.exists()`(`:1156`)——但 `exists()` 只查文件在否，**不查内容/算子版本**，stale-but-present 仍满足。

### 3.5 失效裁定（THE STALENESS VERDICT）—— [已自核] 关键逻辑 + [未核实] 子 agent 细节

**(a) 注册新 `custom_ops` 算子（如 `MyOp`）**：
- [未核实] `str(self)` 嵌 `type(self).__name__`（见 §6）。新命名的 `MyOp` → 不同 DSL 串 `"MyOp($close,5)"` → 不同 `hash_args` key（内存 `base.py:187` + 磁盘 `cache.py:505`/`:657`）。**不与旧缓存冲突**。
- [未核实] 反向危险：若你把自定义算子**命名为内置同名**（如自己的 `Mean`）且之前缓存过内置输出，因 `type(self).__name__` 相同 → key 冲突。
- [未核实] 算 `$close`（裸 Feature）前后不受 MyOp 影响——`$close` key = `Feature.__str__`=`"$close"`(`base.py:250-251`)，与算子注册无关。

**(b) 改既有算子实现（如编辑 `Mean._load_internal`）—— [存疑/部分自核] 结论：静默返旧数据**：
- [已自核] 内存 key = `str(self),...`(`base.py:187`)，磁盘 key = `hash_args(inst,field,freq)`(`cache.py:505`)，均**只看 DSL 串**。
- [未核实] `Mean.__str__` 继承 `Rolling.__str__`(`ops.py:739-740`)，用 `type(self).__name__` + `self.N`——**不含实现**。编辑 `_load_internal` 不改 `__str__` → `field="Mean($close,5)"` byte-identical → 同 `hash_args` → 同 `_cache_uri` → 同 `cache_path`。
- [未核实] 下次 load：`check_cache_exists(cache_path, suffix_list=[".meta"])`(`cache.py:518`) 返 True（旧 `.bin`/`.meta` 仍在）→ 走**读分支**（`:518-537`）`series = read_bin(cache_path, start_index, end_index)`(`:532`) 返**旧 series**，新 `_load_internal` **根本不被调用**。`_expression`(`:507-564`)、`gen_expression_cache`(`:566-584`)、`update`(`:586-644`) 全程**无版本/hash 检查**。
- [已自核] 内存 `H["f"]` 同理（key 不变 → 旧 Series 返，`:189`），但内存**被 `qlib.init` 清**（`__init__.py:56`）；磁盘**不被 `qlib.init` 清**。
- [未核实] 精确失效条件（全满足才 stale）：① `DiskExpressionCache` 已配置（`qlib.init(expression_cache=<非None>)`）；② `<provider_uri>/<features_cache_dir_name>/<instrument>/<hash>` 存在且 `.meta` 有效；③ DSL `field` 与 `(instrument,freq)` 不变（只改 `_load_internal` 体的常见情形）。

**(c) 如何失效（必须手动）**：
- [未核实] **无 API flag** 强制重算。
- [未核实] 删磁盘缓存目录：删 `<provider_uri>/<C.features_cache_dir_name>/`（整树）或具体 `<instrument>/<hash>` + `.meta`。`BaseProviderCache.clear_cache`(`cache.py:313-321`) 删单条 `cache_path`/`.meta`/`.index`——**未接到任何 expression 的 user-facing refresh 调用**，须手动调或 `rm -rf`。删后 `check_cache_exists` 返 False（`:518` else `:538-564`）→ `gen_expression_cache`(`:551,:566`) 用新实现重算。
- [未核实] 整体禁用：`qlib.init(expression_cache=None)` → `ExpressionCache.expression`(`cache.py:343-346`) raise `NotImplementedError` 回退 `self.provider.expression(...)`，不读不写磁盘。
- [未核实] dataset 有 per-call `disk_cache=0`（`cache.py:402-406`、`:699-703`）或 `qlib.init(dataset_cache=None)`；**表达式缓存无 `disk_cache=0` 等价物**。
- [未核实] 无版本字段可 bump（meta 无 version 列，`cache.py:570-573`）。
- **[已自核] `qlib.init()` 单独不够**：`H.clear()`(`__init__.py:56`) 只清内存，不碰磁盘 `<provider_uri>/<features_cache_dir_name>/`。重跑 `qlib.init` 仍命中 stale 磁盘文件。

### 3.6 `str(self)` 是否跨实现变化稳定 —— [未核实] 结论：**稳定，这就是 bug**
- [未核实] 所有 `__str__` **纯结构**——编码类名 + 子表达式/参数的串形式，**绝不编码实现**：
  - `Expression.__str__`(`base.py:26-27`) `type(self).__name__`
  - `Feature.__str__`(`base.py:250-251`) `"$"+name`
  - `PFeature.__str__`(`base.py:267-268`) `"$$"+name`
  - `ElemOperator.__str__`(`ops.py:54-55`) `"{}({})".format(type(self).__name__, self.feature)`
  - `ChangeInstrument.__str__`(`ops.py:86-87`)
  - `Mask.__str__`(`ops.py:205-206`)
  - `PairOperator.__str__`(`ops.py:251-252`) 类名 + left + right
  - `Rolling.__str__`(`ops.py:739-740`) `"{}({},{})".format(type(self).__name__, self.feature, self.N)` —— `Mean`/`Std`/`Ref`/`Rank` 继承（`Mean` `ops.py:827`、`Ref` `:781`、`Std` `:867`、`Rank` `:1133`）
  - `Quantile.__str__`(`ops.py:1067-1068`)、`Corr.__str__`(`ops.py:1550`)
- [未核实] **结论**：编辑 `Mean._load_internal`（如 `ops.py:742-755` 的 `Rolling._load_internal`）不改 `Mean.__str__`=`"Mean($close,5)"` → `base.py:187` key 不变 → `cache.py:505` `_uri` 不变 → 旧 `.bin`/`.meta` 返。**这是真实的静默 stale fork 坑。**
- [未核实] `__str__` 可见信号仅：①算子 Python 类名；②子表达式递归 `str()`；③构造参数（N、qscore、instrument 等）。**无一反映 `_load_internal` 体。**

### 3.7 缓存对照表（子 agent 汇总）
| 缓存 | key (file:line) | key 含算子身份? | `qlib.init` 清? | 改实现 stale? |
|---|---|---|---|---|
| 内存 `H["f"]` | `str(self),inst,start,end,*args`(`base.py:187`) | 仅经类名在 str 里；无 impl/version | 是(`__init__.py:56`) | 单进程内直到 `qlib.init`/LRU——是 |
| DiskExpressionCache | `hash_args(inst,field,freq)`(`cache.py:502-505`) | 否，field 是 DSL 串 | 否（不碰磁盘） | **是——静默 stale** |
| DiskDatasetCache | `hash_args(norm_inst,norm_fields,freq,disk_cache,inst_processors)`(`cache.py:655-657`) | 否，fields 是 DSL 串 | 否 | **是——静默 stale** |
| DatasetURICache(client) | 同 `hash_args(...)`(`cache.py:1121-1122`) | 否 | 内存 URI 经 `MemCacheExpire`(`:1155`) 过期；磁盘只查存在不查内容 | **磁盘是**；内存自过期但重新解析到同一 stale 磁盘文件 |

### 3.8 fork/改算子实现时的行动
- [未核实] 改任何算子 `_load_internal`（或 DSL 串不捕获的代码）后：**手动删磁盘表达式缓存目录** `<provider_uri>/<C.features_cache_dir_name>/`（用 dataset 缓存则还有 `<C.dataset_cache_dir_name>/`），或 `qlib.init(expression_cache=None, dataset_cache=None)` 跑一遍重算。`qlib.init()` 单独**不**清磁盘。
- [未核实] 无版本 bump、无 recompute flag、无 code hash（已读 `hash_args`、`_uri`、`_uri`、meta schema 核实）。

---

## 4. Handler / Processor（DataHandlerLP.fit 泄漏责任、infer vs learn、data_loader 解耦）

来源：特征工程+模型子 agent + 我对 `handler.py:505-564` 的自核。

### 4.1 三层关系
- [未核实] DataHandler：`DataHandlerABC`(abstract)/`DataHandler`(impl)/`DataHandlerLP`(learnable) 在 `qlib/data/dataset/handler.py:25`/`:67`/`:382`。
- [未核实] DatasetH：`Dataset`/`DatasetH`/`TSDatasetH` 在 `qlib/data/dataset/__init__.py:15`/`:72`/`:642`。**注意：`DatasetH` 在 `qlib/data/dataset/__init__.py`，无 `dataset.py` 文件**。
- [未核实] Processor：`Processor`(abstract) `qlib/data/dataset/processor.py:35`。

### 4.2 DataHandlerLP 的 learn_processors vs infer_processors
- [未核实] `DataHandlerLP.__init__`(`handler.py:436`) 三 processor 列表：`infer_processors`(`:442`)→`self._infer`(DK_I)；`learn_processors`(`:443`)→`self._learn`(DK_L)；`shared_processors`(`:444`)先作用于两路。
- [未核实] 三个 data key（`handler.py:422` ATTR_MAP）：`DK_R`→`_data`(raw)、`DK_I`→`_infer`、`DK_L`→`learn`。
- [未核实] 两 process type（`handler.py:425-433`）：`PTYPE_I` "independent"：`_infer=shared+infer`；`_learn=shared+learn`。`PTYPE_A` "append"（**默认**）：`_infer=shared+infer`；`_learn=shared+infer+learn`（learn 叠在 infer 上）。

### 4.3 泄漏边界 —— 关键发现（部分 [已自核]）
- [已自核] `qlib/data/dataset/handler.py:513-519` `DataHandlerLP.fit`：
  ```python
  def fit(self):
      for proc in self.get_all_processors():
          with TimeInspector.logt(f"{proc.__class__.__name__}"):
              proc.fit(self._data)
  ```
  **fit 在整个 raw dataframe `self._data` 上调用，不是 train 切片。**
- [已自核] `handler.py:521` `fit_process_data()` → `process_data(with_fit=True)`(`:552`)。
- [已自核] `handler.py:529-540` `_run_proc_l`：每个 proc `proc.fit(df)` 后 `df = proc(df)`——**fit 输入是前一 processor 的输出**（链式），受 `IT_FIT_SEQ`(`handler.py:629`) 控制。
- [未核实] `setup_data(init_type=IT_FIT_SEQ)`(`handler.py:633-661`) 默认路径：构造时调一次 `fit_process_data()`。
- [未核实] **泄漏边界不在 handler 层强制**。`proc.fit(self._data)` 收全时间范围。防泄漏**逐 processor** 经构造参数 `fit_start_time`/`fit_end_time`。仅时序归一器遵守：
  - `MinMaxNorm.fit`(`processor.py:204-218`) `df = fetch_df_by_index(df, slice(self.fit_start_time, self.fit_end_time), level="datetime")`(`:205`)
  - `ZScoreNorm.fit`(`processor.py:238-252`) `:239`
  - `RobustZScoreNorm.fit`(`processor.py:281-288`) `:282`
  - 各自有醒目警告（`processor.py:198-199`、`:232-233`、`:274-275`）："`fit_end_time` **must not** include any information from the test data!!!"
- [未核实] `check_transform_proc`(`qlib/contrib/data/handler.py:12-34`)：自动把 `fit_start_time`/`fit_end_time` 注入任何构造签名接受它们的 processor——Alpha158/360 用此连边界。

### 4.4 processor 可能用未来信息的地方
- [未核实] 自定义 `Processor` 子类 `fit()` 忽略 `fit_start_time/fit_end_time` 且读全 `df`——handler 传全时间线给它。
- [未核实] `ProcessInf`(`processor.py:161`)、`Fillna`(`:179`)、`TanhProcess`(`:146`)：无 `fit` 无时间切片——无状态变换，无泄漏，但在 `infer_processors` 对全 `_data` 跑（segment 前）。
- [未核实] 截面 processor（`CSZScoreNorm` `:300`、`CSRankNorm` `:326`、`CSZFillna` `:362`）：无 `fit`——按 datetime groupby 变换，构造上无跨时泄漏。
- [未核实] `TimeRangeFlt`(`processor.py:383`) 显式 warn "WARNING: It may induce leakage!!!"(`:388`)。

### 4.5 processor 类别
- [未核实] 截面（CS 前缀，groupby "datetime"，无 fit）：`CSZScoreNorm`(`:300`)、`CSRankNorm`(`:326`)、`CSZFillna`(`:362`)。
- [未核实] 时序（fit 在 `fit_start_time`→`fit_end_time` 切片）：`MinMaxNorm`(`:196`)、`ZScoreNorm`(`:228`)、`RobustZScoreNorm`(`:262`)。
- [未核实] 无状态变换（无 fit 无泄漏）：`DropnaProcessor`(`:94`)、`DropnaLabel`(`:105`，仅 label；`is_for_infer()=False`(`:109`)，不能进 `infer_processors`)、`DropCol`(`:114`)、`FilterCol`(`:129`)、`TanhProcess`(`:146`)、`ProcessInf`(`:161`)、`Fillna`(`:179`)、`HashStockFormat`(`:374`)。
- [未核实] per-instrument（`InstProcessor` 子类，非 `Processor`）：`TimeRangeFlt`(`:383`)。
- [未核实] 抽象闸 `is_for_infer()`(`:62`)：`infer_processors` 链调 `_run_proc_l(..., check_for_infer=True)`(`handler.py:591`)，任一返 False 则 raise(`:534`)。

### 4.6 Alpha158 / Alpha360
- [未核实] `Alpha360` `qlib/contrib/data/handler.py:48`（`DataHandlerLP` 子类）。Label：`Ref($close,-2)/Ref($close,-1)-1`(`:90`)。
- [未核实] `Alpha158` `:98`（`DataHandlerLP` 子类，`process_type=PTYPE_A`）。同 label(`:152`)。
- [未核实] 变体 `Alpha360vwap`(`:93`)、`Alpha158vwap`(`:155`)——label 换 `$vwap`。
- [未核实] 默认 processor（`qlib/contrib/data/handler.py:37-45`）：`_DEFAULT_LEARN_PROCESSORS`=`DropnaLabel`,`CSZScoreNorm(label)`；`_DEFAULT_INFER_PROCESSORS`=`ProcessInf`,`ZScoreNorm`,`Fillna`（Alpha360；Alpha158 `infer_processors=[]` `:105`）。
- [未核实] feature loader：`Alpha360DL`(`qlib/contrib/data/loader.py:4`)：6 原始字段 × 60 天 = 360 特征，CLOSE/OPEN/HIGH/LOW/VWAP/VOLUME 各 lag 59→0，归一到最新 `$close`/`$volume`(`:24-57`)。`Alpha158DL`(`loader.py:61`)，`get_feature_config`(`:73-300+`)：kbar(`:104-126`)、price(`:127-133`)、volume(`:134-137`)、rolling(`:138-300+`，~20 算子 × [5,10,20,30,60]）。默认 5 窗口约 158 特征。

### 4.7 DatasetH.fetch / prepare —— train/valid/test 切分
- [未核实] `DatasetH.__init__`(`__init__.py:84`)：`handler` + `segments: Dict[Text, Tuple]`（如 `{'train':('2008-01-01','2014-12-31'), ...}`）。
- [未核实] `prepare()`(`__init__.py:185-247`)：解析 segment 名→`(start,end)`→`_prepare_seg(self.segments[segments], ...)`(`:239-240`)。
- [未核实] `_prepare_seg()`(`__init__.py:171-183`)：`self.handler.fetch(slc, col_set=..., data_key=..., **self.fetch_kwargs)`。
- [未核实] 时间边界在 `DataHandler._fetch_data`→`fetch_df_by_index`(`handler.py:307/311`，util `qlib/data/dataset/utils.py`)。slice 作用在 `datetime` index level——**processor 此处不跑**（已在 `setup_data` 跑过）。**segmentation 是预处理后 `_infer`/`_learn` 的纯 index 切片**。
- [未核实] `TSDatasetH._prepare_seg`(`__init__.py:688-719`) 向后扩 `step_len`(`:679-686`) 让每样本有完整历史——**故意取 segment 起点之前**（非未来），`TSDataSampler` 构造重切到 `[start,end]`(`__init__.py:424-426,443-446`)。

### 4.8 与直觉不符
- [已自核] **Processor fit 见全时间线**。仅 3 个 norm processor 自切片。自定义带状态 `fit()` 且不切片 → 泄漏。
- [已自核] **Processor 顺序有影响**。`_run_proc_l`(`handler.py:533-540`) 顺序链式，`fit` 输入是前一 proc 输出（`IT_FIT_SEQ`）。Fillna 在 ZScoreNorm 前会改变 fit 的 mean/std。
- [未核实] 归一是 per-segment **仅当**每个 processor `fit_start_time/fit_end_time` 对齐 train segment。基类无"fit on train, apply to valid/test"编排——逐 processor opt-in。`check_transform_proc`(`contrib/data/handler.py:12`) 为 Alpha158/360 自动接线。
- [未核实] **`DataHandler` 不直接调 `D.features`**。委托 `self.data_loader.load(...)`(`handler.py:194`)。loader（`QlibDataLoader`）才调 `D.features`。handler 与 provider 解耦。
- [未核实] `_infer`/`_learn` 与 train/valid/test segment 概念正交（`handler.py:410-414`）：可在 "train" 时间段 fetch `DK_I`。

### 4.9 扩展点 / Fork-Required
- [未核实] 新 data handler：子类 `DataHandlerLP`(`handler.py:382`) 或 `DataHandler`(`:67`)，override `__init__` + 给 `data_loader` 配置。无注册——配置里传 class path。
- [未核实] 新 processor：子类 `Processor`(`processor.py:35`)，实现 `__call__`、可选 `fit`/`is_for_infer`/`readonly`。无注册——`infer_processors`/`learn_processors` 用 class name 串引用，经 `init_instance_by_config(proc, processor_module, accept_types=Processor)`(`handler.py:499-503`) 解析。须从 `qlib.data.dataset.processor` 可 import（name-only 解析）否则给 `module_path`。
- [未核实] 新 model：子类 `Model`(`base.py:22`) 实现 `fit`+`predict`；或 `ModelFT`(`:81`)。无注册——config 引用。可选加 `qlib/contrib/model/__init__.py:all_model_classes` 便于发现。
- [未核实] **Fork-Required**：基 `Processor`(`processor.py:35`) 只有 `fit`/`__call__`/`is_for_infer`/`readonly`。若要 processor **仅在 train 上 fit、apply 到 valid/test 且 handler 层 segment 感知**（非逐 processor `fit_start_time`），基类无钩子——`DataHandlerLP.fit`(`handler.py:513`) 总传全 `self._data`。要么复制 `fit_start_time/fit_end_time` 约定，要么 fork `DataHandlerLP.fit`/`process_data` 传切片 df。
- [未核实] **Per-segment 归一**（fit norm on train，apply 到 valid/test 分开）：当前设计 fit **一次**于全量，全局 apply。要 sklearn 风格 `fit_transform(train)` 后 `transform(valid/test)` 须 fork——架构在 `setup_data`(`handler.py:633`) fit 一次，从不 per-segment 重 fit。

---

## 5. Rolling 窗口与边界（get_extended_window_size、trim、min_periods=1 静默错值）

来源：rolling 窗口子 agent。整体 [未核实]（主 agent 未开 ops.py 窗口方法），但行号由子 agent 给且自述已读，是 §2/§4 之外最高危的边界正确性项，重建时优先复核。

### 5.1 Expression.get_extended_window_size / get_longest_back_rolling
- [未核实] `qlib/data/base.py:222` `get_extended_window_size` `@abc.abstractmethod`（`:235` raise）。返 `(lft_etd, rght_etd)`。语义（`base.py:226-228`）：算 `[start_index,end_index]` 需取叶特征 `[start_index-lft_etd, end_index+rght_etd]`。
- [未核实] `qlib/data/base.py:209` `get_longest_back_rolling` `@abc.abstractmethod`（`:220` raise）。用途（docstring `:211-217`）：取历史数据最大长度，用于 cache/preload。**caveat**（`:215`、TODO `:219`）：不能处理前视嵌套如 `Ref(Ref($close,-1),1)`，仅后视长度估计。

### 5.2 loader 用法 —— LocalExpressionProvider.expression
- [未核实] `qlib/data/data.py:843-879`：
  - 扩张 `:852-854`：
    ```
    _, _, start_index, end_index = Cal.locate_index(start_time, end_time, freq=freq, future=False)
    lft_etd, rght_etd = expression.get_extended_window_size()
    query_start, query_end = max(0, start_index - lft_etd), end_index + rght_etd
    ```
  - load 扩张范围 `:859` `series = expression.load(instrument, query_start, query_end, freq)`
  - trim `:877-878` `if not series.empty: series = series.loc[start_index:end_index]`——扩张部分丢弃，caller 只得请求窗口。
  - `time2idx=False`（`:855-856`）时不扩张（`start_index,end_index=query_start=query_end=start_time,end_time`）。默认 ctor `time2idx=True`(`:839-841`)。

### 5.3 内置 Rolling —— `ops.py:713`
- [未核实] `get_extended_window_size` `ops.py:764-778` 三分支：
  - `N==0`（expanding）`:765-769`：warn（"will not be accurately calculated"）返 `self.feature.get_extended_window_size()` 不变。FIXME `:766` 承认不准。
  - `0<N<1`（EWM alpha）`:770-774`：`size = int(np.log(1e-6)/np.log(1-self.N))`（`(1-N)**size ≈ 1e-6` 的衰减视界），`lft_etd = max(lft_etd+size-1, lft_etd)`，返 `(lft_etd, rght_etd)`。
  - else（整数 N≥1）`:775-778`：`lft_etd, rght_etd = self.feature.get_extended_window_size(); lft_etd = max(lft_etd + self.N - 1, lft_etd); return lft_etd, rght_etd`。**精确公式：`lft_etd = feature_lft + (N-1)`，`rght_etd = feature_rght + 0`**——plain `Rolling($close,N)` 返 **`(N-1, 0)`**，不是 `(N,0)`。
- [未核实] `get_longest_back_rolling` `ops.py:757-762`：`N==0`→`np.inf`(`:758-759`)；`0<N<1`→`int(np.log(1e-6)/np.log(1-N))`(`:760-761`)；else→`self.feature.get_longest_back_rolling()+self.N-1`(`:762`)。
- [未核实] `_load_internal` `ops.py:742-755`：`N==0`→`expanding(min_periods=1)`；`0<N<1`→`ewm(alpha=N, min_periods=1).mean()`；else→`rolling(N, min_periods=1)`。**关键**：`min_periods=1`（`:748,750,752`）→起点 partial window 产**值非 NaN**——这是让 under-sized 扩张**静默错**而非 NaN 的原因。

### 5.4 Ref（Rolling 子类）—— `ops.py:781`
- [未核实] `_load_internal` `ops.py:800-809` 用 `series.shift(self.N)`。
- [未核实] `get_extended_window_size` `ops.py:816-824`：`N==0`→warn + `self.feature.get_extended_window_size()`(`:817-819`)；else→`lft_etd, rght_etd = self.feature.get_extended_window_size(); lft_etd = max(lft_etd + self.N, lft_etd); rght_etd = max(rght_etd - self.N, rght_etd)`(`:820-824`)。**`Ref($close,k)` k>0 需 `k` 天后视**——返 `(lft+k, rght-k)`。注意是 `+N` 非 `+N-1`（shift 需第 k 个前值，非 k 宽聚合）。`N<0`（未来 ref）长 `rght_etd`。
- [未核实] `get_longest_back_rolling` `ops.py:811-814`：`N==0`→`np.inf`；else→`self.feature.get_longest_back_rolling()+self.N`。

### 5.5 ElemOperator / PairOperator 聚合
- [未核实] `ElemOperator`(`ops.py:37`)：`get_longest_back_rolling`→`self.feature.get_longest_back_rolling()`(`:57-58`)；`get_extended_window_size`→`self.feature.get_extended_window_size()`(`:60-61`)。纯透传。
- [未核实] `PairOperator`(`ops.py:231`)：`get_longest_back_rolling` `:254-264` 取 `max(left_br, right_br)`（操作数为数值常量则 0）；`get_extended_window_size` `:266-276` 拆 `(ll,lr)/(rl,rr)` 返 `(max(ll,rl), max(lr,rr))`。**复合按 per-side max 聚合**，非求和。
- [未核实] `If`(`ops.py:639`) 同 max 聚合三子 `:690-705`。

### 5.6 PIT `P` —— `pit.py:24`
- [未核实] `get_extended_window_size` 返 `(0,0)`(`pit.py:58-60`)；`get_longest_back_rolling` 返 `0`(`:54-56`)。
- [未核实] **调和**：P 在 `_load_internal`(`pit.py:25-49`) 内**自行 per-timestep 扩张**。对 `[start_index,end_index]` 每个 `cur_index`(`:29`)，再调 `self.feature.get_extended_window_size()`(`:32`) 取 `(start_ws, end_ws)`，拒 `end_ws>0`(`:33-36`)，调 `self._load_feature(instrument,-start_ws,0,cur_time)`(`:40`)，取 `s.iloc[-1]`(`:41`) collapse。**P 绕过 provider 扩张**：provider 见 `(0,0)` 不扩，但 P 内部逐步向子特征重问窗口并 collapse。

### 5.7 自定义算子契约 —— 四方法 + 失败模式
- [未核实] 写窗口 W 的自定义 rolling 算子（子类 `ExpressionOps`/`Expression`，经 `OpsWrapper.register`/`C.custom_ops`，`ops.py:1619-1681`）须实现：
  1. `__init__`+`__str__`：注册与缓存必需。`Expression.load` 建 `cache_key = str(self),instrument,start_index,end_index,*args`(`base.py:187`)；`__str__` 畸形 → 缓存冲突。
  2. `_load_internal(self, instrument, start_index, end_index, *args)`：abstract `base.py:205-207`，由 `Expression.load`(`:193`) 在**已扩张**的 `[query_start, query_end]` 上调。**失败模式**：若假定窗口预填但 caller 没扩张，segment 起点前 `W-1` 行历史不足；pandas `min_periods=1` → **静默错 partial-window 值非 NaN**；用 `min_periods=W` → segment 起点得 NaN（可见但仍错）。
  3. `get_extended_window_size(self) -> (lft_etd, rght_etd)`：abstract `base.py:222-235`。**边界正确性契约**。loader 用之扩张(`data.py:853-854`)、load(`:859`)、trim(`:878`)。窗口 W 应返 `(W-1,0)`+子所需（公式 `ops.py:775-778`：`lft_etd = max(child_lft + (W-1), child_lft)`）。**失败模式**：
     - **lft_etd 太小（如返 `(0,0)`）**：segment 起点 rolling 在 <W 点上算；`min_periods=1` → **静默错值**（最危险，无标记）；若 `_load_internal` 用 `min_periods=W` 或对短窗 raise → segment 前 `W-1` 行 NaN。
     - **lft_etd 太大**：多取历史——正确但浪费 I/O/cache；`max(0,...)` clamp(`data.py:854`) 在 calendar 起点附近掩盖下溢。
     - **需未来数据 rght_etd 太小**：segment 尾 partial/NaN；`min_periods=1` 同样静默错。
     - **N==0（expanding）**：内置 `Rolling` 兜底 warn 返子窗口不变(`ops.py:765-769`)，`get_longest_back_rolling` 返 `np.inf`(`:758-759`) 示无法准确预载。自定义 expanding op 应遵同样约定或显式处理。
  4. `get_longest_back_rolling(self)`：abstract `base.py:209-220`，用于 sizing 预载/缓存历史。**失败模式**：太小→预载器少取历史→`expression.load` 在扩张范围上叶特征缺行→segment 起点 partial（静默错或 NaN）；太大→过度预载浪费内存；返 `np.inf` 示无界后视。
- **边界正确性总结**：segment 起点窗口 W 的 rolling 需 `start_index` 前 `W-1` 行历史。loader 仅当 `get_extended_window_size` 返 `lft_etd >= W-1`（经表达式树 max 规则 `ops.py:266-276`/`:57-61` 聚合）才取这些行。自定义算子少报 `lft_etd` → `data.py:878` trim 返的 series 前几行在 partial window 上算；惯例 `min_periods=1` → **segment 起点静默错值非 NaN**。

---

## 6. 模型与训练编排（task_train 逐步序列、fill_placeholder、无 try/except）

来源：trainer.py 子 agent。整体 [未核实]（主 agent 未开 trainer.py），但编排序列是 ARCHITECTURE.md 链路 1 骨架，行号子 agent 已给，重建时优先复核。

### 6.1 task_train / _exe_task 序列
- [未核实] 真正工作在私有 `_exe_task`(`trainer.py:42-71`)。`task_train`(`:108-128`) 是薄壳：开 recorder context、log、调 `_exe_task`、返 recorder。
- [未核实] `task_train(task_config, experiment_name, recorder_name=None)` `:108-128`：
  1. `with R.start(experiment_name=..., recorder_name=...):` `:125`
  2. `_log_task_info(task_config)` `:126`（定义 `:36-39`：`R.log_params`、`R.save_objects({"task":...})`、`R.set_tags(hostname=...)`）
  3. `_exe_task(task_config)` `:127`
  4. `return R.get_recorder()` `:128`
  5. context exit 隐式（`with` 块末），无显式 `R.end_recorder()`
- [未核实] `_exe_task(task_config)` `:42-71`：
  1. `rec = R.get_recorder()` `:43`
  2. `model = init_instance_by_config(task_config["model"], accept_types=Model)` `:45`
  3. `dataset = init_instance_by_config(task_config["dataset"], accept_types=Dataset)` `:46`
  4. `reweighter = task_config.get("reweighter", None)` `:47`
  5. `auto_filter_kwargs(model.fit)(dataset, reweighter=reweighter)` `:49`——**reweighter 总被传**，但 `auto_filter_kwargs` 在 `model.fit` 不接受 `reweighter` 时丢弃
  6. `R.save_objects(**{"params.pkl": model})` `:50`
  7. `dataset.config(dump_all=False, recursive=True)` `:52`（不序列化具体数据）
  8. `R.save_objects(**{"dataset": dataset})` `:53`
  9. `placehorder_value = {"<MODEL>": model, "<DATASET>": dataset}` → `task_config = fill_placeholder(task_config, placehorder_value)` `:55-56`（后续 record 配置可引 `<MODEL>`/`<DATASET>`）
  10. `records = task_config.get("record", [])` `:58`，dict→list 规范化 `:59-60`
  11. `for record in records:` `:61`：经 `init_instance_by_config(record, recorder=rec, default_module="qlib.workflow.record_temp", try_kwargs={"model":model,"dataset":dataset})`(`:65-70`) 实例化；`r.generate()` `:71`。

### 6.2 record 循环 —— 顺序、强制、错误处理
- [未核实] **顺序 = config["record"] 列表字面顺序**，plain `for`(`:61`)，**无重排无排序**，**无 try/except** 包实例化(`:65-70`)或 `r.generate()`(`:71`)。任一 record 异常中断剩余循环并传播出 `_exe_task`→`task_train`→`with R.start` 块（recorder 仍创建但 run 标记失败）。
- [未核实] record 类名**非硬编码**于 `trainer.py`，经 `init_instance_by_config` 对 `default_module="qlib.workflow.record_temp"`(`:68`) 解析。标准类 `SignalRecord`/`SigAnaRecord`/`PortAnaRecord` 在 `qlib/workflow/record_temp.py:161/295/358`。fork 可加自定义 record 类不动 trainer.py。

### 6.3 init_instance_by_config 用法
- [未核实] model(`:45`)、dataset(`:46`)、每 record(`:65-70`)。record 变体传 `recorder=rec`、`default_module="qlib.workflow.record_temp"`、`try_kwargs={"model":model,"dataset":dataset}`——`__init__` 接受 model/dataset 的 record 类自动注入。

### 6.4 qrun / CLI
- [未核实] `qlib/cli/run.py:15` `from qlib.model.trainer import task_train`。
- [未核实] `qlib/cli/run.py:147` `recorder = task_train(config.get("task"), experiment_name=experiment_name)`。
- [未核实] `qlib/cli/run.py:148` `recorder.save_objects(config=config)`。
- [未核实] `workflow`(`run.py:~147`) 是 qrun 入口，`fire.Fire(workflow)`(`run.py:152-153`)。

### 6.5 begin_task_train / end_task_train（延迟变体）
- [未核实] `begin_task_train(task_config, experiment_name, recorder_name=None)` `:74-88`：开 `with R.start(...)`(`:86`)、`_log_task_info`(`:87`)、返 `R.get_recorder()`(`:88`)——**不调 `_exe_task`**，只持久化 task config + 建 recorder。
- [未核实] `end_task_train(rec, experiment_name)` `:91-105`：`with R.start(experiment_name=..., recorder_id=rec.info["id"], resume=True):` `:102`，`task_config = R.load_object("task")` `:103`，`_exe_task(task_config)` `:104`——整个 fit+record-generate 在此 resume 的 recorder 内跑。
- [未核实] 二者是**普通函数非 contextmanager**（内部用 `with R.start`）。`DelayTrainerR.__init__` 设 `train_func=begin_task_train`、`end_train_func=end_task_train`(`:298-300`)；`DelayTrainerRM` 同(`:497-504`)。

### 6.6 fork 相关硬编码假设
- [未核实] 默认 record 模块 `default_module="qlib.workflow.record_temp"` 硬编码 `trainer.py:68`。fork 想从别处引 record 须 (a) 在 task config 用全限定 `class` 串，或 (b) patch 此行。
- [未核实] `task_train` 无硬编码 experiment name 默认——`experiment_name` 是必填位置参(`:108`)。默认在一层之上 `TrainerR.__init__`(`:223`)/`TrainerRM.__init__`(`:358`)，qrun 来自 `config["experiment_name"]`(`run.py:145-146`)。
- [未核实] 持久化 key 名 `"params.pkl"`(`:50`)、`"dataset"`(`:53`)、`"task"`(`:38`) 是字面量。下游 `end_task_train` `:103` `R.load_object("task")` 依赖 `"task"` key。
- [未核实] 占位 token `"<MODEL>"`/`"<DATASET>"`(`:55`)——`fill_placeholder` 只替换这两个。
- [未核实] reweighter：总传 `auto_filter_kwargs(model.fit)(dataset, reweighter=reweighter)`(`:49`)；`fit` 签名无 `reweighter` 则静默丢弃。`reweighter=None` 且 model 接受则 None 透传。
- [未核实] **无 per-record 错误隔离**：`SigAnaRecord.generate()` 失败会阻止 `PortAnaRecord.generate()`。fork 要容错须包 `:65-71` 于 try/except。

---

## 7. 回测与撮合（exchange 撮合价/涨跌停/停牌/成本不对称/T+1 缺口）

来源：exchange.py 子 agent。整体 [未核实]，但行号密集且 T+1 缺口是 fork 面核心，BACKTEST_SPEC 落笔前抽样复核。

### 7.1 deal price
- [未核实] `get_deal_price` `exchange.py:494-514`：按 `direction` 选——SELL→`self.sell_price`(`:503`)，BUY→`self.buy_price`(`:505`)，经 `self.quote.get_data(..., field=pstr, method=method)`(`:509`)。
- [未核实] `buy_price`/`sell_price` 在 `__init__` `exchange.py:157-164`：`deal_price` 是 str → 缺 `$` 加前缀，`self.buy_price=self.sell_price=deal_price`(`:160`)；是 tuple/list → split(`:162`)。`deal_price` 构造参默认 `None`(`:44`)，`None` 时回退 `C.deal_price`(`:142`)。
- [未核实] 区域默认 `C.deal_price` 三区均 `"close"`（`config.py:300,305,310`）→ 经 `:159` 加 `$` 成 `"$close"`。
- [未核实] **静默 NaN 回退 $close**：`exchange.py:510-513`，若 `method is not None` 且配置价是 None/np.isnan/`<=1e-08` → warn(`:511-512`) → `deal_price = self.get_close(...)`(`:513`)。注意 `method is not None` 守卫——传 `method=None` 跳过回退。

### 7.2 Order→Fill 路径
- [未核实] 入口 `deal_order(order, trade_account, position, dealt_order_amount)` `exchange.py:421-463`。
- [未核实] 预检 `check_order(order)` `:438`（返回 `:417-419`）；失败 `order.deal_amount=0.0` 返 `(0.0,0.0,np.nan)`(`:439-442`)。
- [未核实] `check_order`→`is_stock_tradable(stock_id,start,end,direction)`(`:419`，定义 `:404-415`)=`not(check_stock_suspended(...) or check_stock_limit(...))`(`:412-414`)。
- [未核实] 核心 `_calc_trade_info_by_order(order, position, dealt_order_amount)` `exchange.py:448-452`（定义 `:859-952`）。**注意真实方法名是 `_calc_trade_info_by_order`**（非 `_calc_trade_by_info_by_order`）。
- [未核实] 结果路由 `trade_account.update_order(...)`(`:459`) 或 `position.update_order(...)`(`:461`)，仅 `trade_val > 1e-5`(`:453-461`)。

`_calc_trade_info_by_order`(`:859-952`) 子步：
1. price pick `trade_price = get_deal_price(...)` `:873-876`
2. `total_trade_val = get_volume(...)*trade_price` `:877`（impact 缩放）
3. `order.factor = get_factor(...)` `:878`；`order.deal_amount = order.amount` `:879`
4. amount clip by volume `_clip_amount_by_volume(order, dealt_order_amount)` `:884`（定义 `:786-832`，in-place 改 `order.deal_amount`）
5. impact cost：`total_trade_val` falsy/NaN → `adj_cost_ratio = self.impact_cost`(`:890`)；否则 `adj_cost_ratio = self.impact_cost * (trade_val/total_trade_val)**2`(`:892`)
6. 分支 `:894`：
   - **SELL**(`:894-917`)：`cost_ratio = self.close_cost + adj_cost_ratio`(`:895`)；clip 到持仓 `round_amount_by_trade_unit(min(current_amount, deal_amount), factor)`(`:906-909`)；cash-floor `:912-917`——`get_cash()+deal_amount*price < max(deal_amount*price*cost_ratio, min_cost)` → `deal_amount=0`
   - **BUY**(`:919-942`)：`cost_ratio = self.open_cost + adj_cost_ratio`(`:920`)；cash check `:925`（cost>cash→0）、`:929`（不足→`_get_buy_amount_by_cash_limit`(`:931`)→`round_amount_by_trade_unit(min(max_buy, deal_amount), factor)`(`:932-935`)）；else round `:939`；无 position 则 round `:942`
7. final cost floor：`trade_val = order.deal_amount*trade_price`(`:947`)；`trade_cost = max(trade_val*cost_ratio, self.min_cost)`(`:948`)；`trade_val<=1e-5` 归零(`:949-951`)；返 `(trade_price, trade_val, trade_cost)`(`:952`)。

### 7.3 涨跌停
- [未核实] limit 列由 `_update_limit(limit_threshold)` `exchange.py:273-292` 构，init 调一次 `:234`。
- [未核实] 检查函数 `check_stock_limit(stock_id, start, end, direction)` `exchange.py:338-376`，用 `method="all"`(`:368-369,372,374`)——**窗口内每根 bar 都 limit 才算 limited**（`# NOTE` `:362-364`）。
- [未核实] 三模式 `_get_limit_type`(`exchange.py:262-271`)，常量 `:258-260`：
  - `LT_NONE="none"`(`:260`)：`limit_buy=suspended`(`:279`)、`limit_sell=suspended`(`:280`)
  - `LT_TP_EXP="(exp)"`(`:258`)：threshold 是 `Tuple[str,str]` qlib 表达式；`limit_buy = quote_df[exp[0]].astype("bool") | suspended`(`:285`)、`limit_sell` 用 `exp[1]`(`:286`)
  - `LT_FLT="float"`(`:259`)：threshold 是 float；`limit_buy = $change.ge(limit_threshold) | suspended`(`:289`)——今日 `$change >= +threshold` 时 buy-limited；`limit_sell = $change.le(-limit_threshold) | suspended`(`:290-292`)——`$change <= -threshold` 时 sell-limited。**LT_FLT 对称 $change-based ±threshold 闸门。**
- [未核实] **默认 limit_threshold**：REG_CN `0.095`(`config.py:299`)、REG_US `None`(`:304`)、REG_TW `0.1`(`:309`)。经 `C.limit_threshold` 于 `exchange.py:139-140`（构造参 `None` 时）。
- [未核实] 合理性 warn：LT_FLT 且 CN/TW `abs(limit_threshold)>0.1` 时 warn(`:153-155`)。

### 7.4 停牌
- [未核实] `check_stock_suspended(stock_id, start_time, end_time)` `exchange.py:378-402`。**suspended == NaN `$close`**：
  - docstring `:384` "if stock is suspended(hence not tradable)"
  - `:386-402`：不在 `get_all_stock()` → True(`:402`)；否则取 `$close`(`:389`)；`close is None` → True(`:390-392`)；`IndexData` → `close.isna().all()`(`:393-396`)；单值 → `np.isnan(close)`(`:398-399`)
  - 与 `:33`/`:171`/`:274` 一致：`$close` None/NaN 即停牌。
- [未核实] `_update_limit` 也从 `$close.isna()` 种 `suspended`(`:275`)，OR 进 `limit_buy`/`limit_sell`(`:279-280,285-286,289,291`)——停牌股双向都 limited。

### 7.5 成本模型作用点
- [未核实] 存储 `self.open_cost`(`exchange.py:187`)、`self.close_cost`(`:188`)、`self.min_cost`(`:189`)、`self.impact_cost`(`:190`)。
- [未核实] `cost_ratio` 组装：SELL `self.close_cost + adj_cost_ratio`(`:895`)；BUY `self.open_cost + adj_cost_ratio`(`:920`)；`adj_cost_ratio` 在 `:890`/`:892`（平方 impact `impact_cost*(trade_val/total_trade_val)**2`）。
- [未核实] `max(trade_val*cost_ratio, self.min_cost)` floor 出现 3 处：SELL cash-floor `:912-915`、BUY cash `:925` 与 `:929`、final `trade_cost = max(trade_val*cost_ratio, self.min_cost)`(`:948`)，`trade_val<=1e-5` 归零(`:949-951`)。
- [未核实] `_get_buy_amount_by_cash_limit`(`:834-857`) 内嵌 `self.min_cost` 作 `critical_price` 阈(`:850`)。
- [未核实] **不对称默认**：`open_cost=0.0015`(`:48`)、`close_cost=0.0025`(`:49`)、`min_cost=5.0`(`:50`)、`impact_cost=0.0`(`:51`)。
- [未核实] **`min_cost` 对称/全局**：单标量同施买卖(`:912,925,929,948` 及 `:848-856`)，无 open/close min_cost。

### 7.6 T+1 —— 确认 Exchange 不强制
- [未核实] grep `t+1|today|bought|holding|T1|day_count|settle` 仅命中两条无关 log(`:152,254`)。无持仓期、无"当日买入"、无 day-count、无结算逻辑。
- [未核实] SELL 分支 `:894-917` clip `order.deal_amount` 仅到 `position.get_stock_amount(...)`（**当前总持仓** `:901-903`），不区分当日 vs 之前。当日买入可立即在 `deal_order` 内全卖。
- [未核实] `check_order`(`:417-419`)→`is_stock_tradable`(`:404-415`) 仅查停牌+涨跌停，无时序持仓约束。
- [未核实] `deal_order`(`:421-463`) 与 `_calc_trade_info_by_order`(`:859-952`) 无 T+1 钩子。
- **结论**：Exchange 不强制 T+1。T+1 若有必在别处（策略层 `signal_strategy.py:242` 的 `hold_thresh` + `Position.add_count_all` `position.py:474-480`）。

### 7.7 trade_unit rounding
- [未核实] `round_amount_by_trade_unit(deal_amount, factor=None, ...)` `exchange.py:761-784`：`not self.trade_w_adj_price and self.trade_unit is not None`(`:775`)→`factor` 经 `_get_factor_or_raise_error`(`:777-782`)，返 `(deal_amount*factor+0.1)//self.trade_unit*self.trade_unit/factor`(`:783`)（`+0.1` 精度修，注释 `:776`）；否则返 `deal_amount` 不变(`:784`)。
- [未核实] `get_amount_of_trade_unit` `:728-759`：非复权且 trade_unit set → `self.trade_unit/factor`(`:750-757`)；否则 `None`(`:759`)。
- [未核实] **`trade_w_adj_price` 在 `$factor` NaN 时静默变**：`get_quote_from_qlib` `exchange.py:222-232`。`($factor.isna() & ~$close.isna()).any()`(`:222`)→`self.trade_w_adj_price=True`(`:225`) + warn。后果：`round_amount_by_trade_unit` 返 `deal_amount` 不改(`:784`)、`get_amount_of_trade_unit` 返 `None`(`:759`)——**整手 rounding 静默禁用**，amount 当已复权处理。`trade_unit` 来自 `kwargs.pop("trade_unit", C.trade_unit)`(`:135`)；区域 `C.trade_unit` CN=100/US=1/TW=1000(`config.py:298,303,308`)。

### 7.8 fork surface 分类
| 关注 | override 路径 | 判定 |
|---|---|---|
| deal price | 子类 Exchange override `get_deal_price`(`:494`)，或构造传 `deal_price` | 子类可override，无需改源 |
| limit rule | 子类 override `_update_limit`(`:273`)/`check_stock_limit`(`:338`)/`_get_limit_type`(`:262`)，或传 `LT_TP_EXP` 表达式 threshold | 子类可override；LT_FLT 公式 `:289-292` source-locked（要不同公式形状须 override 方法） |
| cost model | 标量 rates 构造参(`:187-190`)可调；`max(...,min_cost)` floor(`:948`) 与 impact 公式(`:892`)在 `_calc_trade_info_by_order` 内 | **混合**：标量 config/子类可调；函数形式 fork-required（override 整个 `_calc_trade_info_by_order` 是唯一不改源路径，代价是复制全 fill 逻辑） |
| T+1 | **无钩子可 override**。加 T+1 须子类 override `deal_order`/`_calc_trade_info_by_order`/`check_order` 注入持仓年龄逻辑（需 per-share acquisition-time ledger，Exchange 不维护），或改源/在 Account 层包 | **fork-required / 越界** |

### 7.9 其他硬编码
- [未核实] rounding `0.1` epsilon(`:783`)、`1e-5` 零交易阈(`:453,949`) 是字面常量。
- [未核实] `generate_order_for_target_amount_position` `:638-639` `random.seed(0)` + `random.shuffle` 硬编码 seed。
- [未核实] `$change`/`$factor`/`$volume`/`$close` 字段名硬编码于 `necessary_fields`(`:178`) 及 `_update_limit`/`get_close`/`get_volume`/`get_factor`。

### 7.10 策略层（补充，子 agent）
- [未核实] `BaseStrategy` `qlib/strategy/base.py:23`；抽象 `generate_trade_decision(execute_result=None) -> Union[BaseTradeDecision, Generator]` `:132-146`。
- [已核实-子agent] `TopkDropoutStrategy` 在 **`qlib/contrib/strategy/signal_strategy.py:75`** [已推翻 → 见 fork-docs/ARCHITECTURE.md §2.4] ~~`signal_strategy.py:75`~~（路径缺 `contrib/` 前缀；`qlib/strategy/signal_strategy.py` 不存在）。错因：子 agent 路径误报，未验证文件存在性。`hold_thresh=1` 默认(`:81,134`)，`get_stock_count(code, bar=time_per_step) < self.hold_thresh` 时禁卖(`:242-244`)。count 在 bar 末 `Account.update_current_position`→`add_count_all`(`account.py:248`) 增。**T+1 仅此策略层近似，非核心引擎规则**。
- [未核实] 信号时序用 `shift=1`(`signal_strategy.py:142`)——今日决策用输入窗口早一 bar 的预测（T+1 信息边界，与 T+1 结算约束不同）。
- [未核实] `NestedExecutor` `executor.py:310` 有 `inner_executor`+`inner_strategy`(`:349-358`)，每外步 reset 内 executor calendar 到外步 `[start,end]`(`_init_sub_trading` `:389-394`)，`while not self.inner_executor.finished()`(`:420`) 调 `inner_strategy.generate_trade_decision`(`:436`)。
- [已核实-子agent] `SimulatorExecutor` `executor.py:513`，`trade_type` `TT_SERIAL="serial"`/`TT_PARAL="parallel"`(`:520-525`)。
- [已推翻 → 见 fork-docs/ARCHITECTURE.md §2.2] ~~TT_PARAL 按 `-o.direction` 排序让 SELL 先（释放现金），`executor.py:585`~~。**正确**：`sorted(orders, key=lambda order: -order.direction)`(`executor.py:579-585`)，`Order.SELL=0`/`Order.BUY=1`(`qlib/backtest/decision.py:32-33`)，`-direction` 升序 ⇒ **BUY-first**（`:583` 注释 "make the buying go first"）。错因：子 agent 误读排序语义，按"释放现金"直觉推断，未查 `Order.SELL/BUY` 常量值。
- [未核实] `collect_data` `executor.py:227-303` 每步：track_data(`:262-263`)→atomic 判定(`:265`)→`settle_type!=ST_NO` 时 `position.settle_start`(`:270-271`)→`_collect_data`(`:273`)→`trade_account.update_bar_end`(`:283-293`)→`trade_calendar.step()`(`:295`)→settle commit(`:297-298`)。
- [未核实] **T+1 引擎层默认 OFF**：`BaseExecutor` 默认 `settle_type=BasePosition.ST_NO`(`executor.py:36`)——同 bar 卖出现金立即可买。`ST_CASH` settle(`position.py:377-381`，`executor.py:270-271,297-298`)须显式开。
- [未核实] `rtn`(accum_info.rtn) 不含成本；`earning` 含成本（`account.py:18-31`，`_update_state_from_order` `:183-201` 注 "do not consider cost"）。`return_rate=(now_earning+now_cost)/last_account_value`(`account.py:283`)——报告 return 是 gross of cost，earning 是 net。**读回报数字须分清 rtn/earning/return_rate。**
- [未核实] `deal_price` 在配置买卖价字段 NaN/`<=1e-8` 时回退 `$close`(`exchange.py:510-513`)——静默回退可掩盖缺数据。

---

## 8. 指标口径（238/252/250 三套、ICIR 无 √N vs IR 有 √N、mode="sum" 单利、cumsum 回撤）

来源：workflow+归因子 agent + 我对 `evaluate.py:26-93` 的自核。**这一节是 fork 最要命的一条**——不报错，只让我们对收益数字产生错误信心。

### 8.1 risk_analysis —— [已自核] 公式
- [已自核] `qlib/contrib/evaluate.py:26` `risk_analysis(r, N=None, freq="day", mode="sum")`。
- [已自核] docstring `:28-32`："The calculation of annualized return is different from the definition... It is implemented by design. Qlib tries to cumulate returns by summation instead of production to avoid the cumulated curve being skewed exponentially."
- [已自核] docstring `:39` 参数 N 写 **"day: 252, week: 50, month: 12"**——**与实现 `:52` 的 238 打架（[存疑] 已确认冲突）**。
- [已自核] `cal_risk_analysis_scaler(freq)` `:48-56`，keyed by `Freq.NORM_FREQ_*`(`qlib/utils/time.py:115-118`)：minute `240*238`(`:51`)、**day `238`**(`:52`)、week `50`(`:53`)、month `12`(`:54`)，除以 `_count`（如 "5min"）。
- [已自核] `:58-63` `N is None and freq is None` raise；`:60-61` 两者皆给则 warn ignore freq；`:62-63` `N = cal_risk_analysis_scaler(freq)`。
- [已自核] **mode="sum"（默认）`:65-69`**：
  - `mean = r.mean()`(`:66`)
  - `std = r.std(ddof=1)`(`:67`)
  - `annualized_return = mean * N`(`:68`)——**单利年化**
  - `max_drawdown = (r.cumsum() - r.cumsum().cummax()).min()`(`:69`)——**基于算术累计 cumsum，非乘性（cumprod）** [措辞修正 2026-07-15]：原文"非复权 cumprod"用词不准——cumsum/cumprod 是加性/乘性累计之别，与价格复权（adjustment）无关，勿与 §1.7 混淆。
- [已自核] **mode="product" `:70-80`**：
  - `cumulative_curve = (1+r).cumprod()`(`:71`)
  - `mean = cumulative_curve.iloc[-1]**(1/len(r)) - 1`(`:73`)——几何均值/CAGR
  - `std = np.log(1+r).std(ddof=1)`(`:75`)——对数收益波动
  - `cumulative_return = cumulative_curve.iloc[-1] - 1`(`:77`)
  - `annualized_return = (1+cumulative_return)**(N/len(r)) - 1`(`:78`)
  - `max_drawdown = (cumulative_curve/cumulative_curve.cummax() - 1).min()`(`:80`)——cumprod 回撤
- [已自核] `:81-82` else raise。
- [已自核] **`information_ratio = mean / std * np.sqrt(N)`**(`:84`)——用当前 mode 的 mean/std（默认 sum 模式即 `(r.mean()/r.std(ddof=1))*sqrt(238)` 日频）。这是超额收益 IR（`PortAnaRecord` 传 `return-bench[-cost]`，`record_temp.py:507-512`）。

### 8.2 IC / Rank IC / ICIR
- [未核实] `evaluate.py` **无** `ic`/`ic_rank`/`score_ic`/`ic_signal` 函数（grep 无命中）。
- [未核实] IC 实现在 `qlib/contrib/eva/alpha.py` `calc_ic`，被 `SigAnaRecord`/`HFSignalRecord` 消费：
  - `calc_ic(pred, label, date_col="datetime", dropna=False)` `alpha.py:160-183`，返 `(ic, ric)`：
    - **IC（Pearson）**：`df.groupby(date_col).apply(lambda df: df["pred"].corr(df["label"]))`(`:178`)——**按日截面** Pearson，返每日 IC 的 Series
    - **Rank IC（Spearman）**：`df.groupby(date_col).apply(lambda df: df["pred"].corr(df["label"], method="spearman"))`(`:179`)
- [未核实] ICIR/Rank ICIR 不在 `calc_ic`，在 `SigAnaRecord._generate`(`record_temp.py:324-329`) 与 `HFSignalRecord.generate`(`:264-268`) 派生：
  - `"IC": ic.mean()`(`record_temp.py:325`)
  - **`"ICIR": ic.mean()/ic.std()`(`:326`)——mean(IC)/std(IC)，无 √N 年化**
  - `"Rank IC": ric.mean()`(`:327`)；`"Rank ICIR": ric.mean()/ric.std()`(`:328`)

### 8.3 long-short return
- [未核实] `calc_long_short_return` `alpha.py:71-113`：`r_long = group.apply(lambda x: x.nlargest(N(x),"pred").label.mean())`(`:110`)、`r_short = x.nsmallest(N(x),"pred").label.mean()`(`:111`)、`r_avg = group.label.mean()`(`:112`)、返 `(r_long-r_short)/2, r_avg`(`:113`)；`N(x)=int(len(x)*quantile)`，默认 `quantile=0.2`(`:107-108`)。
- [未核实] `SigAnaRecord` `ana_long_short=True` 时：`Long-Short Ann Return = long_short_r.mean()*ann_scaler`(`record_temp.py:335`，`ann_scaler` 默认 **252** `:304`)；`Long-Short Ann Sharpe = long_short_r.mean()/long_short_r.std()*ann_scaler**0.5`(`:336`)——此处 √N 出现。

### 8.4 evaluate_portfolio.py —— 第三套口径（用 250）
- [未核实] `qlib/contrib/evaluate_portfolio.py` 是**遗留/并行**指标集，从 position dict 算（非 return series）。用 **250**（非 238/252）：
  - `get_position_value`(`:36`)/`get_position_list_value`(`:76`) = Σ close*amount + cash
  - `get_daily_return_series_from_positions`(`:105`) = position value pct_change，首日 `value/init_asset-1`
  - `get_annual_return_from_positions`(`:122`)：`pow(p_end/p_start, 250/n_period)-1`(`:138`)——**250 硬编码**
  - `get_annaul_return_from_return_series`(`:143`，typo "annaul")：`(1+mean)**250-1`（复利）或 `mean*250`（单利）(`:154`)——**250 硬编码**
  - `get_sharpe_ratio_from_return_series`(`:159`)：`(annual-risk_free_rate)/std/np.sqrt(250)`(`:173`)——**250 硬编码**，默认 `risk_free_rate=0`
  - `get_max_drawdown_from_series`(`:178`)：`(((1+r).cumprod()-(1+r).cumprod().cummax())/((1+r).cumprod().cummax())).min()`(`:190`)——**cumprod**
  - `get_normal_ic(a,b)`(`:243`)=`pearsonr(a,b)[0]`；`get_rank_ic(a,b)`(`:229`)=`spearmanr(a,b).correlation`——**整面板**相关（非按日 groupby，与 `calc_ic` 不等价）
  - `get_beta`(`:200`)、`get_alpha`(`:215`，默认 `risk_free_rate=0.03`)

### 8.5 contrib/report/ —— 调回 evaluate.py
- [未核实] `qlib/contrib/report/__init__.py:4-11` 注册图名 `analysis_position.{report_graph, score_ic_graph, cumulative_return_graph, risk_analysis_graph, rank_label_graph}` 与 `analysis_model.model_performance_graph`。
- [未核实] `analysis_position/score_ic.py`：`_get_score_ic`(`:10-22`) 按日 Pearson `label.corr(score)`(`:18`) 与 Spearman(`:19-21`)；`score_ic_graph`(`:25`)。**不调 evaluate.py**。
- [未核实] `analysis_position/risk_analysis.py`：`from ...evaluate import risk_analysis`(`:10`)——**调回 evaluate.py**。`_get_risk_analysis_data_with_report`(`:15`) 调 `risk_analysis(report["return"]-report["bench"])` 与 `...-report["cost"]`(`:35-37`)。`risk_analysis_graph`(`:162`) 画 `annualized_return`/`max_drawdown`/`information_ratio`/`std`。
- [未核实] `analysis_position/report.py`：`report_graph`(`:166`)。`_calculate_mdd`(`:25-32`)=`series-series.cummax()`（cumsum 上加性回撤，与 sum-mode `risk_analysis` 一致）。
- [未核实] `analysis_model/analysis_model_performance.py`：`model_performance_graph`(`:293`)。`_pred_ic`(`:119-220`) 按日 Pearson/Spearman IC(`:135-146`)；`_group_return`(`:21`)、`_pred_autocorr`(`:223`)、`_pred_turnover`(`:240`)。**内联重实现 IC，不 import `calc_ic`/`evaluate.risk_analysis`**。

### 8.6 workflow 层
- [未核实] `R` 模块级全局 `qlib/workflow/__init__.py:681` `R: QlibRecorderWrapper = RecorderWrapper()`（`RecorderWrapper` `:656`，守 re-init 时 `__init__.py:662-667`）。
- [未核实] `QlibRecorder` `qlib/workflow/__init__.py:26`，`ExpManager` facade(`:31-32`)。`qlib.init()` 从 `C["exp_manager"]` 建 ExpManager 并 `R.register(qr)`（`config.py:493-495`）。
- [未核实] `MLflowExpManager` `qlib/workflow/expm.py:317`，`mlflow.tracking.MlflowClient(tracking_uri=self.uri)`(`:326`)。
- [未核实] `MLflowRecorder` `qlib/workflow/recorder.py:247`：`start_run` `mlflow.set_tracking_uri`(`:337`)+`mlflow.start_run`(`:339`)；`save_objects` `client.log_artifact`(`:402-410`)；`load_object` download+pickle(`:432-434`)；`log_params`/`log_metrics`/`set_tags` 经 `AsyncCaller`(`:445-461`)；`end_run` `mlflow.end_run`(`:395`)；自动 log 未提交 git diff/status(`:362-378`) 与 `_QLIB_*` env(`:358`)。
- [未核实] tracking URI **可配非硬编码**：默认 `file:<cwd>/mlruns`（`MLflowSettings` `qlib/config.py:34-35`→`C["exp_manager"]["kwargs"]["uri"]` `:223`）；`ExpManager.default_uri` getter/setter(`expm.py:283-293`)；`R.set_uri`/`R.uri_context`(`__init__.py:361-390`)。
- [未核实] `RecordTemp`(`record_temp.py:28`)；`SignalRecord`(`:161`，`generate` `:190-206`，`pred=self.model.predict(self.dataset)`(`:192`)，存 `pred.pkl`(`:195`)、`label.pkl`(`:206`；`:171-188` 是 `generate_label` 辅助方法) [已推翻 → 见 fork-docs/ARCHITECTURE.md §1.5] ~~`label.pkl`(`:171-188`)~~（错因：子 agent 把 `generate_label` 辅助方法行号当 label.pkl 保存点，未区分方法边界）)；`SigAnaRecord`(`:295`，`artifact_path="sig_analysis"`，`depend_cls=SignalRecord`，`_generate` `:310-349` 调 `calc_ic`(`:323`) log IC/ICIR/Rank IC/Rank ICIR(`:324-329`)，可选 long-short ann return/sharpe `ann_scaler` 默认 **252**(`:304,335-338`))；`PortAnaRecord`(`:358`，`artifact_path="portfolio_analysis"`，`_generate` `:465-550`，替 `<PRED>` 占位(`:468-471`)、从 pred 推回测时间范围(`:473-484`) [已推翻 → 见 fork-docs/ARCHITECTURE.md §2.1] ~~`:474-484` 合并~~（错因：子 agent 把占位替换与时间范围推导两操作行号合并成一段）、`normal_backtest`(`:488-490`)，对每 `risk_analysis_freq` 算 `risk_analysis(report["return"]-report["bench"])`(超额无成本 `:507-509`) 与 `...-report["cost"]`(有成本 `:510-512`)，log 扁平 metrics(`:517`) 存 `port_analysis_<freq>.pkl`(`:519`)，`indicator_analysis`(`:531-549`)；默认 `TopkDropoutStrategy` topk=50 n_drop=5，benchmark `SH000300`(`:399-419`)——**A 股风味**)；`MultiPassPortAnaRecord`(`:575`，跑 `pass_num`(默认 10)次洗首日 score(`:617-633`)，聚合 `annualized_return`/`information_ratio` mean/std/mean_std(`:660-683`))。
- [未核实] `ModelRecorder` **不存在**（grep 无命中）。
- [未核实] `qrun` 不自己编排 RecordTemp；调 `task_train`(`run.py:147`)，`record:` 段驱动哪些 `RecordTemp.generate()` 跑。

### 8.7 口径冲突总览（fork 最要命）
- **[存疑] 三套年化常量并存**：`risk_analysis` 日频 `238`(`evaluate.py:52`)、`SigAnaRecord.ann_scaler` `252`(`record_temp.py:304`)、`evaluate_portfolio` `250`(`:138,154,173`)。
- **[已自核] docstring/实现冲突**：`evaluate.py:39` docstring 写 "day: 252"，`:52` 实现 `238`。
- **[未核实] ICIR 无 √N vs IR 有 √N**：`ICIR = ic.mean()/ic.std()` 无年化(`record_temp.py:326`)；`information_ratio = mean/std*sqrt(N)` 有年化(`evaluate.py:84`)。同名不同口径。
- **[未核实] max_drawdown 定义跨文件不一**：`evaluate.py` sum-mode `(cumsum-cumsum.cummax()).min()` 加性；`evaluate_portfolio.py` `((cumprod-cumprod.cummax())/cumprod.cummax()).min()` 乘性；`report.py:_calculate_mdd` `series-series.cummax()` 加性（与 sum-mode 一致）。
- **[未核实] `evaluate_portfolio.get_normal_ic`/`get_rank_ic` 整面板相关**(`:229,243`)，与 `calc_ic` 按日 groupby **不等价**。

### 8.8 FORK-SURFACE / 扩展点
- [未核实] 新 `RecordTemp`：子类 `RecordTemp`(`record_temp.py:28`) 或 `ACRecordTemp`(`:212`)，实现 `generate`/`_generate`，设 `artifact_path`+`depend_cls`。**无中央注册**——在 task/workflow config 的 `record` 列表声明或代码实例化。`ACRecordTemp` 给依赖检查+skip-existing。
- [未核实] 新 metric：加函数到 `qlib/contrib/evaluate.py`（或 `eva/alpha.py`）从 `RecordTemp._generate` 调，再 `self.recorder.log_metrics(...)`。`risk_analysis` 是组合风险指标的单一漏斗。
- [未核实] FORK-REQUIRED（硬编码/区域锁）：`risk_analysis` 日频 `238` 非 `252`(`evaluate.py:52`)，须改源用 252；`SigAnaRecord.ann_scaler` 默认 `252`(`record_temp.py:304`) 与 238 不一致；`evaluate_portfolio` 全用 `250`；`PortAnaRecord` 默认 benchmark `SH000300`（CSI300）+ 默认 exchange 成本(`:410-416`)——A 股假设，他区须 override；`MLflowSettings.uri` 默认 `file:<cwd>/mlruns`(`config.py:35`)。

---

## 9. 必动核心的位置（FORK_SURFACE 原料）

阶段 0(b) 四处"继承解决不了、必动核心"——独立成 `fork-docs/FORK_SURFACE.md` 的原料。每处保留判断与理由，不只结论。

### 9.1 parse_field —— 新词法语法必改
- **位置**：`qlib/utils/__init__.py:277-302`（[已自核]）。三条 `re.sub` + eval(`qlib/data/data.py:397` [未核实]）。
- **触发条件**：需要新**词法**（新前缀如 `#field`、`$close@5min`——后者 `:282-283` 已是 TODO 未实现）。加新**算子名**不需动此（custom_ops 即可）。
- **影响半径**：所有表达式解析入口经此。改了影响全部 field 串解析；`eval` 作用域（`data.py:397`、`cache.py:543`）也要同步。
- **rebase 风险**：[未核实] 须 `git log --oneline -- qlib/utils/__init__.py | head -20` 看上游改动频率——parse_field 是核心，估计改动不频繁但每次改动影响面大。
- **能否绕过**：加新算子名——能（custom_ops，不改源）；加新词法——不能，必须改 regex。**安全红线**：eval 字段串 = 可执行 Python，外部/模型生成的字段串不许直接喂 `D.features`。
- **理由**：parse_field 不是 parser，是 regex 重写 + Python `eval`。词法层无插件钩子。

### 9.2 T+1 引擎级缺钩子
- **位置**：`qlib/backtest/exchange.py`（[未核实] 整节）。`check_order`(`:417-419`)→`is_stock_tradable`(`:404-415`)→`_calc_trade_info_by_order` SELL 分支(`:894-917`) 仅 clip 到总持仓，不区分当日买入。
- **触发条件**：要 A 股 T+1 引擎级强制（而非策略层 `hold_thresh`）。
- **影响半径**：改 `deal_order`/`_calc_trade_info_by_order`/`check_order` 影响全部策略回测撮合。Exchange 不维护 per-share acquisition-time ledger——子类 override 须自建此状态。
- **rebase 风险**：[未核实] `git log --oneline -- qlib/backtest/exchange.py | head -20`。exchange.py 是高频改动区（cost/limit/quote），patch 冲突概率高。
- **能否绕过**：策略层 `hold_thresh` 近似（`signal_strategy.py:242`），代价是只对用该策略的路径生效；RL/WeightStrategy/rule_strategy 路径无 T+1。引擎级强制须改源或 Account 层包。
- **理由**：Exchange 设计上不跟踪持仓年龄，无扩展点；T+1 被下放到策略层。

### 9.3 三套年化口径（238/252/250）
- **位置**：`qlib/contrib/evaluate.py:52`（[已自核] `238`）、`qlib/workflow/record_temp.py:304`（[未核实] `252`）、`qlib/contrib/evaluate_portfolio.py:138,154,173`（[未核实] `250`）。
- **触发条件**：任何回测收益数字进结论/报告。
- **影响半径**：跨三个模块；改一处不动他处 → 同一报告里数字口径不一。
- **rebase 风险**：[未核实] evaluate.py/record_temp.py/evaluate_portfolio.py 改动频率。evaluate_portfolio 是遗留并行集，估计改动少。
- **能否绕过**：**文档记录差异，不改 upstream**（红线：不在 evaluate.py 顺手修正口径）。代价是须在 BACKTEST_SPEC 裁决表 + CLAUDE.md 红线写死"回测数字必须标是哪个函数算的"。
- **理由**：238/252/250 不报错，只让数字错配。ICIR 无 √N 而 portfolio IR 有 √N 放同一页是事故。

### 9.4 bin dtype 硬编码 float32 + 强制 cast
- **位置**：`qlib/data/storage/file_storage.py`（[未核实] 全程 `"<f"`）、`qlib/data/data.py:872`（[未核实] `LocalExpressionProvider.expression` 强制 cast float32，带 `# FIXME` `:868-870`）。
- **触发条件**：需要非 float 特征（int categorical 等）。
- **影响半径**：改 bin dtype 须同时改 `FileFeatureStorage` 读写与 `LocalExpressionProvider` cast，**只改一处不够**（`data.py:868-870` FIXME 承认）。
- **rebase 风险**：[未核实] file_storage.py / data.py 改动频率。
- **能否绕过**：dump_bin 已无 schema（§1.4 全列 dump），但读侧强 cast float32——非 float 数据须 fork 两处。
- **理由**：dtype 在写侧（file_storage）与读侧（data.py cast）双重硬编码，无单一配置开关。

### 9.5 补：缓存静默 stale（§3）也应进 FORK_SURFACE
- 虽非"必动核心"，但 fork 改算子实现时**最高危**。改 `_load_internal` 后须手动删 `<provider_uri>/<C.features_cache_dir_name>/` 或 `expression_cache=None` 重算。`qlib.init()` 不清磁盘（[已自核] `__init__.py:54-56`）。无版本/recompute flag（[未核实] 全链路核实）。FORK_SURFACE.md 应单列此条为"操作坑"而非"必动核心"。

---

## 10. 遗留待查清单（只登记，不现在查）

> 以下条目按阶段 1/2 需要时再核。登记在此防止失忆。

1. **[已核实 2026-07-15] PortAnaRecord / benchmark 不显式传 `mode`** —— grep `mode` over `qlib/workflow/record_temp.py` 仅 3 命中 `:166,168,192`，全在 `self.model`/`model.predict` 内，**无 `mode=` 形参**；grep `^\s*mode\s*:` over `examples/benchmarks/**` **0 命中**，无 yaml 注入 `mode`。故 `risk_analysis(report["return"]-report["bench"])` / `...-report["cost"]`(`record_temp.py:507-512` 行号待 BACKTEST_SPEC 复核) 走默认 `mode="sum"`(`evaluate.py:65-69` [已自核]) = 单利年化 `mean*N` + cumsum 回撤。**裁定**：我们的实际路径"默认单利"成立。`MultiPassPortAnaRecord`(`record_temp.py:575-683`) 聚合的 `annualized_return`/`information_ratio` mean/std 用哪个 mode 仍待核（BACKTEST_SPEC 落笔时核 `:660-683`）。

2. **[已核实 2026-07-15] `C.features_cache_dir_name` 默认 = `"features_cache"`** —— `qlib/config.py:177` `"features_cache_dir_name": "features_cache",`（[已自核]）。**非** `.cache`（缓存子 agent 误报）。失效路径落地为：删 `<provider_uri>/features_cache/<instrument>/<hash>` 或整树 `<provider_uri>/features_cache/`。磁盘 key = `hash_args(instrument, field, freq)`(`cache.py:502-505` [已自核])。

3. **`EnhancedIndexingOptimizer`（cvxpy）内部** —— `qlib/contrib/strategy/signal_strategy.py` 引 `EnhancedIndexingOptimizer`(`:504-513` [未核实])。BACKTEST_SPEC 若涉及组合优化/带约束的目标权重，须读其 cvxpy 问题构造（约束、目标函数、基准跟踪误差口径）。当前未读。

4. **`qlib/rl/` 链路** —— 按红线跳过（我们暂不用 RL）。仅登记：`qlib/rl/` 存在，`qlib/rl/data/integration.py:54` 用 `custom_ops=[DayLast, FFillNan, BFillNan, Date, Select, IsNull, IsInf, Cut, DayCumsum]`（[未核实]）。`qlib/strategy/base.py` 有 `RLStrategy`(`:240`)/`RLIntStrategy`(`:261` [未核实])。`pyproject.toml` 的 `rl` extra = `tianshou<=0.4.10, torch, numpy<2.0.0`（[未核实] `pyproject.toml:59-108`）。日后若启用须重读。

5. **[已推翻 → 见 fork-docs/DATA_SPEC.md §7] dump_bin.py 的复权"load 时用 $factor"** —— 原登记：§1.7 子 agent 推断 qlib 在 storage/expression 层用 `$factor` 事后复权，未给行号。**本轮已核实为误**：`file_storage.py`/`data.py`/`dump_bin.py` grep `adj|factor|adjust` 全 0 命中，qlib 读层从不复权；复权在 collector/CSV 源 + 用户表达式 `$close/$factor`。错因分类：**推断当事实**。详见 §11.1。

6. **[补充登记] `LocalExpressionProvider.expression` 的 `time2idx`/`FIXME`** —— §5.2 `data.py:855-856` `time2idx=False` 不扩张、`data.py:868-870` FIXME（dtype cast）。二者均 [未核实]，与 §9.4 dtype 问题相关，须同核。

7. **[补充登记] `task_train` 的 `auto_filter_kwargs`** —— §6.1 `:49` `auto_filter_kwargs(model.fit)` 丢 reweighter，[未核实] `auto_filter_kwargs` 的实现在哪（应在 `qlib/utils/`），丢弃是静默还是有 warn。Model 接口文档须澄清。

8. **[补充登记] `TSDatasetH` 的样本起点取数** —— §4.7 `TSDatasetH._prepare_seg`(`__init__.py:688-719`) 向后扩 `step_len` 取历史，与 §5 边界正确性强相关。factor-reviewer 清单第 2 条（rolling 窗口边界取数）依赖此。当前 [未核实]，须读 `TSDataSampler`(`__init__.py:424-446`) 与 `step_len` 语义。

9. **[补充登记] `Freq.NORM_FREQ_*` 常量** —— §8.1 `qlib/utils/time.py:115-118` 的 `NORM_FREQ_MINUTE/DAY/WEEK/MONTH`，影响 `risk_analysis` scaler 分支。[未核实]，BACKTEST_SPEC 涉及分钟/周频口径时须核。

10. **[已执行 2026-07-15 → 见 fork-docs/FORK_SURFACE.md §0.1]** rebase 频率未查 —— 原：§9 所有 FORK_SURFACE 项的 `git log --oneline -- <path> | head -20` 均未执行。**本轮已逐 path 跑完**（12 路径 commit 计数与近一次改动见 FORK_SURFACE.md §0.1）。此项非"被推翻结论"，仅由待查转为已执行。

---

## 11. 本轮纠正记录（2026-07-15）

> 逐条：原结论 → 正确结论 → 错因分类。错因分类是我们的错误模式画像。
> 凡 §11 条目，正文相应处已就地标 `[已推翻 → 见 docs/XXX.md]`。

1. **复权 load-time `$factor`**（原 §1.7:80-81 / §10.5）
   - 原结论：qlib 自身在 storage/expression 层用 `$factor` 字段做事后复权（load 时自动施加）。
   - 正确结论：qlib 读层（`file_storage.py`/`data.py`/`dump_bin.py`）grep `adj|factor|adjust` 全 0 命中——**读时从不复权**。复权在 collector 产出 CSV 时归一价格 + 写 `factor` 列；qlib 原样 dump/裸读，用户表达式 `$close/$factor` 取原始价（见 `docs/component/data.rst:55-56,195`、`fork-docs/DATA_SPEC.md` §7）。
   - 错因分类：**推断当事实**——子 agent 推断无行号支撑，上轮未 grep 核实 storage/expression 层就写成结论+[存疑]。

2. **TT_PARAL SELL-first**（原 §7.10:555）
   - 原结论：TT_PARAL 按 `-o.direction` 排序让 SELL 先（释放现金）。
   - 正确结论：`sorted(orders, key=lambda o: -o.direction)`，`Order.SELL=0`/`Order.BUY=1`（`qlib/backtest/decision.py:32-33`），`-direction` 升序 ⇒ **BUY-first**（`executor.py:583` 注释 "make the buying go first"；见 `fork-docs/ARCHITECTURE.md` §2.2）。
   - 错因分类：**子 agent 误读排序语义**——按"释放现金"直觉推断，未查 `Order.SELL/BUY` 常量值。

3. **TopkDropoutStrategy 路径缺 `contrib/`**（原 §7.10:552）
   - 原结论：`TopkDropoutStrategy` 在 `signal_strategy.py:75`。
   - 正确结论：在 `qlib/contrib/strategy/signal_strategy.py:75`（`qlib/strategy/signal_strategy.py` 不存在；见 `fork-docs/ARCHITECTURE.md` §2.4）。
   - 错因分类：**子 agent 路径误报**——未验证文件存在性，漏 `contrib/` 前缀。

4. **label.pkl 保存点**（原 §8.6:627）
   - 原结论：`label.pkl` 存于 `:171-188`。
   - 正确结论：存于 `:206`；`:171-188` 是 `generate_label` 辅助方法（见 `fork-docs/ARCHITECTURE.md` §1.5）。
   - 错因分类：**子 agent 未区分方法边界**——把辅助方法行号当保存点。

5. **`<PRED>` 占位行号**（原 §8.6:627）
   - 原结论：替 `<PRED>` 占位 + 推回测时间范围在 `:474-484`（合并）。
   - 正确结论：占位替换 `:468-471`，时间范围推导 `:473-484`（见 `fork-docs/ARCHITECTURE.md` §2.1）。
   - 错因分类：**子 agent 合并两操作行号**——占位与时间推导是不同操作。

6. **DumpDataUpdate freq 行号**（原 §1.8:84）
   - 原结论：`DumpDataUpdate.__init__` 重声明 `freq` 在 `:399`。
   - 正确结论：在 `:398`（见 `fork-docs/DATA_SPEC.md` §1.2）。
   - 错因分类：**子 agent 行号 off-by-one**——未开文件亲核。

7. **fname_to_code "仅剥 `_qlib_` 前缀"**（原 §1.2:48）
   - 原结论：`fname_to_code` 仅剥 `_qlib_` 前缀（前缀串）。
   - 正确结论：`str.lstrip(prefix)` 剥的是**字符集**（`_`,`q`,`l`,`i`,`b`）非字面前缀串；正常 symbol 等同剥前缀，边界 symbol 多剥（见 `fork-docs/DATA_SPEC.md` §1.7）。
   - 错因分类：**子 agent 误述 `lstrip` 行为**——把字符集剥离当字面串剥离。

**错误模式画像（汇总）**：本轮 7 条推翻中，6 条错因是**子 agent 报告未亲核**（路径误报 / 行号偏移 / 方法边界 / 操作合并 / `lstrip` 误述），1 条是**推断当事实**（复权）。教训：`[未核实]` 子 agent 的行号/路径/语义必须主 agent 抽样复核后再采信；`[存疑]` 推断不得写成结论。
