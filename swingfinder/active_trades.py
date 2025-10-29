from __future__ import annotations

"""
Active Trades — complete, drop-in module (v2)
- Keeps your original features
- FIX: coaching captions always show on main page (per ticker)
- FIX: "Refresh Prices Now" truly overwrites manual edits with live prices (and reloads fresh)
- NEW: Sidebar per-ticker "Run Intraday Coaching" button
- Morning/EOD reports still run across all open trades
- Per-ticker run updates only that symbol (price + EMA/RSI text) and shows it on main page
"""

import os
import json
import time
import datetime as dt
from typing import List, Dict, Any, Optional

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Back-compat for Streamlit rerun
# ---------------------------------------------------------------------------
if not hasattr(st, "rerun"):
    st.rerun = st.rerun  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# PATH / TOKEN HELPERS
# ---------------------------------------------------------------------------
DATA_PATH = os.path.join("data", "active_trades.json")


def _ensure_data_dir() -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)


def _get_tiingo_token() -> str:
    return (
        st.secrets.get("TIINGO_TOKEN", "")
        or st.secrets.get("TIINGO_API_KEY", "")
        or os.getenv("TIINGO_TOKEN", "")
        or os.getenv("TIINGO_API_KEY", "")
        or ""
    )


# ---------------------------------------------------------------------------
# LOAD / SAVE
# ---------------------------------------------------------------------------
def _load_trades() -> List[Dict[str, Any]]:
    _ensure_data_dir()
    if not os.path.exists(DATA_PATH):
        return []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_trades(rows: List[Dict[str, Any]]) -> None:
    _ensure_data_dir()
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)


# ---------------------------------------------------------------------------
# PRICE FETCHING (TIINGO + YAHOO FALLBACK)
# ---------------------------------------------------------------------------
def _fetch_price_tiingo_iex(symbol: str) -> Optional[float]:
    tok = _get_tiingo_token()
    if not tok:
        return None
    try:
        url = f"https://api.tiingo.com/iex/{symbol.upper()}"
        r = requests.get(url, headers={"Authorization": f"Token {tok}"}, timeout=8)
        if not r.ok:
            return None
        j = r.json()
        if isinstance(j, list) and j:
            val = j[0].get("last") or j[0].get("tngoLast")
            return float(val) if val is not None else None
        if isinstance(j, dict):
            val = j.get("last") or j.get("tngoLast")
            return float(val) if val is not None else None
    except Exception:
        return None
    return None


def _fetch_price_yahoo(symbol: str) -> Optional[float]:
    try:
        url = "https://query1.finance.yahoo.com/v7/finance/quote"
        r = requests.get(url, params={"symbols": symbol.upper()}, timeout=8)
        if not r.ok:
            return None
        res = r.json().get("quoteResponse", {}).get("result", [])
        if not res:
            return None
        p = (
            res[0].get("regularMarketPrice")
            or res[0].get("postMarketPrice")
            or res[0].get("preMarketPrice")
        )
        return float(p) if p is not None else None
    except Exception:
        return None


def get_intraday_price(symbol: str) -> Optional[float]:
    p = _fetch_price_tiingo_iex(symbol)
    if p is not None:
        return p
    return _fetch_price_yahoo(symbol)


# ---------------------------------------------------------------------------
# CALCULATIONS & COACHING
# ---------------------------------------------------------------------------
def _compute_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    try:
        entry = float(row.get("entry", 0) or 0)
        stop = float(row.get("stop", 0) or 0)
        target = float(row.get("target", 0) or 0)
        shares = float(row.get("shares", row.get("size", 0)) or 0)
        last = float(row.get("last_price", entry or 0) or 0)

        risk_ps = (entry - stop) if entry and stop else 0.0
        reward_ps = (target - entry) if target and entry else 0.0
        rr = (reward_ps / risk_ps) if risk_ps else 0.0
        unreal_r = ((last - entry) / risk_ps) if (risk_ps and last) else 0.0
        pos_risk = risk_ps * shares if (risk_ps and shares) else 0.0
        to_target = (
            (target - last) / (target - entry)
            if (target and entry and (target - entry) != 0)
            else None
        )
        to_stop = (
            (last - stop) / (entry - stop)
            if (entry and stop and (entry - stop) != 0)
            else None
        )

        out.update(
            {
                "risk_per_share": round(risk_ps, 4),
                "reward_per_share": round(reward_ps, 4),
                "rr": round(rr, 2),
                "unrealized_r": round(unreal_r, 2),
                "position_risk": round(pos_risk, 2),
                "progress_to_target": round(1 - to_target, 3)
                if isinstance(to_target, (float, int))
                else None,
                "distance_from_stop": round(to_stop, 3)
                if isinstance(to_stop, (float, int))
                else None,
            }
        )
    except Exception:
        pass
    return out


def _coaching_blurb(symbol: str, row: Dict[str, Any]) -> str:
    # Always return *some* coaching text
    last = float(row.get("last_price", 0) or 0)
    entry = float(row.get("entry", 0) or 0)
    rr = float(row.get("rr", 0) or 0)
    unr = float(row.get("unrealized_r", 0) or 0)
    prog = row.get("progress_to_target", None)
    dist = row.get("distance_from_stop", None)

    parts = []
    if last and entry:
        parts.append(
            f"Price {'up' if last >= entry else 'down'} vs entry: {last:.2f} vs {entry:.2f}."
        )
    if rr:
        parts.append(f"Plan R/R ≈ {rr:.2f}.")
    if unr:
        parts.append(f"Unrealized ≈ {unr:+.2f}R.")
    if isinstance(prog, (float, int)):
        if prog >= 0.8:
            parts.append("Approaching target — consider partials or trail stops.")
        elif prog >= 0.5:
            parts.append("Nice progress — keep managing risk.")
    if isinstance(dist, (float, int)):
        if dist <= 0.1:
            parts.append("Near stop — tighten risk or re-evaluate thesis.")
        elif dist >= 0.9:
            parts.append("Well off the stop — room to breathe.")
    if not parts:
        parts = ["Stay disciplined. Follow your plan and size rules."]
    return " ".join(parts)

# ---------------------------------------------------------------------------
# SMART COACHING UTILITIES (signals + coach)
# ---------------------------------------------------------------------------
from dataclasses import dataclass

@dataclass
class IntradaySignals:
    rsi: float | None
    ema_fast_above_slow: bool | None  # ema20 > ema50
    ema_slope_up: bool | None         # ema20 rising vs prior
    vol_ratio: float | None           # last bar volume / 20-bar avg
    last_close: float | None
    lookback_ok: bool

def _compute_intraday_signals_df(df) -> IntradaySignals:
    """Compute minimal signals from an intraday dataframe (expects 'close','volume')."""
    if df is None or df.empty or len(df) < 50:
        return IntradaySignals(None, None, None, None, None, False)

    # EMAs
    ema20 = df["close"].ewm(span=20).mean()
    ema50 = df["close"].ewm(span=50).mean()

    # RSI(14)
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss.replace(0, float("nan")))
    rsi = float(100 - (100 / (1 + rs))).__float__()
    rsi_val = float(rsi if not (rsi != rsi) else 50.0)  # NaN guard

    # EMA relationships
    ema_fast_above_slow = bool(ema20.iloc[-1] > ema50.iloc[-1])
    ema_slope_up = bool(ema20.iloc[-1] > ema20.iloc[-2]) if len(ema20) > 2 else None

    # Volume ratio (last bar vs 20 bar avg)
    vol_ratio = None
    if "volume" in df.columns:
        v20 = df["volume"].rolling(20).mean()
        if v20.iloc[-1] and v20.iloc[-1] > 0:
            vol_ratio = float(df["volume"].iloc[-1] / v20.iloc[-1])

    return IntradaySignals(
        rsi=rsi_val,
        ema_fast_above_slow=ema_fast_above_slow,
        ema_slope_up=ema_slope_up,
        vol_ratio=vol_ratio,
        last_close=float(df["close"].iloc[-1]),
        lookback_ok=True,
    )

def _smart_coach(row: dict, sig: IntradaySignals | None) -> str:
    """
    Rule-based coach combining plan (entry/stop/target/progress) + intraday (RSI/EMA/Volume).
    Non-intraday still returns useful guidance.
    """
    parts: list[str] = []

    entry = float(row.get("entry", 0) or 0)
    stop = float(row.get("stop", 0) or 0)
    target = float(row.get("target", 0) or 0)
    last = float(row.get("last_price", entry or 0) or 0)
    rr = float(row.get("rr", 0) or 0)
    unr = float(row.get("unrealized_r", 0) or 0)
    prog = row.get("progress_to_target", None)  # 0..1 where 1 == at/above target
    dist = row.get("distance_from_stop", None)  # 0..1 where 1 == far from stop

    # --- Plan context
    if rr:
        parts.append(f"Plan R/R {rr:.2f}.")
    if unr:
        parts.append(f"Unrealized {unr:+.2f}R.")
    if isinstance(prog, (int, float)):
        if prog >= 0.85:
            parts.append("Approaching target — prep partials / trail.")
        elif prog >= 0.5:
            parts.append("Past midway to target — manage risk, avoid FOMO adds.")
    if isinstance(dist, (int, float)):
        if dist <= 0.15:
            parts.append("Near stop — tighten risk or reassess thesis.")
        elif dist >= 0.85:
            parts.append("Well clear of stop — room to let it work.")

    # --- Intraday context
    if sig and sig.lookback_ok:
        if sig.ema_fast_above_slow is True and sig.ema_slope_up is True:
            parts.append("Momentum improving (EMA rising).")
        elif sig.ema_fast_above_slow is False and sig.ema_slope_up is False:
            parts.append("Momentum weakening (EMA falling).")

        if sig.rsi is not None:
            if sig.rsi >= 70:
                parts.append(f"RSI {sig.rsi:.0f} overbought — watch for exhaustion.")
            elif sig.rsi <= 30:
                parts.append(f"RSI {sig.rsi:.0f} oversold — bounce risk/reward favorable.")
            elif 55 <= sig.rsi <= 65:
                parts.append(f"RSI {sig.rsi:.0f} — constructive but not stretched.")

        if sig.vol_ratio is not None:
            if sig.vol_ratio >= 1.8:
                parts.append("Volume spike — conviction move.")
            elif sig.vol_ratio <= 0.6:
                parts.append("Light volume — be cautious reading signals.")

    # Fallback if nothing was added
    if not parts:
        if last and entry:
            parts.append(
                f"Price {'above' if last >= entry else 'below'} entry ({last:.2f} vs {entry:.2f}); follow plan."
            )
        else:
            parts.append("Follow plan and sizing; keep risk defined.")

    # Merge nicely
    # De-dup short clauses and keep it readable.
    seen = set()
    ordered = []
    for p in parts:
        if p not in seen:
            ordered.append(p)
            seen.add(p)
    return " ".join(ordered)

# ---------------------------------------------------------------------------
# WEBULL ALERT SUGGESTIONS
# ---------------------------------------------------------------------------
def suggest_alert_levels(r: dict) -> dict:
    """Return suggested Webull alert prices for an open trade."""
    entry = float(r.get("entry", 0) or 0)
    stop = float(r.get("stop", 0) or 0)
    target = float(r.get("target", 0) or 0)
    last = float(r.get("last_price", 0) or 0)

    alerts = {}
    if entry and stop and target:
        alerts["Breakout Alert"] = round(entry * 1.01, 2)
        alerts["Stop Watch"] = round(stop * 0.995, 2)
        alerts["Target Near"] = round(target * 0.985, 2)

    # Optional momentum-type alerts based on movement from last price
    if last and entry and stop and target:
        move_up = abs(target - entry) / 2
        move_down = abs(entry - stop) / 2
        alerts["Momentum Up"] = round(last + move_up, 2)
        alerts["Momentum Down"] = round(last - move_down, 2)

    return alerts

# ---------------------------------------------------------------------------
# INTRADAY COACHING (EMA/RSI)
# ---------------------------------------------------------------------------
from utils.tiingo_api import fetch_tiingo_intraday


def _intraday_coaching(symbol: str, token: str) -> str:
    try:
        df = fetch_tiingo_intraday(
            symbol, token, timeframe="1hour", lookback_days=7
        )
    except Exception:
        return "No intraday data available."

    if df.empty or len(df) < 20:
        return "Not enough intraday data."

    # Indicators
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()

    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    ema_trend = "up" if df["ema20"].iloc[-1] > df["ema50"].iloc[-1] else "down"
    rsi_val = float(df["rsi"].iloc[-1])

    insights = []
    insights.append(
        "📈 EMA trend rising — short-term bullish momentum."
        if ema_trend == "up"
        else "📉 EMA trend weakening — short-term pressure building."
    )
    if rsi_val > 70:
        insights.append(f"⚠️ RSI {rsi_val:.1f} overbought — watch for pullback.")
    elif rsi_val < 30:
        insights.append(f"💪 RSI {rsi_val:.1f} oversold — potential bounce.")
    else:
        insights.append(f"RSI stable at {rsi_val:.1f} — neutral zone.")
    return " ".join(insights)


# ---------------------------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------------------------
def _prefill_from_session() -> Dict[str, Any]:
    s = st.session_state
    return {
        "symbol": s.get("analyze_symbol", ""),
        "entry": float(s.get("planned_entry", s.get("planner_entry", 0)) or 0),
        "stop": float(s.get("planned_stop", s.get("planner_stop", 0)) or 0),
        "target": float(s.get("planned_target", s.get("planner_target", 0)) or 0),
        "shares": float(s.get("planner_shares", 0) or 0),
        "notes": s.get("planner_notes", ""),
        "webull_alerts": s.get("planner_webull_alerts", ""),
    }


def _sidebar_controls(rows: List[Dict[str, Any]]) -> str:
    """Sidebar: add/update/close + report buttons. Returns 'morning'/'eod'/'ticker:<SYM>'/''."""
    st.sidebar.markdown("### 🧠 Active Trader")
    action = ""

    c1, c2 = st.sidebar.columns(2)
    if c1.button("🕗 Morning", key="atc_btn_morning"):
        action = "morning"
    if c2.button("🌇 EOD", key="atc_btn_eod"):
        action = "eod"

    st.sidebar.markdown("---")

    open_syms = [r["symbol"] for r in rows if r.get("status", "OPEN") == "OPEN"]
    selected = st.sidebar.selectbox(
        "Open Trades", options=["(new)"] + open_syms, key="atc_select_open"
    )

    defaults = _prefill_from_session()
    if selected != "(new)":
        row = next(
            (r for r in rows if r.get("symbol") == selected and r.get("status") == "OPEN"),
            None,
        )
        if row:
            defaults.update(
                {
                    "symbol": row.get("symbol", ""),
                    "entry": row.get("entry", 0.0),
                    "stop": row.get("stop", 0.0),
                    "target": row.get("target", 0.0),
                    "shares": row.get("shares", 0.0),
                    "notes": row.get("notes", ""),
                    "webull_alerts": row.get("webull_alerts", ""),
                }
            )

    symbol = (
        st.sidebar.text_input("Symbol", value=str(defaults["symbol"]), key="atc_symbol")
        .upper()
        .strip()
    )
    c3, c4 = st.sidebar.columns(2)
    with c3:
        entry = st.sidebar.number_input(
            "Entry",
            min_value=0.0,
            step=0.01,
            value=float(defaults["entry"] or 0.0),
            key="atc_entry",
        )
        target = st.sidebar.number_input(
            "Target",
            min_value=0.0,
            step=0.01,
            value=float(defaults["target"] or 0.0),
            key="atc_target",
        )
    with c4:
        stop = st.sidebar.number_input(
            "Stop",
            min_value=0.0,
            step=0.01,
            value=float(defaults["stop"] or 0.0),
            key="atc_stop",
        )
        shares = st.sidebar.number_input(
            "Shares",
            min_value=0.0,
            step=1.0,
            value=float(defaults["shares"] or 0.0),
            key="atc_shares",
        )

    entry_date = st.sidebar.date_input(
        "Entry Date", value=dt.date.today(), key="atc_entry_date"
    )
    notes = st.sidebar.text_area("Notes", value=defaults["notes"], key="atc_notes", height=80)
    wab = st.sidebar.text_area(
        "🔔 Webull Alerts", value=defaults["webull_alerts"], key="atc_wab", height=60
    )

    # Per-ticker run button when existing symbol selected
    per_ticker_run = False
    if selected != "(new)":
        if st.sidebar.button("🔍 Run Intraday Coaching (this ticker only)", key="atc_run_one"):
            per_ticker_run = True
            action = f"ticker:{selected}"

    c5, c6 = st.sidebar.columns(2)
    if c5.button("💾 Save/Update", key="atc_save"):
        if not symbol or entry <= 0 or stop <= 0 or shares <= 0:
            st.sidebar.warning("Fill Symbol, Entry, Stop, Shares.")
        else:
            new_row = {
                "symbol": symbol,
                "entry": float(entry),
                "stop": float(stop),
                "target": float(target),
                "shares": float(shares),
                "last_price": float(entry),
                "opened": entry_date.isoformat(),
                "status": "OPEN",
                "notes": notes,
                "webull_alerts": wab,
            }
            replaced = False
            for i, r in enumerate(rows):
                if r.get("symbol") == symbol and r.get("status", "OPEN") == "OPEN":
                    rows[i] = _compute_fields(new_row)
                    replaced = True
                    break
            if not replaced:
                rows.append(_compute_fields(new_row))
            _save_trades(rows)
            st.sidebar.success(f"Saved {symbol}")
            st.rerun()

    if c6.button("❌ Close", key="atc_close"):
        if selected != "(new)":
            for i, r in enumerate(rows):
                if r.get("symbol") == selected and r.get("status") == "OPEN":
                    rows[i]["status"] = "CLOSED"
                    rows[i]["closed"] = dt.date.today().isoformat()
                    rows[i] = _compute_fields(rows[i])
                    _save_trades(rows)
                    st.sidebar.info(f"Closed {selected}")
                    st.rerun()
        else:
            st.sidebar.info("Pick an open trade to close.")

    return action


# ---------------------------------------------------------------------------
# IN-MEMORY (SESSION) INTRADAY COACHING CACHE
# ---------------------------------------------------------------------------
def _get_intraday_cache() -> Dict[str, str]:
    if "atc_intraday_cache" not in st.session_state:
        st.session_state["atc_intraday_cache"] = {}
    return st.session_state["atc_intraday_cache"]


def _set_intraday_cache(symbol: str, text: str) -> None:
    cache = _get_intraday_cache()
    cache[symbol.upper()] = text
    
def _get_intraday_metrics_cache() -> dict[str, IntradaySignals]:
    if "atc_intraday_metrics_cache" not in st.session_state:
        st.session_state["atc_intraday_metrics_cache"] = {}
    return st.session_state["atc_intraday_metrics_cache"]

def _set_intraday_metrics_cache(symbol: str, sig: IntradaySignals) -> None:
    cache = _get_intraday_metrics_cache()
    cache[symbol.upper()] = sig



# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# DEBUG: PRICE REFRESH (with live logging)
# ---------------------------------------------------------------------------
def _refresh_intraday_for_opens(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Force refresh all OPEN trades — overwrite last_price from Tiingo/Yahoo."""
    updated_rows: List[Dict[str, Any]] = []

    for r in rows:
        if r.get("status") != "OPEN":
            updated_rows.append(r)
            continue

        sym = str(r.get("symbol", "")).upper().strip()
        print(f"\n--- {sym} ---")

        price_tiingo = _fetch_price_tiingo_iex(sym)
        price_yahoo = None

        if price_tiingo is not None:
            price = price_tiingo
            print(f"Tiingo → {price_tiingo}")
        else:
            price_yahoo = _fetch_price_yahoo(sym)
            price = price_yahoo
            print(f"Yahoo → {price_yahoo}")

        if price is None:
            print(f"❌ No price fetched for {sym}. Leaving as {r.get('last_price')}.")
        else:
            old_price = r.get("last_price")
            r["last_price"] = round(float(price), 2)
            r = _compute_fields(r)
            print(f"✅ Updated {sym}: {old_price} → {r['last_price']}")

        updated_rows.append(r)
        time.sleep(0.15)

    _save_trades(updated_rows)
    print("=== Done refreshing ===\n")
    return updated_rows



def _aggregate_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    opens = [r for r in rows if r.get("status") == "OPEN"]
    total_risk = sum(float(r.get("position_risk", 0) or 0) for r in opens)
    total_unreal_r = sum(float(r.get("unrealized_r", 0) or 0) for r in opens)
    rr_vals = [float(r.get("rr", 0) or 0) for r in opens if (r.get("rr") or 0) > 0]
    avg_rr = (sum(rr_vals) / len(rr_vals)) if rr_vals else 0.0
    return {
        "open_count": len(opens),
        "total_risk": round(total_risk, 2),
        "total_unreal_r": round(total_unreal_r, 2),
        "avg_rr": round(avg_rr, 2) if avg_rr else 0.0,
    }


def _render_report(rows: List[Dict[str, Any]], title: str) -> None:
    st.markdown(f"#### {title}")
    agg = _aggregate_metrics(rows)
    st.write(
        f"Open trades: **{agg['open_count']}**  •  Exposure: **${agg['total_risk']:.2f}**  •  "
        f"Unrealized: **{agg['total_unreal_r']:+.2f}R**  •  Avg R/R: **{agg['avg_rr']:.2f}**"
    )

    token = _get_tiingo_token()
    for r in [x for x in rows if x.get("status") == "OPEN"]:
        sy = r.get("symbol", "")
        st.write(
            f"- **{sy}** — last {float(r.get('last_price', 0) or 0):.2f} | "
            f"entry {r.get('entry')} | stop {r.get('stop')} | target {r.get('target', 0)} | "
            f"R≈{r.get('unrealized_r', 0)}"
        )
        # 💬 Always show the blurb
        st.caption("💬 " + _smart_coach(r, _get_intraday_metrics_cache().get(sy.upper())))

        
        # Suggested Webull alert levels
        alerts = suggest_alert_levels(r)
        if alerts:
            st.caption("📳 **Webull Alert Suggestions:**")
            for label, val in alerts.items():
                st.markdown(f"- {label}: `{val}`")

        # 🧠 Intraday insights for reports (ok to compute across all)
        if token:
            try:
                st.caption("🧠 " + _intraday_coaching(sy, token))
            except Exception:
                st.caption("🧠 Intraday: unavailable right now.")

        if r.get("webull_alerts"):
            st.caption("🔔 Webull: " + str(r.get("webull_alerts", "")))


# ---------------------------------------------------------------------------
# MAIN PAGE RENDER
# ---------------------------------------------------------------------------
def _render_open_positions(rows: List[Dict[str, Any]]) -> None:
    # -----------------------------------------------------------------------
    # Reset number_input widgets after global refresh to force live values
    # -----------------------------------------------------------------------
    if st.session_state.get("force_refresh"):
        for k in list(st.session_state.keys()):
            if "atc_last_" in k:
                st.session_state.pop(k, None)

    st.subheader("📜 Open Positions")
    opens = [r for r in rows if r.get("status") == "OPEN"]

    if not opens:
        st.info("No open trades yet.")
        return

    intraday_cache = _get_intraday_cache()
    token = _get_tiingo_token()


    for idx, r in enumerate(opens):
        r = _compute_fields(r)
        sy = r.get("symbol", "")
        st.markdown(
            f"**{sy}** — entry {r.get('entry')} | stop {r.get('stop')} | "
            f"target {r.get('target', 0)} | shares {r.get('shares', 0)}"
        )
        c = st.columns([1.2, 1, 1, 1, 1])
        with c[0]:
            last_val = st.number_input(
                "Last Price",
                min_value=0.0,
                step=0.01,
                value=float(r.get("last_price", r.get("entry", 0)) or 0),
                key=f"atc_last_{sy}_{idx}_{int(st.session_state.get('refresh_counter', 0))}",
            )
            # 🔧 Force Streamlit to forget stale number_input value after a global refresh
        if st.session_state.get("force_refresh"):
            st.session_state.pop(f"atc_last_{sy}_{idx}", None)

        c[1].metric("R/R", r.get("rr", 0))
        c[2].metric("Unrealized R", r.get("unrealized_r", 0))
        c[3].metric("Risk/Share", r.get("risk_per_share", 0))
        c[4].metric("Pos Risk $", r.get("position_risk", 0))

        # Persist quick last price edits (and recompute)
        prev_last = float(r.get("last_price", r.get("entry", 0)) or 0)
        if abs(last_val - prev_last) > 1e-9:
            for i, rr in enumerate(rows):
                if rr.get("symbol") == sy and rr.get("status") == "OPEN":
                    rr["last_price"] = float(last_val)
                    rows[i] = _compute_fields(rr)
                    break
            _save_trades(rows)
            st.rerun()

        # Smart Coaching (uses cached intraday metrics when available)
        sig_cache = _get_intraday_metrics_cache()
        sig = sig_cache.get(sy.upper())
        st.caption("💬 " + _smart_coach(r, sig))


        # Intraday coaching: show cached result if available for this symbol
        if sy.upper() in intraday_cache:
            st.caption("🧠 " + intraday_cache[sy.upper()])
        else:
            # Hint to user how to get it without hammering API
            if token:
                st.caption("🧠 Click '🔍 Run Intraday Coaching (this ticker only)' in the sidebar to compute.")

        st.markdown("---")


def _render_closed_positions(rows: List[Dict[str, Any]]) -> None:
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    if not closed:
        return
    with st.expander("📦 Closed Trades", expanded=False):
        for r in closed:
            st.write(
                f"**{r.get('symbol', '')}** — opened {r.get('opened', '?')} • "
                f"closed {r.get('closed', '?')} • entry {r.get('entry')} • "
                f"stop {r.get('stop')} • target {r.get('target', 0)} • shares {r.get('shares', 0)}"
            )


# ---------------------------------------------------------------------------
# PUBLIC ENTRY — (used by app.py)
# ---------------------------------------------------------------------------
def active_trades_ui() -> None:
    st.title("💼 Active Trades")
    st.caption("Track, update, and coach your open trades.")
    show_active_trader_coaching()


def show_active_trader_coaching() -> None:
    st.header("🔔 Active Trader Coaching")

    rows = _load_trades()
    rows = [_compute_fields(r) for r in rows]

    # --- Intraday Price Refresh (ALL) ---
    st.markdown("### 🔄 Intraday Price Refresh")
    auto_refresh = st.checkbox(
        "Auto-refresh prices on load", value=False, key="atc_auto_refresh"
    )

    if st.button("🔁 Refresh Prices Now", use_container_width=True):
        st.info("Fetching latest intraday prices...")
        _refresh_intraday_for_opens(rows)  # refresh + save live Tiingo/Yahoo
        st.success("Prices refreshed from Tiingo/Yahoo!")

        # ✅ Mark that a global refresh occurred (used by _render_open_positions)
        st.session_state["force_refresh"] = True

        # Reload fresh data so new prices appear on next render
        rows = _load_trades()
        rows = [_compute_fields(r) for r in rows]
        
        # Increment refresh counter to force new widget keys (rebuilds inputs)
        st.session_state["refresh_counter"] = st.session_state.get("refresh_counter", 0) + 1
        st.rerun()


        st.rerun()




    if auto_refresh and not st.session_state.get("auto_refreshed_once", False):
        rows = _refresh_intraday_for_opens(rows)
        _save_trades(rows)
        st.session_state["auto_refreshed_once"] = True
        st.success("Auto-refreshed prices once on load.")

    # --- Sidebar actions (can return morning/eod or ticker:<SYM>) ---
    action = _sidebar_controls(rows)

    # --- Handle per-ticker intraday coaching run ---
    if action.startswith("ticker:"):
        sym = action.split(":", 1)[1].upper().strip()
        token = _get_tiingo_token()
        if token and sym:
            # Update just this symbol's price from Tiingo (only)
            price = _fetch_price_tiingo_iex(sym)
            if price is not None:
                for i, r in enumerate(rows):
                    if r.get("symbol", "").upper() == sym and r.get("status") == "OPEN":
                        r["last_price"] = round(float(price), 2)
                        rows[i] = _compute_fields(r)
                        break
                _save_trades(rows)
            # Compute and cache coaching text
            try:
                txt = _intraday_coaching(sym, token)
            except Exception:
                txt = "Intraday: unavailable right now."
            _set_intraday_cache(sym, txt)
            st.session_state["force_refresh"] = True
            st.query_params.update({"_": str(time.time())})  # bust Streamlit state cache
            st.rerun()

    # --- Reports (across ALL open trades) ---
    if action == "morning":
        rows = _refresh_intraday_for_opens(rows)
        _render_report(rows, "☀️ Morning Report")
        st.markdown("---")
    elif action == "eod":
        rows = _refresh_intraday_for_opens(rows)
        _render_report(rows, "🌇 End-of-Day Report")
        st.markdown("---")
        
            # NEW: compute and cache structured signals for Smart Coaching
        try:
            df = fetch_tiingo_intraday(sym, token, timeframe="1hour", lookback_days=7)
            sig = _compute_intraday_signals_df(df)
            _set_intraday_metrics_cache(sym, sig)
        except Exception:
            pass
    

    # --- Forced reload after any mutation ---
    if st.session_state.get("force_refresh"):
        del st.session_state["force_refresh"]
        rows = _load_trades()
        rows = [_compute_fields(r) for r in rows]

    # --- Main content ---
    _render_open_positions(rows)
    _render_closed_positions(rows)
