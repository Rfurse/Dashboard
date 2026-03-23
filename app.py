"""
Should I Be Trading? — Bloomberg Terminal-style Streamlit dashboard.
Run: streamlit run app.py
"""

import time
import streamlit as st
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from config import COLORS, SECTOR_NAMES, SECTOR_ETFS, MODE_CONFIG

mode = "Swing"
from data_fetcher import fetch_all, _last_quote_error
from scoring import compute_scores, generate_analysis

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Should I Be Trading?",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS — Bloomberg Terminal Style
# ─────────────────────────────────────────────────────────────────────────────

C = COLORS

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

  html, body, [class*="css"] {{
    font-family: 'Share Tech Mono', 'Courier New', monospace !important;
    background-color: {C['bg']} !important;
    color: {C['text']} !important;
  }}

  /* Hide Streamlit chrome + sidebar collapse arrow */
  #MainMenu, footer, header {{ visibility: hidden; height: 0 !important; }}

  /* Remove all top space — main content */
  .block-container {{ padding: 0 1rem 2rem 1rem !important; margin-top: 0 !important; }}
  [data-testid="stAppViewContainer"] > section:first-child {{ padding-top: 0 !important; }}
  [data-testid="stAppViewBlockContainer"] {{ padding-top: 0 !important; margin-top: 0 !important; }}
  .main > div:first-child {{ padding-top: 0 !important; }}
  .stApp > header {{ display: none !important; }}

  /* Remove all top space — sidebar */
  [data-testid="stSidebar"] > div:first-child {{ padding-top: 0 !important; margin-top: 0 !important; }}
  [data-testid="stSidebarContent"] {{ padding-top: 0.5rem !important; }}
  section[data-testid="stSidebar"] {{ padding-top: 0 !important; }}

  /* Hide sidebar toggle button and its tooltip — covers all Streamlit versions */
  [data-testid="collapsedControl"],
  [data-testid="stSidebarCollapsedControl"],
  [data-testid="stSidebarNavCollapseButton"],
  button[kind="header"],
  .st-emotion-cache-1rtdyuf,
  section[data-testid="stSidebar"] > div > div > button,
  [data-testid="stSidebar"] button[title*="keyboard"],
  [data-testid="stSidebar"] button[aria-label*="collapse"],
  [data-testid="stSidebar"] button[aria-label*="Close"] {{ display: none !important; }}

  /* Kill any tooltip that contains keyboard_double */
  [role="tooltip"] {{ display: none !important; }}

  /* Scrollbar */
  ::-webkit-scrollbar {{ width: 4px; }}
  ::-webkit-scrollbar-track {{ background: {C['bg']}; }}
  ::-webkit-scrollbar-thumb {{ background: {C['border']}; }}

  /* Card panels */
  .terminal-card {{
    background: {C['surface']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    padding: 14px 16px;
    margin-bottom: 8px;
    height: 100%;
  }}
  .terminal-card:hover {{ border-color: {C['blue']}44; }}

  /* Decision badge */
  .badge-yes     {{ color:{C['green']}; border:2px solid {C['green']}; }}
  .badge-caution {{ color:{C['amber']}; border:2px solid {C['amber']}; }}
  .badge-no      {{ color:{C['red']};   border:2px solid {C['red']};   }}
  .badge-base {{
    text-align: center;
    font-size: 3.5rem;
    font-weight: 900;
    letter-spacing: 6px;
    padding: 18px 30px;
    border-radius: 6px;
    display: inline-block;
    width: 100%;
    margin-top: 10px;
  }}

  /* Status labels */
  .label-healthy  {{ color:{C['green']}; font-size:.7rem; letter-spacing:2px; }}
  .label-weakening{{ color:{C['amber']}; font-size:.7rem; letter-spacing:2px; }}
  .label-risk-off {{ color:{C['red']};   font-size:.7rem; letter-spacing:2px; }}
  .label-active   {{ color:{C['green']}; font-size:.7rem; letter-spacing:2px; }}
  .label-mixed    {{ color:{C['amber']}; font-size:.7rem; letter-spacing:2px; }}
  .label-broken   {{ color:{C['red']};   font-size:.7rem; letter-spacing:2px; }}
  .label-unknown  {{ color:{C['muted']}; font-size:.7rem; letter-spacing:2px; }}

  /* Metric values */
  .metric-val {{
    font-size: 1.6rem;
    font-weight: 700;
    line-height: 1.1;
    margin: 4px 0;
  }}
  .metric-sub {{
    font-size: .72rem;
    color: {C['subtext']};
    margin-top: 2px;
  }}
  .metric-dir-up   {{ color:{C['green']}; }}
  .metric-dir-down {{ color:{C['red']};   }}
  .metric-dir-flat {{ color:{C['muted']}; }}

  /* Section headers */
  .section-header {{
    font-size: .65rem;
    letter-spacing: 3px;
    color: {C['subtext']};
    border-bottom: 1px solid {C['border']};
    padding-bottom: 4px;
    margin-bottom: 10px;
    text-transform: uppercase;
  }}

  /* Score bar */
  .score-bar-wrap {{
    background: {C['border']};
    border-radius: 2px;
    height: 4px;
    margin-top: 6px;
  }}
  .score-bar-fill {{
    height: 4px;
    border-radius: 2px;
    transition: width .5s;
  }}

  /* Ticker tape */
  .ticker-wrap {{
    background: {C['surface']};
    border-bottom: 1px solid {C['border']};
    padding: 6px 0;
    overflow: hidden;
    white-space: nowrap;
  }}
  .ticker-inner {{
    display: inline-block;
    animation: scroll-left 40s linear infinite;
  }}
  @keyframes scroll-left {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
  }}
  .ticker-item {{
    display: inline-block;
    margin: 0 20px;
    font-size: .78rem;
  }}
  .ticker-up   {{ color: {C['green']}; }}
  .ticker-down {{ color: {C['red']};   }}
  .ticker-flat {{ color: {C['subtext']}; }}

  /* News headline ticker */
  .news-ticker-wrap {{
    background: {C['surface']};
    border-top: 1px solid {C['border']};
    border-bottom: 1px solid {C['border']};
    padding: 7px 0;
    overflow: hidden;
    white-space: nowrap;
    margin-bottom: 12px;
  }}
  .news-ticker-inner {{
    display: inline-block;
    animation: scroll-left 80s linear infinite;
  }}
  .news-ticker-item {{
    display: inline-block;
    margin: 0 40px;
    font-size: .78rem;
    color: {C['text']};
    letter-spacing: .5px;
    text-decoration: none;
  }}
  a.news-ticker-item:hover {{
    color: {C['amber']};
    text-decoration: underline;
  }}
  .news-ticker-sep {{
    color: {C['amber']};
    margin: 0 8px;
  }}

  /* Analysis box */
  .analysis-box {{
    background: {C['surface']};
    border: 1px solid {C['border']};
    border-left: 3px solid {C['blue']};
    border-radius: 4px;
    padding: 14px 18px;
    font-size: .85rem;
    line-height: 1.6;
    color: {C['text']};
    margin-top: 4px;
  }}
  .analysis-label {{
    font-size:.6rem; letter-spacing:3px; color:{C['blue']};
    margin-bottom:6px; text-transform:uppercase;
  }}

  /* Sidebar */
  [data-testid="stSidebar"] {{
    background: {C['surface']} !important;
    border-right: 1px solid {C['border']};
  }}
  [data-testid="stSidebar"] * {{
    font-family: 'Share Tech Mono', monospace !important;
    color: {C['text']} !important;
  }}

  /* Streamlit radio buttons */
  .stRadio > div {{ flex-direction: column; gap: 4px; }}
  .stRadio label {{ font-size:.8rem !important; }}

  /* Plotly chart background */
  .js-plotly-plot .plotly .bg {{ fill: transparent !important; }}

  /* Table styling */
  .breakdown-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: .78rem;
  }}
  .breakdown-table th {{
    color: {C['subtext']};
    font-size: .62rem;
    letter-spacing: 2px;
    padding: 4px 8px;
    border-bottom: 1px solid {C['border']};
    text-align: left;
  }}
  .breakdown-table td {{
    padding: 6px 8px;
    border-bottom: 1px solid {C['border']}44;
  }}
  .live-dot {{
    display: inline-block;
    width: 8px; height: 8px;
    background: {C['green']};
    border-radius: 50%;
    margin-right: 6px;
    animation: pulse 1.5s ease-in-out infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity:1; }}
    50%       {{ opacity:.3; }}
  }}

  /* ── Tooltip system ── */
  .tt {{
    position: relative;
    display: inline-block;
    cursor: help;
  }}
  .tt-icon {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 14px;
    height: 14px;
    border: 1px solid {C['blue']};
    border-radius: 50%;
    color: {C['blue']};
    font-size: .58rem;
    font-weight: 700;
    margin-left: 5px;
    vertical-align: middle;
    line-height: 1;
    flex-shrink: 0;
  }}
  .tt-box {{
    visibility: hidden;
    opacity: 0;
    background: #0d1b33;
    color: {C['text']};
    border: 1px solid {C['blue']};
    border-radius: 4px;
    padding: 9px 12px;
    position: absolute;
    z-index: 9999;
    width: 260px;
    left: 22px;
    top: -4px;
    font-size: .72rem;
    line-height: 1.55;
    pointer-events: none;
    transition: opacity .15s ease;
    white-space: normal;
    box-shadow: 0 4px 16px rgba(0,0,0,.6);
  }}
  .tt-box b {{ color: {C['blue']}; }}
  .tt:hover .tt-box {{
    visibility: visible;
    opacity: 1;
  }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# JS: remove sidebar collapse button from DOM (CSS alone cannot reach it)
# ─────────────────────────────────────────────────────────────────────────────

import streamlit.components.v1 as components
components.html("""
<script>
(function() {
  function removeSidebarToggle() {
    var doc = window.parent.document;
    // Target the collapsed-control button (arrow that appears outside sidebar)
    var selectors = [
      '[data-testid="collapsedControl"]',
      '[data-testid="stSidebarCollapsedControl"]',
      '[data-testid="stSidebarNavCollapseButton"]'
    ];
    selectors.forEach(function(sel) {
      doc.querySelectorAll(sel).forEach(function(el) { el.style.display = 'none'; });
    });
    // Also hide any button whose text/title/aria-label contains "keyboard_double"
    doc.querySelectorAll('button').forEach(function(btn) {
      var txt = (btn.innerText || '') + (btn.getAttribute('aria-label') || '') + (btn.getAttribute('title') || '');
      if (txt.indexOf('keyboard_double') !== -1 || txt.indexOf('collapse') !== -1) {
        btn.style.display = 'none';
      }
    });
    // Hide any active tooltips
    doc.querySelectorAll('[role="tooltip"]').forEach(function(el) { el.style.display = 'none'; });
  }
  removeSidebarToggle();
  setTimeout(removeSidebarToggle, 300);
  setTimeout(removeSidebarToggle, 800);
  setTimeout(removeSidebarToggle, 2000);
  // MutationObserver to catch re-renders
  var observer = new MutationObserver(function() { removeSidebarToggle(); });
  observer.observe(window.parent.document.body, { childList: true, subtree: true });
})();
</script>
""", height=0)

# ─────────────────────────────────────────────────────────────────────────────
# Tooltip helper + definitions
# ─────────────────────────────────────────────────────────────────────────────

def tt(text: str) -> str:
    """Return a hoverable ⓘ icon that shows `text` as a tooltip."""
    safe = text.replace("'", "&#39;").replace('"', "&quot;")
    return f"<span class='tt'><span class='tt-icon'>i</span><span class='tt-box'>{text}</span></span>"

TIPS = {
    "decision": (
        "<b>Trading Decision</b><br>"
        "YES ≥ 80 — full size, press risk.<br>"
        "CAUTION 60–79 — half size, A+ setups only.<br>"
        "NO &lt; 60 — stand aside, preserve capital.<br><br>"
        "<b>Calc:</b> weighted average of all 5 category scores."
    ),
    "mqs": (
        "<b>Market Quality Score</b><br>"
        "0–100 composite score of the overall trading environment.<br><br>"
        "<b>Weights:</b> Volatility 25% · Momentum 25% · Trend 20% · Breadth 20% · Macro 10%.<br><br>"
        "Higher = safer, more productive environment for swing trades."
    ),
    "ews": (
        "<b>Execution Window Score</b><br>"
        "Separate from MQS — measures whether setups are <i>actually working</i> right now, not just whether conditions look good on paper.<br><br>"
        "<b>Bonuses:</b> +20 breakouts holding · +15 follow-through · +15 pullbacks bought.<br>"
        "<b>Penalties:</b> −20 VIX spiking · −20 downtrend.<br><br>"
        "ACTIVE ≥ 65 · MIXED 40–64 · BROKEN &lt; 40."
    ),
    "volatility": (
        "<b>Volatility Score (25% weight)</b><br>"
        "Measures market fear and uncertainty using VIX.<br><br>"
        "<b>Calc:</b> VIX level sets base score (&lt;15→100, 15–20→80, 20–25→60, 25–30→40, &gt;30→20). "
        "Adjusted by 5-day slope (falling VIX +10, rising −10) and 1-year percentile rank (±10).<br><br>"
        "Low VIX + falling trend = HEALTHY."
    ),
    "trend": (
        "<b>Trend Score (20% weight)</b><br>"
        "Measures price structure relative to key moving averages.<br><br>"
        "<b>Calc:</b> SPY &gt; 200d SMA +40 · SPY &gt; 50d SMA +30 · SPY &gt; 20d SMA +20 · QQQ &gt; 50d SMA +10. "
        "RSI modifier: RSI &gt; 75 −10 (overbought) · RSI &lt; 30 +5 (oversold).<br><br>"
        "All MAs aligned above price = UPTREND."
    ),
    "breadth": (
        "<b>Breadth Score (20% weight)</b><br>"
        "Measures how many stocks/sectors are participating in the move.<br><br>"
        "<b>Calc:</b> % of 11 sector ETFs with positive 5-day return (×70 pts) + "
        "gainers/losers ratio from market movers as A/D proxy (×30 pts).<br><br>"
        "High breadth = broad rally, low risk of sudden reversal."
    ),
    "momentum": (
        "<b>Momentum Score (25% weight)</b><br>"
        "Measures the strength and rotation of sector performance.<br><br>"
        "<b>Calc:</b> Average 20-day return across all 11 sectors normalised to 0–70 pts. "
        "Leadership spread (top 3 avg − bottom 3 avg) adds 0–30 pts.<br><br>"
        "Strong positive spread = healthy rotation and leadership."
    ),
    "macro": (
        "<b>Macro Score (10% weight)</b><br>"
        "Measures liquidity and macro headwind/tailwind.<br><br>"
        "<b>Calc:</b> 10yr yield base 50 pts (&lt;4% +20, &gt;5% −20), adjusted ±10 by 5-day yield trend. "
        "EURUSD rising (weak dollar, risk-on) +30. FOMC within 72h −20.<br><br>"
        "Falling yields + weak dollar + no FOMC = HEALTHY."
    ),
    "vix": (
        "<b>VIX — CBOE Volatility Index</b><br>"
        "Measures the market's expectation of 30-day S&amp;P 500 volatility.<br><br>"
        "Below 15: calm · 15–20: normal · 20–25: elevated · 25–30: high fear · Above 30: extreme fear.<br><br>"
        "Arrow shows 5-day slope direction. Percentile ranks today vs last 252 trading days."
    ),
    "move": (
        "<b>MOVE Index — ICE BofA Bond Volatility</b><br>"
        "Measures implied volatility in US Treasury options — the bond market's equivalent of VIX.<br><br>"
        "Elevated MOVE signals stress in the rates market, which often precedes equity volatility.<br><br>"
        "1yr percentile ranks today's reading vs the past year. High MOVE applies a small penalty to the Volatility score."
    ),
    "regime": (
        "<b>Market Regime</b><br>"
        "UPTREND: SPY above both 50d and 200d SMA — favours longs.<br>"
        "DOWNTREND: SPY below both — avoid new longs.<br>"
        "CHOP: mixed MA alignment — reduce size, wait for resolution.<br><br>"
        "Derived from SPY price vs 20d / 50d / 200d simple moving averages."
    ),
    "rsi": (
        "<b>RSI-14 — Relative Strength Index</b><br>"
        "Momentum oscillator measuring speed and magnitude of recent price moves on a 0–100 scale.<br><br>"
        "Below 30: oversold (potential bounce) · 30–50: weakening · 50–70: healthy momentum · Above 70: overbought.<br><br>"
        "Swing mode healthy zone: 40–75."
    ),
    "breadth_ratio": (
        "<b>Advance / Decline Proxy</b><br>"
        "Ratio of stocks advancing vs declining, approximated from FMP's market gainers and losers lists.<br><br>"
        "Above 60%: broad buying pressure · Below 40%: broad selling · Near 50%: indecisive."
    ),
    "yield": (
        "<b>10-Year Treasury Yield</b><br>"
        "Benchmark rate for borrowing costs and equity discount rates.<br><br>"
        "Rising yields = tighter financial conditions, headwind for growth stocks. "
        "Falling yields = easier conditions, tailwind for equities.<br><br>"
        "Arrow shows direction vs 5 trading days ago."
    ),
    "spread": (
        "<b>Sector Leadership Spread</b><br>"
        "Top 3 sector 20-day return average minus bottom 3 sector average.<br><br>"
        "Wide positive spread = clear leadership, healthy rotation. "
        "Narrow or negative spread = no leadership, choppy environment."
    ),
    "eurusd": (
        "<b>EUR/USD — Dollar Strength Proxy</b><br>"
        "Rising EURUSD = weakening US dollar = risk-on environment (bullish for equities). "
        "Falling EURUSD = strengthening dollar = risk-off headwind.<br><br>"
        "Used as an inverse proxy for DXY (US Dollar Index)."
    ),
    "fomc": (
        "<b>FOMC Event Flag</b><br>"
        "Federal Open Market Committee meetings set US interest rate policy.<br><br>"
        "Within 72 hours of an FOMC decision, volatility typically rises and breakouts become unreliable. "
        "Score applies a −20 penalty to the Macro category when an event is imminent."
    ),
}

def elapsed_str(dt: datetime) -> str:
    secs = int((datetime.utcnow() - dt).total_seconds())
    if secs < 60:
        return f"{secs}s ago"
    return f"{secs//60}m ago"


# Dynamic font scale — injected after session state is available
if "font_scale" not in st.session_state:
    st.session_state.font_scale = 75
_scale = st.session_state.font_scale
st.markdown(f"<style>[data-testid='stAppViewBlockContainer'] {{ font-size: {_scale}% !important; }}</style>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

if "font_scale" not in st.session_state:
    st.session_state.font_scale = 75  # percent, 70–130

with st.sidebar:
    # ── Logo graphic ─────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="padding:12px 8px 4px 8px;">
      <svg viewBox="0 0 200 64" xmlns="http://www.w3.org/2000/svg" style="width:100%;display:block;">
        <!-- Grid lines -->
        <line x1="0" y1="16" x2="200" y2="16" stroke="{C['border']}" stroke-width="0.5"/>
        <line x1="0" y1="32" x2="200" y2="32" stroke="{C['border']}" stroke-width="0.5"/>
        <line x1="0" y1="48" x2="200" y2="48" stroke="{C['border']}" stroke-width="0.5"/>
        <!-- Area fill under line -->
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="{C['green']}" stop-opacity="0.18"/>
            <stop offset="100%" stop-color="{C['green']}" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <polygon points="0,52 20,48 38,44 55,46 70,36 85,30 100,34 112,22 125,18 138,24 150,14 162,20 175,10 190,6 200,8 200,64 0,64"
          fill="url(#areaGrad)"/>
        <!-- Price line -->
        <polyline points="0,52 20,48 38,44 55,46 70,36 85,30 100,34 112,22 125,18 138,24 150,14 162,20 175,10 190,6 200,8"
          fill="none" stroke="{C['green']}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>
        <!-- Glowing end dot -->
        <circle cx="200" cy="8" r="3.5" fill="{C['green']}" opacity="0.9"/>
        <circle cx="200" cy="8" r="6" fill="{C['green']}" opacity="0.2"/>
        <!-- Label -->
        <text x="6" y="62" font-family="Share Tech Mono, Courier New, monospace"
          font-size="9" fill="{C['subtext']}" letter-spacing="2">SHOULD I BE TRADING</text>
      </svg>
    </div>
    """, unsafe_allow_html=True)

    # ── LIVE status + last updated clock (moved to top) ──────────────────────
    st.markdown("---")
    _fetched: datetime = st.session_state.get("last_fetched", datetime.utcnow())
    _elapsed = elapsed_str(_fetched)
    _ET = ZoneInfo("America/New_York")
    _fetched_utc = _fetched.replace(tzinfo=timezone.utc)
    _fetched_et  = _fetched_utc.astimezone(_ET)
    _et_str = _fetched_et.strftime("%H:%M:%S %Z")
    _et_date = _fetched_et.strftime("%b %d, %Y")
    _live_col, _refresh_col = st.columns([3, 1])
    with _live_col:
        st.markdown(
            f"<div style='font-size:.72rem;margin-bottom:6px;'>"
            f"<span class='live-dot'></span>"
            f"<span style='color:{C['green']};'>LIVE</span>"
            f"<span style='color:{C['muted']};margin-left:8px;'>{_elapsed}</span>"
            f"</div>"
            f"<div style='font-size:.68rem;color:{C['subtext']};margin-bottom:2px;'>LAST UPDATED</div>"
            f"<div style='font-size:.82rem;color:{C['text']};letter-spacing:1px;'>{_et_str}</div>"
            f"<div style='font-size:.66rem;color:{C['muted']};'>Eastern Time Zone &nbsp;·&nbsp; {_et_date}</div>",
            unsafe_allow_html=True,
        )
    with _refresh_col:
        st.markdown("<div style='transform:scale(0.55);transform-origin:top right;margin-top:2px;'>", unsafe_allow_html=True)
        refresh_btn = st.button("↺", use_container_width=True, help="Manual refresh")
        st.markdown("</div>", unsafe_allow_html=True)
        if refresh_btn:
            st.cache_data.clear()
            st.rerun()
    import streamlit.components.v1 as _cv1
    _cv1.html(f"""
    <div id="tz-clock" style="font-family:'Share Tech Mono',monospace;font-size:.72rem;color:{C['subtext']};margin-top:6px;line-height:1.7;">
      <div>NOW (ET) &nbsp;&nbsp;<span id="et-now" style="color:{C['text']};"></span></div>
      <div>NOW (UTC) &nbsp;<span id="utc-now" style="color:{C['text']};"></span></div>
    </div>
    <script>
    (function(){{
      function pad(n){{return n<10?'0'+n:n;}}
      function tick(){{
        var now=new Date();
        var utcStr=pad(now.getUTCHours())+':'+pad(now.getUTCMinutes())+':'+pad(now.getUTCSeconds());
        var etStr=now.toLocaleTimeString('en-US',{{timeZone:'America/New_York',hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'}});
        var el=document.getElementById('utc-now');
        var el2=document.getElementById('et-now');
        if(el)el.innerText=utcStr;
        if(el2)el2.innerText=etStr;
      }}
      tick();
      setInterval(tick,1000);
    }})();
    </script>
    """, height=56)

    # API status — shown after data loads
    if "dashboard_data" in st.session_state:
        _d = st.session_state["dashboard_data"]
        _ok = _d.get("api_ok", False)
        _errs = _d.get("errors", [])
        st.markdown("---")
        st.markdown(f"<div class='section-header'>API STATUS</div>", unsafe_allow_html=True)
        if _ok:
            st.markdown(f"<div style='font-size:.68rem;color:{C['green']};'>● CONNECTED</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-size:.68rem;color:{C['red']};'>● ERRORS ({len(_errs)})</div>", unsafe_allow_html=True)
        for e in _errs[:4]:
            st.markdown(f"<div style='font-size:.6rem;color:{C['amber']};margin-top:2px;'>⚠ {e}</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div class='section-header'>SCORING WEIGHTS</div>", unsafe_allow_html=True)
    from config import WEIGHTS
    for cat, w in WEIGHTS.items():
        st.markdown(f"<div style='font-size:.72rem;display:flex;justify-content:space-between;margin-bottom:4px;'><span>{cat.upper()}</span><span style='color:{C['blue']};'>{int(w*100)}%</span></div>", unsafe_allow_html=True)


    # ── FONT SIZE (moved to bottom, compact) ─────────────────────────────────
    st.markdown("---")
    fs_col1, fs_col2, fs_col3, fs_col4 = st.columns([1.2, 1.2, 1, 1.5])
    with fs_col1:
        if st.button("A−", use_container_width=True, help="Decrease font size"):
            st.session_state.font_scale = max(70, st.session_state.font_scale - 10)
    with fs_col2:
        if st.button("A+", use_container_width=True, help="Increase font size"):
            st.session_state.font_scale = min(130, st.session_state.font_scale + 10)
    with fs_col3:
        if st.button("↺", use_container_width=True, help="Reset font size"):
            st.session_state.font_scale = 75
    with fs_col4:
        st.markdown(f"<div style='padding-top:6px;font-size:.72rem;color:{C['muted']};'>font {st.session_state.font_scale}%</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div style='font-size:.65rem;color:{C['muted']};'>Data: Financial Modeling Prep<br>Refresh: {MODE_CONFIG[mode]['refresh_ms']//60000}m</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Auto-refresh
# ─────────────────────────────────────────────────────────────────────────────

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=MODE_CONFIG[mode]["refresh_ms"], key=f"autorefresh_{mode}")
except ImportError:
    pass  # graceful: manual refresh still works


# ─────────────────────────────────────────────────────────────────────────────
# Data + Scores
# ─────────────────────────────────────────────────────────────────────────────

if "last_fetched" not in st.session_state:
    st.session_state.last_fetched = datetime.utcnow()

with st.spinner(""):
    data   = fetch_all()
    scores = compute_scores(data, mode)
    analysis_text = generate_analysis(scores, data)

st.session_state.last_fetched    = data.get("fetched_at", datetime.utcnow())
st.session_state["dashboard_data"] = data   # exposes errors to sidebar


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def score_color(s: float) -> str:
    if s >= 70:
        return C["green"]
    if s >= 45:
        return C["amber"]
    return C["red"]


def status_html(status: str) -> str:
    cls = f"label-{status.lower().replace(' ', '-')}"
    return f"<span class='{cls}'>◆ {status}</span>"


def dir_class(arrow: str, inv: bool = False) -> str:
    if arrow == "↑":
        return "metric-dir-down" if inv else "metric-dir-up"
    if arrow == "↓":
        return "metric-dir-up" if inv else "metric-dir-down"
    return "metric-dir-flat"


def score_bar_html(score: float) -> str:
    color = score_color(score)
    return f"<div class='score-bar-wrap'><div class='score-bar-fill' style='width:{score}%;background:{color};'></div></div>"


def fmt(v, fmt_str=".2f", fallback="N/A"):
    if v is None:
        return fallback
    try:
        return format(v, fmt_str)
    except Exception:
        return fallback


def gauge_chart(score: float, label: str, size: int = 220) -> go.Figure:
    color = score_color(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"color": color, "size": 32, "family": "Courier New"}, "suffix": "%"},
        title={"text": label, "font": {"color": C["subtext"], "size": 11, "family": "Courier New"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": C["muted"],
                     "tickfont": {"color": C["muted"], "size": 9}},
            "bar":  {"color": color, "thickness": 0.25},
            "bgcolor": C["surface"],
            "borderwidth": 0,
            "steps": [
                {"range": [0,  60], "color": "#1a0a0a"},
                {"range": [60, 80], "color": "#1a1500"},
                {"range": [80, 100], "color": "#0a1a0a"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.75,
                "value": score,
            },
        },
    ))
    fig.update_layout(
        height=size, margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Courier New", "color": C["text"]},
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TOP BAR — Scrolling Ticker
# ─────────────────────────────────────────────────────────────────────────────


# ── API diagnostic (shown when quotes are missing) ───────────────────────────
_errs = data.get("errors", [])
_spy_price = data.get("spy", {}).get("price")
if _spy_price is None:
    _diag_err = _last_quote_error[0] or (_errs[0] if _errs else "Unknown — check FMP_API_KEY in .env")
    st.markdown(f"<div style='background:#1a0a0a;border:1px solid {C['red']};border-radius:4px;padding:8px 14px;font-size:.75rem;color:{C['red']};margin-bottom:6px;'>⚠ API data unavailable — {_diag_err}<br><span style='color:{C['muted']};'>Ensure FMP_API_KEY is set in dashboard/.env and restart: <code style='color:{C['amber']};'>streamlit run app.py</code></span></div>", unsafe_allow_html=True)

# Build ticker
spy_q   = data.get("spy", {})
qqq_q   = data.get("qqq", {})
vix_q   = data.get("vix", {})
tsy_q   = data.get("treasury", {})
eu_q    = data.get("eurusd", {})
sec_q   = data.get("sectors", {})

def ticker_item(sym: str, price, chg) -> str:
    if price is None:
        return f"<span class='ticker-item ticker-flat'>{sym} N/A</span>"
    chg_str = f"{chg:+.2f}%" if chg is not None else ""
    cls = "ticker-up" if (chg or 0) >= 0 else "ticker-down"
    arrow = "▲" if (chg or 0) >= 0 else "▼"
    return f"<span class='ticker-item {cls}'>{sym} {price:.2f} {arrow}{chg_str}</span>"

ticker_items = (
    ticker_item("SPY",  spy_q.get("price"),  spy_q.get("change_pct")) +
    ticker_item("QQQ",  qqq_q.get("price"),  qqq_q.get("change_pct")) +
    ticker_item("VIX",  vix_q.get("level"),  None) +
    ticker_item("EURUSD", eu_q.get("rate"),  eu_q.get("change_pct")) +
    ticker_item("TNX",  tsy_q.get("yield_10yr"), None)
)
for sym in SECTOR_ETFS:
    sv = sec_q.get(sym, {})
    ticker_items += ticker_item(sym, sv.get("price"), sv.get("change_1d"))

# Duplicate for seamless loop
ticker_html = f"""
<div class='ticker-wrap'>
  <div class='ticker-inner'>
    {ticker_items}{ticker_items}
  </div>
</div>
"""
st.markdown(ticker_html, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL ANALYSIS (below ticker)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(f"<div class='analysis-box' style='margin:8px 0;'><div class='analysis-label'>TERMINAL ANALYSIS {tt(TIPS['mqs'])}</div>{analysis_text}</div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# NEWS HEADLINE TICKER
# ─────────────────────────────────────────────────────────────────────────────

headlines = data.get("headlines", [])
if headlines:
    sep = "<span class='news-ticker-sep'>◆</span>"
    parts = []
    for h in headlines:
        t, u = h.get("title", ""), h.get("url", "")
        parts.append(f"<a class='news-ticker-item' href='{u}' target='_blank'>{t}</a>" if u else f"<span class='news-ticker-item'>{t}</span>")
    items_html = sep.join(parts)
    doubled = items_html + sep + items_html  # duplicate for seamless loop
    st.markdown(f"<div class='news-ticker-wrap'><div class='news-ticker-inner'>{doubled}</div></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HERO PANEL
# ─────────────────────────────────────────────────────────────────────────────

decision   = scores["decision"]
mqs        = scores["market_quality"]
ew         = scores["execution_window"]
ew_score   = ew["score"]

badge_cls = {
    "YES":     "badge-yes",
    "CAUTION": "badge-caution",
    "NO":      "badge-no",
}[decision]
badge_color = {
    "YES":     C["green"],
    "CAUTION": C["amber"],
    "NO":      C["red"],
}[decision]

sizing_text = {
    "YES":     "FULL SIZE — PRESS RISK",
    "CAUTION": "HALF SIZE — A+ ONLY",
    "NO":      "STAND ASIDE — PRESERVE CAPITAL",
}[decision]

h_left, h_mid, h_right = st.columns([2, 2, 3])

with h_left:
    st.markdown(f"<div class='terminal-card' style='text-align:center;padding:20px 16px;'><div class='section-header' style='text-align:center;border:none;'>TRADING DECISION {tt(TIPS['decision'])}</div><div class='badge-base {badge_cls}'>{decision}</div><div style='font-size:.72rem;color:{badge_color};letter-spacing:2px;margin-top:10px;'>{sizing_text}</div><div style='font-size:.65rem;color:{C['muted']};margin-top:8px;'>SWING TRADING</div></div>", unsafe_allow_html=True)

with h_mid:
    st.markdown(f"<div class='terminal-card' style='padding:8px;'><div style='font-size:.62rem;color:{C['subtext']};text-align:right;padding:2px 4px 0 0;'>{tt(TIPS['mqs'])}</div>", unsafe_allow_html=True)
    st.plotly_chart(gauge_chart(mqs, "MARKET QUALITY SCORE", 220), use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

with h_right:
    st.markdown(f"<div class='terminal-card' style='padding:8px 8px 0 8px;'><div style='font-size:.62rem;color:{C['subtext']};text-align:right;padding:2px 4px 0 0;'>{tt(TIPS['ews'])}</div>", unsafe_allow_html=True)
    st.plotly_chart(gauge_chart(ew_score, "EXECUTION WINDOW SCORE", 180), use_container_width=True, config={"displayModeBar": False})

    ew_status = ew["status"]
    ew_color  = C["green"] if ew_status == "ACTIVE" else (C["amber"] if ew_status == "MIXED" else C["red"])
    st.markdown(f"<div style='font-size:.72rem;padding:0 8px 8px 8px;'><div class='analysis-label'>EXECUTION STATUS</div><div style='color:{ew_color};font-size:.8rem;'>◆ {ew_status}</div><div class='metric-sub' style='margin-top:4px;'>{'✓' if ew['breakout_health'] > 0.6 else '✗'} Breakouts holding &nbsp; {'✓' if ew['follow_through'] else '✗'} Follow-through &nbsp; {'✓' if ew['pullback_buying'] else '✗'} Dips bought</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CORE PANELS — 5 Categories
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("<div class='section-header'>CATEGORY BREAKDOWN</div>", unsafe_allow_html=True)

cat = scores["categories"]
panels = ["volatility", "trend", "breadth", "momentum", "macro"]
cols   = st.columns(5)

panel_labels = {
    "volatility": "VOLATILITY",
    "trend":      "TREND",
    "breadth":    "BREADTH",
    "momentum":   "MOMENTUM",
    "macro":      "MACRO",
}

for i, key in enumerate(panels):
    c = cat[key]
    score   = c["score"]
    status  = c["status"]
    label   = c["label"]
    val_str = c["value_str"]
    arrow   = c["dir"]
    inv     = c.get("dir_inv", False)
    color   = score_color(score)
    dircls  = dir_class(arrow, inv)

    with cols[i]:
        st.markdown(f"<div class='terminal-card'><div class='section-header'>{panel_labels[key]} {tt(TIPS[key])}</div><div style='font-size:.65rem;color:{C['muted']};'>{label}</div><div class='metric-val' style='color:{color};'><span class='{dircls}'>{arrow}</span> {val_str}</div><div class='metric-sub'>Score: {score:.0f}/100</div>{score_bar_html(score)}<div style='margin-top:8px;'>{status_html(status)}</div></div>", unsafe_allow_html=True)

        # Extra stats per panel
        if key == "volatility":
            pct       = c.get("percentile")
            slp       = c.get("slope")
            move_lvl  = c.get("move_level")
            move_pct  = c.get("move_pct")
            move_chg  = c.get("move_chg")
            move_chg_str = f" ({move_chg:+.1f}%)" if move_chg is not None else ""
            move_color   = C["red"] if (move_pct or 0) > 75 else (C["amber"] if (move_pct or 0) > 50 else C["green"])
            st.markdown(
                f"<div style='font-size:.67rem;color:{C['subtext']};margin-top:6px;padding:0 4px;'>"
                f"VIX 1yr pct: {fmt(pct, '.0f')}% {tt(TIPS['vix'])}<br>"
                f"5d slope: {fmt(slp, '+.2f')}<br>"
                f"<span style='color:{C['subtext']};'>MOVE close: </span>"
                f"<span style='color:{move_color};font-weight:700;'>{fmt(move_lvl, '.2f')}</span>"
                f" {tt(TIPS['move'])}<br>"
                f"<span style='color:{C['subtext']};'>MOVE chg: </span>"
                f"<span style='color:{move_color};'>{move_chg_str.strip() if move_chg_str else 'N/A'}</span><br>"
                f"<span style='color:{C['subtext']};'>MOVE 1yr pct: {fmt(move_pct, '.0f')}%</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        elif key == "trend":
            rsi  = c.get("rsi")
            s20  = c.get("sma20")
            s50  = c.get("sma50")
            s200 = c.get("sma200")
            p    = c.get("price")
            st.markdown(f"<div style='font-size:.67rem;color:{C['subtext']};margin-top:6px;padding:0 4px;'>RSI14: {fmt(rsi, '.1f')} {tt(TIPS['rsi'])}<br>{'✓' if (p and s20 and p > s20) else '✗'} SMA20 &nbsp; {'✓' if (p and s50 and p > s50) else '✗'} SMA50 &nbsp; {'✓' if (p and s200 and p > s200) else '✗'} SMA200 {tt(TIPS['regime'])}</div>", unsafe_allow_html=True)

        elif key == "breadth":
            up = c.get("up_count", 0)
            n  = c.get("n_total", 11)
            r  = c.get("ratio")
            st.markdown(f"<div style='font-size:.67rem;color:{C['subtext']};margin-top:6px;padding:0 4px;'>Sectors up: {up}/{n}<br>A/D proxy: {fmt(r, '.0%')} {tt(TIPS['breadth_ratio'])}</div>", unsafe_allow_html=True)

        elif key == "momentum":
            avg = c.get("avg_20d")
            sprd = c.get("spread")
            st.markdown(f"<div style='font-size:.67rem;color:{C['subtext']};margin-top:6px;padding:0 4px;'>Avg 20d: {fmt(avg, '+.1f')}%<br>Spread: {fmt(sprd, '.1f')}% {tt(TIPS['spread'])}</div>", unsafe_allow_html=True)

        elif key == "macro":
            y10  = c.get("yield_10yr")
            ytr  = c.get("yield_trend", "—")
            fhrs = c.get("fomc_hrs")
            st.markdown(f"<div style='font-size:.67rem;color:{C['subtext']};margin-top:6px;padding:0 4px;'>10yr: {fmt(y10, '.2f')}% {tt(TIPS['yield'])}<br>EUR/USD trend {tt(TIPS['eurusd'])}<br>{'⚠ FOMC: ' + str(int(fhrs or 0)) + 'h' if fhrs else 'No FOMC'} {tt(TIPS['fomc'])}</div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR HEATMAP
# ─────────────────────────────────────────────────────────────────────────────

hmap_cols = st.columns([6, 1])
with hmap_cols[0]:
    hmap_period = st.radio("", ["1D", "5D"], horizontal=True, key="hmap_period", label_visibility="collapsed")
with hmap_cols[1]:
    st.markdown("")  # spacer

st.markdown(f"<div class='section-header'>SECTOR HEATMAP — {hmap_period} PERFORMANCE</div>", unsafe_allow_html=True)

sec_data = data.get("sectors", {})
hmap_items = []
for sym in SECTOR_ETFS:
    v = sec_data.get(sym, {})
    r5    = v.get("return_5d")
    r1    = v.get("change_1d")
    price = v.get("price")
    if hmap_period == "1D":
        val = r1 if r1 is not None else 0.001
    else:
        src = v.get("data_source", "1d")
        val = r5 if r5 is not None else (r1 if r1 is not None else 0.001)
    hmap_items.append({
        "sym":    sym,
        "name":   SECTOR_NAMES.get(sym, sym),
        "val":    val,
        "price":  price,
    })

hmap_items.sort(key=lambda x: x["val"], reverse=True)

vals   = [x["val"]  for x in hmap_items]
labels = [f"{x['sym']} ({x['name']})" for x in hmap_items]
colors = [C["green"] if v >= 0 else C["red"] for v in vals]
text_labels = [
    f"${x['price']:.2f}  {x['val']:+.2f}%"
    if x["price"] is not None else
    f"{x['val']:+.2f}%"
    for x in hmap_items
]

fig_hmap = go.Figure()
fig_hmap.add_trace(go.Bar(
    x=vals,
    y=labels,
    orientation="h",
    marker_color=colors,
    marker_opacity=1.0,
    text=text_labels,
    textposition="outside",
    textfont={"size": 12, "color": C["text"], "family": "Share Tech Mono, Courier New, monospace"},
    hovertemplate="<b>%{y}</b><br>Return: %{x:.2f}%<extra></extra>",
    name="Return",
))

fig_hmap.update_layout(
    height=360,
    margin=dict(l=360, r=100, t=10, b=20),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"family": "Share Tech Mono, Courier New, monospace", "color": C["text"], "size": 12},
    xaxis=dict(
        gridcolor=C["border"],
        zerolinecolor=C["muted"],
        ticksuffix="%",
        tickfont={"size": 12},
    ),
    yaxis=dict(
        gridcolor="rgba(0,0,0,0)",
        tickfont={"size": 12},
    ),
    showlegend=False,
)

st.plotly_chart(fig_hmap, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────────────
# SCORING BREAKDOWN
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("<div class='section-header'>SCORING BREAKDOWN</div>", unsafe_allow_html=True)

from config import WEIGHTS

bd_cols = st.columns([3, 2])

with bd_cols[0]:
    rows = ""
    for key in panels:
        c   = cat[key]
        w   = WEIGHTS[key]
        s   = c["score"]
        contrib = s * w
        color = score_color(s)
        bar = f"<div style='background:{C['border']};border-radius:2px;height:4px;width:100%;'><div style='background:{color};height:4px;border-radius:2px;width:{s}%;'></div></div>"
        rows += f"<tr><td>{panel_labels[key]}</td><td style='color:{C['subtext']};'>{int(w*100)}%</td><td style='color:{color};font-weight:700;'>{s:.0f}</td><td style='width:120px;'>{bar}</td><td style='color:{C['subtext']};'>{contrib:.1f}</td></tr>"
    mqs_color = score_color(mqs)
    table_html = (
        f"<table class='breakdown-table'>"
        f"<thead><tr><th>CATEGORY</th><th>WEIGHT</th><th>SCORE</th><th>BAR</th><th>CONTRIB</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        f"<tfoot><tr style='border-top:1px solid {C['border']};'>"
        f"<td colspan='4' style='font-size:.75rem;padding-top:8px;'>MARKET QUALITY SCORE</td>"
        f"<td style='color:{mqs_color};font-size:1.1rem;font-weight:700;padding-top:8px;'>{mqs:.1f}</td>"
        f"</tr></tfoot></table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)

with bd_cols[1]:
    # Mini donut-style contribution chart
    contrib_vals  = [cat[k]["score"] * WEIGHTS[k] for k in panels]
    contrib_labels = [panel_labels[k] for k in panels]
    contrib_colors = [score_color(cat[k]["score"]) for k in panels]

    fig_pie = go.Figure(go.Pie(
        labels=contrib_labels,
        values=contrib_vals,
        hole=0.6,
        marker=dict(colors=contrib_colors, line=dict(color=C["bg"], width=2)),
        textinfo="label+percent",
        textfont={"size": 9, "family": "Courier New"},
        hovertemplate="<b>%{label}</b><br>Contribution: %{value:.1f}<extra></extra>",
    ))
    fig_pie.update_layout(
        height=220,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Courier New", "color": C["text"], "size": 9},
        showlegend=False,
        annotations=[dict(
            text=f"<b>{mqs:.0f}</b>",
            x=0.5, y=0.5, showarrow=False,
            font={"size": 26, "color": score_color(mqs), "family": "Courier New"},
        )],
    )
    st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style='margin-top:24px;padding-top:10px;border-top:1px solid {C['border']};
     font-size:.62rem;color:{C['muted']};display:flex;justify-content:space-between;'>
  <span>DATA: FINANCIAL MODELING PREP API</span>
  <span>NOT FINANCIAL ADVICE — FOR RESEARCH PURPOSES ONLY</span>
  <span>SWING MODE | REFRESH: {MODE_CONFIG[mode]['refresh_ms']//60000}m</span>
</div>
""", unsafe_allow_html=True)
