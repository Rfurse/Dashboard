"""
FMP Stable API data fetcher (v3 deprecated Aug 31 2025).

Base: https://financialmodelingprep.com/stable
Single cached fetch_all() — no nested cache calls.

Key endpoint changes from v3:
  Quote:      /stable/quote?symbol=SPY          (field: changePercentage, priceAvg50, priceAvg200)
  Historical: /stable/historical-price-eod/full?symbol=SPY&from=X&to=Y
  Treasury:   /stable/treasury-rates
  Calendar:   /stable/economic-calendar
  Gainers:    /stable/biggest-gainers
  Losers:     /stable/biggest-losers
  SMA/RSI:    calculated from historical (stable tech-indicator endpoints return [])
"""

import requests
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

from config import FMP_API_KEY, SECTOR_ETFS

STABLE = "https://financialmodelingprep.com/stable"


# ── HTTP helper ───────────────────────────────────────────────────────────────

def _get(path: str, params: dict = None) -> tuple:
    """GET /stable{path}. Returns (data, error_str)."""
    url = f"{STABLE}{path}"
    p = {"apikey": FMP_API_KEY}
    if params:
        p.update(params)
    try:
        r = requests.get(url, params=p, timeout=12)
        if r.status_code in (401, 403):
            return None, f"HTTP {r.status_code} — check FMP_API_KEY or plan access ({path})"
        if r.status_code == 429:
            return None, f"429 Rate limit hit ({path})"
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            err = data.get("Error Message") or data.get("message") or data.get("error")
            if err:
                return None, f"{err} ({path})"
        return data, None
    except requests.exceptions.Timeout:
        return None, f"Timeout ({path})"
    except Exception as e:
        return None, f"{type(e).__name__}: {e} ({path})"


# ── Primitive helpers ─────────────────────────────────────────────────────────

def _quote(symbol: str) -> dict:
    """GET /stable/quote?symbol=SYM. Returns first result or {}."""
    data, err = _get("/quote", {"symbol": symbol})
    if isinstance(data, list) and data:
        return data[0]
    _last_quote_error[0] = err or f"empty response for {symbol}"
    return {}


def _hist(symbol: str, days: int = 40) -> list:
    """
    GET /stable/historical-price-eod/full?symbol=SYM&limit=N.
    Returns list sorted most-recent first, or [].
    """
    data, _ = _get("/historical-price-eod/full", {
        "symbol": symbol,
        "limit":  days,
    })
    if isinstance(data, list):
        return data
    return []


def _calc_sma(hist: list, period: int) -> float | None:
    """Calculate SMA from historical list (most-recent first)."""
    if len(hist) >= period:
        return float(np.mean([h["close"] for h in hist[:period]]))
    return None


def _calc_rsi(hist: list, period: int = 14) -> float | None:
    """Calculate RSI-14 from historical list (most-recent first)."""
    if len(hist) < period + 1:
        return None
    closes = [h["close"] for h in reversed(hist[:period + 1])]
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


# Mutable container so importers can read the last error
_last_quote_error: list = [None]


# ── Single aggregated fetch ───────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def fetch_all() -> dict:
    """
    All dashboard data in one cached call.
    Keys: spy, qqq, vix, sectors, treasury, eurusd, fomc, breadth,
          fetched_at, errors (list[str]), api_ok (bool).
    """
    errors: list[str] = []
    today    = datetime.utcnow().date()
    yr_ago   = today - timedelta(days=380)

    # ── SPY ──────────────────────────────────────────────────────────────────
    spy_q = _quote("SPY")
    if not spy_q:
        errors.append(f"SPY quote failed: {_last_quote_error[0]}")

    # Quote already contains 50d and 200d averages
    spy_price  = spy_q.get("price")
    spy_chg    = spy_q.get("changePercentage")
    spy_sma50  = spy_q.get("priceAvg50")
    spy_sma200 = spy_q.get("priceAvg200")

    # Need history for 20d SMA and RSI-14
    spy_hist   = _hist("SPY", 220)
    spy_sma20  = _calc_sma(spy_hist, 20)
    spy_rsi14  = _calc_rsi(spy_hist, 14)

    regime = None
    if spy_price and spy_sma50 and spy_sma200:
        if spy_price > spy_sma200 and spy_price > spy_sma50:
            regime = "uptrend"
        elif spy_price < spy_sma200 and spy_price < spy_sma50:
            regime = "downtrend"
        else:
            regime = "chop"

    spy = {
        "price":      spy_price,
        "change_pct": spy_chg,
        "sma20":      spy_sma20,
        "sma50":      spy_sma50,
        "sma200":     spy_sma200,
        "rsi14":      spy_rsi14,
        "regime":     regime,
    }

    # ── QQQ ──────────────────────────────────────────────────────────────────
    qqq_q   = _quote("QQQ")
    qqq_sma50 = qqq_q.get("priceAvg50")
    qqq = {
        "price":      qqq_q.get("price"),
        "change_pct": qqq_q.get("changePercentage"),
        "sma50":      qqq_sma50,
    }

    # ── VIX ──────────────────────────────────────────────────────────────────
    vix_q     = _quote("^VIX")
    vix_level = vix_q.get("price")
    if not vix_level:
        errors.append("VIX quote failed")

    vix_hist = _hist("^VIX", 260)
    vix_slope = None
    vix_pct   = None
    if vix_hist and len(vix_hist) >= 6:
        closes = [h["close"] for h in vix_hist]
        y = np.array(closes[:5][::-1])
        vix_slope = float(np.polyfit(np.arange(5), y, 1)[0])
        cur = vix_level or closes[0]
        vix_pct = float(np.mean(np.array(closes) <= cur) * 100)

    vix = {
        "level":          vix_level,
        "slope":          vix_slope,
        "percentile_1yr": vix_pct,
    }

    # ── SECTORS ──────────────────────────────────────────────────────────────
    sectors = {}
    sector_failures = 0
    for sym in SECTOR_ETFS:
        sq = _quote(sym)
        if not sq:
            sector_failures += 1

        change_1d = sq.get("changePercentage")
        price     = sq.get("price")

        entry = {
            "price":       price,
            "change_1d":   change_1d,
            "return_5d":   None,
            "return_20d":  None,
            "data_source": "1d",
        }

        sh = _hist(sym, 25)
        if sh and len(sh) >= 6:
            latest = sh[0]["close"]
            entry["return_5d"]   = (latest - sh[5]["close"]) / sh[5]["close"] * 100
            entry["data_source"] = "5d"
            if len(sh) >= 21:
                entry["return_20d"] = (latest - sh[20]["close"]) / sh[20]["close"] * 100
        elif change_1d is not None:
            entry["return_5d"] = change_1d

        sectors[sym] = entry

    if sector_failures == len(SECTOR_ETFS):
        errors.append("All sector quotes failed")

    # ── TREASURY ─────────────────────────────────────────────────────────────
    tsy_data, tsy_err = _get("/treasury-rates", {"limit": 7})
    if tsy_err:
        errors.append(f"Treasury: {tsy_err}")
    yield_10yr  = None
    yield_trend = None
    if isinstance(tsy_data, list) and tsy_data:
        yield_10yr = tsy_data[0].get("year10")
        if len(tsy_data) >= 6 and yield_10yr:
            old = tsy_data[5].get("year10")
            if old:
                yield_trend = "rising" if yield_10yr > old else "falling"

    treasury = {"yield_10yr": yield_10yr, "trend": yield_trend}

    # ── EUR/USD ───────────────────────────────────────────────────────────────
    eu_q   = _quote("EURUSD")
    eurusd = {
        "rate":       eu_q.get("price"),
        "change_pct": eu_q.get("changePercentage"),
    }

    # ── FOMC ─────────────────────────────────────────────────────────────────
    fomc_end = today + timedelta(days=7)
    cal_data, _ = _get("/economic-calendar", {
        "from": str(today),
        "to":   str(fomc_end),
    })
    fomc = {"hours_until": None, "event_name": None}
    if isinstance(cal_data, list):
        keywords = ["fed", "fomc", "federal reserve", "rate decision", "federal funds"]
        now = datetime.utcnow()
        for ev in cal_data:
            name = (ev.get("event") or "").lower()
            if not any(k in name for k in keywords):
                continue
            dt_str = ev.get("date") or ""
            try:
                ev_dt = datetime.fromisoformat(dt_str.replace("Z", ""))
                hours = (ev_dt - now).total_seconds() / 3600
                if 0 <= hours <= 72:
                    if fomc["hours_until"] is None or hours < fomc["hours_until"]:
                        fomc["hours_until"] = round(hours, 1)
                        fomc["event_name"]  = ev.get("event", "FOMC Event")
            except Exception:
                continue

    # ── BREADTH PROXY ─────────────────────────────────────────────────────────
    gainers_data, _ = _get("/biggest-gainers")
    losers_data,  _ = _get("/biggest-losers")
    g = len(gainers_data) if isinstance(gainers_data, list) else 0
    l = len(losers_data)  if isinstance(losers_data,  list) else 0
    breadth = {
        "gainers": g or None,
        "losers":  l or None,
        "ratio":   g / (g + l) if (g + l) > 0 else None,
    }

    return {
        "spy":        spy,
        "qqq":        qqq,
        "vix":        vix,
        "sectors":    sectors,
        "treasury":   treasury,
        "eurusd":     eurusd,
        "fomc":       fomc,
        "breadth":    breadth,
        "fetched_at": datetime.utcnow(),
        "errors":     errors,
        "api_ok":     spy_price is not None,
    }
