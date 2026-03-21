# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the dashboard

```bash
cd /Users/robertfurse/Claude/dashboard
streamlit run app.py
```

Requires `FMP_API_KEY` in `.env` (gitignored). For Streamlit Cloud deployment, set it via the Secrets panel — `os.getenv()` in `config.py` picks it up automatically.

Install dependencies:
```bash
pip install -r requirements.txt
```

## Architecture

Data flows in one direction: `data_fetcher.py` → `scoring.py` → `app.py`.

**`config.py`** — single source of truth for all tunable values: sector ETF list, VIX score tiers, decision thresholds, scoring weights, mode config (RSI bounds, VIX penalty multiplier, refresh interval). Edit here to change behaviour without touching logic.

**`data_fetcher.py`** — one public function `fetch_all()` decorated with `@st.cache_data(ttl=30)`. Makes all FMP REST calls and returns a single dict. No nested cache calls. Uses the FMP **Stable API** (`https://financialmodelingprep.com/stable`) — v3 is deprecated. Key gotchas:
- VIX symbol must be `"^VIX"` (literal caret), not `"%5EVIX"` — `requests` will double-encode the `%`.
- Batch quote (`symbol=SPY,QQQ`) returns `[]` on the stable API — use individual calls.
- The stable technical-indicator endpoint returns `[]` — SMA and RSI are calculated locally via `_calc_sma()` and `_calc_rsi()`.
- `priceAvg50` / `priceAvg200` are available directly in the quote response.
- MOVE Index uses symbol `"MOVE"`. If the quote returns `None`, the fetcher falls back to the most recent historical close.

**`scoring.py`** — pure functions, no Streamlit imports. `compute_scores(data, mode)` is the entry point. Returns `categories` (5 scored dicts), `market_quality` (weighted composite 0–100), `decision` (YES/CAUTION/NO), and `execution_window` (separate score, not in MQS weighting). `generate_analysis()` produces the plain-English summary from scoring outputs.

**`app.py`** — all UI. Key layout order: JS sidebar-toggle removal → CSS → tooltips → font scale injection → sidebar → auto-refresh → data fetch → page render. `mode` is hardcoded to `"Swing"` at the top of the file (Day mode removed). `st.session_state["dashboard_data"]` is set after fetch so the sidebar API status block can read it.

## Scoring weights

| Category   | Weight |
|------------|--------|
| Volatility | 25%    |
| Momentum   | 25%    |
| Trend      | 20%    |
| Breadth    | 20%    |
| Macro      | 10%    |

Decision thresholds: ≥ 80 → YES, 60–79 → CAUTION, < 60 → NO.

## UI conventions

- All colours come from `COLORS` in `config.py`, aliased as `C` in `app.py`.
- Font: `Share Tech Mono` (Google Fonts) with `Courier New` fallback.
- HTML passed to `st.markdown()` must be collapsed to single-line strings — Streamlit treats 4+ space indented lines as code blocks and renders HTML as text.
- Tooltip system: `tt(text)` returns a hoverable `ⓘ` icon; tooltip definitions live in the `TIPS` dict near the top of `app.py`.
- Plotly charts use `paper_bgcolor="rgba(0,0,0,0)"` and `plot_bgcolor="rgba(0,0,0,0)"` to blend with the dark theme.
- The sidebar collapse button cannot be hidden via CSS alone — a JS `MutationObserver` injected via `st.components.v1.html` handles it.
- Main content font scale targets `[data-testid='stAppViewBlockContainer']` (not `html`) so the sidebar is unaffected.
