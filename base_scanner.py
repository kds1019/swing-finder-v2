"""
Base Formation Scanner
Scans the quality universe for stocks coiling into low-volatility consolidation bases.
Tier 1 = high conviction (score 8-10), Tier 2 = developing (6-7), Tier 3 = early (4-5).
"""
import concurrent.futures as futures
import json
import math
import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from utils.tiingo_api import tiingo_history, tiingo_all_us_tickers, get_next_earnings_date  # tiingo_all_us_tickers used as fallback in _load_universe
from utils.indicators import compute_indicators
from utils.storage import (
    save_watchlists_to_gist,
    load_base_scan_metadata, save_base_scan_metadata,
)
from utils.universe_builder import CACHE_PATH
from utils.claude_analyzer import analyze_base_formations, render_ai_chat
from utils.portfolio_settings import load_portfolio_settings, format_portfolio_context_for_claude

# ---------------------------------------------------------------------------
# Universe Loader  (mirrors scanner.py logic, no cross-import needed)
# ---------------------------------------------------------------------------
MAX_WORKERS = 6
BATCH_SIZE  = 40
BATCH_PAUSE = 0.25   # seconds between batches


def _load_universe(token: str) -> list[str]:
    """Load the cached quality universe; fall back to Tiingo API."""
    try:
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, "r") as f:
                data = json.load(f)
            tickers = [t["ticker"].upper() for t in data.get("tickers", [])]
            seen, unique = set(), []
            for t in tickers:
                if t not in seen:
                    seen.add(t); unique.append(t)
            if unique:
                return unique
    except Exception:
        pass
    return tiingo_all_us_tickers(token)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _days_to_earnings(ticker: str, token: str) -> int | None:
    """Return calendar days until next earnings, or None if unknown."""
    try:
        earnings_str = get_next_earnings_date(ticker, token)
        if not earnings_str or earnings_str in ("N/A", "Not Scheduled", None):
            return None
        days = (pd.to_datetime(earnings_str) - pd.Timestamp.now()).days
        return int(days)
    except Exception:
        return None


def _is_earnings_within_14_days(ticker: str, token: str) -> bool:
    """Hard exclude — return True when earnings are 0-14 days away."""
    days = _days_to_earnings(ticker, token)
    return days is not None and 0 <= days <= 14


# ---------------------------------------------------------------------------
# Core Evaluation
# ---------------------------------------------------------------------------

def evaluate_base_formation(
    ticker: str,
    token: str,
    price_min: float = 5.0,
    price_max: float = 500.0,
    min_avg_vol: float = 300_000,
) -> dict | None:
    """
    Score a ticker for base-formation quality (0–10).
    Applies price/volume pre-filters before scoring.
    Returns None if it fails any filter or scores < 4.
    Resistance is the 20-day high (breakout trigger price).
    """
    try:
        df = tiingo_history(ticker, token, days=90)
        if df is None or df.empty or len(df) < 60:
            return None

        df = compute_indicators(df)
        last = df.iloc[-1]

        price    = float(last["Close"])
        ema50    = float(last.get("EMA50") or 0)
        atr_now  = float(last.get("ATR14") or 0)
        avg_vol  = float(last.get("AvgVol20") or 0)
        hh20     = float(last.get("HH20") or price)

        # --- Pre-filters (fast exit before scoring) ---
        if not (price_min <= price <= price_max):
            return None
        if avg_vol < min_avg_vol:
            return None

        if ema50 == 0 or atr_now == 0:
            return None

        score   = 0
        details = []

        # 1 · ATR Contraction (3 pts)
        atr_20ago = float(df["ATR14"].iloc[-21]) if len(df) >= 21 else atr_now
        if atr_20ago > 0:
            pct = (atr_20ago - atr_now) / atr_20ago * 100
            if pct >= 20:
                score += 3; details.append(f"✅ ATR contracted {pct:.0f}% (+3)")
            elif pct >= 10:
                score += 2; details.append(f"✅ ATR contracted {pct:.0f}% (+2)")
            elif pct >= 5:
                score += 1; details.append(f"⚠️ ATR contracted {pct:.0f}% (+1)")
            else:
                details.append(f"❌ ATR expanding ({pct:.0f}%)")

        # 2 · Higher Lows (2 pts) — last 10 sessions
        lows = df["Low"].iloc[-10:].values
        hl_count = sum(lows[i] > lows[i - 1] for i in range(1, len(lows)))
        if hl_count >= 6:
            score += 2; details.append(f"✅ Higher lows {hl_count}/9 (+2)")
        elif hl_count >= 4:
            score += 1; details.append(f"⚠️ Partial higher lows {hl_count}/9 (+1)")
        else:
            details.append(f"❌ No higher lows ({hl_count}/9)")

        # 3 · Volume Dry-up (2 pts)
        if avg_vol > 0:
            vol5 = float(df["Volume"].iloc[-5:].mean())
            vr = vol5 / avg_vol
            if vr <= 0.60:
                score += 2; details.append(f"✅ Volume dry-up {vr:.0%} of avg (+2)")
            elif vr <= 0.75:
                score += 1; details.append(f"⚠️ Volume quiet {vr:.0%} of avg (+1)")
            else:
                details.append(f"❌ Volume not drying up ({vr:.0%} of avg)")

        # 4 · EMA50 Proximity (2 pts)
        dist = (price - ema50) / ema50 * 100
        if 0 <= dist <= 5:
            score += 2; details.append(f"✅ Price {dist:.1f}% above EMA50 (+2)")
        elif 0 <= dist <= 10 or -3 <= dist < 0:
            score += 1; details.append(f"⚠️ Price {dist:+.1f}% vs EMA50 (+1)")
        else:
            details.append(f"❌ Price too far from EMA50 ({dist:+.1f}%)")

        # 5 · EMA50 Slope (1 pt)
        e50_prev = float(df["EMA50"].iloc[-11]) if len(df) >= 11 else ema50
        if ema50 > e50_prev:
            score += 1; details.append("✅ EMA50 rising (+1)")
        else:
            details.append("❌ EMA50 flat or declining")

        if score < 4:
            return None

        tier = (
            "Tier 1 — High Conviction" if score >= 8 else
            "Tier 2 — Developing"      if score >= 6 else
            "Tier 3 — Early"
        )

        return {
            "Symbol": ticker,
            "Price": round(price, 2),
            "BaseScore": score,
            "Tier": tier,
            "Resistance": round(hh20, 2),
            "ATR14": round(atr_now, 2),
            "EMA50": round(ema50, 2),
            "EMA50_dist_pct": round(dist, 1),
            "Details": details,
        }

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

TIER_COLORS = {
    "Tier 1 — High Conviction": "#22c55e",
    "Tier 2 — Developing":      "#f59e0b",
    "Tier 3 — Early":           "#94a3b8",
}


def base_scanner_ui(TIINGO_TOKEN: str):
    """Full Streamlit page for the Base Formation Scanner."""

    st.header("🔭 Base Formation Scanner")
    st.caption(
        "Scans the quality universe for stocks coiling into tight consolidation bases — "
        "stocks to **stalk and add to your watchlist** before the breakout move."
    )

    # ── Sidebar Controls ──────────────────────────────────────────────────────
    with st.sidebar:
        st.subheader("🔭 Base Scanner Filters")
        price_min = st.number_input("Min Price ($)", value=10.0, step=5.0, min_value=1.0)
        price_max = st.number_input("Max Price ($)", value=300.0, step=25.0, min_value=5.0)
        min_volume = st.number_input(
            "Min Avg Volume", value=500_000, step=100_000, min_value=50_000,
            format="%d",
        )
        min_score = st.slider(
            "Min Base Score", 4, 10, 6,
            help="4 = Early  |  6 = Developing  |  8 = High Conviction",
        )

    st.markdown("---")

    # ── Universe info + Run button ────────────────────────────────────────────
    universe = _load_universe(TIINGO_TOKEN)
    st.caption(f"📋 Universe: **{len(universe)} quality tickers** (S&P 500 + NASDAQ 100 + popular stocks)")

    run_btn = st.button("🚀 Run Base Scan", use_container_width=True, type="primary")

    # ── Execute Scan (parallel, same pattern as main scanner) ─────────────────
    if run_btn:
        results = []
        excluded_earn = []
        total = len(universe)
        progress = st.progress(0, text="Scanning for base formations…")

        for batch_start in range(0, total, BATCH_SIZE):
            batch = universe[batch_start: batch_start + BATCH_SIZE]

            def _eval(ticker):
                if _is_earnings_within_14_days(ticker, TIINGO_TOKEN):
                    return ("earnings", ticker)
                rec = evaluate_base_formation(
                    ticker, TIINGO_TOKEN,
                    price_min=price_min,
                    price_max=price_max,
                    min_avg_vol=min_volume,
                )
                return ("result", rec)

            with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                futs = {ex.submit(_eval, t): t for t in batch}
                for f in futures.as_completed(futs):
                    try:
                        kind, val = f.result()
                        if kind == "earnings":
                            excluded_earn.append(val)
                        elif kind == "result" and val and val["BaseScore"] >= min_score:
                            results.append(val)
                    except Exception:
                        pass

            scanned = min(batch_start + len(batch), total)
            progress.progress(
                scanned / total,
                text=f"🔎 {scanned}/{total} scanned | Bases found: {len(results)}",
            )
            time.sleep(BATCH_PAUSE)

        progress.empty()
        results.sort(key=lambda x: x["BaseScore"], reverse=True)
        st.session_state["base_scan_results"] = results

        msg = f"✅ Scan complete — **{len(results)} base formation(s)** from {total} tickers scanned"
        if excluded_earn:
            msg += f" | {len(excluded_earn)} excluded (earnings ≤14 days)"
        st.success(msg)
        st.rerun()

    # ── Results Display ───────────────────────────────────────────────────────
    results = st.session_state.get("base_scan_results", [])
    if not results:
        st.info("Set your filters above and click **Run Base Scan** to discover consolidating stocks.")
        return

    st.markdown(f"### 📋 {len(results)} Base Formation(s) — sorted by score")

    # ── AI Stalking Review ────────────────────────────────────────────────────
    try:
        anthropic_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    except Exception:
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not anthropic_key:
        st.caption("💡 Add ANTHROPIC_API_KEY to secrets to unlock AI Stalking Review.")
    else:
        col_ai, _ = st.columns([2, 3])
        with col_ai:
            run_ai = st.button(
                "🤖 AI Stalking Review",
                type="primary",
                use_container_width=True,
                help="Claude reviews each base and gives a verdict: Worth Stalking / Watch + Wait / Skip",
            )
        if run_ai:
            with st.spinner("🤖 Reviewing bases… fetching news, 52W context, and market conditions…"):
                _port = st.session_state.get("portfolio") or load_portfolio_settings()
                _port_ctx = format_portfolio_context_for_claude(_port)
                ai_output = analyze_base_formations(results, TIINGO_TOKEN, anthropic_key, _port_ctx)
            st.session_state["base_scan_ai_summary"] = ai_output

        if st.session_state.get("base_scan_ai_summary"):
            with st.expander("🤖 AI Stalking Review", expanded=True):
                st.markdown(st.session_state["base_scan_ai_summary"])
                if st.button("🗑️ Clear AI Review", key="clear_base_ai"):
                    st.session_state["base_scan_ai_summary"] = None
                    st.session_state["chat_base_scanner"] = []
                    st.rerun()
            render_ai_chat("base_scanner", anthropic_key, st.session_state["base_scan_ai_summary"])

    st.divider()
    existing_meta = st.session_state.get("base_scan_metadata") or load_base_scan_metadata()

    per_row = 3
    for r_idx in range(math.ceil(len(results) / per_row)):
        cols = st.columns(per_row)
        for j, col in enumerate(cols):
            idx = r_idx * per_row + j
            if idx >= len(results):
                break
            rec = results[idx]
            color = TIER_COLORS.get(rec["Tier"], "#94a3b8")

            with col:
                st.markdown(f"""
                <div style="border:2px solid {color};border-radius:14px;padding:12px;margin-bottom:6px;">
                    <div style="display:flex;justify-content:space-between;">
                        <span style="font-weight:700;font-size:1.15rem;">{rec['Symbol']}</span>
                        <span style="font-weight:600;">${rec['Price']:.2f}</span>
                    </div>
                    <div style="color:{color};font-size:0.8rem;margin:2px 0 6px;">{rec['Tier']}</div>
                    <div style="font-size:0.88rem;line-height:1.6;">
                        📊 Score: <b>{rec['BaseScore']}/10</b><br/>
                        🎯 Breakout trigger: <b>${rec['Resistance']:.2f}</b><br/>
                        📐 vs EMA50: <b>{rec['EMA50_dist_pct']:+.1f}%</b><br/>
                        📉 ATR14: <b>{rec['ATR14']:.2f}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander("📋 Scoring breakdown"):
                    for d in rec["Details"]:
                        st.write(d)

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("➕ Watchlist", key=f"bs_wl_{rec['Symbol']}_{r_idx}_{j}"):
                        sym = rec["Symbol"]
                        active_wl = st.session_state.get("active_watchlist", "Unnamed")
                        wls = st.session_state.get("watchlists", {})
                        wl = wls.get(active_wl, [])
                        if sym not in wl:
                            wl.append(sym)
                            wls[active_wl] = wl
                            st.session_state.watchlists = wls
                            st.session_state.watchlist = wl
                            save_watchlists_to_gist(wls)
                            existing_meta[sym] = {
                                "resistance": rec["Resistance"],
                                "base_score": rec["BaseScore"],
                                "tier": rec["Tier"],
                                "date_added": datetime.now().strftime("%Y-%m-%d"),
                            }
                            st.session_state.base_scan_metadata = existing_meta
                            save_base_scan_metadata(existing_meta)
                            st.success(f"✅ {sym} → '{active_wl}' | trigger ${rec['Resistance']:.2f}")
                        else:
                            st.info(f"{sym} already on watchlist.")
                with c2:
                    if st.button("🔍 Analyze", key=f"bs_an_{rec['Symbol']}_{r_idx}_{j}"):
                        st.session_state["analyze_symbol"] = rec["Symbol"]
                        st.session_state["active_page"] = "Analyzer"
                        st.rerun()
