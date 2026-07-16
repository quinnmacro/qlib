# CLAUDE.md — qlib fork (因子挖掘 + 回测归因)

fork 自 microsoft/qlib，用途：**因子/Alpha 挖掘与评估、回测组合优化与风险归因**。本文件是四份事实文档的索引 + 红线提炼；细节不在本文件复述，去读对应文档。

## 本 fork 的改动面（相对 `upstream/main`）
相对 `microsoft/qlib` 的 `main`，本 fork **只有以下三处纯新增，零源码改动**：

```text
CLAUDE.md      # 本文件（索引 + 红线）
.claude/       # skills / agents / commands（脚手架，不改源码）
fork-docs/     # 架构 / fork 面 / 数据 / 回测口径 / 废弃研究笔记
```

- 随时自查改动面：`git diff upstream/main --stat`（应只见上述三处新增）。
- **任何对 `qlib/` `scripts/` `examples/` `docs/` `tests/` 的改动，动手前必须先在 `fork-docs/FORK_SURFACE.md` 登记**：触发条件 / 影响半径 / rebase 风险 / 能否子类化绕过。未登记不动手。

## 事实文档索引（按需读，勿通读）
| 文档 | 何时该看它 |
|---|---|
| `fork-docs/ARCHITECTURE.md` | 问"这块逻辑在哪/调谁"——两条链路函数级调用序列 + 扩展点表（算子/processor/model/handler/strategy/exchange 各自基类 file:line + 注册机制） |
| `fork-docs/DATA_SPEC.md` | 灌数据 / bin 格式 / dump 契约 / 复权 / float32——唯一事实源 `scripts/dump_bin.py` |
| `fork-docs/BACKTEST_SPEC.md` | 读任何回测数字前——口径裁决表（238/252/250 + 有无 √N）、risk_analysis 全函数体、回报三层 rtn/earning/return_rate |
| `fork-docs/FORK_SURFACE.md` | fork 改动前——改动面 + rebase 风险 + 操作坑，按危险度排序（§1 缓存 stale 最高危） |

> `fork-docs/_RESEARCH_NOTES.md` **已废弃，勿读**（被四份文档取代）。

## 目录地图（每包一行：何时该看它）
| 包 / 路径 | 何时该看它 |
|---|---|
| `qlib/cli/run.py` | CLI 入口 `workflow()`（`:86`） |
| `qlib/model/trainer.py` | task_train / _exe_task orchestration（`:108`/`:42`） |
| `qlib/data/dataset/handler.py` | DataHandlerLP.fit / processor 链 / 泄漏边界（`:513-540`,`:519`） |
| `qlib/data/dataset/processor.py` | processor 基类 + 状态 fit（`:35`,`:83`,`:196/228/262`） |
| `qlib/data/ops.py` | 内置算子 + 自定义四方法签名（`:54/57/60/93`） |
| `qlib/data/base.py` | Expression.load / cache key = str(self)（`:142`,`:187`） |
| `qlib/data/cache.py` | 磁盘表达式缓存 / stale 机制（`:502`,`:518`） |
| `qlib/data/data.py` | LocalExpressionProvider / parse_field→eval（`:843`,`:397`） |
| `qlib/utils/__init__.py` | parse_field（`:277-302`）/ init_instance_by_config / fname 往返 |
| `qlib/workflow/record_temp.py` | SigAnaRecord(IC/ICIR) / PortAnaRecord(回测+risk_analysis)（`:295`,`:358`,`:465`） |
| `qlib/contrib/evaluate.py` | risk_analysis / 238 / IR（`:26-93`,`:52`,`:84`） |
| `qlib/contrib/eva/alpha.py` | calc_ic / long-short（`:160-183`,`:71-113`） |
| `qlib/contrib/evaluate_portfolio.py` | legacy 弃用（250） |
| `qlib/backtest/` | backtest / executor / exchange（`__init__.py:217`,`executor.py:227`,`exchange.py:421`） |
| `qlib/contrib/strategy/signal_strategy.py` | TopkDropoutStrategy / T+1 策略层近似（`:75`,`:242`） |
| `scripts/dump_bin.py` | bin 产出唯一入口（`:541`） |

## 环境与常用命令（实测，2026-07）

**Python 必须 3.11，不能 3.13**——根因：`setup.py` 不调 `cythonize()`，靠 setuptools 自动转译 `.pyx`；py3.13 下 `Cython.Compiler.Main` 导入破裂 → setuptools `build_ext` 的 `try/except ImportError`（`setuptools/command/build_ext.py:26-34`）回退到 `distutils.command.build_ext` → `error: unknown file type '.pyx'`。`--no-build-isolation` + 装 Cython + legacy `setup.py build_ext` 三路全失败；切 3.11 一次装通。**别"再试一次 py3.13"白烧一小时。**

```bash
# 环境（conda-forge，无 Anaconda ToS）
conda create -n qlib --override-channels -c conda-forge python=3.11 -y
conda activate qlib   # 或直接用全路径 python: C:/Users/Q/miniconda3/envs/qlib/python.exe
pip install -e ".[dev]"
# 装完必核 import 指向工作区（装错则改动静默不生效，与 stale cache 同类静默失败）：
python -c "import qlib; print(qlib.__file__)"   # 必须输出 c:\Users\Q\Code\qlib\qlib\__init__.py
# 编译产物自检（存在才算 Cython 扩展装通）：
ls qlib/data/_libs/rolling.cp311-win_amd64.pyd qlib/data/_libs/expanding.cp311-win_amd64.pyd
# 跑 workflow 回测（mlflow 3.x 弃用 file-store，须放行）
MLFLOW_ALLOW_FILE_STORE=true qrun examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml
# 灌自有 CSV → bin（唯一入口；单合并 CSV 用 dump_update 非 dump_all）
python scripts/dump_bin.py dump_all --data_path <csv_dir> --qlib_dir <provider_uri> --freq day
# 程序内初始化（开发期建议关磁盘缓存避免 stale）
qlib.init(provider_uri="~/.qlib/qlib_data/cn_data", expression_cache=None)
```

**数据源**：官方数据集停用，用社区 `chenditc/investment_data`。Windows 下 curl 需 `--ssl-no-revoke`（Schannel 吊销检查 `CRYPT_E_REVOCATION_OFFLINE`，anaconda.com 链尤其触发；github.com 一般不触发）：

```bash
curl --ssl-no-revoke -L -o /tmp/qlib_bin.tar.gz https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz
mkdir -p ~/.qlib/qlib_data/cn_data && tar -xzf /tmp/qlib_bin.tar.gz -C ~/.qlib/qlib_data/cn_data --strip-components=1
python scripts/check_data_health.py check_data --qlib_dir ~/.qlib/qlib_data/cn_data
```
工具：本仓 `.claude/` 下有 skills（`qlib-data-ops`/`factor-research`/`backtest-analysis`）、agents（`qlib-explorer` 只读定位 / `factor-reviewer` 审查清单）、commands（`/new-factor`/`/run-backtest`）。

## 改造约定（各放哪 / 继承什么 / 在哪注册）
qlib 扩展靠**继承 + 配置引用**（非装饰器/钩子），统一漏斗 = `init_instance_by_config`（`qlib/utils/mod.py:122`），无中央注册表（除算子）。

| 扩展 | 继承（file:line） | 放哪 / 注册 |
|---|---|---|
| **自定义算子** | `ExpressionOps`（`qlib/data/base.py`） | 实现四方法 `_load_internal`/`get_extended_window_size`/`get_longest_back_rolling`/`__str__`（签名 `ops.py:54/57/60/93`）；`qlib.init(custom_ops=[Op])` 注册（`config.py:490` `register_all_ops`） |
| **processor** | `Processor`（`processor.py:35`） | 实现 `__call__`/`fit`/`is_for_infer`/`readonly`；在 handler 的 `shared/infer/learn_processors` 用 `{"class","module_path","kwargs"}` 引用（`handler.py:510`） |
| **data handler** | `DataHandlerLP`（`handler.py:382`） | override loader/processors/segments；放 `task["dataset"]` |
| **model** | `Model`（`qlib/model/base.py:22`）/`ModelFT` | 放 `task["model"]`；`_exe_task` `accept_types=Model` 实例化 |
| **strategy** | `BaseStrategy`（`qlib/strategy/base.py:23`） | 实现 `generate_trade_decision(execute_result)`；放 `PortAnaRecord.strategy_config` 或 `backtest(strategy=...)` |
| **exchange 行为** | `Exchange`（`exchange.py:28`） | 子类 override `deal_order`/`_calc_trade_info_by_order`/`check_order` 等；作 `exchange_kwargs` 传 |

fork 改动尽量**子类化/配置化**而非 inline patch（`handler.py`/`record_temp.py`/`exchange.py`/`file_storage.py` 是 rebase 冲突高发区，见 `fork-docs/FORK_SURFACE.md §0.1`）。

## 红线（不可越过）
1. **改算子实现后未清磁盘缓存一律视为结果无效**——**两个磁盘缓存同型 stale**：表达式缓存 `<provider_uri>/features_cache/`（key=`str(self)` `base.py:187` + 磁盘 `hash_args` `cache.py:502`）与数据集缓存 `<C.dataset_cache_dir_name>/`（key=`hash_args(instruments,fields,freq,disk_cache,inst_processors)` `cache.py:656`）**都不含算子实现 hash / processor 身份**，`__str__`/field 串不变 → 静默跑旧 bin。**唯一可靠修复 = 手动删两个缓存目录**。`qlib.init(expression_cache=None, dataset_cache=None)` 与 per-call `disk_cache=0`(`cache.py:699`) 都仅**旁路本次 session/调用**——`data.py:1320`/`:1326` 为 False → `Disk*Cache` 根本不实例化（不读不写、当场重算），**不删** stale bin；重启用即 `cache.py:518`/`:725` 命中旧 `.meta` 静默复用。**不等价于删文件**。注：数据集缓存存 `D.features` 结果（pre-processor，`loader.py:223`），processor 在 handler 内存跑（`handler.py:194`→`:519`）——**改 processor 不咬数据集缓存，但改算子 `_load_internal` 两个缓存都咬**。**（经验复现 2026-07，见 `fork-docs/FORK_SURFACE.md §1.7`）** stale 只在**显式 `expression_cache="DiskExpressionCache"` + redis 跑**时才咬——client 模式默认 cache OFF（`config.py:156`+client 块无 `expression_cache` 键），`DiskExpressionCache` 写锁依赖 redis（连不上则 `config.py:478` 带 WARNING 静默禁用），`DiskDatasetCache` 依赖 `pytables`（`cache.py:917`，`[client]` extra）。已用 `RollingZScore`+`SCALE` 5 阶段复现 stale+旁路≠清除（`V1=-1.2040842772` 在 SCALE=2 cache-on 下静默返回，不是 `2×V1`）。
2. **任何回测数字出现在结论里必须标注是哪个函数算的**——`risk_analysis` sum 模式 → 238 单利；`SigAnaRecord` long-short → 252；`evaluate_portfolio` → 250（弃用）。**ICIR（`record_temp.py:326`）无 √N，IR（`evaluate.py:84`）有 √N，同名不同口径，同页必须标注。**
3. **字段串经 `parse_field` → `eval()`（`data.py:397`）= 可执行 Python。外部/模型生成的字段串不许直接进 `D.features`。**
4. **自定义带状态 `fit()` 的 processor 必须显式设 `fit_start_time`/`fit_end_time`** 并在 `fit()` 里 `fetch_df_by_index(slice(...))` 切片（`processor.py:239/282/205`）——否则泄漏（`handler.py:519` 在全 raw `_data` 上调 fit）。截面 processor（CSZScoreNorm/CSRankNorm）例外。
5. **qlib 读时不复权，复权是 CSV 数据源的责任**——读层裸读 `factor` 列不自动施加；取原始价用 `$close/$factor`（`fork-docs/DATA_SPEC.md §7`）。**（经验复现 2026-07）** chinditc 社区数据为**后复权**（IPO 锚定）：`close[0]=1.0`（归一）、`adjclose[0]`=真实 IPO 价、`adjclose[-1]` 累计高于名义价；`$close/$factor`=名义价（10送10 split 上减半，已验 sh600005 7.52→3.80）；`$volume`=raw/factor（split 上不翻倍，守恒 turnover）。**任何依赖绝对价格水平或成交量绝对值的因子必须显式说明复权假设**（后复权下末日≠当时可见价，绝对阈值类因子会漂移）。
6. **不要向 `docs/` 写任何东西**——那是上游的 sphinx 文档树（`.readthedocs.yaml` 指向它，`make html` 构建它）。本 fork 的文档一律进 `fork-docs/`，保持 `docs/` 与 `upstream/main` 完全一致（`git diff upstream/main --stat -- docs/` 必须为空）。

## 不要碰
- `qlib/rl/`（强化学习子树，与因子/回测主线无关）。
- MLflow 存储路径 / recorder uri。
- **不要"顺手修正" `evaluate.py` 年化口径**（238→252）——上游 `c38e799c`(#1938) 口径仍在演进，改了 rebase 冲突；差异靠文档裁决 + fork 侧 wrapper（`fork-docs/BACKTEST_SPEC.md §5`）。
