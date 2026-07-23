"""
CARRY strategy on USDCNH (offshore), 1M forward points.

Annualization convention (label verbatim in all outputs):
  - 252 trading days. ann_vol = daily_std * sqrt(252).
  - ann_ret / CAGR = (1+total)^(252/n_days)-1  (geo).
  - This is NOT qlib risk_analysis (238, sum mode) and NOT the 250 legacy figure.
  - Sharpe-like ratio = raw mean_daily / vol_daily (rf=0). NOT qlib IR (has sqrt(N)),
    NOT ICIR (no sqrt(N)).

Sign derivation (CIP) -- DOCUMENTED, do not blindly trust a draft formula.

  USD/CNH spot S = last (CNH per 1 USD). 1M forward points fwd_1m (in pips, 1 pip=1e-4).
  CIP (log form, 1M horizon):  ln(F/S) ~ r_US - r_CN  =>  r_CN - r_US ~ -(F-S)/S.
  Standard market forward points for USD/CNH = (F - S)*1e4 in pips.

  BUT: the carry_fwd.csv series has its OWN sign convention. Cross-check vs reality:
    2015: CN policy rate ~5%, US Fed funds ~0.25%  => r_CN - r_US ~ +4.5%  => fwd_1m ~ +211
    2024-26: US ~5%, CN ~2%                     => r_CN - r_US ~ -3%    => fwd_1m ~ -150
  So in THIS data, fwd_1m > 0 exactly when r_CN > r_US, i.e. fwd_1m ~ (r_CN - r_US).
  Therefore fwd_1m in this file = (S - F)*1e4  (negative of standard market points),
  and the correct sign here is:

      r_CN - r_US  (annualized)  =  (fwd_1m / 10000) / spot_last * 12        [NO leading minus]

  The draft formula's leading minus is INVERTED for this data's convention; using it would
  put the trade on backwards (short CNH when CN yields more). We use the corrected sign below
  and document the cross-check in carry.md.

Position / PnL:
  carry_signal_t = r_CN - r_US (annualized)         = (fwd_1m_t/1e4)/last_t * 12
  position_t = sign(carry_signal_t)   # +1 long CNH if CN yield>US, -1 short CNH if US yield>CN

  spot_ret_t = long-CNH spot return in USD = last_{t-1}/last_t - 1
             = -pct_change(USD/CNH)   (USD/CNH up => CNH weak => long CNH loses)

  Full carry variant:   PnL_t  = position_{t-1} * ( spot_ret_t + carry_signal_{t-1}/252 )
  Spot-only variant:   PnL_sp  = position_{t-1} *   spot_ret_t            (carry leg not booked)

  1-day lag on signal (decide on close t-1, trade earns day-t move + carry accrued at t-1).
  1 unit notional. Equity = cumprod(1 + PnL).  B&H CNH = cumprod(1 + spot_ret).
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..")  # fx_research dir
OUT = HERE

N_TRADE = 252  # annualization


def load():
    nh = pd.read_csv(os.path.join(DATA, "usdcnh.csv"), index_col=0, parse_dates=True)
    cf = pd.read_csv(os.path.join(DATA, "carry_fwd.csv"), index_col=0, parse_dates=True)
    m = nh.join(cf, how="left")
    # restrict to rows where we have both spot and fwd_1m
    m = m.dropna(subset=["last", "fwd_1m"]).copy()
    return m


def metrics(name, pnl, spot_ret_same_window):
    """Compute the metric spec for a daily PnL series (already aligned to trade window).
    spot_ret_same_window: B&H CNH daily return over the SAME window (for vs label)."""
    eq = (1 + pnl).cumprod()
    n_days = len(pnl)
    total = eq.iloc[-1] - 1
    cagr = (1 + total) ** (N_TRADE / n_days) - 1
    ann_vol = pnl.std() * np.sqrt(N_TRADE)
    sharpe = (pnl.mean() / pnl.std()) if pnl.std() > 0 else float("nan")
    # max drawdown on equity curve
    rollmax = eq.cummax()
    dd = eq / rollmax - 1
    max_dd = dd.min()
    calmar = cagr / abs(max_dd) if max_dd != 0 else float("nan")
    win_rate = (pnl > 0).mean()
    # turnover / flips require the position series; pass via attribute-free recomputation outside
    return {
        "strategy": name,
        "total_return": f"{total*100:.2f}%",
        "cagr": f"{cagr*100:.2f}%",
        "ann_vol_252": f"{ann_vol*100:.2f}%",
        "sharpe_like": f"{sharpe:.3f}",
        "max_drawdown": f"{max_dd*100:.2f}%",
        "calmar": f"{calmar:.3f}",
        "win_rate": f"{win_rate*100:.2f}%",
        # placeholder for turnover/n_flips/vs_buyhold; filled by caller
        "turnover": None,
        "n_flips": None,
        "vs_buyhold": None,
    }


def run():
    m = load()
    last = m["last"]
    fwd_1m = m["fwd_1m"]

    # spot return of being LONG CNH (USD terms): CNH appreciates => +ret
    spot_ret = -(last.pct_change())   # = last.shift(1)/last - 1  (long CNH)
    # carry signal (annualized r_CN - r_US), corrected sign
    carry_signal = (fwd_1m / 1e4) / last * 12.0

    # position decided at t from signal at t; trade executed earns t+1 spot return + carry at t.
    # We follow the 1-day-lag convention: position_t = sign(carry_signal_t);
    # PnL_{t+1} = position_t * (spot_ret_{t+1} + carry_signal_t/252).
    position = np.sign(carry_signal)  # +1/-1/0

    # align: PnL at t uses position at t-1
    pos_prev = position.shift(1)
    carry_prev = carry_signal.shift(1)
    spot_cur = spot_ret  # spot_ret_t already a 1-day return on last

    pnl_full = pos_prev * (spot_cur + carry_prev / N_TRADE)
    pnl_spot = pos_prev * spot_cur

    # drop the leading NaN (first row has no position-prev)
    df = pd.DataFrame({
        "last": last, "fwd_1m": fwd_1m, "carry_signal": carry_signal,
        "position": position, "pos_prev": pos_prev,
        "spot_ret": spot_cur, "pnl_full": pnl_full, "pnl_spot": pnl_spot,
    }).dropna(subset=["pnl_full", "pnl_spot"])

    # B&H CNH over the SAME window (same spot_ret series, restricted)
    bh = df["spot_ret"]
    bh_eq = (1 + bh).cumprod()

    # turnover & flips (use the position actually traded = pos_prev aligned to df)
    pos_trade = df["pos_prev"]
    turnover = (pos_trade.diff().abs()).mean()
    n_flips = int((np.sign(pos_trade).diff().replace(0, np.nan).dropna() != 0).sum())

    # signal flips (the underlying signal, not the executed position) for commentary
    sig = np.sign(df["carry_signal"])
    sig_flips = int((sig.diff().replace(0, np.nan).dropna() != 0).sum())

    # metrics
    mfull = metrics("CARRY (spot+carry legs, 1M fwd)", df["pnl_full"], bh)
    mspot = metrics("CARRY spot-only (signal for direction, no carry leg)", df["pnl_spot"], bh)
    mbh = metrics("B&H CNH (same window)", bh, bh)
    # fill turnover/n_flips/vs_buyhold
    bh_total = bh_eq.iloc[-1] - 1
    mfull.update({
        "turnover": f"{turnover:.4f}", "n_flips": str(n_flips),
        "vs_buyhold": f"{bh_total*100:.2f}% (B&H CNH same window)",
    })
    mspot.update({
        "turnover": f"{turnover:.4f}", "n_flips": str(n_flips),
        "vs_buyhold": f"{bh_total*100:.2f}% (B&H CNH same window)",
    })
    mbh.update({
        "turnover": "0.0000 (buy once)", "n_flips": "0",
        "vs_buyhold": "— (is the benchmark)",
    })

    # leg decomposition for commentary: mean abs contribution of spot vs carry leg
    spot_leg = (pos_prev * spot_cur).dropna()
    carry_leg = (pos_prev * carry_prev / N_TRADE).dropna()
    spot_leg = spot_leg.reindex(df.index)
    carry_leg = carry_leg.reindex(df.index)

    # plot: each strategy vs B&H CNH, log-y
    for label, pnl_s, fname in [
        ("CARRY (spot+carry legs)", df["pnl_full"], "carry_equity.png"),
    ]:
        eq_s = (1 + pnl_s).cumprod()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(eq_s.index, eq_s.values, label=label, lw=1.4)
        ax.plot(bh_eq.index, bh_eq.values, label="B&H CNH", lw=1.2, ls="--", color="gray")
        ax.set_yscale("log")
        ax.set_xlabel("date")
        ax.set_ylabel("equity (log scale, start=1)")
        ax.set_title(f"{label} vs B&H CNH — USDCNH offshore, 1M fwd points\n"
                     "252-day ann | sharpe_like=mean/vol rf=0 | NOT qlib 238/IR")
        ax.legend()
        ax.grid(True, which="both", ls=":", alpha=0.5)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, fname), dpi=110)
        plt.close(fig)

    # also save spot-only equity for reference (not required but useful)
    eq_spot = (1 + df["pnl_spot"]).cumprod()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(eq_spot.index, eq_spot.values, label="CARRY spot-only", lw=1.4)
    ax.plot(bh_eq.index, bh_eq.values, label="B&H CNH", lw=1.2, ls="--", color="gray")
    ax.set_yscale("log")
    ax.set_xlabel("date"); ax.set_ylabel("equity (log scale)")
    ax.set_title("CARRY spot-only vs B&H CNH — USDCNH offshore")
    ax.legend(); ax.grid(True, which="both", ls=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "carry_equity_spotonly.png"), dpi=110)
    plt.close(fig)

    summary = {
        "window_start": str(df.index[0].date()),
        "window_end": str(df.index[-1].date()),
        "n_days": len(df),
        "sig_flips_underlying": sig_flips,
        "n_flips_executed_position": n_flips,
        "mean_daily_spot_leg": float(spot_leg.mean()),
        "mean_daily_carry_leg": float(carry_leg.mean()),
        "std_daily_spot_leg": float(spot_leg.std()),
        "std_daily_carry_leg": float(carry_leg.std()),
        "frac_days_long": float((df["pos_prev"] > 0).mean()),
        "frac_days_short": float((df["pos_prev"] < 0).mean()),
        "bh_cnh_total_same_window": float(bh_total),
    }
    return mfull, mspot, mbh, summary, df


if __name__ == "__main__":
    mfull, mspot, mbh, summary, df = run()
    print("=== METRICS ===")
    for mm in [mfull, mspot, mbh]:
        print(mm)
    print("=== SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    # sanity prints
    print("=== HEAD ===")
    print(df[["last", "fwd_1m", "carry_signal", "pos_prev", "spot_ret", "pnl_full", "pnl_spot"]].head(4))
    print("=== TAIL ===")
    print(df[["last", "fwd_1m", "carry_signal", "pos_prev", "spot_ret", "pnl_full", "pnl_spot"]].tail(4))
