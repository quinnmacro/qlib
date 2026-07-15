---
name: qlib-data-ops
description: Use when operating qlib bin data — dumping CSV to bin, wiring a custom data source, or (most critically) ensuring a changed operator implementation actually re-runs instead of silently returning stale cached .bin. Also use when questions arise about qlib's read-time price-adjustment behavior or bin float32 dtype.
---

# qlib-data-ops

## 概述
qlib 数据层操作手册。本 skill 只给**操作步骤 + 命令 + 坑**；细节不复述，事实指向 `fork-docs/DATA_SPEC.md`（bin 格式 / dump 契约）与 `fork-docs/FORK_SURFACE.md §1`（缓存静默 stale）。

## 何时使用
- 改过算子 `_load_internal` 后跑因子，结果可疑 / 与预期不符 → 先怀疑 stale 缓存。
- 要把自有 CSV 灌成 qlib bin。
- 接自定义数据源（symbol 命名、calendar、复权）。
- 被问"qlib 读时复权吗 / bin 是什么 dtype"。

## 缓存失效 checklist（全项目最高危，不报错）
> 机制：`Expression.load` 内存 cache key = `str(self), instrument, start_index, end_index, *args`（`qlib/data/base.py:187`）；磁盘 key = `hash_args(instrument, field, freq)`（`qlib/data/cache.py:502-505`）。两者**都不含算子实现 hash / class 身份 / 版本**。`__str__` 纯结构（类名 + 子表达式 + 构造参数），改 `_load_internal` 体**不改 `__str__`** → key byte-identical → `.meta` 命中直接返旧 series，新代码根本不执行。详见 `fork-docs/FORK_SURFACE.md §1`。

改任何**复合算子**（`Mean`/`Std`/`Ref`/`Rank`/...，DSL 串捕获的；**非裸 `$close`**）`_load_internal` 后：

- [ ] 1. 停掉 qlib 进程。
- [ ] 2. 手动删磁盘缓存整树：`<provider_uri>/features_cache/`。若用了 dataset 缓存，再删 `<provider_uri>/<dataset_cache_dir_name>/`（默认目录名见 `qlib/config.py`）。
      - Windows / PowerShell：`Remove-Item -Recurse -Force <provider_uri>\features_cache`
      - POSIX：`rm -rf <provider_uri>/features_cache`
- [ ] 3. 或者（替代 2）：不开磁盘表达式缓存跑一遍重算，再开回来：
      `qlib.init(provider_uri=..., expression_cache=None, dataset_cache=None)` → 跑一次 → 再恢复 `expression_cache={"class":..., "module_path":...}`。
- [ ] 4. **`qlib.init()` 单独不够**——`qlib/__init__.py:54-56` 的 `clear_mem_cache` 只清内存 `H["f"]`，**不碰磁盘** `features_cache/`。重 init 仍命中 stale 磁盘。
- [ ] 5. 验证清掉：重跑后 `str(expr)` 不变但结果数值变了 → 清成功；若数值仍旧 → 缓存还在。
- [ ] 6. 裸 `$close` 改 load 只咬内存（`qlib.init` 清），不咬磁盘——但为安全**统一清**。

## dump CSV → bin
唯一事实来源 = `scripts/dump_bin.py`（`dump_all` / `dump_fix` / `dump_update` 三模式同源）。`scripts/get_data.py` 只下远端预构建 zip，**不是** CSV→bin 转换器。细节见 `fork-docs/DATA_SPEC.md`。

```bash
# 全量 dump（symbol 取自文件名，须按 symbol 拆分 CSV）
python scripts/dump_bin.py dump_all \
  --data_path <csv_dir> --qlib_dir <provider_uri> \
  --freq day --date_field_name date --file_suffix .csv \
  --include_fields "" --exclude_fields ""
# 单合并 CSV（所有 symbol 在一个文件、无分文件）→ 不能用 dump_all，改 dump_update（读 symbol 列）
```

坑（详见 `fork-docs/DATA_SPEC.md §9`）：
- 单合并 CSV **不能**走 `dump_all`（symbol 取自文件名 `dump_bin.py:281`）——用 `dump_update`（读 `symbol` 列 `:474`）或按 symbol 拆文件。
- **全列强 cast float32**（`:269`）——string/category 列静默成 NaN，用 `--exclude_fields` 排除。
- **symbol 文件名须能 `fname_to_code`/`code_to_fname` 往返**（`qlib/utils/__init__.py:905-936`）；Windows 保留名自动加/剥 `_qlib_` 前缀。
- **calendar 仅是 CSV 日期 union**（`:316`/`:330`）——不与外部交易日历合并。CSV 缺日不补、CSV 假日留。改 calendar 必重 dump（否则 `start_index` 头 4 字节错位）。
- **复权不在 qlib 读层**——`dump_bin.py` / `file_storage.py` / `data.py` grep `adj|factor|adjust` 全 0 命中（`fork-docs/DATA_SPEC.md §7`）。复权在 collector/CSV 源（写 `factor` 列）+ 表达式层 `$close / $factor`。qlib 读层裸读 `factor` 列不自动施加。

## 红线（摘自 `fork-docs/FORK_SURFACE.md §1.6` / `fork-docs/DATA_SPEC.md §7`）
- 改算子实现后未清 `features_cache` → 结果一律视为无效。
- qlib 读时不复权；复权是 CSV 数据源的责任，表达式层用 `$close/$factor` 取原始价。
- 非数值列进 bin 前必须 `--exclude_fields`，否则静默 NaN。

> 不要碰 `qlib/rl/`、MLflow 存储路径；不要顺手改 `evaluate.py` 年化口径。
