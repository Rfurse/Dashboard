"""
Configuration: symbols, thresholds, scoring weights.
Edit this file to tune the scoring system without touching logic.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API ──────────────────────────────────────────────────────────────────────
FMP_API_KEY = os.getenv("FMP_API_KEY", "demo")

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
        "refresh_ms": 45_000,
    },
    "Day": {
        "rsi_low":  45,
        "rsi_high": 70,
        "vix_penalty_multiplier": 1.3,   # harsher VIX penalty
        "refresh_ms": 20_000,
    },
}

# ── UI ────────────────────────────────────────────────────────────────────────
COLORS = {
    "bg":       "#0a0e1a",
    "surface":  "#0f1629",
    "border":   "#1e2d4a",
    "green":    "#00ff41",
    "amber":    "#ffab00",
    "red":      "#ff3b3b",
    "blue":     "#0ea5e9",
    "muted":    "#4a5568",
    "text":     "#e2e8f0",
    "subtext":  "#94a3b8",
}
