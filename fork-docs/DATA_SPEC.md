# DATA_SPEC.md —— qlib bin 数据格式与 dump 契约（唯一事实来源 = `scripts/dump_bin.py`）

> 给"上下文被 clear 之后的我"看的 bin 数据格式操作手册。不是介绍文。
> 唯一事实来源：`scripts/dump_bin.py`（dump_all/dump_fix/dump_update 三模式同源）。
> 规则：每条可追溯 `路径:行号`。`[已自核]` = 本轮主 agent 亲开文件核对；`[已核实-子agent]` = 本轮派出的子 agent 亲读并逐字引用代码（主 agent 已抽样复核 spine，且 bin 布局经 `cache.py:583` 独立交叉确认）。

---

## 0. 谁产出 bin —— 唯一入口

- `[已核实-子agent]` `scripts/get_data.py:5,8` —— `from qlib.tests.data import GetData` / `fire.Fire(GetData)`。是薄壳。
- `[已核实-子agent]` `qlib/tests/data.py:44-70` `download`(`:56` `requests.get(url, stream=True, timeout=60)`)、`:72-109` `download_data`、`:119-131` `_unzip`。**GetData 只从远端 release URL 下载预构建 zip 并解压，不是 CSV→bin 转换器。**
- **结论**：`scripts/dump_bin.py` 是 bin 产出的**唯一事实来源**。get_data.py 拿到的远端数据集本身就是别人用 dump_bin（或等价流程）产出的。

CLI 入口 `[已核实-子agent]` `dump_bin.py:541-542` `fire.Fire({"dump_all": DumpDataAll, "dump_fix": DumpDataFix, "dump_update": DumpDataUpdate})`：
- `DumpDataAll` `:305`（全量 dump）
- `DumpDataFix` `:356`（`class DumpDataFix(DumpDataAll)`，修数据）
- `DumpDataUpdate` `:392`（`class DumpDataUpdate(DumpDataBase)`，增量 append）

基类 `DumpDataBase` `:68`（`__init__` 签名 `:68-81`，docstring `:82-108`，可执行体 `:109+`）。

---

## 1. 输入 CSV 契约

### 1.1 文件发现与读取
- `[已核实-子agent]` `dump_bin.py:118` `self.df_files = sorted(data_path.glob(f"*{self.file_suffix}") if data_path.is_dir() else [data_path])`——目录则 `glob *{file_suffix}`，单文件则直取。
- `[已核实-子agent]` `dump_bin.py:20-50` `read_as_df`；`:46` `pd.read_csv`（CSV 分支）/`:48` `pd.read_parquet`（parquet 分支）。
- `[已核实-子agent]` `dump_bin.py:169-174` `_get_source_data(file_path)`；`:170` `read_as_df(file_path, low_memory=False)`。

### 1.2 默认参数（`DumpDataBase.__init__` `[已自核]`）
| 参数 | 默认 | 行号 |
|---|---|---|
| `freq` | `"day"` | `:73` |
| `date_field_name` | `"date"` | `:75` |
| `file_suffix` | `".csv"` | `:76` |
| `symbol_field_name` | `"symbol"` | `:77` |
| `exclude_fields` | `""` | `:78` |
| `include_fields` | `""` | `:79` |
| `max_workers` | `16` | `:74` |

`DumpDataUpdate.__init__` 重声明 `freq: str = "day"` 在 `:398`（`[已核实-子agent]`，注意非 `:399`）。

### 1.3 date_field_name 必须存在
`[已核实-子agent]` `dump_bin.py:172` `df[self.date_field_name] = pd.to_datetime(df[self.date_field_name])`——`pd.to_datetime` 灵活解析，但列必须存在，否则 KeyError。

### 1.4 symbol 来源 —— 关键坑
- `[已核实-子agent]` `DumpDataAll` 的 symbol 取自**文件名**：`dump_bin.py:281` `code = self.get_symbol_from_file(file_or_data)`；`get_symbol_from_file` 定义 `:176-177` `return fname_to_code(file_path.stem.strip().lower())`。**不是 CSV 列。**
- `[已核实-子agent]` `dump_bin.py:462-485` `DumpDataUpdate._load_all_source_data`；`:473-474` `if self.symbol_field_name not in _df.columns: _df[self.symbol_field_name] = self.get_symbol_from_file(file_path)`——UPDATE 模式读 `symbol` 列，缺失时从文件名合成。
- `[已核实-子agent]` 单个合并 CSV（所有 symbol、无分文件）**不能走 `dump_all`**——改用 `dump_update`（读 `symbol` 列）或按 symbol 拆文件。

### 1.5 dump 字段集（无固定 OHLCV schema）`[已核实-子agent]`
`dump_bin.py:179-184` `get_dump_fields`：
```python
self._include_fields if self._include_fields else set(df_columns) - set(self._exclude_fields) if self._exclude_fields else df_columns
```
- 有 `include_fields` → 用之；
- elif `exclude_fields` → 全列减 exclude；
- else → **全列**。

**无固定 OHLCV schema——CSV 有什么数值列就 dump 什么列。** 非数值/string/category 列在 `:269` 被强 cast float32 → 静默成 NaN。须用 `--exclude_fields` 排除。

### 1.6 日期格式
- `[已核实-子agent]` 读时 `:172` `pd.to_datetime` 灵活解析。
- `[已自核]` 输出 calendar 格式常量 `:60` `DAILY_FORMAT = "%Y-%m-%d"`、`:61` `HIGH_FREQ_FORMAT = "%Y-%m-%d %H:%M:%S"`；`:127` `self.calendar_format = self.DAILY_FORMAT if self.freq == "day" else self.HIGH_FREQ_FORMAT`；`:146` 应用 `datetime_d.strftime(self.calendar_format)`。

### 1.7 symbol 文件名往返
- `[已核实-子agent]` `fname_to_code` 在 `qlib/utils/__init__.py:925-936`：`prefix = "_qlib_"`，`:935` `fname = fname.lstrip(prefix)`。
  - **caveat**：`lstrip(prefix)` 剥的是**字符集**（`_`,`q`,`l`,`i`,`b`）而非字面前缀串。对正常 symbol 行为等同"剥 `_qlib_` 前缀"；对以这些字符开头的异常 symbol 会多剥。
- `[已核实-子agent]` `code_to_fname`（逆）`qlib/utils/__init__.py:898-922` 对 Windows 保留名（CON/PRN/AUX/NUL/COMn/LPTn）加 `_qlib_` 前缀。
- `[已核实-子agent]` instruments 文件大写：`dump_bin.py:221` `lambda x: fname_to_code(x.lower()).upper()`。
- symbol 须能经 `fname_to_code`/`code_to_fname` 往返。

### 1.8 输入排序不要求
`[已自核]` `dump_bin.py:290` `df = df.drop_duplicates(self.date_field_name)`（防 reindex 异常）；对齐靠 `:253` `data_merge_calendar` reindex 到 calendar 切片（`:238` `r_df = df.reindex(cal_df.index)`，`cal_df` 是 `[df[date].min(), df[date].max()]` 切片）。

---

## 2. 目录常量 `[已自核]`

`dump_bin.py:55-66`：
| 常量 | 值 | 行号 |
|---|---|---|
| `INSTRUMENTS_START_FIELD` | `"start_datetime"` | `:54` |
| `INSTRUMENTS_END_FIELD` | `"end_datetime"` | `:55` |
| `CALENDARS_DIR_NAME` | `"calendars"` | `:56` |
| `FEATURES_DIR_NAME` | `"features"` | `:57` |
| `INSTRUMENTS_DIR_NAME` | `"instruments"` | `:58` |
| `DUMP_FILE_SUFFIX` | `".bin"` | `:59` |
| `DAILY_FORMAT` / `HIGH_FREQ_FORMAT` | `"%Y-%m-%d"` / `"%Y-%m-%d %H:%M:%S"` | `:60-61` |
| `INSTRUMENTS_SEP` | `"\t"` | `:62` |
| `INSTRUMENTS_FILE_NAME` | `"all.txt"` | `:63` |
| `UPDATE_MODE` / `ALL_MODE` | `"update"` / `"all"` | `:65-66` |

---

## 3. calendar 生成 `calendars/<freq>.txt`

- `[已核实-子agent]` `dump_bin.py:306-326` `DumpDataAll._get_all_date`：`:308` `all_datetime = set()`；`:310` `_fun = partial(self._get_date, as_set=True, is_begin_end=True)` 跑 `self.df_files`；`:316` `all_datetime = all_datetime | _set_calendars`（逐文件 union）；`:317-322` 逐文件收 begin/end/instrument 行。
- `[已核实-子agent]` `dump_bin.py:328-332` `_dump_calendars`：`:330` `self._calendars_list = sorted(map(pd.Timestamp, self._kwargs["all_datetime_set"]))`。
- `[已核实-子agent]` `dump_bin.py:208-212` `save_calendars`：`:210` `calendars_path = str(self._calendars_dir.joinpath(f"{self.freq}.txt").expanduser().resolve())`；`:212` `np.savetxt(calendars_path, result_calendars_list, fmt="%s", encoding="utf-8")`——每行一个日期。

**[已核实-子agent] 重要**：calendar 是 **CSV 日期的 union**，`dump_bin.py` 此路径**无** `read_calendar`、无外部 `.txt`、无 `DataCalendar`/exchange-calendar import。**不与外部交易日历合并**。后果：CSV 缺的上市日不进 calendar；CSV 里的假期留在 calendar。

更新路径 `DumpDataUpdate`：`[已自核]` 扩展 >旧末的日期并重存——DATA_SPEC 落笔前如需增量语义须再读 `dump_bin.py:458-538`。

---

## 4. instruments 生成 `instruments/all.txt`

- `[已自核]` **文件名恒为 `all.txt`**（`INSTRUMENTS_FILE_NAME="all.txt"`，`:63`）——**dump 时不分 market**，单文件存全部 symbol。
- `[已核实-子agent]` `dump_bin.py:161-163` `_get_date(..., is_begin_end=True)` 返 `(df[date].min(), df[date].max())`（在 `_get_date` `:148-167` 内；`:162-163` `elif is_begin_end: return _calendars.min(), _calendars.max()`）。
- `[已核实-子agent]` `dump_bin.py:214-225` `save_instruments`：`:218-219` 列 `[symbol_field_name, INSTRUMENTS_START_FIELD, INSTRUMENTS_END_FIELD]` = `symbol\tstart_datetime\tend_datetime`；`:221` symbol 经 `fname_to_code(x.lower()).upper()`；`:223` `to_csv(header=False, sep=self.INSTRUMENTS_SEP, index=False)`——**TSV 三列无表头**。
- `[已自核]` `DumpDataFix._dump_instruments`(`dump_bin.py:357-378`) 合并新 symbol 进既有 `all.txt`；`DumpDataUpdate.dump`(`:533-538`) 重写。

---

## 5. bin 写入 `features/<symbol>/<field>.<freq>.bin` —— spine `[已自核]`

### 5.1 路径布局
- `[已自核]` `dump_bin.py:293` `features_dir = self._features_dir.joinpath(code_to_fname(code).lower())` → `features/<code_to_fname(code).lower()>`。
- `[已自核]` `dump_bin.py:260` `bin_path = features_dir.joinpath(f"{field.lower()}.{self.freq}{self.DUMP_FILE_SUFFIX}")` → `{field.lower()}.{freq}.bin`。`DUMP_FILE_SUFFIX=".bin"`(`:59`)。例：`features/sh600000/close.day.bin`。

### 5.2 数据对齐（reindex 到 calendar 切片）
`[已自核]` `dump_bin.py:245-269` `_data_to_bin`：
- `:253` `_df = self.data_merge_calendar(df, calendar_list)`——reindex 到 `[df[date].min(), df[date].max()]` 的 calendar 切片（`data_merge_calendar :227-239`，`:238` `r_df = df.reindex(cal_df.index)`）。
- `:258` `date_index = self.get_datetime_index(_df, calendar_list)`。
- `:241-243` `get_datetime_index` `return calendar_list.index(df.index.min())`——**start_index = 该 symbol 首日在整个 calendar 中的位置索引**。

### 5.3 ALL_MODE 写（全量）
`[已自核]` `dump_bin.py:269`：
```python
np.hstack([date_index, _df[field]]).astype("<f").tofile(str(bin_path.resolve()))
```
- **头 4 字节 = `date_index` cast 成 float32**（little-endian），后接数值列 cast float32。
- dtype `"<f"` = little-endian float32（`:269`、`:266`）。
- `_df[field]` 无条件 cast float32——非数值/NaN 多的列静默成 NaN float。

### 5.4 UPDATE_MODE 写（append）
`[已自核]` `dump_bin.py:263-266`：
```python
if bin_path.exists() and self._mode == self.UPDATE_MODE:
    with bin_path.open("ab") as fp:
        np.array(_df[field]).astype("<f").tofile(fp)
```
- `"ab"` 打开，**只 append 数值不写头**，依赖既有 4 字节 header（先 ALL_MODE 写过）。
- 无 `date_index`——追加段对齐靠 calendar 位置增量。

### 5.5 bin 布局的独立交叉确认
`[已自核]` `qlib/data/cache.py:583` `DiskExpressionCache.gen_expression_cache` 用**同一布局**写表达式缓存：
```python
r = np.hstack([df.index[0], expression_data]).astype("<f")
r.tofile(str(cache_path))
```
`df.index[0]` = calendar 起始索引，对应 dump_bin 的 `date_index`。dump 与 cache 写法一致——读侧 `read_bin` 按此布局解。

---

## 6. `$` 前缀在哪一层

- `[已自核]` `$` 是**读取层 / 表达式引擎**约定，**不在 dump 层**。
- `[已核实-子agent]` dump 时文件名**无 `$`**：`dump_bin.py:260` f-string `f"{field.lower()}.{self.freq}{self.DUMP_FILE_SUFFIX}"`——`close.day.bin`、`volume.day.bin`。
- `[已自核-上轮]` `qlib/data/base.py:250-251` `Feature.__str__` 返 `"$" + self._name`；`:267-268` `PFeature.__str__` 返 `"$$" + self._name`。`$close` 在 load 时解析成 bin 文件里名为 `close` 的字段。

---

## 7. 复权（adjustment）—— 决议：qlib 从不在 dump/load 施加复权 `[已核实-子agent]`

> 上一轮 §1.7/§10.5 的子 agent 推断"qlib 在 load 时用 `$factor` 复权"**无行号支撑，本轮核实为误**。

- `[已核实-子agent]` `scripts/dump_bin.py` grep `adj|factor|adjust|forward|backward` → **0 命中**。dump_bin 从不应用前/后复权，从不引用 `adjfactor`/`factor` 列。CSV 有什么数值列就原样写。
- `[已核实-子agent]` `qlib/data/storage/file_storage.py` grep `adj|factor|adjust` → **0 命中**。`FileFeatureStorage.__getitem__`(`:346-375`) 经 `:372` `np.frombuffer` 读裸 `<f` float32 字节返 `pd.Series`，**无乘因子、无 factor 查找、无 adj 应用**。`FileFeatureStorage.write`(`:299-329`) 同样写裸值。唯一 "index" 概念是 calendar start-index header(`:332-337`)，非复权因子。
- `[已核实-子agent]` `qlib/data/data.py` grep `adj|factor|adjust` → **0 命中**。

**结论**：qlib 的 storage/读路径把 `.bin` 特征值当不透明裸 float，**读时绝不施加任何价格复权**（dump_bin/file_storage/data.py grep `adj|factor|adjust` 全 0 命中）。复权语义见官方 `docs/component/data.rst:55-56,195`：`factor = adjusted_price / original_price`，qlib 在 **collector 产出 CSV** 时将价格归一（首交易日归 1）并写 `factor` 列；`dump_bin.py` 原样 dump 该列（§1.5 全数值列 dump），读层裸读为 `$factor`。**用户在表达式层显式写 `$close / $factor` 取原始价**（`original = adjusted / factor`；~~`$close * $factor`~~ 方向错）。qlib 读层不自动施加复权——推翻上轮"load 时用 `$factor` 事后复权"推断（见 `_RESEARCH_NOTES.md` §11.1）。

### 7.1 chinditc 社区数据复权实证 `[已经验复现]` 2026-07（6118 symbols，numpy 直读 bin）

对 chinditc/investment_data 社区数据（`~/.qlib/qlib_data/cn_data`）逐字段实证，确认 §7 的读层结论 + 补全字段语义：

- **`close` = 后复权相对价，IPO 归 1**：`close[0] = 1.0` 对**全部 6118 只**股票成立（p1=p99=1.0）——即首交易日锚定（后复权）。`close[-1]` median 1.36（相对数，非真实价）。
- **`adjclose` = 后复权绝对价**：`adjclose[0]` median 25.07 = 真实 IPO 价（4.5–294 yuan 区间，合理）；`adjclose[-1]` p99=1375 = 累计复权远超名义价（长上市+分红的backward累积）。`adjclose = close × adjclose[0]`。
- **后复权（非前复权）决定性判据**：`close[0]=1.0`（首日锚定）；`factor[-1]` 全样本**无一是 1.0**（median 0.125，min 0.001，max 49.18）→ 最新日非锚定 → **后复权**。前复权会是 `close[-1]` 归 1 / `factor[-1]=1.0`，均不成立。
- **`factor` = close/nominal = adjusted/original**：10送10 split 上 `factor` 翻倍（sh600005 2004-10-18：0.3094→0.6186）。`$close/$factor` = 名义价（§7 结论确认）——sh600005 split 前后 7.52→3.80（减半，名义价应有的 split 行为），而 `close`/`adjclose` 均连续不减半（后复权应有的连续行为）。
- **`$volume` = raw_volume / factor（非原始量，非 ×factor）**：10送10 split 上 `volume` 不翻倍（sh600005 509857→194615，非 2×；aggregate 11284 个 split 日 median vo_r=0.86，远非 2.0）。决定性证据：`volume × factor` 恢复 raw（split 上 ~2×，509857×0.3094=157757 → 1051646×0.619=650962，share-count 翻倍），`volume / factor` 连续。即 `volume = raw_volume / factor`（向下调，守恒 turnover = adjclose × volume = nominal_price × raw_volume）。

**因子研究后果**：后复权下，**最新日 `adjclose` ≠ 当时可见名义价**（累计高于名义），历史 `adjclose` 对早期≈名义（少 corp action）。任何依赖**绝对价格水平**（价格阈值筛选）或**成交量绝对值**的因子，须显式说明复权假设——绝对阈值会在后复权尺度上随时间漂移。`exchange.py` 的 `$change ±0.095` 涨跌停用后复权 `close`（连续，split 不误触 0.095）——正确；`trade_w_adj_price` 同理。复现脚本 `.claude/ops/scan_adjust.py`、`scan_window.py`。

---

## 8. freq 与变体

- `[已自核]` `dump_bin.py:73` `freq: str = "day"` 默认。
- `[已核实-子agent]` `DumpDataUpdate.__init__` 重声明 `freq: str = "day"` 在 `:398`。
- `[已自核]` **无 `dump_baostock`**。baostock/yahoo 是独立 **collector**（下载器，产出 CSV，不是 bin dumper）：`scripts/data_collector/baostock_5min/collector.py:273`、`scripts/data_collector/yahoo/collector.py:755`。

---

## 9. 自定义数据源会踩的坑（操作清单）

1. **单合并 CSV 不能走 `dump_all`**（symbol 取自文件名 `:281`）——改用 `dump_update`（读 `symbol` 列 `:474`）或按 symbol 拆文件。
2. **全列强 cast float32**（`:269`）——string/category 列成 NaN，用 `--exclude_fields` 排除。
3. **symbol 文件名须能 `fname_to_code`/`code_to_fname` 往返**（`qlib/utils/__init__.py:905-936`）。Windows 保留名自动加/剥 `_qlib_` 前缀；注意 `lstrip` 剥的是字符集非字面前缀（§1.7 caveat）。
4. **calendar 仅是 CSV 日期 union**（`:316`/`:330`）——无外部交易日历合并。CSV 缺日不补、CSV 假日留。
5. **`start_index`（头 4 字节）= symbol 首日 calendar 位置**（`:243`/`:269`）。dump 与 load 间 calendar 不一致 → 每个值错位。改 calendar 必重 dump。
6. **复权在 collector/CSV 源与表达式层，不在 qlib 读层**（§7）——读层裸读 `factor` 列不自动施加；要复权须 CSV 含 `factor` 列 + 表达式 `$close/$factor`。
7. **bin 跨 `[min,max]` 切片**（`:227-239` reindex）——bin 只覆盖该 symbol 首末日区间，不跨全 calendar。
