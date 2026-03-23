"""
Configuration: symbols, thresholds, scoring weights.
Edit this file to tune the scoring system without touching logic.
"""

import os
from dotenv import load_dotenv

load_dotenv()

def _get_secret(key: str, default: str = "") -> str:
    """Check os.getenv first, then st.secrets (Streamlit Cloud)."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default

# ── API ──────────────────────────────────────────────────────────────────────
FMP_API_KEY = _get_secret("FMP_API_KEY", "demo")
MARKETAUX_API_KEY = _get_secret("MARKETAUX_API_KEY", "")

# ── Symbols ───────────────────────────────────────────────────────────────────
SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]
SECTOR_NAMES = {
    "XLK":  "SPDR Technology Select Sector",
    "XLF":  "SPDR Financial Select Sector",
    "XLE":  "SPDR Energy Select Sector",
    "XLV":  "SPDR Health Care Select Sector",
    "XLI":  "SPDR Industrials Select Sector",
    "XLY":  "SPDR Consumer Discretionary Select Sector",
    "XLP":  "SPDR Consumer Staples Select Sector",
    "XLU":  "SPDR Utilities Select Sector",
    "XLB":  "SPDR Materials Select Sector",
    "XLRE": "SPDR Real Estate Select Sector",
    "XLC":  "SPDR Communication Services Select Sector",
}
TICKER_SYMBOLS = ["SPY", "QQQ", "^VIX", "EURUSD", "^TNX"] + SECTOR_ETFS

# ── Scoring Weights ───────────────────────────────────────────────────────────
WEIGHTS = {
    "volatility": 0.25,
    "momentum":   0.25,
    "trend":      0.20,
    "breadth":    0.20,
    "macro":      0.10,
}

# ── VIX Thresholds → Base Score ───────────────────────────────────────────────
VIX_SCORE_TIERS = [
    (15,  100),   # VIX < 15  → 100
    (20,   80),   # VIX 15-20 → 80
    (25,   60),   # VIX 20-25 → 60
    (30,   40),   # VIX 25-30 → 40
    (999,  20),   # VIX > 30  → 20
]

# ── Decision Thresholds ───────────────────────────────────────────────────────
DECISION_THRESHOLDS = {
    "YES":     80,
    "CAUTION": 60,
    # below 60 → NO
}

# ── Macro Thresholds ──────────────────────────────────────────────────────────
YIELD_LOW  = 4.0    # below this → bullish signal
YIELD_HIGH = 5.0    # above this → bearish signal
FOMC_WINDOW_HOURS = 72

# ── Mode Configs ──────────────────────────────────────────────────────────────
MODE_CONFIG = {
    "Swing": {
        "rsi_low":  40,
        "rsi_high": 75,
        "vix_penalty_multiplier": 1.0,
        "refresh_ms": 900_000,
    },
}

# ── UI ────────────────────────────────────────────────────────────────────────
COLORS = {
    "bg":         "#080b12",
    "surface":    "#0d1117",
    "surface2":   "#111827",
    "border":     "#1f2937",
    "border2":    "#374151",
    "green":      "#10b981",
    "amber":      "#f59e0b",
    "red":        "#ef4444",
    "cyan":       "#06b6d4",
    "blue":       "#3b82f6",
    "zone_red":   "#150a0a",
    "zone_amber": "#141008",
    "zone_green": "#0a1410",
    "text":       "#f1f5f9",
    "subtext":    "#94a3b8",
    "muted":      "#475569",
    "accent":     "#06b6d4",
    "glass":      "rgba(255,255,255,0.03)",
}
