"""Roll drag: the cost of being "long crude" forever.

You cannot buy-and-hold a futures contract the way you buy-and-hold a stock
-- it expires. The standard way to hold commodity exposure indefinitely is
the PERPETUAL LONG: every month, roll the whole position into the front
contract and keep riding.

We compare two wealth curves over the same window, both starting at $1:

  1. Futures-long: monthly returns of the continuous front-month contract.
  2. Spot: monthly returns of the spot benchmark (impossible to hold
     directly for oil -- you can't keep barrels in a brokerage account --
     which is exactly why the gap matters).

The gap between them is the ROLL DRAG: in contango the roll is sell-low /
buy-high, so the futures leg bleeds even when spot is flat; in backwardation
the roll pays and the futures leg can beat spot.

Assumptions (know these cold for interviews):
  - Rebalance monthly to the front contract; the continuous series' roll
    jumps at contract switches are left in (no back-adjustment).
  - No transaction costs, no margin calls, fills at month-end closes.
  - Spot is proxied by a benchmark (FRED) whose delivery spec is not
    identical to the futures contract's -- some "basis risk" leaks into the
    gap alongside the true roll yield.
"""
import numpy as np
import pandas as pd


def wealth(monthly_prices):
    """$1 invested, compounded monthly."""
    return (1 + monthly_prices.pct_change().fillna(0)).cumprod()


def simulate(monthly_frame):
    """Run the perpetual-long vs spot horse race on one commodity's frame."""
    w_fut = wealth(monthly_frame["fut"])
    w_spot = wealth(monthly_frame["spot"])
    years = (w_fut.index[-1] - w_fut.index[0]).days / 365.25
    out = {"years": float(years)}
    for leg, w in (("futures_long", w_fut), ("spot", w_spot)):
        total = float(w.iloc[-1] / w.iloc[0] - 1)
        # Geometric annualization: (1+R)^(1/years) - 1
        ann = float((w.iloc[-1] / w.iloc[0]) ** (1 / years) - 1)
        out[f"{leg}_total"] = total
        out[f"{leg}_annualized"] = ann
    # Annualized drag = how much the roll costs (or pays) per year, approx.
    out["drag_annualized"] = out["futures_long_annualized"] - out["spot_annualized"]
    out["wealth_fut"] = w_fut
    out["wealth_spot"] = w_spot
    return out
