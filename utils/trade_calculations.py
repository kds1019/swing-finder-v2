"""
utils/trade_calculations.py
Pure calculation and coaching helpers for active trades.
No Streamlit dependency — safe to import and unit-test anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# TRADE MANAGEMENT PLAN
# ---------------------------------------------------------------------------
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
# FIELD CALCULATIONS
# ---------------------------------------------------------------------------
def _compute_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    try:
        planned_entry = float(row.get("entry", 0) or 0)
        actual_entry = float(row.get("actual_entry", 0) or 0)
        entry = actual_entry if actual_entry > 0 else planned_entry

        planned_stop = float(row.get("stop", 0) or 0)
        actual_stop = float(row.get("actual_stop", 0) or 0)
        if actual_entry > 0 and actual_stop == 0 and planned_entry > 0 and planned_stop > 0:
            risk_ratio = (planned_entry - planned_stop) / planned_entry
            actual_stop = actual_entry * (1 - risk_ratio)
        stop = actual_stop if actual_stop > 0 else planned_stop

        planned_target = float(row.get("target", 0) or 0)
        actual_target = float(row.get("actual_target", 0) or 0)
        if actual_entry > 0 and actual_target == 0 and planned_entry > 0 and planned_target > 0:
            reward_ratio = (planned_target - planned_entry) / planned_entry
            actual_target = actual_entry * (1 + reward_ratio)
        target = actual_target if actual_target > 0 else planned_target

        shares = float(row.get("shares", row.get("size", 0)) or 0)
        last = float(row.get("last_price", entry or 0) or 0)
        realized_pnl = float(row.get("realized_pnl", 0) or 0)

        risk_ps = (entry - stop) if entry and stop else 0.0
        reward_ps = (target - entry) if target and entry else 0.0
        rr = (reward_ps / risk_ps) if risk_ps else 0.0
        unreal_r = ((last - entry) / risk_ps) if (risk_ps and last) else 0.0
        pos_risk = risk_ps * shares if (risk_ps and shares) else 0.0
        unrealized_pnl_dollar = round((last - entry) * shares, 2) if (last and entry and shares) else 0.0
        total_pnl_dollar = round(unrealized_pnl_dollar + realized_pnl, 2)
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

        out.update({
            "risk_per_share": round(risk_ps, 4),
            "reward_per_share": round(reward_ps, 4),
            "rr": round(rr, 2),
            "unrealized_r": round(unreal_r, 2),
            "position_risk": round(pos_risk, 2),
            "unrealized_pnl_dollar": unrealized_pnl_dollar,
            "total_pnl_dollar": total_pnl_dollar,
            "progress_to_target": round(1 - to_target, 3) if isinstance(to_target, (float, int)) else None,
            "distance_from_stop": round(to_stop, 3) if isinstance(to_stop, (float, int)) else None,
        })
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# SIMPLE COACHING BLURB
# ---------------------------------------------------------------------------
def _coaching_blurb(symbol: str, row: Dict[str, Any]) -> str:
    last = float(row.get("last_price", 0) or 0)
    entry = float(row.get("entry", 0) or 0)
    rr = float(row.get("rr", 0) or 0)
    unr = float(row.get("unrealized_r", 0) or 0)
    prog = row.get("progress_to_target", None)
    dist = row.get("distance_from_stop", None)

    parts = []
    if last and entry:
        parts.append(f"Price {'up' if last >= entry else 'down'} vs entry: {last:.2f} vs {entry:.2f}.")
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
# INTRADAY SIGNALS + SMART COACH
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

    ema20 = df["close"].ewm(span=20).mean()
    ema50 = df["close"].ewm(span=50).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0.0).rolling(14).mean()
    loss = (-delta.clip(upper=0.0)).rolling(14).mean()
    avg_loss = loss.replace(0, float("nan"))
    rs_series = gain / avg_loss
    rsi_series = 100 - (100 / (1 + rs_series))
    rsi_val = float(rsi_series.iloc[-1]) if rsi_series.iloc[-1] == rsi_series.iloc[-1] else 50.0

    ema_fast_above_slow = bool(ema20.iloc[-1] > ema50.iloc[-1])
    ema_slope_up = bool(ema20.iloc[-1] > ema20.iloc[-2]) if len(ema20) > 2 else None

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


def _smart_coach(row: dict, sig: "IntradaySignals | None") -> str:
    """Rule-based coach combining plan + intraday signals."""
    parts: list[str] = []

    entry = float(row.get("entry", 0) or 0)
    stop = float(row.get("stop", 0) or 0)
    target = float(row.get("target", 0) or 0)
    last = float(row.get("last_price", entry or 0) or 0)
    rr = float(row.get("rr", 0) or 0)
    unr = float(row.get("unrealized_r", 0) or 0)
    prog = row.get("progress_to_target", None)
    dist = row.get("distance_from_stop", None)

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

    if not parts:
        if last and entry:
            parts.append(f"Price {'above' if last >= entry else 'below'} entry ({last:.2f} vs {entry:.2f}); follow plan.")
        else:
            parts.append("Follow plan and sizing; keep risk defined.")

    seen: set[str] = set()
    ordered: list[str] = []
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
    if last and entry and stop and target:
        move_up = abs(target - entry) / 2
        move_down = abs(entry - stop) / 2
        alerts["Momentum Up"] = round(last + move_up, 2)
        alerts["Momentum Down"] = round(last - move_down, 2)
    return alerts


# ---------------------------------------------------------------------------
# PORTFOLIO AGGREGATE METRICS
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


# ---------------------------------------------------------------------------
# AI PROMPT BUILDERS (copy-for-AI helpers)
# ---------------------------------------------------------------------------
def _build_ai_prompt(row: Dict[str, Any], sig: "IntradaySignals | None", intraday_text: str) -> str:
    """Create a copy-ready prompt for ChatGPT (educational coaching only)."""
    sy = (row.get("symbol") or "").upper()
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

    return (
        "You are a swing-trading coach. Provide educational coaching only — no financial advice.\n\n"
        f"Symbol: {sy}\n"
        f"Plan: entry {row.get('entry')}, stop {row.get('stop')}, target {row.get('target')}, shares {row.get('shares')}\n"
        f"Live: last {row.get('last_price')}, R/R {row.get('rr')}, unrealizedR {row.get('unrealized_r')}, "
        f"progress_to_target {row.get('progress_to_target')}, distance_from_stop {row.get('distance_from_stop')}\n"
        f"Intraday signals: {sig_str}\n"
        f"Intraday notes: {intraday_text or '-'}\n"
        f"Trader notes: {row.get('notes', '') or '-'}\n\n"
        "Coach me on:\n"
        "- risk and position management,\n"
        "- realistic next steps for the current context,\n"
        "- what to watch for next technically and emotionally."
    )


def _build_ai_prompt_claude(row: Dict[str, Any], sig: "IntradaySignals | None", intraday_text: str) -> str:
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

    prog_pct = prog * 100 if prog else 0
    dist_pct = dist * 100 if dist else 0

    intraday_section = ""
    if sig and sig.lookback_ok:
        rsi_str = f"{sig.rsi:.0f}" if sig.rsi else "N/A"
        trend_str = "EMA20 > EMA50 ✅" if sig.ema_fast_above_slow else "EMA20 < EMA50 ⚠️"
        ema_str = "Rising ✅" if sig.ema_slope_up else "Falling ⚠️"
        vol_str = f"{sig.vol_ratio:.2f}x average" if sig.vol_ratio else "N/A"
        intraday_section = f"\n📊 INTRADAY SIGNALS:\n- RSI: {rsi_str}\n- Trend: {trend_str}\n- EMA20: {ema_str}\n- Volume: {vol_str}\n"

    last_str = f"${last:.2f}" if last else "N/A"
    entry_str = f"${entry:.2f}" if entry else "N/A"
    stop_str = f"${stop:.2f}" if stop else "N/A"
    target_str = f"${target:.2f}" if target else "N/A"
    rr_str = f"{rr:.2f}:1" if rr else "N/A"
    unr_str = f"{unr:.2f}R" if unr else "N/A"

    return f"""Act as my swing trading coach for an ACTIVE POSITION.

📈 ACTIVE TRADE: {sy} | {shares} shares | Current: {last_str}
🎯 PLAN: Entry {entry_str} | Stop {stop_str} | Target {target_str} | R:R {rr_str}
📊 STATUS: Unrealized {unr_str} | Progress to Target {prog_pct:.1f}% | Distance from Stop {dist_pct:.1f}%
{intraday_section}
💭 NOTES: {row.get('notes', 'None') or 'None'}

Provide: hold/scale/exit recommendation, stop adjustment, key levels, invalidation signals, risk rating.
"""
