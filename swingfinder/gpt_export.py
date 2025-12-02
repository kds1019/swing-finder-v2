"""
GPT Export Module for SwingFinder
Formats trade data for your custom ChatGPT coaching assistant.
"""

from typing import Dict, Any, Optional


def build_trade_plan_for_gpt(data: Dict[str, Any]) -> str:
    """
    Format a new trade plan for GPT coaching.
    
    Args:
        data: Trade dictionary with entry, stop, target, shares, setup, etc.
    
    Returns:
        Formatted text ready to paste into your custom GPT
    """
    symbol = data.get("symbol", "").upper()
    entry = data.get("entry", 0)
    stop = data.get("stop", 0)
    target = data.get("target", 0)
    shares = data.get("shares", 0)
    setup = data.get("setup_type", "")
    timeframe = data.get("timeframe", "Daily")
    notes = data.get("notes", "")
    
    # Calculate R values
    risk_r = abs(entry - stop) if entry and stop else 0
    reward_r = abs(target - entry) if entry and target else 0
    rr_ratio = round(reward_r / risk_r, 2) if risk_r > 0 else 0
    
    return f"""Trade Plan:
Symbol: {symbol}
Entry: ${entry:.2f}
Stop: ${stop:.2f}
Target: ${target:.2f}
Shares: {shares}
Setup Type: {setup}
Timeframe: {timeframe}
Indicators / Technical Notes: {notes or "None provided"}
Risk (R): ${risk_r:.2f}
Reward (R): ${reward_r:.2f}
R/R Ratio: {rr_ratio}"""


def build_live_update_for_gpt(data: Dict[str, Any]) -> str:
    """
    Format a live trade update for GPT coaching.
    
    Args:
        data: Trade dictionary with current price, unrealized R, progress, etc.
    
    Returns:
        Formatted text ready to paste into your custom GPT
    """
    symbol = data.get("symbol", "").upper()
    last_price = data.get("last_price", 0)
    unrealized_r = data.get("unrealized_r", 0)
    distance_from_stop = data.get("distance_from_stop", "N/A")
    progress_to_target = data.get("progress_to_target", "N/A")
    entry = data.get("entry", 0)
    stop = data.get("stop", 0)
    target = data.get("target", 0)
    
    # Format distance and progress
    if isinstance(distance_from_stop, (int, float)):
        distance_str = f"{distance_from_stop:.1f}%"
    else:
        distance_str = str(distance_from_stop)
    
    if isinstance(progress_to_target, (int, float)):
        progress_str = f"{progress_to_target:.1f}%"
    else:
        progress_str = str(progress_to_target)
    
    # Additional context
    notes = []
    if last_price and entry:
        pnl_pct = ((last_price - entry) / entry) * 100
        notes.append(f"P&L: {pnl_pct:+.2f}%")
    
    if last_price and stop:
        if last_price < stop:
            notes.append("⚠️ BELOW STOP")
        elif last_price < stop * 1.02:
            notes.append("⚠️ Near stop")
    
    notes_str = " | ".join(notes) if notes else "Monitoring"
    
    return f"""Live Trade Update:
Symbol: {symbol}
Entry: ${entry:.2f}
Stop: ${stop:.2f}
Target: ${target:.2f}
Last Price: ${last_price:.2f}
Unrealized R: {unrealized_r:.2f}R
Distance from Stop: {distance_str}
Progress to Target: {progress_str}
Notes: {notes_str}"""


def build_trade_review_for_gpt(data: Dict[str, Any]) -> str:
    """
    Format a closed trade review for GPT coaching.
    
    Args:
        data: Closed trade dictionary with exit info, result, notes, etc.
    
    Returns:
        Formatted text ready to paste into your custom GPT
    """
    symbol = data.get("symbol", "").upper()
    entry = data.get("entry", 0)
    exit_price = data.get("exit_price", 0)
    stop = data.get("stop", 0)
    target = data.get("target", 0)
    shares = data.get("shares", 0)
    exit_reason = data.get("exit_reason", "")
    
    # Calculate result in R
    risk_r = abs(entry - stop) if entry and stop else 1
    pnl_dollars = (exit_price - entry) * shares if exit_price and entry and shares else 0
    result_r = round(pnl_dollars / (risk_r * shares), 2) if risk_r > 0 and shares > 0 else 0
    
    # Determine if plan was followed
    followed_plan = "Yes"
    if exit_reason and "stop" in exit_reason.lower():
        followed_plan = "Yes - Hit stop loss"
    elif exit_reason and "target" in exit_reason.lower():
        followed_plan = "Yes - Hit target"
    elif exit_reason and ("manual" in exit_reason.lower() or "early" in exit_reason.lower()):
        followed_plan = "Partial - Exited early"
    
    return f"""Trade Review:
Symbol: {symbol}
Entry: ${entry:.2f}
Exit: ${exit_price:.2f}
Stop: ${stop:.2f}
Target: ${target:.2f}
Result (R): {result_r:+.2f}R
Result ($): ${pnl_dollars:+,.2f}
Exit Reason: {exit_reason or "Not specified"}
Followed Plan?: {followed_plan}
Mistakes Made: [Add your notes here]
What I Did Well: [Add your notes here]
What to Improve: [Add your notes here]
Emotional Notes: [Add your notes here]"""


def build_coaching_request_for_gpt(data: Dict[str, Any], intraday_signals: Optional[Dict[str, Any]] = None) -> str:
    """
    Format a coaching request with live trade data + intraday signals.
    
    Args:
        data: Trade dictionary with current state
        intraday_signals: Optional dict with RSI, EMA, volume data
    
    Returns:
        Formatted text ready to paste into your custom GPT
    """
    symbol = data.get("symbol", "").upper()
    entry = data.get("entry", 0)
    stop = data.get("stop", 0)
    target = data.get("target", 0)
    last_price = data.get("last_price", 0)
    unrealized_r = data.get("unrealized_r", 0)
    
    # Build signal summary
    signal_lines = []
    if intraday_signals:
        rsi = intraday_signals.get("rsi")
        ema_trend = intraday_signals.get("ema_fast_above_slow")
        vol_ratio = intraday_signals.get("vol_ratio")
        
        if rsi is not None:
            signal_lines.append(f"RSI: {rsi:.1f}")
        if ema_trend is not None:
            signal_lines.append(f"EMA Trend: {'Bullish' if ema_trend else 'Bearish'}")
        if vol_ratio is not None:
            signal_lines.append(f"Volume: {vol_ratio:.2f}x avg")
    
    signals_str = " | ".join(signal_lines) if signal_lines else "No intraday data"
    
    return f"""Coaching Request:
Symbol: {symbol}
Entry: ${entry:.2f}
Stop: ${stop:.2f}
Target: ${target:.2f}
Current Price: ${last_price:.2f}
Unrealized R: {unrealized_r:.2f}R
Intraday Signals: {signals_str}

What should I be watching for? Any adjustments to my plan?"""

