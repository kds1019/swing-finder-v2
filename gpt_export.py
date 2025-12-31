"""
GPT Export Module for SwingFinder
Formats trade data for your custom ChatGPT coaching assistant.
"""

from typing import Dict, Any, Optional


def build_trade_plan_for_gpt(data: Dict[str, Any]) -> str:
    """
    Format a new trade plan for GPT coaching with comprehensive analysis.

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

    # Get additional technical data if available
    current_price = data.get("current_price", entry)

    # Format RSI safely
    rsi_raw = data.get("rsi", "N/A")
    if isinstance(rsi_raw, (int, float)):
        rsi = f"{rsi_raw:.1f}"
    else:
        rsi = str(rsi_raw)

    # Format EMAs safely
    ema20_raw = data.get("ema20", "N/A")
    if isinstance(ema20_raw, (int, float)):
        ema20 = f"{ema20_raw:.2f}"
    else:
        ema20 = str(ema20_raw)

    ema50_raw = data.get("ema50", "N/A")
    if isinstance(ema50_raw, (int, float)):
        ema50 = f"{ema50_raw:.2f}"
    else:
        ema50 = str(ema50_raw)

    # Format volume safely
    volume_raw = data.get("volume", "N/A")
    if isinstance(volume_raw, (int, float)):
        volume = f"{int(volume_raw):,}"
    else:
        volume = str(volume_raw)

    rel_volume = data.get("rel_volume", "N/A")
    if isinstance(rel_volume, (int, float)):
        rel_volume = f"{rel_volume:.2f}x"

    # Fibonacci data
    fib_position = data.get("fib_position", "N/A")
    if isinstance(fib_position, (int, float)):
        fib_position = f"{fib_position:.1f}"

    fib_zone = data.get("fib_zone", "N/A")

    # Support/Resistance
    support = data.get("support", "N/A")
    resistance = data.get("resistance", "N/A")

    # Patterns
    patterns = data.get("patterns", "None detected")

    # Fundamentals
    fund_score = data.get("fundamental_score", "N/A")

    # Earnings
    earnings_date = data.get("earnings_date", "N/A")

    return f"""═══════════════════════════════════════════════════════════════════
📊 NEW TRADE PLAN: {symbol}
═══════════════════════════════════════════════════════════════════

**TRADE PARAMETERS:**
Entry: ${entry:.2f}
Stop Loss: ${stop:.2f}
Target: ${target:.2f}
Position Size: {shares} shares
Setup Type: {setup}
Timeframe: {timeframe}
Risk per Share: ${risk_r:.2f}
Reward per Share: ${reward_r:.2f}
Risk/Reward Ratio: {rr_ratio}:1

**CURRENT TECHNICAL INDICATORS:**
Current Price: ${current_price:.2f}
RSI(14): {rsi}
EMA20: ${ema20} | EMA50: ${ema50}
Trend: {"UPTREND ✅" if isinstance(ema20_raw, (int, float)) and isinstance(ema50_raw, (int, float)) and ema20_raw > ema50_raw else "Check trend"}
Volume: {volume} | Relative Volume: {rel_volume}

**FIBONACCI ANALYSIS:**
Current Position: {fib_position}%
Zone: {fib_zone.upper() if isinstance(fib_zone, str) else fib_zone}

**SUPPORT & RESISTANCE:**
Support: ${support}
Resistance: ${resistance}

**CHART PATTERNS:**
{patterns}

**FUNDAMENTAL SCORE:** {fund_score}/100

**UPCOMING CATALYSTS:**
Next Earnings: {earnings_date}

**TRADER'S NOTES:**
{notes or "None provided"}

═══════════════════════════════════════════════════════════════════
🎯 COACHING REQUEST
═══════════════════════════════════════════════════════════════════

Please analyze this trade plan and provide coaching on:

1. **ENTRY QUALITY:**
   - Is this a high-probability setup based on the technical data?
   - Are there any red flags I should be aware of?
   - Should I wait for additional confirmation?

2. **RISK MANAGEMENT:**
   - Is my stop placement optimal given the support levels?
   - Is my position size appropriate?
   - What's the probability of hitting my stop vs target?

3. **EXECUTION PLAN:**
   - What specific price action should I wait for before entering?
   - What would invalidate this setup before entry?
   - Any suggestions for improving entry/exit levels?"""


def build_live_update_for_gpt(data: Dict[str, Any]) -> str:
    """
    Format a live trade update for GPT coaching with exit guidance.

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
    shares = data.get("shares", 0)

    # Format distance and progress
    if isinstance(distance_from_stop, (int, float)):
        distance_str = f"{distance_from_stop:.1f}%"
    else:
        distance_str = str(distance_from_stop)

    if isinstance(progress_to_target, (int, float)):
        progress_str = f"{progress_to_target:.1f}%"
    else:
        progress_str = str(progress_to_target)

    # Calculate P&L
    pnl_dollars = 0
    pnl_pct = 0
    if last_price and entry and shares:
        pnl_dollars = (last_price - entry) * shares
        pnl_pct = ((last_price - entry) / entry) * 100

    # Determine status
    status_notes = []
    if last_price and stop:
        if last_price < stop:
            status_notes.append("🚨 BELOW STOP - IMMEDIATE ACTION NEEDED")
        elif last_price < stop * 1.02:
            status_notes.append("⚠️ Near stop - High risk")
        elif unrealized_r >= 1.0:
            status_notes.append("✅ Above 1R - Consider trailing stop")
        elif unrealized_r >= 0.5:
            status_notes.append("📈 Positive momentum")
        else:
            status_notes.append("⏸️ Developing")

    status_str = " | ".join(status_notes) if status_notes else "Monitoring"

    # Get intraday data if available
    intraday_rsi = data.get("intraday_rsi", "N/A")
    intraday_trend = data.get("intraday_trend", "N/A")
    intraday_volume = data.get("intraday_volume", "N/A")

    return f"""═══════════════════════════════════════════════════════════════════
📊 ACTIVE TRADE UPDATE: {symbol}
═══════════════════════════════════════════════════════════════════

**TRADE STATUS:**
Entry Price: ${entry:.2f}
Current Price: ${last_price:.2f}
Stop Loss: ${stop:.2f}
Target: ${target:.2f}
Position Size: {shares} shares

**PERFORMANCE:**
Unrealized R: {unrealized_r:+.2f}R
Unrealized P&L: ${pnl_dollars:+,.2f} ({pnl_pct:+.2f}%)
Distance from Stop: {distance_str}
Progress to Target: {progress_str}

**CURRENT STATUS:**
{status_str}

**INTRADAY SIGNALS:**
RSI: {intraday_rsi}
Trend: {intraday_trend}
Volume: {intraday_volume}

═══════════════════════════════════════════════════════════════════
🎯 COACHING REQUEST
═══════════════════════════════════════════════════════════════════

Please provide guidance on:

1. **CURRENT POSITION:**
   - How is this trade developing?
   - Are there any warning signs I should watch for?
   - Is the price action confirming or contradicting my thesis?

2. **EXIT STRATEGY:**
   - Should I take partial profits here? If so, how much?
   - Where should I move my stop to protect gains?
   - What price action would signal it's time to exit?

3. **RISK MANAGEMENT:**
   - Am I managing this trade correctly?
   - Any adjustments needed to my plan?
   - What are the key levels to watch from here?"""


def build_trade_review_for_gpt(data: Dict[str, Any]) -> str:
    """
    Format a closed trade review for GPT coaching with deep analysis prompts.

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
    setup_type = data.get("setup_type", "Unknown")
    entry_date = data.get("entry_date", "N/A")
    exit_date = data.get("exit_date", "N/A")

    # Calculate result in R
    risk_r = abs(entry - stop) if entry and stop else 1
    pnl_dollars = (exit_price - entry) * shares if exit_price and entry and shares else 0
    pnl_pct = ((exit_price - entry) / entry) * 100 if entry else 0
    result_r = round(pnl_dollars / (risk_r * shares), 2) if risk_r > 0 and shares > 0 else 0

    # Determine if plan was followed
    followed_plan = "Yes"
    plan_notes = ""
    if exit_reason and "stop" in exit_reason.lower():
        followed_plan = "Yes - Hit stop loss"
        plan_notes = "Stopped out as planned"
    elif exit_reason and "target" in exit_reason.lower():
        followed_plan = "Yes - Hit target"
        plan_notes = "Target reached as planned"
    elif exit_reason and ("manual" in exit_reason.lower() or "early" in exit_reason.lower()):
        followed_plan = "Partial - Exited early"
        plan_notes = "Deviated from original plan"
    elif exit_reason and "time" in exit_reason.lower():
        followed_plan = "Yes - Time stop"
        plan_notes = "Exited due to lack of progress"

    # Determine outcome category
    if result_r >= 2.0:
        outcome = "🎯 BIG WIN"
    elif result_r >= 1.0:
        outcome = "✅ WIN"
    elif result_r >= 0:
        outcome = "📊 SMALL WIN"
    elif result_r >= -0.5:
        outcome = "📉 SMALL LOSS"
    else:
        outcome = "❌ LOSS"

    return f"""═══════════════════════════════════════════════════════════════════
📝 TRADE REVIEW: {symbol} - {outcome}
═══════════════════════════════════════════════════════════════════

**TRADE SUMMARY:**
Symbol: {symbol}
Setup Type: {setup_type}
Entry Date: {entry_date}
Exit Date: {exit_date}

**EXECUTION:**
Entry Price: ${entry:.2f}
Exit Price: ${exit_price:.2f}
Stop Loss: ${stop:.2f}
Target: ${target:.2f}
Position Size: {shares} shares

**RESULTS:**
Result (R): {result_r:+.2f}R
Result ($): ${pnl_dollars:+,.2f}
Result (%): {pnl_pct:+.2f}%
Exit Reason: {exit_reason or "Not specified"}
Followed Plan?: {followed_plan}
Notes: {plan_notes}

═══════════════════════════════════════════════════════════════════
📊 SELF-REFLECTION (Fill this out before asking GPT)
═══════════════════════════════════════════════════════════════════

**ENTRY ANALYSIS:**
1. Was my entry timing good? (1-10): ___
2. Did I wait for proper confirmation?: ___
3. Was the setup as strong as I thought?: ___

**TRADE MANAGEMENT:**
4. Did I follow my stop loss rule?: ___
5. Did I manage emotions well?: ___
6. Did I exit at the right time?: ___

**MISTAKES MADE:**
[Write what you did wrong - be honest]


**WHAT I DID WELL:**
[Write what you did right - acknowledge wins]


**EMOTIONAL STATE:**
Entry emotion (fear/greed/calm): ___
During trade (anxious/confident/neutral): ___
Exit emotion (relief/regret/satisfied): ___

**PATTERN RECOGNITION:**
Have I made this same mistake before?: ___
Is this a recurring issue?: ___

═══════════════════════════════════════════════════════════════════
🎯 COACHING REQUEST
═══════════════════════════════════════════════════════════════════

Based on this trade review, please help me:

1. **IDENTIFY MISTAKES:**
   - What did I do wrong in this trade?
   - Were there early warning signs I missed?
   - How could I have improved my execution?

2. **RECOGNIZE PATTERNS:**
   - Do you see any recurring mistakes in my trading?
   - What patterns should I watch for in future trades?
   - Am I making the same errors repeatedly?

3. **ACTIONABLE IMPROVEMENTS:**
   - What specific rule should I add to prevent this mistake?
   - What should I do differently next time?
   - How can I improve my discipline?

4. **EMOTIONAL MANAGEMENT:**
   - Did emotions affect my decision-making?
   - How can I better manage fear/greed in similar situations?
   - What mental checklist should I use before exiting?"""


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

