"""End-to-end pipeline: download -> regime timeline -> roll-drag simulation."""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from data import download_futures, download_spot, SPOT_IDS, RESULTS
from regimes import build, regime_summary
from rolldrag import simulate

COMMODITIES = ["CL", "NG", "GC"]   # WTI crude, nat gas, gold
NAMES = {"CL": "WTI crude (CL=F)", "NG": "Henry Hub nat gas (NG=F)",
         "GC": "gold (GC=F)"}


def shade_regimes(ax, frame):
    """Shade contango runs light red and backwardation runs light blue."""
    regs = frame["regime"]
    start, prev = regs.index[0], regs.iloc[0]
    for t, r in list(regs.items())[1:] + [(regs.index[-1], None)]:
        if r != prev:                       # regime changed -> close the run
            if prev == "contango":
                ax.axvspan(start, t, color="red", alpha=0.10)
            elif prev == "backwardation":
                ax.axvspan(start, t, color="blue", alpha=0.10)
            start, prev = t, r


def main():
    futures = download_futures(COMMODITIES, period="10y")
    spot_names = [n for n in COMMODITIES if n in SPOT_IDS]
    spot = download_spot(spot_names)

    print("\n=== 1. Term-structure regimes (monthly basis proxy) ===")
    frames = build(futures, spot)
    summaries = {}
    for name in frames:
        s = regime_summary(frames[name]["regime"])
        summaries[name] = s
        sh, lg = s["shares"], s["longest_months"]
        print(f"\n{NAMES[name]}: {s['n_months']} months "
              f"({frames[name].index[0].date()} to {frames[name].index[-1].date()})")
        print(f"  contango      {sh['contango']*100:5.1f}%  "
              f"(longest run {lg.get('contango', 0)} months)")
        print(f"  backwardation {sh['backwardation']*100:5.1f}%  "
              f"(longest run {lg.get('backwardation', 0)} months)")
        print(f"  neutral       {sh['neutral']*100:5.1f}%")
    for name in COMMODITIES:
        if name not in frames:
            reason = {
                "GC": "no spot benchmark (FRED removed the LBMA gold fixings "
                      "in Jan 2022)",
                "NG": "NG=F on Yahoo is mis-scaled vs Henry Hub spot "
                      "(levels ~400-1600x off, drifting ratio -- no honest "
                      "unit conversion exists)",
            }.get(name, "no spot benchmark")
            print(f"\n{NAMES[name]}: {reason} -- "
                  f"futures downloaded, regime classification skipped.")

    print("\n=== 2. Roll drag: perpetual long crude futures vs spot ===")
    sim = simulate(frames["CL"])
    for k in ("years", "futures_long_total", "spot_total",
              "futures_long_annualized", "spot_annualized", "drag_annualized"):
        print(f"  {k:22s} {sim[k]:+.4f}")

    # ---- save results ----
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "summary.txt"), "w") as f:
        f.write("Commodity term-structure regimes & roll drag\n")
        f.write("=" * 50 + "\n")
        for name in frames:
            s, fr = summaries[name], frames[name]
            f.write(f"\n{NAMES[name]} ({s['n_months']} months, "
                    f"{fr.index[0].date()} to {fr.index[-1].date()})\n")
            for r in ("contango", "backwardation", "neutral"):
                f.write(f"  {r:14s} {s['shares'][r]*100:5.1f}% of months, "
                        f"longest run {s['longest_months'].get(r, 0)} months\n")
        for name in COMMODITIES:
            if name not in frames:
                reason = {
                    "GC": "no spot benchmark (FRED removed LBMA gold "
                          "fixings Jan 2022)",
                    "NG": "NG=F on Yahoo mis-scaled vs Henry Hub spot "
                          "(no honest unit conversion)",
                }.get(name, "no spot benchmark")
                f.write(f"\n{NAMES[name]}: futures only -- {reason}; "
                        f"regime classification skipped.\n")
        f.write("\nRoll-drag simulation: perpetual long CL front-month "
                "futures vs WTI spot\n")
        for k in ("years", "futures_long_total", "spot_total",
                  "futures_long_annualized", "spot_annualized", "drag_annualized"):
            f.write(f"  {k}: {sim[k]:.6f}\n")
    print(f"\nSaved summary -> {RESULTS}/summary.txt")

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    cl = frames["CL"]

    # Top: price levels -- the contract you trade vs the price you wish you held.
    axes[0].plot(cl.index, cl["fut"], lw=1.2, label="CL front-month futures")
    axes[0].plot(cl.index, cl["spot"], lw=1.2, label="WTI spot (FRED)")
    axes[0].set_title("WTI crude: front-month futures vs spot ($/bbl)")
    axes[0].legend(loc="upper left", fontsize=9)

    # Middle: the basis proxy with regime shading.
    axes[1].axhline(0.01, ls="--", c="r", lw=0.8)
    axes[1].axhline(-0.01, ls="--", c="b", lw=0.8)
    axes[1].plot(cl.index, cl["basis"] * 100, lw=1.0, c="k")
    shade_regimes(axes[1], cl)
    axes[1].set_title("Basis proxy (F-S)/S, % -- red = contango, blue = backwardation")

    # Bottom: the roll drag made visible -- $1 perpetual long vs $1 of spot.
    axes[2].plot(sim["wealth_fut"].index, sim["wealth_fut"], lw=1.4,
                 label="perpetual long futures")
    axes[2].plot(sim["wealth_spot"].index, sim["wealth_spot"], lw=1.4,
                 label="spot (unattainable)")
    axes[2].set_title("Wealth of $1: futures-long vs spot (gap = roll drag)")
    axes[2].legend(loc="upper left", fontsize=9)
    axes[2].set_xlabel("Date")

    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "analysis.png"), dpi=110)
    print(f"Saved chart -> {RESULTS}/analysis.png")


if __name__ == "__main__":
    main()
