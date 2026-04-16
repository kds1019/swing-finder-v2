from __future__ import annotations

"""
Active Trades — complete, drop-in module (v3)
- Preserves your original UI and behavior
- FIX: No undefined variables during reports; safer cache busting
- FIX: RSI calc in smart signals (uses last value correctly)
- ENHANCE: Per-ticker Smart Coaching signals cached & used in captions
- ENHANCE: 'Copy for AI' prompt block per open trade
"""

import os
import json
import time
import datetime as dt
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import requests
import streamlit as st
# NOTE: fetch_tiingo_intraday returns a pandas DataFrame
from utils.tiingo_api import fetch_tiingo_intraday
from utils.tiingo_api import fetch_tiingo_realtime_quote
from utils.storage import load_gist_json, save_gist_json
from utils.active_trade_analyzer import analyze_active_trades




# ---------------------------------------------------------------------------
# Back-compat for Streamlit rerun
# ---------------------------------------------------------------------------
if not hasattr(st, "rerun"):
    st.rerun = st.rerun  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# PATH / TOKEN HELPERS
# ---------------------------------------------------------------------------
DATA_PATH = os.path.join("data", "active_trades.json")
JOURNAL_PATH = os.path.join("data", "trade_journal.json")


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


def _get_gist_id() -> Optional[str]:
    """Get Gist ID from secrets or environment for cloud persistence."""
    return (
        st.secrets.get("GIST_TRADES_ID")
        or st.secrets.get("GIST_ID")  # Use existing Gist ID
        or os.getenv("GIST_TRADES_ID")
        or os.getenv("GIST_ID")
    )


# ---------------------------------------------------------------------------
# LOAD / SAVE (with Cloud Persistence via GitHub Gist)
# ---------------------------------------------------------------------------
def _load_trades() -> List[Dict[str, Any]]:
    """Load trades from GitHub Gist (cloud) or local file (fallback)."""
    gist_id = _get_gist_id()

    # Try loading from Gist first (for Streamlit Cloud persistence)
    if gist_id:
        try:
            data = load_gist_json(gist_id, "active_trades.json")
            if data and isinstance(data, dict) and "trades" in data:
                return data["trades"] if isinstance(data["trades"], list) else []
            elif isinstance(data, list):
                return data
        except Exception as e:
            st.warning(f"⚠️ Could not load from cloud storage: {e}")

    # Fallback to local file
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
    """Save trades to both GitHub Gist (cloud) and local file."""
    # Save to local file first
    _ensure_data_dir()
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
    except Exception as e:
        st.warning(f"⚠️ Could not save locally: {e}")

    # Save to Gist for cloud persistence
    gist_id = _get_gist_id()
    if gist_id:
        try:
            save_gist_json(gist_id, "active_trades.json", {"trades": rows})
        except Exception as e:
            st.warning(f"⚠️ Could not save to cloud storage: {e}")


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


def _fetch_atr(symbol: str) -> Optional[float]:
    """Fetch ATR14 from daily data using Tiingo."""
    tok = _get_tiingo_token()
    if not tok:
        return None

    try:
        from utils.tiingo_api import tiingo_history
        from utils.indicators import compute_indicators

        df = tiingo_history(symbol, tok, days=30)
        if df is None or df.empty or len(df) < 14:
            return None

        df = compute_indicators(df)
        if "ATR14" in df.columns:
            return float(df["ATR14"].iloc[-1])
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# TRADE JOURNAL & PERFORMANCE ANALYTICS (with Cloud Persistence)
# ---------------------------------------------------------------------------
def load_trade_journal() -> List[Dict[str, Any]]:
    """Load closed trades from journal (cloud or local)."""
    gist_id = _get_gist_id()

    # Try loading from Gist first
    if gist_id:
        try:
            data = load_gist_json(gist_id, "trade_journal.json")
            if data and isinstance(data, dict) and "journal" in data:
                return data["journal"] if isinstance(data["journal"], list) else []
            elif isinstance(data, list):
                return data
        except Exception:
            pass

    # Fallback to local file
    try:
        if os.path.exists(JOURNAL_PATH):
            with open(JOURNAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_trade_journal(journal: List[Dict[str, Any]]) -> None:
    """Save trade journal to both cloud and local."""
    # Save locally
    try:
        _ensure_data_dir()
        with open(JOURNAL_PATH, "w", encoding="utf-8") as f:
            json.dump(journal, f, indent=2)
    except Exception:
        pass

    # Save to Gist for cloud persistence
    gist_id = _get_gist_id()
    if gist_id:
        try:
            save_gist_json(gist_id, "trade_journal.json", {"journal": journal})
        except Exception:
            pass


def add_to_journal(trade: Dict[str, Any], exit_price: float, exit_reason: str, mistake: str = None) -> None:
    """Add a closed trade to the journal."""
    journal = load_trade_journal()

    entry = float(trade.get("entry", 0))
    stop = float(trade.get("stop", 0))
    target = float(trade.get("target", 0))
    shares = float(trade.get("shares", trade.get("size", 0)))

    pnl = (exit_price - entry) * shares
    pnl_pct = ((exit_price - entry) / entry) * 100 if entry else 0
    risk_ps = entry - stop if entry and stop else 0
    r_multiple = (exit_price - entry) / risk_ps if risk_ps else 0

    journal_entry = {
        "symbol": trade.get("symbol", ""),
        "entry_date": trade.get("opened", ""),
        "exit_date": dt.datetime.now().isoformat(),
        "entry_price": entry,
        "exit_price": exit_price,
        "shares": shares,
        "pnl_dollar": round(pnl, 2),
        "pnl_percent": round(pnl_pct, 2),
        "r_multiple": round(r_multiple, 2),
        "exit_reason": exit_reason,
        "setup_type": trade.get("setup_type", "Unknown"),
        "notes": trade.get("notes", ""),
        "mistake": mistake if mistake and mistake != "None - Followed my plan perfectly" else None,
    }

    journal.append(journal_entry)
    save_trade_journal(journal)


def calculate_mistake_stats() -> Dict[str, Any]:
    """Calculate mistake tracking statistics."""
    journal = load_trade_journal()

    if not journal:
        return {}

    # Get all trades with mistakes
    trades_with_mistakes = [t for t in journal if t.get("mistake")]

    if not trades_with_mistakes:
        return {"total_mistakes": 0, "mistake_breakdown": {}, "total_cost": 0}

    # Count mistakes by type
    mistake_counts = {}
    mistake_costs = {}

    for trade in trades_with_mistakes:
        mistake = trade.get("mistake")
        pnl = trade.get("pnl_dollar", 0)

        if mistake not in mistake_counts:
            mistake_counts[mistake] = 0
            mistake_costs[mistake] = 0

        mistake_counts[mistake] += 1
        mistake_costs[mistake] += pnl  # Will be negative for losses

    # Sort by frequency
    sorted_mistakes = sorted(mistake_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_mistakes": len(trades_with_mistakes),
        "mistake_breakdown": dict(sorted_mistakes),
        "mistake_costs": mistake_costs,
        "total_cost": sum(mistake_costs.values()),
        "top_mistake": sorted_mistakes[0][0] if sorted_mistakes else None,
        "top_mistake_count": sorted_mistakes[0][1] if sorted_mistakes else 0,
    }


def calculate_performance_stats() -> Dict[str, Any]:
    """Calculate trading performance statistics."""
    journal = load_trade_journal()

    if not journal:
        return {}

    wins = [t for t in journal if t.get("pnl_dollar", 0) > 0]
    losses = [t for t in journal if t.get("pnl_dollar", 0) <= 0]

    total_pnl = sum(t.get("pnl_dollar", 0) for t in journal)
    avg_win = sum(t.get("pnl_dollar", 0) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.get("pnl_dollar", 0) for t in losses) / len(losses) if losses else 0

    return {
        "total_trades": len(journal),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(journal) * 100, 1) if journal else 0,
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
        "avg_r_multiple": round(sum(t.get("r_multiple", 0) for t in journal) / len(journal), 2) if journal else 0,
        "largest_win": max((t.get("pnl_dollar", 0) for t in journal), default=0),
        "largest_loss": min((t.get("pnl_dollar", 0) for t in journal), default=0),
    }


def generate_trade_management_plan(trade: Dict[str, Any]) -> str:
    """Generate specific trade management rules based on current position."""
    entry = float(trade.get("entry", 0))
    stop = float(trade.get("stop", 0))
    target = float(trade.get("target", 0))
    last_price = float(trade.get("last_price", entry))

    risk_ps = entry - stop if entry and stop else 0
    unreal_r = (last_price - entry) / risk_ps if risk_ps else 0

    plan = []
    plan.append(f"**Trade Management Plan for {trade.get('symbol', '')}**\n")
    plan.append(f"Entry: ${entry:.2f} | Stop: ${stop:.2f} | Target: ${target:.2f}\n")
    plan.append(f"Current: ${last_price:.2f} | Unrealized R: {unreal_r:.2f}R\n")
    plan.append("---")

    # Position-based rules
    if unreal_r >= 2.0:
        plan.append("✅ **At +2R**: Take 50% off, move stop to +1R")
        plan.append(f"   - Sell 50% at current price (${last_price:.2f})")
        plan.append(f"   - Move stop to ${entry + risk_ps:.2f} (breakeven + 1R)")
    elif unreal_r >= 1.0:
        plan.append("✅ **At +1R**: Move stop to breakeven")
        plan.append(f"   - Move stop to ${entry:.2f}")
        plan.append("   - Consider taking 25% off if resistance nearby")
    elif unreal_r >= 0.5:
        plan.append("⏸️ **At +0.5R**: Hold and monitor")
        plan.append("   - Let it run toward +1R")
        plan.append("   - Watch for volume confirmation")
    elif unreal_r <= -0.5:
        plan.append("⚠️ **Down 0.5R**: Review thesis")
        plan.append("   - Is the setup still valid?")
        plan.append("   - Any news/catalysts changed?")
        plan.append("   - Prepare to cut at stop if invalidated")
    else:
        plan.append("⏸️ **Near Entry**: Be patient")
        plan.append("   - Let the trade develop")
        plan.append("   - Honor your stop if hit")

    plan.append("\n**Exit Rules:**")
    plan.append(f"- Stop Loss: ${stop:.2f} (no exceptions)")
    plan.append(f"- Target: ${target:.2f} (take remaining position)")
    plan.append("- Time Stop: If no progress in 5 days, consider exit")

    return "\n".join(plan)


# ---------------------------------------------------------------------------
# CALCULATIONS & COACHING
# ---------------------------------------------------------------------------
def _compute_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    try:
        # Use actual_entry if available, otherwise fall back to planned entry
        planned_entry = float(row.get("entry", 0) or 0)
        actual_entry = float(row.get("actual_entry", 0) or 0)
        entry = actual_entry if actual_entry > 0 else planned_entry

        # Use actual_stop if available, otherwise recalculate from actual entry
        planned_stop = float(row.get("stop", 0) or 0)
        actual_stop = float(row.get("actual_stop", 0) or 0)

        # If we have actual entry but no actual stop, recalculate stop maintaining same R
        if actual_entry > 0 and actual_stop == 0 and planned_entry > 0 and planned_stop > 0:
            risk_ratio = (planned_entry - planned_stop) / planned_entry
            actual_stop = actual_entry * (1 - risk_ratio)

        stop = actual_stop if actual_stop > 0 else planned_stop

        # Same for target
        planned_target = float(row.get("target", 0) or 0)
        actual_target = float(row.get("actual_target", 0) or 0)

        # If we have actual entry but no actual target, recalculate maintaining same R:R
        if actual_entry > 0 and actual_target == 0 and planned_entry > 0 and planned_target > 0:
            reward_ratio = (planned_target - planned_entry) / planned_entry
            actual_target = actual_entry * (1 + reward_ratio)

        target = actual_target if actual_target > 0 else planned_target

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


# --- Simple blurb (always shows something) -----------------------------------
def _coaching_blurb(symbol: str, row: Dict[str, Any]) -> str:
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
    if df is None or getattr(df, "empty", True) or len(df) < 50:
        return IntradaySignals(None, None, None, None, None, False)

    # EMAs
    ema20 = df["close"].ewm(span=20).mean()
    ema50 = df["close"].ewm(span=50).mean()

    # RSI(14) — use last value (safe against divide-by-zero)
    delta = df["close"].diff()
    gain = delta.clip(lower=0.0).rolling(14).mean()
    loss = (-delta.clip(upper=0.0)).rolling(14).mean()
    avg_loss = loss.replace(0, float("nan"))
    rs_series = gain / avg_loss
    rsi_series = 100 - (100 / (1 + rs_series))
    rsi_val = float(rsi_series.iloc[-1]) if rsi_series.iloc[-1] == rsi_series.iloc[-1] else 50.0

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
# INTRADAY COACHING (EMA/RSI) — text summary
# ---------------------------------------------------------------------------
def _intraday_coaching(symbol: str, token: str) -> str:
    try:
        df = fetch_tiingo_intraday(symbol, token, timeframe="1hour", lookback_days=7)
    except Exception:
        return "No intraday data available."

    if df.empty or len(df) < 20:
        return "Not enough intraday data."

    # Indicators
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0.0).rolling(14).mean()
    loss = (-delta.clip(upper=0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, float("nan"))
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
                    "actual_entry": row.get("actual_entry", 0.0),
                    "actual_stop": row.get("actual_stop", 0.0),
                    "actual_target": row.get("actual_target", 0.0),
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

    # ✅ Actual Fill Prices (optional - overrides planned prices)
    with st.sidebar.expander("💰 Actual Fill Prices (Optional)", expanded=False):
        st.caption("Enter your actual fill prices to recalculate stop/target based on real entry")

        # Get existing actual values if editing
        actual_entry_default = 0.0
        actual_stop_default = 0.0
        actual_target_default = 0.0

        if selected != "(new)":
            row = next(
                (r for r in rows if r.get("symbol") == selected and r.get("status") == "OPEN"),
                None,
            )
            if row:
                actual_entry_default = float(row.get("actual_entry", 0) or 0)
                actual_stop_default = float(row.get("actual_stop", 0) or 0)
                actual_target_default = float(row.get("actual_target", 0) or 0)

        actual_entry = st.number_input(
            "Actual Entry (leave 0 to use planned)",
            min_value=0.0,
            step=0.01,
            value=actual_entry_default,
            key="atc_actual_entry",
            help="Your actual fill price (if different from planned entry)"
        )

        c_actual1, c_actual2 = st.columns(2)
        with c_actual1:
            actual_stop = st.number_input(
                "Actual Stop",
                min_value=0.0,
                step=0.01,
                value=actual_stop_default,
                key="atc_actual_stop",
                help="Leave 0 to auto-calculate from actual entry"
            )
        with c_actual2:
            actual_target = st.number_input(
                "Actual Target",
                min_value=0.0,
                step=0.01,
                value=actual_target_default,
                key="atc_actual_target",
                help="Leave 0 to auto-calculate from actual entry"
            )

        # Show preview of recalculated values
        if actual_entry > 0:
            if actual_stop == 0 and entry > 0 and stop > 0:
                risk_ratio = (entry - stop) / entry
                calc_stop = actual_entry * (1 - risk_ratio)
                st.caption(f"📊 Auto Stop: ${calc_stop:.2f}")

            if actual_target == 0 and entry > 0 and target > 0:
                reward_ratio = (target - entry) / entry
                calc_target = actual_entry * (1 + reward_ratio)
                st.caption(f"📊 Auto Target: ${calc_target:.2f}")

    notes = st.sidebar.text_area("Notes", value=defaults["notes"], key="atc_notes", height=80)
    wab = st.sidebar.text_area(
        "🔔 Webull Alerts", value=defaults["webull_alerts"], key="atc_wab", height=60
    )

    # Per-ticker run button when existing symbol selected
    if selected != "(new)":
        if st.sidebar.button(
            f"🔍 Run Intraday Coaching ({selected})",
            key=f"atc_run_one_{selected}"
        ):
            print(f"DEBUG: Intraday button clicked for {selected}")
            action = f"ticker:{selected}"


    # Trailing Stop Loss Settings
    st.sidebar.divider()
    st.sidebar.markdown("### 🎯 Trailing Stop Settings")

    enable_trailing = st.sidebar.checkbox(
        "Enable Auto Trailing Stop",
        value=False,
        key="atc_enable_trailing",
        help="Automatically move stop loss as price moves in your favor"
    )

    if enable_trailing:
        trail_method = st.sidebar.selectbox(
            "Trailing Method",
            options=["R-Multiple", "ATR-Based", "Percentage"],
            index=0,
            help="Choose how to trail your stop loss"
        )

        if trail_method == "R-Multiple":
            st.sidebar.caption("📊 **R-Multiple Trailing** - Based on initial risk")
            col_trail1, col_trail2 = st.sidebar.columns(2)
            with col_trail1:
                trail_at_1r = st.checkbox("At +1R → BE", value=True, help="Move stop to breakeven at +1R")
                trail_at_2r = st.checkbox("At +2R → +1R", value=True, help="Move stop to +1R at +2R")
            with col_trail2:
                trail_at_3r = st.checkbox("At +3R → +2R", value=True, help="Move stop to +2R at +3R")
                trail_at_4r = st.checkbox("At +4R → +3R", value=False, help="Move stop to +3R at +4R")
            # Set dummy values for other methods (not used in R-Multiple mode)
            atr_multiplier = 2.0
            trail_percentage = 5.0
            trail_trigger_r = 1.0

        elif trail_method == "ATR-Based":
            st.sidebar.caption("📈 **ATR Trailing** - Adapts to volatility")
            atr_multiplier = st.sidebar.number_input(
                "ATR Multiplier",
                min_value=0.5,
                max_value=5.0,
                value=2.0,
                step=0.5,
                help="Trail stop = Current Price - (X × ATR). Higher = wider stop."
            )
            trail_trigger_r = st.sidebar.number_input(
                "Start Trailing at +R",
                min_value=0.0,
                max_value=5.0,
                value=1.0,
                step=0.5,
                help="Only start trailing after reaching this R-multiple"
            )
            st.sidebar.info(f"💡 Stop will trail {atr_multiplier}× ATR below price once you hit +{trail_trigger_r}R")
            # Set dummy values for other methods (not used in ATR mode)
            trail_at_1r = False
            trail_at_2r = False
            trail_at_3r = False
            trail_at_4r = False
            trail_percentage = 5.0

        elif trail_method == "Percentage":
            st.sidebar.caption("📉 **Percentage Trailing** - Fixed % below price")
            trail_percentage = st.sidebar.number_input(
                "Trail Percentage",
                min_value=1.0,
                max_value=20.0,
                value=5.0,
                step=0.5,
                help="Stop = Current Price × (1 - X%). E.g., 5% = stop 5% below current price"
            )
            trail_trigger_r = st.sidebar.number_input(
                "Start Trailing at +R",
                min_value=0.0,
                max_value=5.0,
                value=1.0,
                step=0.5,
                help="Only start trailing after reaching this R-multiple"
            )
            st.sidebar.info(f"💡 Stop will trail {trail_percentage}% below price once you hit +{trail_trigger_r}R")
            # Set dummy values for other methods (not used in % mode)
            trail_at_1r = False
            trail_at_2r = False
            trail_at_3r = False
            trail_at_4r = False
            atr_multiplier = 2.0
    else:
        trail_method = "R-Multiple"
        trail_at_1r = False
        trail_at_2r = False
        trail_at_3r = False
        trail_at_4r = False
        atr_multiplier = 2.0
        trail_percentage = 5.0
        trail_trigger_r = 1.0

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
                "actual_entry": float(actual_entry) if actual_entry > 0 else 0.0,
                "actual_stop": float(actual_stop) if actual_stop > 0 else 0.0,
                "actual_target": float(actual_target) if actual_target > 0 else 0.0,
                "shares": float(shares),
                "last_price": float(actual_entry if actual_entry > 0 else entry),
                "opened": entry_date.isoformat(),
                "status": "OPEN",
                "notes": notes,
                "webull_alerts": wab,
                "trailing_enabled": enable_trailing,
                "trail_method": trail_method if enable_trailing else "R-Multiple",
                "trail_at_1r": trail_at_1r if enable_trailing else False,
                "trail_at_2r": trail_at_2r if enable_trailing else False,
                "trail_at_3r": trail_at_3r if enable_trailing else False,
                "trail_at_4r": trail_at_4r if enable_trailing else False,
                "atr_multiplier": atr_multiplier if enable_trailing else 2.0,
                "trail_percentage": trail_percentage if enable_trailing else 5.0,
                "trail_trigger_r": trail_trigger_r if enable_trailing else 1.0,
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
                    # Store the closed trade data for GPT export BEFORE closing
                    closed_trade_copy = r.copy()
                    closed_trade_copy["status"] = "CLOSED"
                    closed_trade_copy["closed"] = dt.date.today().isoformat()
                    closed_trade_copy = _compute_fields(closed_trade_copy)

                    st.session_state["just_closed_trade"] = closed_trade_copy
                    st.session_state["show_close_modal"] = True

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
# IN-MEMORY (SESSION) CACHES
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
# PRICE REFRESH (with live logging)
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

            # Apply trailing stop logic if enabled
            if r.get("trailing_enabled", False):
                entry = r.get("entry", 0)
                stop = r.get("stop", 0)
                target = r.get("target", 0)
                last = r.get("last_price", 0)
                trail_method = r.get("trail_method", "R-Multiple")

                if entry > 0 and stop > 0 and last > 0:
                    risk_per_share = entry - stop
                    unrealized_r = (last - entry) / risk_per_share if risk_per_share > 0 else 0

                    old_stop = stop
                    new_stop = stop
                    trail_reason = ""

                    # Method 1: R-Multiple Based Trailing
                    if trail_method == "R-Multiple":
                        # At +4R: Move stop to +3R
                        if r.get("trail_at_4r", False) and unrealized_r >= 4.0:
                            new_stop = entry + (3.0 * risk_per_share)
                            trail_reason = "At +4R → moved stop to +3R"

                        # At +3R: Move stop to +2R
                        elif r.get("trail_at_3r", False) and unrealized_r >= 3.0:
                            new_stop = entry + (2.0 * risk_per_share)
                            trail_reason = "At +3R → moved stop to +2R"

                        # At +2R: Move stop to +1R
                        elif r.get("trail_at_2r", False) and unrealized_r >= 2.0:
                            new_stop = entry + (1.0 * risk_per_share)
                            trail_reason = "At +2R → moved stop to +1R"

                        # At +1R: Move stop to breakeven
                        elif r.get("trail_at_1r", False) and unrealized_r >= 1.0:
                            new_stop = entry
                            trail_reason = "At +1R → moved stop to breakeven"

                    # Method 2: ATR-Based Trailing
                    elif trail_method == "ATR-Based":
                        trigger_r = r.get("trail_trigger_r", 1.0)
                        if unrealized_r >= trigger_r:
                            # Fetch current ATR for this symbol
                            try:
                                from utils.tiingo_utils import tiingo_history
                                token = _get_tiingo_token()
                                if token:
                                    df = tiingo_history(sym, token, days=30)
                                    if df is not None and len(df) > 0 and "ATR14" in df.columns:
                                        current_atr = float(df["ATR14"].iloc[-1])
                                        atr_mult = r.get("atr_multiplier", 2.0)
                                        new_stop = last - (atr_mult * current_atr)
                                        trail_reason = f"ATR Trail: {atr_mult}× ATR ({current_atr:.2f}) below ${last:.2f}"
                            except Exception as e:
                                print(f"⚠️ ATR fetch failed for {sym}: {e}")

                    # Method 3: Percentage-Based Trailing
                    elif trail_method == "Percentage":
                        trigger_r = r.get("trail_trigger_r", 1.0)
                        if unrealized_r >= trigger_r:
                            trail_pct = r.get("trail_percentage", 5.0) / 100.0
                            new_stop = last * (1 - trail_pct)
                            trail_reason = f"% Trail: {trail_pct*100:.1f}% below ${last:.2f}"

                    # Only update if new stop is higher than current stop (never lower it)
                    if new_stop > old_stop:
                        r["stop"] = round(new_stop, 2)
                        r = _compute_fields(r)
                        print(f"🎯 Trailing Stop: {sym} stop {old_stop:.2f} → {new_stop:.2f} ({trail_reason})")

        updated_rows.append(r)
        time.sleep(0.15)

    _save_trades(updated_rows)
    print("=== Done refreshing ===\n")
    return updated_rows


# ---------------------------------------------------------------------------
# REPORT AGG & RENDER
# ---------------------------------------------------------------------------
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
        
            # --- Pre-market info (Tiingo Power plan) ---
        if title.startswith("☀️"):
            from utils.tiingo_api import fetch_tiingo_realtime_quote
            quote = fetch_tiingo_realtime_quote(sy, token)
            print(f"DEBUG: realtime quote for {sy} → {quote}")
            pm_price = quote.get("last")
            pm_volume = quote.get("volume")
            if pm_price and r.get("last_price"):
                # Prefer Tiingo's prevClose if provided
                prev_close = quote.get("prevClose") or float(r["last_price"])
                gap_pct = ((pm_price - prev_close) / prev_close) * 100
                st.markdown(
                    f"📈 **Pre-market {pm_price:.2f} ({gap_pct:+.2f}%) • Vol {pm_volume:,}**"
                )



        # ⚙️ Compute & cache structured signals for Smart Coaching (report-time)
        if token:
            try:
                df = fetch_tiingo_intraday(sy, token, timeframe="1hour", lookback_days=7)
                sig = _compute_intraday_signals_df(df)
                _set_intraday_metrics_cache(sy, sig)
            except Exception:
                pass

        # 💬 Smart coach using cached signals (if available)
        st.caption("💬 " + _smart_coach(r, _get_intraday_metrics_cache().get(sy.upper())))

        # 📳 Suggested Webull alert levels
        alerts = suggest_alert_levels(r)
        if alerts:
            st.caption("📳 **Webull Alert Suggestions:**")
            for label, val in alerts.items():
                st.markdown(f"- {label}: `{val}`")

        # 🧠 Intraday insights summary
        if token:
            try:
                st.caption("🧠 " + _intraday_coaching(sy, token))
            except Exception:
                st.caption("🧠 Intraday: unavailable right now.")

        if r.get("webull_alerts"):
            st.caption("🔔 Webull: " + str(r.get("webull_alerts", "")))


# ---------------------------------------------------------------------------
# COPY-FOR-AI PROMPT
# ---------------------------------------------------------------------------
def _build_ai_prompt(row: Dict[str, Any], sig: IntradaySignals | None, intraday_text: str) -> str:
    """Create a copy-ready prompt you can paste into ChatGPT (educational coaching only)."""
    sy = (row.get("symbol") or "").upper()
    entry = row.get("entry")
    stop = row.get("stop")
    target = row.get("target")
    shares = row.get("shares")
    last = row.get("last_price")
    rr = row.get("rr")
    unr = row.get("unrealized_r")
    prog = row.get("progress_to_target")
    dist = row.get("distance_from_stop")
    notes = row.get("notes", "")

    sig_str = "-"
    if sig and sig.lookback_ok:
        bits = []
        if sig.rsi is not None:
            bits.append(f"RSI {sig.rsi:.0f}")
        if sig.ema_fast_above_slow is not None:
            bits.append("EMA20>EMA50" if sig.ema_fast_above_slow else "EMA20<EMA50")
        if sig.ema_slope_up is not None:
            bits.append("EMA20 rising" if sig.ema_slope_up else "EMA20 falling")
        if sig.vol_ratio is not None:
            bits.append(f"Vol× {sig.vol_ratio:.2f}")
        sig_str = " | ".join(bits)

    # --- ChatGPT version (simple) ---
    return (
        "You are a swing-trading coach. Provide educational coaching only — no financial advice.\n\n"
        f"Symbol: {sy}\n"
        f"Plan: entry {entry}, stop {stop}, target {target}, shares {shares}\n"
        f"Live: last {last}, R/R {rr}, unrealizedR {unr}, progress_to_target {prog}, distance_from_stop {dist}\n"
        f"Intraday signals: {sig_str}\n"
        f"Intraday notes: {intraday_text or '-'}\n"
        f"Trader notes: {notes or '-'}\n\n"
        "Before analyzing, fetch **fresh, real-time price data** for this symbol from Yahoo Finance or another "
        "reliable market data source. Use that updated price when evaluating risk, R/R, and position context.\n\n"
        "Coach me on:\n"
        "- risk and position management,\n"
        "- realistic next steps for the current context,\n"
        "- what to watch for next technically and emotionally."
    )


def _build_ai_prompt_claude(row: Dict[str, Any], sig: IntradaySignals | None, intraday_text: str) -> str:
    """Create a Claude-optimized prompt with structured format."""
    sy = (row.get("symbol") or "").upper()
    entry = row.get("entry")
    stop = row.get("stop")
    target = row.get("target")
    shares = row.get("shares")
    last = row.get("last_price")
    rr = row.get("rr")
    unr = row.get("unrealized_r")
    prog = row.get("progress_to_target", 0)
    dist = row.get("distance_from_stop", 0)
    notes = row.get("notes", "")

    # Calculate percentages
    prog_pct = prog * 100 if prog else 0
    dist_pct = dist * 100 if dist else 0

    # Build intraday signals section
    intraday_section = ""
    if sig and sig.lookback_ok:
        rsi_str = f"{sig.rsi:.0f}" if sig.rsi else "N/A"
        trend_str = "EMA20 > EMA50 ✅" if sig.ema_fast_above_slow else "EMA20 < EMA50 ⚠️"
        ema_str = "Rising ✅" if sig.ema_slope_up else "Falling ⚠️"
        vol_str = f"{sig.vol_ratio:.2f}x average" if sig.vol_ratio else "N/A"

        intraday_section = f"""
📊 INTRADAY SIGNALS (Last Hour):
- RSI: {rsi_str}
- Trend: {trend_str}
- EMA20: {ema_str}
- Volume: {vol_str}
"""

    # Format values safely
    last_str = f"${last:.2f}" if last else "N/A"
    entry_str = f"${entry:.2f}" if entry else "N/A"
    stop_str = f"${stop:.2f}" if stop else "N/A"
    target_str = f"${target:.2f}" if target else "N/A"
    rr_str = f"{rr:.2f}:1" if rr else "N/A"
    unr_str = f"{unr:.2f}R" if unr else "N/A"

    return f"""Act as my swing trading coach for an ACTIVE POSITION. Focus on risk management and exit strategy.

📈 ACTIVE TRADE:
Symbol: {sy}
Shares: {shares}
Current Price: {last_str}

🎯 ORIGINAL PLAN:
- Entry: {entry_str}
- Stop Loss: {stop_str}
- Target: {target_str}
- Planned R:R: {rr_str}

📊 CURRENT STATUS:
- Unrealized R: {unr_str}
- Progress to Target: {prog_pct:.1f}%
- Distance from Stop: {dist_pct:.1f}%
{intraday_section}
💭 MY NOTES:
{notes or 'None'}

❓ COACHING QUESTIONS:
1. Should I hold, scale out, or exit completely based on current price action?
2. Where should I move my stop loss (if at all)?
3. What are the key levels to watch for next move?
4. What could invalidate this trade (exit signals)?
5. How should I manage this emotionally (avoid panic/greed)?

📋 INSTRUCTIONS:
- Fetch LIVE price data from Yahoo Finance before analyzing
- Be specific about price levels and actions
- Consider both technical and psychological aspects
- Rate the current risk level (Low/Medium/High)
- Suggest concrete next steps

Remember: I'm in this trade NOW and need actionable guidance, not generic advice.
"""



# ---------------------------------------------------------------------------
# MAIN PAGE RENDER
# ---------------------------------------------------------------------------
def _render_open_positions(rows: List[Dict[str, Any]]) -> None:
    # Reset number_input widgets after global refresh to force live values
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
    sig_cache = _get_intraday_metrics_cache()
    token = _get_tiingo_token()

    for idx, r in enumerate(opens):
        r = _compute_fields(r)
        sy = r.get("symbol", "")

        # Fetch ATR if trailing is enabled and ATR-based
        if r.get("trailing_enabled") and r.get("trail_method") == "ATR-Based":
            if "atr14" not in r or r.get("atr14", 0) == 0:
                atr = _fetch_atr(sy)
                if atr:
                    r["atr14"] = atr

        # Build header with actual prices if available
        actual_entry = r.get('actual_entry', 0)
        actual_stop = r.get('actual_stop', 0)
        actual_target = r.get('actual_target', 0)

        # Determine which prices to display
        display_entry = actual_entry if actual_entry > 0 else r.get('entry')
        display_stop = actual_stop if actual_stop > 0 else r.get('stop')
        display_target = actual_target if actual_target > 0 else r.get('target', 0)

        header_parts = [
            f"**{sy}** — entry {display_entry} | stop {display_stop} | "
            f"target {display_target} | shares {r.get('shares', 0)}"
        ]

        # Add indicator if using actual prices
        if actual_entry > 0:
            header_parts.append(" | 💰 **Using Actual Fill**")
            if r.get('entry') != actual_entry:
                header_parts.append(f" (planned: ${r.get('entry'):.2f})")

        # Add trailing stop indicator if enabled
        if r.get("trailing_enabled", False):
            trail_method = r.get("trail_method", "R-Multiple")
            unrealized_r = r.get("unrealized_r", 0)

            if trail_method == "R-Multiple":
                if unrealized_r >= 4.0 and r.get("trail_at_4r", False):
                    header_parts.append(" | 🎯 **Trailing: +4R → Stop at +3R**")
                elif unrealized_r >= 3.0 and r.get("trail_at_3r", False):
                    header_parts.append(" | 🎯 **Trailing: +3R → Stop at +2R**")
                elif unrealized_r >= 2.0 and r.get("trail_at_2r", False):
                    header_parts.append(" | 🎯 **Trailing: +2R → Stop at +1R**")
                elif unrealized_r >= 1.0 and r.get("trail_at_1r", False):
                    header_parts.append(" | 🎯 **Trailing: +1R → Stop at BE**")
                else:
                    header_parts.append(" | 🎯 R-Trail Active")

            elif trail_method == "ATR-Based":
                atr_mult = r.get("atr_multiplier", 2.0)
                trigger_r = r.get("trail_trigger_r", 1.0)
                atr_value = r.get("atr14", 0)  # Will be fetched below
                last_price = r.get("last_price", 0)

                if unrealized_r >= trigger_r and atr_value > 0 and last_price > 0:
                    calculated_stop = last_price - (atr_mult * atr_value)
                    header_parts.append(f" | 🎯 **ATR Trail: ${calculated_stop:.2f}** ({atr_mult}× ATR)")
                elif unrealized_r >= trigger_r:
                    header_parts.append(f" | 🎯 **ATR Trail: {atr_mult}× ATR** (calculating...)")
                else:
                    header_parts.append(f" | 🎯 ATR Trail (starts at +{trigger_r}R)")

            elif trail_method == "Percentage":
                trail_pct = r.get("trail_percentage", 5.0)
                trigger_r = r.get("trail_trigger_r", 1.0)
                last_price = r.get("last_price", 0)

                if unrealized_r >= trigger_r and last_price > 0:
                    calculated_stop = last_price * (1 - trail_pct / 100)
                    header_parts.append(f" | 🎯 **% Trail: ${calculated_stop:.2f}** ({trail_pct}% below)")
                else:
                    header_parts.append(f" | 🎯 % Trail (starts at +{trigger_r}R)")

        st.markdown("".join(header_parts))
        c = st.columns([1.2, 1, 1, 1, 1])
        with c[0]:
            last_val = st.number_input(
                "Last Price",
                min_value=0.0,
                step=0.01,
                value=float(r.get("last_price", r.get("entry", 0)) or 0),
                key=f"atc_last_{sy}_{idx}_{int(st.session_state.get('refresh_counter', 0))}",
            )
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

        # 🎯 Trailing Stop Callout (if enabled and active)
        if r.get("trailing_enabled", False):
            trail_method = r.get("trail_method", "R-Multiple")
            unrealized_r = r.get("unrealized_r", 0)
            trigger_r = r.get("trail_trigger_r", 1.0)

            if unrealized_r >= trigger_r:
                if trail_method == "ATR-Based":
                    atr_mult = r.get("atr_multiplier", 2.0)
                    atr_value = r.get("atr14", 0)
                    last_price = r.get("last_price", 0)

                    if atr_value > 0 and last_price > 0:
                        calculated_stop = last_price - (atr_mult * atr_value)
                        st.info(f"🎯 **TRAILING STOP ACTIVE:** Set your stop at **${calculated_stop:.2f}** (Current Price ${last_price:.2f} - {atr_mult}× ATR ${atr_value:.2f})")
                    else:
                        st.warning(f"🎯 **TRAILING STOP ACTIVE:** ATR data loading... (Method: {atr_mult}× ATR)")

                elif trail_method == "Percentage":
                    trail_pct = r.get("trail_percentage", 5.0)
                    last_price = r.get("last_price", 0)

                    if last_price > 0:
                        calculated_stop = last_price * (1 - trail_pct / 100)
                        st.info(f"🎯 **TRAILING STOP ACTIVE:** Set your stop at **${calculated_stop:.2f}** ({trail_pct}% below ${last_price:.2f})")

                elif trail_method == "R-Multiple":
                    entry = r.get("entry", 0)
                    stop = r.get("stop", 0)
                    risk_ps = entry - stop if entry and stop else 0

                    # Determine which R-level to trail to
                    if unrealized_r >= 4.0 and r.get("trail_at_4r", False):
                        new_stop = entry + (3 * risk_ps)
                        st.info(f"🎯 **TRAILING STOP ACTIVE:** Move stop to **${new_stop:.2f}** (+3R)")
                    elif unrealized_r >= 3.0 and r.get("trail_at_3r", False):
                        new_stop = entry + (2 * risk_ps)
                        st.info(f"🎯 **TRAILING STOP ACTIVE:** Move stop to **${new_stop:.2f}** (+2R)")
                    elif unrealized_r >= 2.0 and r.get("trail_at_2r", False):
                        new_stop = entry + (1 * risk_ps)
                        st.info(f"🎯 **TRAILING STOP ACTIVE:** Move stop to **${new_stop:.2f}** (+1R)")
                    elif unrealized_r >= 1.0 and r.get("trail_at_1r", False):
                        st.info(f"🎯 **TRAILING STOP ACTIVE:** Move stop to **${entry:.2f}** (Breakeven)")

        # 💬 Smart Coaching (uses cached intraday metrics when available)
        sig = sig_cache.get(sy.upper())
        st.caption("💬 " + _smart_coach(r, sig))

        # 🧠 Intraday coaching: cached text if available; hint otherwise
        intraday_text = intraday_cache.get(sy.upper())
        if intraday_text:
            st.caption("🧠 " + intraday_text)
        else:
            if token:
                st.caption("🧠 Click '🔍 Run Intraday Coaching (this ticker only)' in the sidebar to compute.")

        # 📋 Trade Management Plan
        with st.expander("📋 Trade Management Plan", expanded=False):
            plan = generate_trade_management_plan(r)
            st.markdown(plan)

        # 📋 GPT Export Options (Enhanced)
        with st.expander("💬 Copy for Custom GPT", expanded=False):
            st.markdown("**Choose export format:**")

            # Enhance trade data with intraday signals
            enhanced_trade_data = r.copy()
            if sig:
                enhanced_trade_data["intraday_rsi"] = f"{sig.rsi:.1f}" if sig.rsi is not None else "N/A"
                enhanced_trade_data["intraday_trend"] = "Bullish ✅" if sig.ema_fast_above_slow else "Bearish ⚠️"
                enhanced_trade_data["intraday_volume"] = f"{sig.vol_ratio:.2f}x avg" if sig.vol_ratio is not None else "N/A"

            # Removed: Live Update GPT export (replaced with built-in Claude AI analysis)

            st.markdown("---")

            # Removed: Coaching Request copy/paste (replaced with built-in Claude AI Trade Analysis)

            # Trade Plan (for reference)
            st.markdown("---")
            st.markdown("**📋 Original Trade Plan**")
            # Removed: Trade Plan GPT export (replaced with built-in Claude AI analysis)

        st.markdown("---")


def _render_closed_positions(rows: List[Dict[str, Any]]) -> None:
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    if not closed:
        return
    with st.expander("📦 Closed Trades", expanded=False):
        for idx, r in enumerate(closed):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(
                    f"**{r.get('symbol', '')}** — opened {r.get('opened', '?')} • "
                    f"closed {r.get('closed', '?')} • entry {r.get('entry')} • "
                    f"stop {r.get('stop')} • target {r.get('target', 0)} • shares {r.get('shares', 0)}"
                )

            # Removed: GPT Trade Review export (replaced with built-in Claude AI analysis)

            st.markdown("---")


# ---------------------------------------------------------------------------
# PUBLIC ENTRY — (used by app.py)
# ---------------------------------------------------------------------------
def active_trades_ui() -> None:
    st.title("💼 Active Trades")
    st.caption("Track, update, and coach your open trades.")

    # ===================== Close Trade Modal =====================
    if st.session_state.get("show_close_modal") and "just_closed_trade" in st.session_state:
        closed_trade = st.session_state["just_closed_trade"]

        # Show modal dialog for closing trade
        @st.dialog("📝 Close Trade & Add to Journal")
        def show_close_dialog():
            st.success(f"✅ Closing trade: **{closed_trade.get('symbol')}**")
            st.markdown("---")

            # Get exit details for journaling
            st.subheader("📊 Exit Details")
            col1, col2 = st.columns(2)

            with col1:
                exit_price = st.number_input(
                    "Exit Price",
                    min_value=0.01,
                    value=float(closed_trade.get("last_price", closed_trade.get("entry", 100.0))),
                    step=0.01,
                    key="modal_exit_price",
                    help="The price at which you exited the trade"
                )

            with col2:
                exit_reason = st.selectbox(
                    "Exit Reason",
                    ["Hit Target", "Hit Stop", "Trailing Stop", "Time Stop", "Manual Exit", "Other"],
                    key="modal_exit_reason",
                    help="Why did you exit this trade?"
                )

            # Calculate P&L preview
            entry = float(closed_trade.get("entry", 0))
            shares = float(closed_trade.get("shares", 0))
            pnl = (exit_price - entry) * shares
            pnl_pct = ((exit_price - entry) / entry) * 100 if entry else 0

            col1, col2 = st.columns(2)
            with col1:
                st.metric("P&L", f"${pnl:+,.2f}")
            with col2:
                st.metric("Return", f"{pnl_pct:+.1f}%")

            # Mistake Tracker (only show if it's a loss)
            mistake = None
            if pnl < 0:
                st.markdown("---")
                st.subheader("🚨 Mistake Tracker (Optional)")
                st.caption("Help identify patterns in your losing trades")

                mistake = st.selectbox(
                    "What went wrong? (Select if applicable)",
                    [
                        "None - Followed my plan perfectly",
                        "Entered too early",
                        "Entered too late",
                        "Didn't follow my stop",
                        "Moved my stop (gave it more room)",
                        "Took profit too early",
                        "Held past my target (greed)",
                        "Ignored my rules",
                        "Traded on emotion",
                        "Position size too large",
                        "Traded during earnings",
                        "Traded against the trend",
                        "FOMO trade (no setup)",
                        "Revenge trading",
                        "Other"
                    ],
                    key="modal_mistake",
                    help="Tracking mistakes helps you identify patterns and improve faster"
                )

            st.info("💡 **Tip:** Trade will be saved to Journal. You can add notes and get GPT coaching from the Journal page!")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state["show_close_modal"] = False
                    if "just_closed_trade" in st.session_state:
                        del st.session_state["just_closed_trade"]
                    st.rerun()
            with col2:
                if st.button("✅ Save to Journal", use_container_width=True, type="primary"):
                    # Add to journal automatically (with mistake if applicable)
                    add_to_journal(closed_trade, exit_price, exit_reason, mistake=mistake)

                    st.session_state["show_close_modal"] = False
                    if "just_closed_trade" in st.session_state:
                        del st.session_state["just_closed_trade"]

                    st.success("✅ Trade added to Journal!")
                    st.balloons()
                    st.rerun()

        show_close_dialog()

    # ===================== Performance Analytics Dashboard =====================
    stats = calculate_performance_stats()

    if stats:
        st.divider()
        st.subheader("📊 Performance Analytics")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            win_rate = stats.get("win_rate", 0)
            color = "green" if win_rate >= 50 else "orange" if win_rate >= 40 else "red"
            st.markdown(
                f"<div style='background-color:{color};padding:10px;border-radius:10px;color:white;text-align:center;'>"
                f"<b>Win Rate</b><br>{win_rate:.1f}%<br>"
                f"<small>{stats.get('wins', 0)}W / {stats.get('losses', 0)}L</small></div>",
                unsafe_allow_html=True
            )

        with col2:
            total_pnl = stats.get("total_pnl", 0)
            color = "green" if total_pnl > 0 else "red"
            st.markdown(
                f"<div style='background-color:{color};padding:10px;border-radius:10px;color:white;text-align:center;'>"
                f"<b>Total P&L</b><br>${total_pnl:,.2f}<br>"
                f"<small>{stats.get('total_trades', 0)} trades</small></div>",
                unsafe_allow_html=True
            )

        with col3:
            avg_r = stats.get("avg_r_multiple", 0)
            color = "green" if avg_r > 1 else "orange" if avg_r > 0.5 else "red"
            st.markdown(
                f"<div style='background-color:{color};padding:10px;border-radius:10px;color:white;text-align:center;'>"
                f"<b>Avg R-Multiple</b><br>{avg_r:.2f}R<br>"
                f"<small>Per trade</small></div>",
                unsafe_allow_html=True
            )

        with col4:
            profit_factor = stats.get("profit_factor", 0)
            color = "green" if profit_factor > 2 else "orange" if profit_factor > 1 else "red"
            st.markdown(
                f"<div style='background-color:{color};padding:10px;border-radius:10px;color:white;text-align:center;'>"
                f"<b>Profit Factor</b><br>{profit_factor:.2f}<br>"
                f"<small>Avg Win / Avg Loss</small></div>",
                unsafe_allow_html=True
            )

        with col5:
            largest_win = stats.get("largest_win", 0)
            st.markdown(
                f"<div style='background-color:blue;padding:10px;border-radius:10px;color:white;text-align:center;'>"
                f"<b>Best Trade</b><br>${largest_win:,.2f}<br>"
                f"<small>Largest win</small></div>",
                unsafe_allow_html=True
            )

        # Additional stats in expander
        with st.expander("📈 Detailed Statistics"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Average Win", f"${stats.get('avg_win', 0):,.2f}")
                st.metric("Average Loss", f"${stats.get('avg_loss', 0):,.2f}")
            with col_b:
                st.metric("Largest Win", f"${stats.get('largest_win', 0):,.2f}")
                st.metric("Largest Loss", f"${stats.get('largest_loss', 0):,.2f}")

    st.divider()

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

        # Mark that a global refresh occurred (used by _render_open_positions)
        st.session_state["force_refresh"] = True

        # Reload fresh data so new prices appear on next render
        rows = _load_trades()
        rows = [_compute_fields(r) for r in rows]

        # Increment refresh counter to force new widget keys (rebuilds inputs)
        st.session_state["refresh_counter"] = st.session_state.get("refresh_counter", 0) + 1
        st.rerun()

    if auto_refresh and not st.session_state.get("auto_refreshed_once", False):
        rows = _refresh_intraday_for_opens(rows)
        _save_trades(rows)
        st.session_state["auto_refreshed_once"] = True
        st.success("Auto-refreshed prices once on load.")

    action = _sidebar_controls(rows)

    # Persist the last clicked report type (so page reload keeps it)
    if action in ("morning", "eod"):
        st.session_state["last_action"] = action
    elif not action:
        action = st.session_state.get("last_action", "")
        
        print(f"DEBUG main received action = {action!r}")


    token = _get_tiingo_token()

    # --- Handle per-ticker intraday coaching run ---
    if isinstance(action, str) and action.startswith("ticker:"):
        sym = action.split(":", 1)[1].upper().strip()
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
            # Compute & cache *both* coaching text and structured signals
            try:
                df = fetch_tiingo_intraday(sym, token, timeframe="1hour", lookback_days=7)
                txt = _intraday_coaching(sym, token)
                sig = _compute_intraday_signals_df(df)
            except Exception:
                txt = "Intraday: unavailable right now."
                sig = None
            _set_intraday_cache(sym, txt)
            if sig:
                _set_intraday_metrics_cache(sym, sig)
            st.session_state["force_refresh"] = True
            # Safer cache-bust without relying on st.set_query_params
            try:
                st.query_params.update({"_": str(time.time())})
            except Exception:
                pass
            st.rerun()

        # --- Reports (across ALL open trades) ---
    # --- Reports (across ALL open trades) ---
    if action in ("morning", "eod"):
        title = "☀️ Morning Report" if action == "morning" else "🌇 End-of-Day Report"

        if not st.session_state.get("_report_active", False):
            # First time: mark active and do a one-time price refresh
            st.session_state["_report_active"] = True
            rows = _refresh_intraday_for_opens(rows)

        # Always render the report while active
        _render_report(rows, title)
        st.markdown("---")

        # Clear button resets state and re-runs once
        if st.button("🧹 Clear Report"):
            st.session_state["_report_active"] = False
            st.session_state["last_action"] = ""
            st.session_state["force_refresh"] = True
            st.rerun()






    # --- Forced reload after any mutation ---
    if st.session_state.get("force_refresh"):
        del st.session_state["force_refresh"]
        rows = _load_trades()
        rows = [_compute_fields(r) for r in rows]

    # ============================================================================
    # CLAUDE AI TRADE ANALYSIS
    # ============================================================================
    st.markdown("---")
    st.markdown("## 🤖 AI Trade Analysis (Claude)")
    st.caption("Get Claude's analysis of your active trades with actionable recommendations")

    # Get open trades
    open_trades = [r for r in rows if r.get("status") == "OPEN"]

    # DEBUG: Show what we found
    st.caption(f"🔍 DEBUG: Total trades loaded: {len(rows)}, Open trades: {len(open_trades)}")
    if rows and len(rows) > 0:
        statuses = [r.get("status", "NO_STATUS") for r in rows]
        st.caption(f"🔍 DEBUG: Trade statuses: {statuses}")

    # Check if Claude API is configured
    anthropic_key = (
        st.secrets.get("swingfinder_key") or
        st.secrets.get("ANTHROPIC_API_KEY") or
        os.getenv("ANTHROPIC_API_KEY") or
        os.getenv("swingfinder_key")
    )
    tiingo_token = _get_tiingo_token()

    if not anthropic_key:
        st.warning("⚠️ Claude API not configured. Add your Claude API key to use AI trade analysis.")
    elif not open_trades:
        st.info("📭 No open trades to analyze. Open some trades first!")
    else:
        # Multiselect for trade selection
        trade_options = []
        for t in open_trades:
            symbol = t.get('symbol', 'N/A')
            entry = t.get('entry', 0)
            current = t.get('last_price', 0) or 0
            pnl_pct = ((current - entry) / entry * 100) if entry > 0 else 0
            trade_options.append(f"{symbol} - Entry: ${entry:.2f}, Current: ${current:.2f} ({pnl_pct:+.1f}%)")

        selected_trades_display = st.multiselect(
            "Select trades to analyze:",
            options=trade_options,
            default=[]
        )

        if selected_trades_display:
            # Map selected display names back to trade dictionaries
            selected_symbols = [s.split(" - ")[0] for s in selected_trades_display]
            selected_trades = [t for t in open_trades if t.get('symbol') in selected_symbols]

            # DEBUG: Show what data we're sending
            with st.expander("🔍 Debug: View Trade Data Being Sent to Analyzer", expanded=False):
                for trade in selected_trades:
                    st.json({
                        'symbol': trade.get('symbol'),
                        'entry': trade.get('entry'),
                        'stop': trade.get('stop'),
                        'target': trade.get('target'),
                        'shares': trade.get('shares'),
                        'opened': trade.get('opened'),
                        'entry_date': trade.get('entry_date'),
                    })

            if st.button(f"🤖 Analyze {len(selected_trades)} Selected Trade{'s' if len(selected_trades) > 1 else ''}",
                        type="primary", use_container_width=True):
                if not tiingo_token:
                    st.error("❌ Tiingo API token not configured")
                else:
                    with st.spinner(f"🤖 Analyzing {len(selected_trades)} trade(s)... (with prompt caching)"):
                        analysis = analyze_active_trades(
                            selected_trades=selected_trades,
                            token=tiingo_token,
                            api_key=anthropic_key
                        )

                        st.markdown(f"### 🎯 Trade Analysis: {', '.join(selected_symbols)}")
                        st.markdown(analysis)

                        st.session_state['trade_analysis'] = analysis
                        st.session_state['trade_analysis_time'] = dt.datetime.now().strftime("%Y-%m-%d %I:%M %p")
                        st.session_state['trade_analysis_symbols'] = selected_symbols

        # Show previous analysis
        if 'trade_analysis' in st.session_state:
            trades_analyzed = st.session_state.get('trade_analysis_symbols', [])
            st.caption(f"💾 Last analysis: {', '.join(trades_analyzed)} at {st.session_state.get('trade_analysis_time', 'Unknown')}")
            with st.expander("📊 View Last Trade Analysis", expanded=False):
                st.markdown(st.session_state['trade_analysis'])

    st.markdown("---")

    # --- Main content ---
    _render_open_positions(rows)
    _render_closed_positions(rows)
