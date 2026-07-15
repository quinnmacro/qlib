# BACKTEST_SPEC.md —— 回测指标口径裁决与撮合成本口径

> 给"上下文被 clear 之后的我"看的回测指标口径操作手册。不是介绍文。
> 规则：每条可追溯 `路径:行号`。`[已自核]` = 主 agent 亲开文件核对；`[已核实-子agent]` = 本轮子 agent 亲读逐字引用。
> **核心红线**：qlib 存在三套年化常量（238/252/250）与两种 IR 口径（有/无 √N），都不报错，只让数字错配。任何回测收益数字进结论前必须先查本文件裁决表。

---

## 0. 口径裁决表（我们采信的口径）

| 指标 | 实现位置 | 实际公式（逐字） | scaler | 我们采信的口径 |
|---|---|---|---|---|
| **annualized_return（组合，sum 模式）** | `qlib/contrib/evaluate.py:68` `[已自核]` | `mean * N`（`mean=r.mean()` `:66`） | `N=238`（日频，`:52`） | **采信**。`PortAnaRecord` 不传 `mode=`（`record_temp.py:507-512` `[已核实-子agent]`）→ 默认 `mode="sum"` → 单利年化 `mean*238`。**注意是单利不是复利。** |
| **max_drawdown（组合，sum 模式）** | `evaluate.py:69` `[已自核]` | `(r.cumsum() - r.cumsum().cummax()).min()` | — | **采信**。**算术累计 cumsum 上的加性回撤**（非 cumprod）。 |
| **information_ratio（组合）** | `evaluate.py:84` `[已自核]` | `mean / std * np.sqrt(N)` | `N=238`（日频） | **采信**。超额收益 IR：`PortAnaRecord` 传 `return-bench[-cost]`（`:507-512`）。**有 √N 年化。** |
| **std（组合）** | `evaluate.py:67` `[已自核]` | `r.std(ddof=1)` | — | 采信。sum 模式下 std 是日收益标准差（未年化）。 |
| **IC（Pearson，信号）** | `qlib/contrib/eva/alpha.py:178` `[已核实-子agent]` | `df.groupby(date_col, group_keys=False).apply(lambda df: df["pred"].corr(df["label"]))` | — | 采信。**按日截面** Pearson，返每日 IC Series。 |
| **Rank IC（Spearman，信号）** | `alpha.py:179` `[已核实-子agent]` | `df.groupby(date_col, group_keys=False).apply(lambda df: df["pred"].corr(df["label"], method="spearman"))` | — | 采信。按日截面 Spearman。 |
| **ICIR（信号）** | `qlib/workflow/record_temp.py:326` `[已核实-子agent]` | `ic.mean() / ic.std()` | **无 √N，不年化** | 采信但**标注**：`ICIR` 无年化，与组合 `information_ratio`（有 √N）**同名不同口径**，禁止同页不标。 |
| **Rank ICIR（信号）** | `record_temp.py:328` `[已核实-子agent]` | `ric.mean() / ric.std()` | 无 √N | 同上。 |
| **Long-Short Ann Return** | `record_temp.py:335` `[已核实-子agent]` | `long_short_r.mean() * self.ann_scaler` | `ann_scaler=252`（`:304`） | 采信但**标注**：用 **252**，与组合年化用 **238** 不一致。 |
| **Long-Short Ann Sharpe** | `record_temp.py:336` `[已核实-子agent]` | `long_short_r.mean() / long_short_r.std() * self.ann_scaler**0.5` | `252`（√252） | 采信但标注（252 vs 238）。 |
| **long_short_r 构造** | `alpha.py:71-113` `[已核实-子agent]` | `r_long=nlargest(N(x),columns="pred").label.mean()`(`:110`)、`r_short=nsmallest(...)`(`:111`)、`((r_long-r_short)/2, r_avg)`(`:113`)；`quantile=0.2`(`:75,:107-108`) | — | 采信。`N(x)=int(len(x)*0.2)`。 |
| ~~annualized_return（evaluate_portfolio）~~ | `qlib/contrib/evaluate_portfolio.py:138` `[已核实-子agent]` | `pow(p_end/p_start, 250/n_period)-1` | **250** | **不采信**。legacy 并行集，250 硬编码。除非显式从 position dict 算指标，否则不用。 |
| ~~sharpe（evaluate_portfolio）~~ | `evaluate_portfolio.py:173` `[已核实-子agent]` | `(annual-risk_free_rate)/std/np.sqrt(250)` | **250** | 不采信。 |
| ~~max_drawdown（evaluate_portfolio）~~ | `evaluate_portfolio.py:190` `[已核实-子agent]` | `(((1+r).cumprod()-(1+r).cumprod().cummax())/((1+r).cumprod().cummax())).min()` | — | 不采信。cumprod 乘性回撤，与 sum 模式加性不同。 |
| ~~get_normal_ic / get_rank_ic~~ | `evaluate_portfolio.py:244/240` `[已核实-子agent]` | `pearsonr(a,b)[0]` / `spearmanr(a,b).correlation` | — | **不采信**。**整面板**单相关，与 `calc_ic` 按日 groupby **不等价**。 |

**汇总 scaler 一致性**：
- 组合风险指标（annualized_return / IR）→ **238**（`evaluate.py:52`）。
- 信号 long-short 年化 → **252**（`record_temp.py:304`）。
- legacy evaluate_portfolio → **250**（弃用）。
- **同一报告里 238 与 252 共存是默认状态**——读数字前先查来源函数。

---

## 1. risk_analysis 全函数体 `[已自核]`（`qlib/contrib/evaluate.py:26-93`）

- `:26` `def risk_analysis(r, N: int = None, freq: str = "day", mode: Literal["sum", "product"] = "sum"):`。
- `:28-32` docstring："The calculation of annualized return is different from the definition... It is implemented by design. Qlib tries to cumulate returns by summation instead of production to avoid the cumulated curve being skewed exponentially."
- `:39` docstring 参数 N 写 **"day: 252, week: 50, month: 12"**——**与实现 `:52` 的 238 打架**。docstring 过时，**以 238 为准**。
- `:48-56` `cal_risk_analysis_scaler(freq)`，dict `:50-55`：
  - minute `Freq.NORM_FREQ_MINUTE: 240*238`(`:51`)
  - **day `Freq.NORM_FREQ_DAY: 238`**(`:52`)
  - week `Freq.NORM_FREQ_WEEK: 50`(`:53`)
  - month `Freq.NORM_FREQ_MONTH: 12`(`:54`)
  - 除以 `_count`（如 "5min"）。
- `:58-63` `N is None and freq is None` raise；两者皆给 warn ignore freq；`:62-63` `N = cal_risk_analysis_scaler(freq)`。

### 1.1 sum 模式（默认）`:65-69`
```
mean = r.mean()
std = r.std(ddof=1)
annualized_return = mean * N              # 单利年化
max_drawdown = (r.cumsum() - r.cumsum().cummax()).min()   # 加性回撤
```

### 1.2 product 模式 `:70-80`
```
cumulative_curve = (1 + r).cumprod()
mean = cumulative_curve.iloc[-1] ** (1 / len(r)) - 1     # 几何均值/CAGR
std = np.log(1 + r).std(ddof=1)
cumulative_return = cumulative_curve.iloc[-1] - 1
annualized_return = (1 + cumulative_return) ** (N / len(r)) - 1
max_drawdown = (cumulative_curve / cumulative_curve.cummax() - 1).min()   # 乘性回撤
```

> **mode=product 登记（公式已核、未启用）** `[已自核]`：上式逐行亲核 `evaluate.py:70-80`，公式准确。**全链路无 caller 传 `mode=product`**（§2.1 grep 0 命中；`PortAnaRecord` 默认 sum）——当前采信口径全走 sum。若 fork 改用 product：年化 = CAGR `(1+cum_ret)**(N/len(r))-1`（N=238 日频），**非** sum 的 `mean*238` 单利；`max_drawdown` 改乘性。须显式传 `mode="product"`。

### 1.3 IR `:84`
```
information_ratio = mean / std * np.sqrt(N)
```
用当前 mode 的 mean/std。默认 sum 模式即 `(r.mean()/r.std(ddof=1))*sqrt(238)` 日频。

### 1.4 `:81-82` else raise。

---

## 2. PortAnaRecord 实际调用 —— 默认 sum 模式 `[已核实-子agent]`

`qlib/workflow/record_temp.py` `PortAnaRecord._generate`(`:465-550`)：
- `:468-471` 替 `<PRED>` 占位：`placeholder_value = {"<PRED>": pred}`，对 `executor_config`/`strategy_config` 调 `fill_placeholder`。
- `:473-484` 从 pred 推回测时间范围（`dt_values` `:474`、`start_time` `:475-476`、`end_time` `:477-478`）。
- `:488-490` `portfolio_metric_dict, indicator_dict = normal_backtest(executor=..., strategy=..., **self.backtest_config)`。
- `:507-509`：
  ```
  analysis["excess_return_without_cost"] = risk_analysis(
      report_normal["return"] - report_normal["bench"], freq=_analysis_freq
  )
  ```
- `:510-512`：
  ```
  analysis["excess_return_with_cost"] = risk_analysis(
      report_normal["return"] - report_normal["bench"] - report_normal["cost"], freq=_analysis_freq
  )
  ```
**两次 `risk_analysis` 调用只传位置参 `r` 与 `freq=_analysis_freq`，无 `mode=`** → 默认 `mode="sum"`。超额收益 = `return - bench`（无成本）或 `return - bench - cost`（有成本）。

- `:517` `self.recorder.log_metrics(**{f"{_analysis_freq}.{k}": v ...})` 扁平 log。
- `:519` 存 `port_analysis_<freq>.pkl`。
- `:531-549` `indicator_analysis` 循环。
- `:399-419` 默认 config：`:402` `"class": "TopkDropoutStrategy"`、`:404` `"kwargs": {"signal":"<PRED>","topk":50,"n_drop":5}`、`:410` `"benchmark": "SH000300"`——A 股风味（CSI300 基准 + 默认 exchange 成本）。

### 2.1 benchmark yaml 不注入 mode
`[已自核]` grep `^\s*mode\s*:` over `examples/benchmarks/**` → **0 命中**。`record_temp.py` grep `mode` 仅命中 `self.model`(`:166,168,192`)。**全链路无 `mode=product`**——我们采信 sum 模式成立。

### 2.2 MultiPassPortAnaRecord `[已核实-子agent]`
`record_temp.py:575` `class MultiPassPortAnaRecord(PortAnaRecord)`：
- `:594` `pass_num=10` 默认；`:594` `shuffle_init_score=True`。
- `:617-633` `random_init`：`:628` `first_date_score = pred_df.loc[first_bt_pred_date]["score"]`、`:629` `np.random.shuffle(first_date_score.values)`、`:633` 赋回 `strategy_config["kwargs"]["signal"]`。
- `:660-664` 聚合：`groupby(level=[0,1]).apply(lambda x: pd.Series({"mean":x["risk"].mean(),"std":x["risk"].std(),"mean_std":x["risk"].mean()/x["risk"].std()}))`。
- `:667-669` 过滤到 `["annualized_return","information_ratio"]` 两指标。
- `:676-683` `flatten_dict` log mean/std/mean_std。
- **每 pass 的 `annualized_return`/`information_ratio` 来自 `port_analysis_<freq>.pkl`，即 `PortAnaRecord._generate` 的 `risk_analysis`（sum 模式）输出**。故 MultiPass 聚合的也是 sum 模式数字。

---

## 3. 信号 IC / ICIR / long-short `[已核实-子agent]`

### 3.1 calc_ic（`qlib/contrib/eva/alpha.py:160-183`）
`:323` `SigAnaRecord._generate` 调 `ic, ric = calc_ic(pred.iloc[:,0], label.iloc[:,self.label_col])`。返 `(ic, ric)` 两 Series（每日一值）：
- `:178` `ic = df.groupby(date_col, group_keys=False).apply(lambda df: df["pred"].corr(df["label"]))`——按日截面 Pearson。
- `:179` `ric = df.groupby(date_col, group_keys=False).apply(lambda df: df["pred"].corr(df["label"], method="spearman"))`——按日截面 Spearman。

### 3.2 SigAnaRecord 派生（`record_temp.py:324-329`）
- `:325` `"IC": ic.mean()`
- `:326` `"ICIR": ic.mean() / ic.std()`——**无 √N，不年化**
- `:327` `"Rank IC": ric.mean()`
- `:328` `"Rank ICIR": ric.mean() / ric.std()`——无 √N

### 3.3 long-short（`record_temp.py:335-336` + `alpha.py:71-113`）
- `ann_scaler` 默认 `252`（`:304`）。
- `:335` `"Long-Short Ann Return": long_short_r.mean() * self.ann_scaler`
- `:336` `"Long-Short Ann Sharpe": long_short_r.mean() / long_short_r.std() * self.ann_scaler**0.5`——此处 √252 出现。
- `calc_long_short_return`(`alpha.py:71-113`)：`:75` `quantile: float = 0.2`；`:107-108` `N(x)=int(len(x)*quantile)`；`:110` `r_long=group.apply(lambda x: x.nlargest(N(x),columns="pred").label.mean())`；`:111` `r_short=group.apply(lambda x: x.nsmallest(N(x),columns="pred").label.mean())`；`:112` `r_avg=group.label.mean()`；`:113` `return (r_long-r_short)/2, r_avg`。

---

## 4. 撮合成本与回报数字口径

### 4.1 成本模型（Exchange）`[已核实-子agent]`
- 存 `self.open_cost`/`self.close_cost`/`self.min_cost`/`self.impact_cost`（`exchange.py:187-190`）。
- 默认**不对称**：`open_cost=0.0015`(`:48`)、`close_cost=0.0025`(`:49`)、`min_cost=5.0`(`:50`)、`impact_cost=0.0`(`:51`)。
- `cost_ratio`：SELL `self.close_cost + adj_cost_ratio`(`:895`)；BUY `self.open_cost + adj_cost_ratio`(`:920`)；impact 平方 `adj_cost_ratio = self.impact_cost * (trade_val/total_trade_val)**2`(`:892`)，`total_trade_val` falsy 时 `adj_cost_ratio = self.impact_cost`(`:890`)。
- `trade_cost = max(trade_val * cost_ratio, self.min_cost)`(`:948`)；`trade_val <= 1e-5` 归零(`:949-951`)。
- **`min_cost` 对称/全局**：单标量同施买卖（`max(...,self.min_cost)` 在 `:948` 及 SELL cash-floor `:912-916` / BUY cash `:923-928`），无 open/close min_cost。
- **deal_price 静默回退 `$close`**：`exchange.py:510-513` `[已核实-子agent]` 配置价 NaN/`<=1e-8` 时 warn 后回退 `$close`——可掩盖缺数据。

### 4.2 回报数字三层（Account）`[已核实-子agent]`
- `rtn`(accum_info.rtn) **不含成本**；`earning` **含成本**（`account.py:18-31`，`_update_state_from_order` `:183-201` 注 "do not consider cost"）。
- `return_rate=(now_earning+now_cost)/last_account_value`(`account.py:283`)——报告 return 是 **gross of cost**，earning 是 **net**。
- **读回报数字须分清 rtn/earning/return_rate。**

### 4.3 回测数字裁决
- `report_normal["return"]`（喂给 `risk_analysis` 的 series）来自组合 return_rate 路径——**确认其是否含成本须在 arch 链路核**。`risk_analysis(return-bench)` 算超额无成本，`risk_analysis(return-bench-cost)` 算有成本超额——两个数字都出，读时取哪个看问题。

---

## 5. 红线（写入 CLAUDE.md）

1. **回测收益数字必须标来源函数 + scaler**：`risk_analysis` sum 模式 → 238；`SigAnaRecord` long-short → 252；`evaluate_portfolio` → 250（弃用）。禁止裸报"年化 X%"。
2. **ICIR ≠ IR**：信号 `ICIR=ic.mean()/ic.std()` 无 √N；组合 `information_ratio=mean/std*sqrt(238)` 有 √N。同页必须标注。
3. **sum 模式 = 单利 + cumsum 加性回撤**：默认路径。`annualized_return=mean*N` 是单利不是复利。改复利须显式传 `mode="product"`（但 qlib 自身不传，须 fork）。
4. **不改 upstream 口径**：不在 `evaluate.py` 顺手把 238 改 252（上游 `c38e799c`(#1938) 口径仍在演进，冲突）。差异靠文档裁决 + fork 侧 wrapper。
5. **`evaluate_portfolio.py` 弃用**：除非显式从 position dict 算指标，否则不用其 250 指标；其 `get_normal_ic`/`get_rank_ic` 整面板相关与 `calc_ic` 不等价，禁止混用。
6. **读回报数字先查 rtn/earning/return_rate**（§4.2）。
