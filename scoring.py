"""
Scoring engine. Pure functions — no Streamlit imports.
All inputs come from data_fetcher.fetch_all().
Edit thresholds in config.py.
"""

import numpy as np
from config import WEIGHTS, VIX_SCORE_TIERS, DECISION_THRESHOLDS, YIELD_LOW, YIELD_HIGH, SECTOR_ETFS, MODE_CONFIG


# ── Helpers ───────────────────────────────────────────────────────────────────

def clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def direction_arrow(value: float | None, threshold: float = 0) -> str:
    if value is None:
        return "→"
    if value > threshold:
        return "↑"
    if value < threshold:
        return "↓"
    return "→"


# ── Category Scorers ──────────────────────────────────────────────────────────

def score_volatility(vix: dict, mode: str = "Swing") -> dict:
    """Score 0-100. Higher = calmer = better."""
    level    = vix.get("level")
    slope    = vix.get("slope")
    pct      = vix.get("percentile_1yr")
    mult     = MODE_CONFIG[mode]["vix_penalty_multiplier"]

    base = 50
    if level is not None:
        for threshold, pts in VIX_SCORE_TIERS:
            if level < threshold:
                base = pts
                break

    slope_adj = 0
    if slope is not None:
        if slope < -0.2:
            slope_adj = +10
        elif slope > 0.2:
            slope_adj = -10 * mult

    pct_adj = 0
    if pct is not None:
        # low percentile = VIX historically calm → reward
        pct_adj = (50 - pct) * 0.2   # ±10

    raw = clamp(base + slope_adj + pct_adj)

    status = "HEALTHY" if raw >= 70 else ("WEAKENING" if raw >= 45 else "RISK-OFF")

    return {
        "score":      raw,
        "status":     status,
        "level":      level,
        "slope":      slope,
        "percentile": pct,
        "label":      "VIX",
        "value_str":  f"{level:.1f}" if level else "N/A",
        "dir":        direction_arrow(slope, 0) if slope is not None else "→",
        "dir_inv":    True,  # higher VIX = bad, so ↑ is red
    }


def score_trend(spy: dict, qqq: dict, mode: str = "Swing") -> dict:
    """Score 0-100 based on MA alignment and RSI."""
    p    = spy.get("price")
    s20  = spy.get("sma20")
    s50  = spy.get("sma50")
    s200 = spy.get("sma200")
    rsi  = spy.get("rsi14")
    qp   = qqq.get("price")
    qs50 = qqq.get("sma50")

    pts = 0
    if p is not None and s200 is not None and p > s200:
        pts += 40
    if p is not None and s50 is not None and p > s50:
        pts += 30
    if p is not None and s20 is not None and p > s20:
        pts += 20
    if qp is not None and qs50 is not None and qp > qs50:
        pts += 10

    rsi_low  = MODE_CONFIG[mode]["rsi_low"]
    rsi_high = MODE_CONFIG[mode]["rsi_high"]
    rsi_mod  = 0
    if rsi is not None:
        if rsi < 30:
            rsi_mod = +5
        elif rsi > rsi_high:
            rsi_mod = -10
        elif rsi_low <= rsi <= rsi_high:
            rsi_mod = 0

    raw = clamp(pts + rsi_mod)
    status = "HEALTHY" if raw >= 70 else ("WEAKENING" if raw >= 40 else "RISK-OFF")

    regime = spy.get("regime", "unknown")

    return {
        "score":   raw,
        "status":  status,
        "regime":  regime,
        "rsi":     rsi,
        "price":   p,
        "sma20":   s20,
        "sma50":   s50,
        "sma200":  s200,
        "label":   "SPY TREND",
        "value_str": regime.upper() if regime else "N/A",
        "dir":     "↑" if regime == "uptrend" else ("↓" if regime == "downtrend" else "→"),
        "dir_inv": False,
    }


def score_breadth(sectors: dict, breadth: dict) -> dict:
    """Score 0-100 based on sector breadth and gainers/losers ratio."""
    # Count sectors with positive 5d return
    five_d_returns = [v["return_5d"] for v in sectors.values() if v["return_5d"] is not None]
    up_count = sum(1 for r in five_d_returns if r > 0)
    n = len(five_d_returns) if five_d_returns else 11

    sector_base = (up_count / n) * 70

    ratio = breadth.get("ratio")
    gainers_contrib = (ratio * 30) if ratio is not None else 15   # default neutral

    raw = clamp(sector_base + gainers_contrib)
    status = "HEALTHY" if raw >= 65 else ("WEAKENING" if raw >= 40 else "RISK-OFF")

    return {
        "score":    raw,
        "status":   status,
        "up_count": up_count,
        "n_total":  n,
        "ratio":    ratio,
        "label":    "BREADTH",
        "value_str": f"{up_count}/{n} UP",
        "dir":      "↑" if up_count > n // 2 else "↓",
        "dir_inv":  False,
    }


def score_momentum(sectors: dict) -> dict:
    """Score 0-100 based on average sector return and leadership spread."""
    returns_20d = [(sym, v["return_20d"]) for sym, v in sectors.items() if v["return_20d"] is not None]

    if len(returns_20d) < 3:
        return {
            "score": 50, "status": "UNKNOWN",
            "top3": [], "bot3": [], "spread": None,
            "label": "MOMENTUM", "value_str": "N/A", "dir": "→", "dir_inv": False,
        }

    returns_20d.sort(key=lambda x: x[1], reverse=True)
    all_vals = [r for _, r in returns_20d]
    avg = float(np.mean(all_vals))

    top3 = returns_20d[:3]
    bot3 = returns_20d[-3:]
    spread = float(np.mean([r for _, r in top3]) - np.mean([r for _, r in bot3]))

    # Normalize avg: -10% → 0 pts, +10% → 70 pts (linear)
    base = clamp((avg + 10) / 20 * 70)
    # Normalize spread: 0% → 0 pts, 20%+ → 30 pts
    spread_bonus = clamp(spread / 20 * 30, 0, 30)

    raw = clamp(base + spread_bonus)
    status = "HEALTHY" if raw >= 65 else ("WEAKENING" if raw >= 40 else "RISK-OFF")

    return {
        "score":    raw,
        "status":   status,
        "avg_20d":  avg,
        "spread":   spread,
        "top3":     top3,
        "bot3":     bot3,
        "label":    "MOMENTUM",
        "value_str": f"{avg:+.1f}% 20d avg",
        "dir":      "↑" if avg > 0 else "↓",
        "dir_inv":  False,
    }


def score_macro(treasury: dict, eurusd: dict, fomc: dict) -> dict:
    """Score 0-100 based on yield, dollar, FOMC proximity."""
    y10      = treasury.get("yield_10yr")
    y_trend  = treasury.get("trend")
    eu_chg   = eurusd.get("change_pct")
    fomc_hrs = fomc.get("hours_until")

    yield_score = 50
    if y10 is not None:
        if y10 < YIELD_LOW:
            yield_score += 20
        elif y10 > YIELD_HIGH:
            yield_score -= 20
        if y_trend == "falling":
            yield_score += 10
        elif y_trend == "rising":
            yield_score -= 10

    # EURUSD rising → weak dollar → risk-on
    dollar_score = 0
    if eu_chg is not None:
        dollar_score = 30 if eu_chg > 0 else 0

    fomc_penalty = -20 if fomc_hrs is not None else 0

    raw = clamp(yield_score + dollar_score + fomc_penalty)
    status = "HEALTHY" if raw >= 65 else ("WEAKENING" if raw >= 40 else "RISK-OFF")

    return {
        "score":      raw,
        "status":     status,
        "yield_10yr": y10,
        "yield_trend":y_trend,
        "fomc_hrs":   fomc_hrs,
        "label":      "MACRO",
        "value_str":  f"{y10:.2f}%" if y10 else "N/A",
        "dir":        "↑" if y_trend == "rising" else ("↓" if y_trend == "falling" else "→"),
        "dir_inv":    True,  # rising yield = bad = dir_inv
    }


# ── Execution Window Score ────────────────────────────────────────────────────

def score_execution_window(spy: dict, sectors: dict, vix: dict) -> dict:
    """
    Separate score measuring whether setups are actually working right now.
    Does NOT feed into Market Quality Score.
    """
    base = 50

    # Breakout health: majority of sectors accelerating (5d > 20d trend direction)
    accel = 0
    for v in sectors.values():
        r5 = v.get("return_5d")
        r20 = v.get("return_20d")
        if r5 is not None and r20 is not None:
            # accelerating if 5d annualized > 20d annualized
            if r5 * 4 > r20:
                accel += 1
    n_sectors = len(SECTOR_ETFS)
    breakout_health = accel / n_sectors

    regime  = spy.get("regime")
    rsi     = spy.get("rsi14")
    price   = spy.get("price")
    sma20   = spy.get("sma20")
    slope   = vix.get("slope")

    bonuses = 0
    if breakout_health > 0.6:
        bonuses += 20
    if regime == "uptrend" and rsi is not None and rsi > 50:
        bonuses += 15   # follow-through
    if price is not None and sma20 is not None and price > sma20:
        bonuses += 15   # pullbacks being bought

    penalties = 0
    if slope is not None and slope > 0.5:
        penalties += 20   # VIX spiking
    if regime == "downtrend":
        penalties += 20

    raw = clamp(base + bonuses - penalties)
    status = "ACTIVE" if raw >= 65 else ("MIXED" if raw >= 40 else "BROKEN")

    return {
        "score":            raw,
        "status":           status,
        "breakout_health":  breakout_health,
        "follow_through":   regime == "uptrend" and rsi is not None and rsi > 50,
        "pullback_buying":  price is not None and sma20 is not None and price > sma20,
    }


# ── Master Score ──────────────────────────────────────────────────────────────

def compute_scores(data: dict, mode: str = "Swing") -> dict:
    """
    Entry point. Takes raw data dict from fetch_all(), returns full scores dict.
    """
    vix      = data.get("vix", {})
    spy      = data.get("spy", {})
    qqq      = data.get("qqq", {})
    sectors  = data.get("sectors", {})
    treasury = data.get("treasury", {})
    eurusd   = data.get("eurusd", {})
    fomc     = data.get("fomc", {})
    breadth  = data.get("breadth", {})

    cat = {
        "volatility": score_volatility(vix, mode),
        "trend":      score_trend(spy, qqq, mode),
        "breadth":    score_breadth(sectors, breadth),
        "momentum":   score_momentum(sectors),
        "macro":      score_macro(treasury, eurusd, fomc),
    }

    mqs = sum(cat[k]["score"] * WEIGHTS[k] for k in cat)
    mqs = round(clamp(mqs), 1)

    if mqs >= DECISION_THRESHOLDS["YES"]:
        decision = "YES"
    elif mqs >= DECISION_THRESHOLDS["CAUTION"]:
        decision = "CAUTION"
    else:
        decision = "NO"

    exec_window = score_execution_window(spy, sectors, vix)

    return {
        "categories":      cat,
        "market_quality":  mqs,
        "decision":        decision,
        "execution_window": exec_window,
    }


# ── Terminal Analysis Text ────────────────────────────────────────────────────

def generate_analysis(scores: dict, data: dict) -> str:
    """Rule-based plain-English summary."""
    mqs      = scores["market_quality"]
    decision = scores["decision"]
    cat      = scores["categories"]
    ew       = scores["execution_window"]
    fomc_hrs = data.get("fomc", {}).get("hours_until")
    regime   = data.get("spy", {}).get("regime", "unknown")

    # Environment quality
    if mqs >= 80:
        quality = "strong trend"
    elif mqs >= 65:
        quality = "constructive"
    elif mqs >= 50:
        quality = "mixed"
    else:
        quality = "hostile"

    # Breadth
    up = cat["breadth"].get("up_count", 0)
    n  = cat["breadth"].get("n_total", 11)
    if up >= 8:
        breadth_desc = "expanding breadth"
    elif up >= 5:
        breadth_desc = "selective breadth"
    else:
        breadth_desc = "narrow or negative breadth"

    # Volatility
    vix_lvl = data.get("vix", {}).get("level")
    if vix_lvl is not None:
        if vix_lvl < 15:
            vol_desc = "low volatility"
        elif vix_lvl < 25:
            vol_desc = "moderate volatility"
        else:
            vol_desc = "elevated volatility"
    else:
        vol_desc = "uncertain volatility"

    # Sector leadership
    top3 = cat["momentum"].get("top3", [])
    from config import SECTOR_NAMES
    if top3:
        leader_syms = [SECTOR_NAMES.get(s, s) for s, _ in top3]
        leaders_str = " and ".join(leader_syms[:2])
        sector_line = f" Sector leadership in {leaders_str}."
    else:
        sector_line = ""

    # Execution window
    ew_score = ew["score"]
    if ew_score >= 65:
        ew_line = " Setups are working — breakouts holding."
    elif ew_score >= 40:
        ew_line = " Execution window is mixed — be selective."
    else:
        ew_line = " Setups are failing — wait for follow-through."

    # FOMC
    fomc_line = ""
    if fomc_hrs is not None:
        fomc_line = f" ⚠ FOMC in {fomc_hrs:.0f}h — reduce size."

    # Recommendation
    if decision == "YES":
        rec = "Full position sizing. Press risk on A+ setups."
    elif decision == "CAUTION":
        rec = "Half size, A+ setups only. Protect capital."
    else:
        rec = "Stand aside. Preserve capital and wait for clarity."

    return (
        f"This is a {quality} environment with {breadth_desc} and {vol_desc}. "
        f"Regime: {(regime or 'unknown').upper()}.{sector_line}{ew_line}{fomc_line} — {rec}"
    )
