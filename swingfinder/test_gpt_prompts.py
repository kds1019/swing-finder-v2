"""
Test the new GPT prompts to see the improvements
"""

from gpt_export import build_trade_plan_for_gpt, build_live_update_for_gpt, build_trade_review_for_gpt

print("="*70)
print("🚀 TESTING NEW GPT PROMPTS")
print("="*70)

# Test 1: Entry Analysis / Trade Plan
print("\n\n1️⃣ ENTRY ANALYSIS PROMPT (New Trade Plan)")
print("="*70)

trade_plan_data = {
    "symbol": "AAPL",
    "entry": 175.00,
    "stop": 172.00,
    "target": 180.00,
    "shares": 100,
    "setup_type": "Pullback",
    "timeframe": "Daily",
    "notes": "Bouncing off EMA20 support with bullish divergence",
    "current_price": 175.50,
    "rsi": 48.2,
    "ema20": 175.20,
    "ema50": 172.30,
    "volume": 50000000,
    "rel_volume": 1.35,
    "fib_position": 42.5,
    "fib_zone": "discount",
    "support": "$172.50",
    "resistance": "$177.00",
    "patterns": "Bull Flag, Higher Lows",
    "fundamental_score": "85/100",
    "earnings_date": "2025-01-25"
}

prompt = build_trade_plan_for_gpt(trade_plan_data)
print(prompt)

# Test 2: Active Trade Update
print("\n\n2️⃣ ACTIVE TRADE UPDATE PROMPT")
print("="*70)

active_trade_data = {
    "symbol": "AAPL",
    "entry": 175.00,
    "stop": 172.00,
    "target": 180.00,
    "shares": 100,
    "last_price": 176.50,
    "unrealized_r": 0.50,
    "distance_from_stop": 2.6,
    "progress_to_target": 30.0,
    "intraday_rsi": "55.2",
    "intraday_trend": "Bullish ✅",
    "intraday_volume": "1.2x avg"
}

prompt = build_live_update_for_gpt(active_trade_data)
print(prompt)

# Test 3: Closed Trade Review
print("\n\n3️⃣ CLOSED TRADE REVIEW PROMPT")
print("="*70)

closed_trade_data = {
    "symbol": "AAPL",
    "entry": 175.00,
    "exit_price": 180.00,
    "stop": 172.00,
    "target": 180.00,
    "shares": 100,
    "exit_reason": "Hit target",
    "setup_type": "Pullback",
    "entry_date": "2025-12-10",
    "exit_date": "2025-12-15"
}

prompt = build_trade_review_for_gpt(closed_trade_data)
print(prompt)

print("\n\n" + "="*70)
print("✅ ALL PROMPTS GENERATED SUCCESSFULLY!")
print("="*70)
print("\n💡 These prompts are now available in:")
print("   - Analyzer → 'Copy for GPT' button")
print("   - Active Trades → 'Copy for Custom GPT' expander")
print("   - Closed Trades → Modal popup when closing a trade")

