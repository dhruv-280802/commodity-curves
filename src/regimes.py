"""Term-structure regimes: is the market in contango or backwardation?

The TERM STRUCTURE is the curve of futures prices across expiries. Its shape
is governed by the cost-of-carry relation:

    F(T) = S * exp((r + u - y) * T)

where r is the financing rate, u the storage cost, and y the CONVENIENCE
YIELD -- the (unobservable) benefit of holding the physical commodity now
rather than a paper claim on it later.

- CONTANGO: futures trade ABOVE spot (upward-sloping curve). Typical when
  inventories are abundant: storage is expensive (high u), nobody pays a
  premium for immediate delivery (low y), so deferred prices sit above spot.
- BACKWARDATION: futures trade BELOW spot (downward-sloping curve). Typical
  in a shortage: having the physical stuff now is worth a lot (high y),
  which overwhelms storage + financing costs.

We only have the front-month expiry, not the full curve, so we use a BASIS
proxy sampled monthly:

    basis_t = (F_front,t - S_t) / S_t

and classify: basis > +1% -> contango, basis < -1% -> backwardation, else
neutral. This proxies the *sign of the near curve's slope*, not the whole
term structure -- see README "Honest limitations".

Why a long futures position bleeds in contango (ROLL YIELD): to stay long
you must repeatedly sell the expiring contract (cheap) and buy the next one
(expensive). That sell-low/buy-high roll is a built-in cost -- negative roll
yield. In backwardation the roll runs the other way (sell high, buy low) and
pays you. A perpetual long in contango can lose money even if the spot price
goes nowhere: the roll drag eats the position.

Samuelson effect (for interviews): near-dated futures are more volatile than
far-dated ones, because spot shocks (a refinery outage, a cold snap) fade as
they propagate down the curve -- hence we use the FRONT contract, the most
sensitive point on the curve.
"""
import numpy as np
import pandas as pd

THRESHOLD = 0.01   # +/-1% basis defines contango / backwardation


def monthly(fut, spot):
    """Align daily futures and spot to month-end observations (last available)."""
    # Month-end sampling keeps the series clean and matches how commodity
    # indices rebalance; ffill first so an incomplete last bar (NaN) falls
    # back to the most recent traded close instead of dropping the month.
    m = pd.concat({"F": fut, "S": spot}, axis=1).ffill()
    # "ME" is the month-end alias in pandas >= 2.2; older pandas only
    # accept "M" for the same thing, so fall back instead of crashing.
    try:
        m = m.resample("ME").last()
    except ValueError:
        m = m.resample("M").last()
    return m.dropna()


def basis_proxy(monthly_frame):
    """(front futures - spot) / spot, the near-curve slope proxy."""
    return (monthly_frame["F"] - monthly_frame["S"]) / monthly_frame["S"]


def classify(basis, threshold=THRESHOLD):
    """Label each month contango / backwardation / neutral."""
    labels = pd.Series("neutral", index=basis.index)
    labels[basis > threshold] = "contango"
    labels[basis < -threshold] = "backwardation"
    return labels


def regime_summary(labels):
    """Share of months per regime and the longest consecutive run of each."""
    out = {}
    counts = labels.value_counts()
    out["shares"] = {r: float(counts.get(r, 0)) / len(labels)
                     for r in ("contango", "backwardation", "neutral")}
    # Longest streak: walk the label series and count consecutive repeats.
    longest = {}
    run_regime, run_len = None, 0
    for r in list(labels) + [None]:          # trailing None flushes the last run
        if r == run_regime:
            run_len += 1
        else:
            if run_regime is not None:
                longest[run_regime] = max(longest.get(run_regime, 0), run_len)
            run_regime, run_len = r, 1
    out["longest_months"] = longest
    out["n_months"] = len(labels)
    return out


def build(futures, spot):
    """Basis proxy + regime labels for every commodity with a spot benchmark."""
    out = {}
    for name in futures.columns:
        if name not in spot.columns:
            continue                    # no spot benchmark -> no regime call
        m = monthly(futures[name], spot[name])
        b = basis_proxy(m)
        out[name] = pd.DataFrame({"fut": m["F"], "spot": m["S"],
                                  "basis": b, "regime": classify(b)})
    return out
