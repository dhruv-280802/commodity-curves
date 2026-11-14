# Commodity Curves: Term-Structure Regimes and Roll Drag

A quantitative research project on commodity futures term structure: when is
the oil market in contango vs backwardation, and what does it cost to stay
long crude forever? Built with real market data (Yahoo Finance front-month
futures, FRED spot benchmarks) and honest accounting of what the data can
and cannot say.

**Status:** working prototype (Week 0). See "Roadmap" below for the 2-week
extension plan that turns this into a flagship resume project.

## The idea (in plain English)

A futures contract is a promise to buy oil (or gas, or gold) at a fixed
price on a fixed future date. Plot those prices across all expiry dates and
you get the **term structure** — the "curve." Its shape is set by the
cost-of-carry relation:

```
F(T) = S · e^((r + u − y)·T)
```

`r` = financing cost, `u` = storage cost, `y` = convenience yield (the
unobservable value of holding the physical stuff *now* instead of a paper
claim on it later).

- **Contango** — futures trade *above* spot (upward-sloping curve). Happens
  when inventories are flush: storage is expensive, nobody pays a premium
  for immediate delivery.
- **Backwardation** — futures trade *below* spot (downward-sloping curve).
  Happens in a shortage: having barrels today is worth more than the cost
  of storing them.

Key insight this project teaches (interviewers love it): **you cannot
buy-and-hold a futures contract.** It expires, so a "perpetual long" must
roll — sell the expiring contract, buy the next one — every month. In
contango that roll is sell-low/buy-high: a built-in bleed called negative
**roll yield**. In backwardation the roll runs the other way and pays you.
The cumulative gap between a rolled futures position and the spot price is
the **roll drag**: the reason oil ETFs can lose money for years while the
spot price goes nowhere.

What this project does:

1. **Download** 10 years of daily front-month futures (CL=F crude, NG=F nat
   gas, GC=F gold) plus FRED spot benchmarks.
2. **Classify regimes** — monthly basis proxy `(F − S)/S`: > +1% contango,
   < −1% backwardation, else neutral; report shares and longest runs.
3. **Simulate the perpetual long** — $1 rolled monthly in front-month crude
   futures vs $1 of (unattainable) spot; the gap is the roll drag.
4. **Plot everything** — futures vs spot, the regime timeline, and the two
   wealth curves.

## Results (10 years of data, Sep 2016 – Sep 2026, 121 months)

Term-structure regimes (monthly basis proxy, ±1% threshold):

| Commodity | Contango | Backwardation | Neutral | Longest run |
|-----------|----------|---------------|---------|-------------|
| WTI crude | 1.7% (2 mo) | 20.7% (25 mo) | 77.7% | 21 mo neutral |
| Nat gas   | — (excluded: NG=F mis-scaled, see below) | | | |
| Gold      | — (excluded: no free spot benchmark, see below) | | | |

The crude result looks odd until you think about it: the **front-month**
contract is days from expiry, so it hugs spot — the ±1% threshold mostly
reads "neutral." The true curve shape lives in the *slope across expiries*,
which needs 12 contracts, not one (Week 2 of the roadmap). The backwardation
months that do print are real: physical tightness episodes (e.g. 2022, 2026)
when spot commanded a genuine premium.

Roll-drag simulation — perpetual long front-month crude vs WTI spot:

| Leg | Total return | Annualized |
|-----|-------------|------------|
| Futures-long (rolled monthly) | **+86.0%** | **+6.40%** |
| Spot (unattainable) | +124.3% | +8.41% |
| **Roll drag** | | **−2.01%/yr** |

$1 held as a perpetual crude long became $1.86; $1 of spot became $2.24.
The 38-point gap is a decade of contango bleed — the exact mechanism that
ate oil ETFs alive in the 2010s.

## How to run

```bash
cd commodity-curves
../.venv/bin/python run.py        # full pipeline: download -> regimes -> roll drag
```

Outputs land in `results/`: `analysis.png` (futures vs spot / regime
timeline / wealth curves), `summary.txt`, `futures.csv`, `spot.csv`
(cached data — delete to force a fresh download).

## Project layout

```
run.py            # pipeline: download -> regime timeline -> roll-drag sim -> plots
src/data.py       # Yahoo futures + FRED spot downloads, local cache
src/regimes.py    # basis proxy, contango/backwardation classifier, run lengths
src/rolldrag.py   # perpetual-long vs spot wealth simulation
results/          # generated outputs
```

## Honest limitations (know these before any interview)

- **Single-expiry proxy, not the curve.** Everything here uses the front
  month only. Real contango/backwardation is the slope across many expiries;
  the front-vs-spot basis is a noisy shadow of it (hence 78% "neutral").
  Week 2 fixes this with 12 expiries per commodity.
- **Spot/futures timing mismatches.** FRED spot prints lag (e.g. WTI spot
  ends 2026-09-15 while futures trade to 2026-09-22); holidays leave spot
  stale while futures move (Nov 29, 2019 reads −5% "backwardation" that is
  really Thanksgiving). Month-end sampling inherits these artifacts.
- **No transaction costs on rolls.** The −2.01%/yr drag excludes bid/ask and
  commissions on every monthly roll; real drag is worse.
- **NG=F is unusable as quoted.** Yahoo's series sits ~400–1600× above
  Henry Hub spot with a drifting ratio — a mislabeled series, not a unit
  conversion. Included in the download, excluded from regimes; no conversion
  was invented.
- **No free daily gold spot.** FRED deleted the LBMA gold fixings in Jan
  2022; stooq is unreachable; GLD trades in $/share, not $/oz. Gold ships
  futures-only until a real spot source is wired in.
- **Survivorship/simplicity.** Monthly rebalancing, month-end fills, no
  margin, no position sizing — a measurement exercise, not a strategy.

## Roadmap — the next 2 weeks

**Week 1 — own the economics**
- Internalize the cost-of-carry model `F = S·e^((r+u−y)T)`: derive it from
  no-arbitrage (cash-and-carry), and explain what breaks it (e.g. WTI going
  negative in April 2020 — storage wasn't just costly, it was unavailable).
- Estimate the *implied convenience yield* `y` from the basis proxy and the
  3-month T-bill rate; plot convenience yield vs inventory data (EIA weekly
  stocks) — the classic inverse relationship is a great interview chart.
- Read every line of `src/` until you can whiteboard why a contango roll
  bleeds and why the front contract is the most volatile point on the curve
  (Samuelson effect).

**Week 2 — the true term structure (the documented extension)**
- Pull 12 expiries per commodity (e.g. via barchart/CME settlement pages or
  a futures-data API) and build the **true term-structure surface**:
  price vs time-to-expiry, daily.
- Re-run regime classification on actual curve slope (e.g. 12m−1m
  calendar spread sign), not the front-vs-spot proxy.
- Backtest a **calendar-spread** strategy: long backwardated curves / short
  contangoed curves (or long the roll yield directly), net of realistic
  roll costs; report Sharpe and drawdown like the stat-arb project.

**Resume bullet:**
"Commodity futures term-structure research — built a Python pipeline
(yfinance, FRED) classifying contango/backwardation regimes from the
futures–spot basis and simulating a perpetual crude long vs spot; measured
−2.01%/yr roll drag over 10 years; documented data limitations (single-expiry
proxy, stale spot prints) and specified the 12-expiry term-structure
extension."
