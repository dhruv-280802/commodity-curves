"""Commodity data: front-month continuous futures + FRED spot benchmarks.

A futures contract has an EXPIRY -- a "March 2027 delivery" crude contract
dies on a fixed date. You cannot hold "crude oil futures" forever the way
you hold a stock: every month you must ROLL, i.e. sell the expiring contract
and buy the next one. To study a decade of "being long crude," we stitch
successive front-month contracts into one CONTINUOUS series: at each roll
the series steps from the old contract to the new one.

yfinance serves this stitching directly via futures tickers:
    CL=F   WTI crude (NYMEX, $/barrel)
    NG=F   Henry Hub natural gas (NYMEX, $/MMBtu)
    GC=F   gold (COMEX, $/ounce)

We pass auto_adjust=False: futures pay no dividends and never split, so raw
and adjusted closes coincide -- the important choice here is the continuous
front-month roll, which Yahoo's series handles for us.
"""
import os
import pandas as pd
import yfinance as yf

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")
CACHE_FUT = os.path.join(RESULTS, "futures.csv")
CACHE_SPOT = os.path.join(RESULTS, "spot.csv")

# Short names -> Yahoo futures tickers (continuous front-month series).
FUTURES = {"CL": "CL=F",   # WTI crude oil
           "NG": "NG=F",   # Henry Hub natural gas
           "GC": "GC=F"}   # gold

# FRED spot benchmarks (daily). Each roughly matches its futures contract.
#
# NOTE on gold: FRED carried the LBMA gold fixings (GOLDPMGBD228NLBM /
# GOLDAMGBD228NLBM) until ICE Benchmark Administration data was removed from
# FRED on 2022-01-31 -- the CSV endpoint now 404s, so there is no free daily
# gold spot on FRED. Free alternatives fail honestly too: stooq is
# unreachable from here, and GLD trades in $/share (not $/oz), so forming
# (F-S)/S from it would require inventing a share-to-ounce conversion.
# Gold therefore ships futures-only (no regime classification); see README.
#
# NOTE on nat gas: NG=F on Yahoo is unusable as quoted -- its levels sit
# ~400-1600x above the Henry Hub spot benchmark (DHHNGSP, $/MMBtu) and the
# ratio drifts over time (428 in 2016, 847 in 2020, 1606 in 2026), so this
# is not a stable unit conversion we can apply; it is a mislabeled series.
# Rather than invent a conversion factor, nat gas also ships futures-only.
SPOT_IDS = {"CL": "DCOILWTICO"}        # WTI spot, $/bbl
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"


def _cache_ok(path, names):
    """A cache is only reusable if it exists, has the right columns, and rows."""
    if not os.path.exists(path):
        return False
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    except Exception:
        return False
    return len(df) > 0 and all(n in df.columns for n in names)


def download_futures(names=None, period="10y", cache_path=CACHE_FUT, retries=3):
    """Daily front-month futures closes from Yahoo. Reuses the cache if present."""
    names = list(names or FUTURES)
    tickers = [FUTURES[n] for n in names]
    if _cache_ok(cache_path, names):
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        print(f"Loaded {len(df)} rows of futures from cache.")
        return df[names].dropna()

    print(f"Downloading {len(tickers)} futures ({period}) from Yahoo Finance ...")
    raw = None
    for attempt in range(1, retries + 1):
        # Yahoo's API is flaky; retry a few times before giving up.
        raw = yf.download(tickers, period=period, interval="1d",
                          auto_adjust=False, progress=False)
        if raw is not None and len(raw) > 0:
            break
        print(f"  attempt {attempt} returned no data, retrying ...")
    if raw is None or len(raw) == 0:
        raise RuntimeError("yfinance returned no data after retries; "
                           "check network access and try again later.")
    # Multi-ticker downloads come back as a (field, ticker) MultiIndex.
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw[["Close"]].rename(columns={"Close": names[0]})
    closes.columns = names
    closes = closes.dropna()
    closes.index = pd.to_datetime(closes.index).tz_localize(None)

    os.makedirs(RESULTS, exist_ok=True)
    closes.to_csv(cache_path)
    print(f"Saved {len(closes)} rows x {len(closes.columns)} futures to cache.")
    return closes


def download_spot(names=None, cache_path=CACHE_SPOT):
    """Daily spot benchmarks from FRED (CSV download). Reuses the cache if present."""
    names = list(names or SPOT_IDS)
    if _cache_ok(cache_path, names):
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        print(f"Loaded {len(df)} rows of spot data from cache.")
        return df[names].dropna()

    frames, failed = [], []
    for n in names:
        # FRED marks missing observations with "." -- coerce those to NaN.
        # The date column is named "observation_date" in fredgraph.csv exports.
        url = FRED_URL.format(sid=SPOT_IDS[n])
        try:
            s = pd.read_csv(url, index_col=0, parse_dates=True)
        except Exception as e:
            # One bad series must not kill the pipeline: report and continue
            # with the commodities that work. (This is how the LBMA gold
            # series failed -- FRED removed it in Jan 2022.)
            print(f"  {n}: DOWNLOAD FAILED ({type(e).__name__}) -- skipped")
            failed.append(n)
            continue
        s.columns = [n]
        s[n] = pd.to_numeric(s[n], errors="coerce")
        frames.append(s)
        print(f"  {n}: {s[n].notna().sum()} observations "
              f"({s.index.min().date()} to {s.index.max().date()})")
    if not frames:
        raise RuntimeError("No FRED spot series could be downloaded.")
    spot = pd.concat(frames, axis=1).dropna()
    ok = [n for n in names if n not in failed]
    spot = spot[ok]

    os.makedirs(RESULTS, exist_ok=True)
    spot.to_csv(cache_path)
    print(f"Saved {len(spot)} rows of spot data ({', '.join(ok)}) to cache.")
    if failed:
        print(f"Spot unavailable for: {', '.join(failed)} -- excluded.")
    return spot
