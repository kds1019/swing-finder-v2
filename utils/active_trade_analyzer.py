"""
Claude AI Active Trade Analyzer
Analyzes active trades with real-time data and provides actionable recommendations
"""

import anthropic
from typing import List, Dict
from utils.tiingo_api import tiingo_history
from utils.logger import get_logger

logger = get_logger(__name__)


def get_active_trade_data(trade: Dict, token: str):
    """
    Fetch comprehensive data for an active trade.

    Args:
        trade: Active trade dictionary with entry/stop/target/shares
        token: Tiingo API token

    Returns:
        Dictionary with all trade analysis data
    """
    try:
        symbol = trade.get('symbol')
        entry = trade.get('entry', 0)
        stop = trade.get('stop', 0)
        target = trade.get('target', 0)
        shares = trade.get('shares', 0)
        # Active trades uses 'opened' field, not 'entry_date'
        entry_date = trade.get('opened') or trade.get('entry_date', 'Unknown')
        
        # Get historical data (last 20 days)
        df = tiingo_history(symbol, token, days=20)

        if df is None or df.empty:
            return None

        # Get current price from latest close
        current_price = float(df.iloc[-1]['Close'])
        
        # Calculate P&L
        pnl_per_share = current_price - entry
        pnl_total = pnl_per_share * shares
        pnl_percent = (pnl_per_share / entry * 100) if entry > 0 else 0
        
        # Distance to stop/target
        distance_to_stop = ((current_price - stop) / current_price * 100) if stop > 0 else 0
        distance_to_target = ((target - current_price) / current_price * 100) if target > 0 else 0
        
        # Calculate RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not rsi.empty else 50
        
        # Volume analysis
        current_volume = df.iloc[-1]['Volume']
        avg_volume = df['Volume'].mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Recent price action
        recent_closes = df['Close'].tail(5).tolist()

        # Calculate EMAs for trend context
        ema20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1] if len(df) >= 50 else None

        # Recent highs/lows (for support/resistance)
        recent_high = df['High'].tail(20).max()
        recent_low = df['Low'].tail(20).min()

        # Trend direction
        if ema50:
            trend = "Uptrend" if ema20 > ema50 else "Downtrend"
        else:
            trend = "Uptrend" if df['Close'].iloc[-1] > df['Close'].iloc[0] else "Downtrend"

        # Days in trade
        from datetime import datetime
        try:
            entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
            days_in_trade = (datetime.now() - entry_dt).days
        except:
            days_in_trade = 0

        return {
            "symbol": symbol,
            "entry_price": round(entry, 2),
            "current_price": round(current_price, 2),
            "stop_loss": round(stop, 2),
            "target": round(target, 2),
            "shares": shares,
            "pnl_per_share": round(pnl_per_share, 2),
            "pnl_total": round(pnl_total, 2),
            "pnl_percent": round(pnl_percent, 2),
            "distance_to_stop_pct": round(distance_to_stop, 2),
            "distance_to_target_pct": round(distance_to_target, 2),
            "rsi": round(current_rsi, 1),
            "volume_ratio": round(volume_ratio, 2),
            "recent_closes": [round(c, 2) for c in recent_closes],
            "days_in_trade": days_in_trade,
            "entry_date": entry_date,
            "ema20": round(ema20, 2),
            "ema50": round(ema50, 2) if ema50 else None,
            "recent_high_20d": round(recent_high, 2),
            "recent_low_20d": round(recent_low, 2),
            "trend": trend
        }
    
    except Exception as e:
        symbol = trade.get('symbol', 'UNKNOWN')
        logger.error(f"Error fetching trade data for {symbol}: {e}")
        logger.error(f"Trade data structure: entry={trade.get('entry')}, stop={trade.get('stop')}, target={trade.get('target')}, shares={trade.get('shares')}")
        return None


def analyze_active_trades(selected_trades: List[Dict], token: str, api_key: str) -> str:
    """
    Analyze selected active trades with Claude AI.
    
    Args:
        selected_trades: List of active trades to analyze
        token: Tiingo API token
        api_key: Anthropic API key
    
    Returns:
        Claude's trade analysis with recommendations
    """
    try:
        # Fetch real-time data for each trade
        trades_data = []
        errors = []
        detailed_errors = []

        for trade in selected_trades:
            symbol = trade.get('symbol', 'UNKNOWN')

            # Try to fetch data and capture specific error
            try:
                data = get_active_trade_data(trade, token)
                if data:
                    trades_data.append(data)
                else:
                    # Data fetch returned None - check why
                    entry = trade.get('entry', 0)
                    stop = trade.get('stop', 0)
                    target = trade.get('target', 0)

                    if entry == 0:
                        detailed_errors.append(f"{symbol}: Entry price is 0 or missing")
                    elif stop == 0:
                        detailed_errors.append(f"{symbol}: Stop loss is 0 or missing")
                    elif target == 0:
                        detailed_errors.append(f"{symbol}: Target is 0 or missing")
                    else:
                        detailed_errors.append(f"{symbol}: Tiingo API failed to fetch data (check if symbol is valid or API is down)")

                    errors.append(f"{symbol}")
            except Exception as e:
                detailed_errors.append(f"{symbol}: Exception - {str(e)}")
                errors.append(f"{symbol}")

        if not trades_data:
            error_details = '\n'.join([f"- {err}" for err in detailed_errors])
            error_msg = f"""❌ No trade data available to analyze.

**Detailed Error Report:**
{error_details}

**Common Solutions:**
- **If "Tiingo API failed"**: Your Tiingo token might be invalid, expired, or rate limited. Check your .env file.
- **If "Entry/Stop/Target is 0"**: Edit your trade and add the missing values.
- **If "Symbol invalid"**: Make sure ticker symbol is spelled correctly (BAC, ALLY, etc.)

**Your Trade Data (from debug):**
Symbol: {', '.join([t.get('symbol', 'N/A') for t in selected_trades])}
Entry: {', '.join([str(t.get('entry', 'N/A')) for t in selected_trades])}
Stop: {', '.join([str(t.get('stop', 'N/A')) for t in selected_trades])}
Target: {', '.join([str(t.get('target', 'N/A')) for t in selected_trades])}"""
            return error_msg
        
        # Build system prompt with caching
        system_prompt = """You are an expert swing trading analyst specializing in active trade management. 

Your role is to analyze ongoing trades and provide clear, actionable recommendations on:
- Whether to HOLD, EXIT, or take PARTIAL PROFITS
- Stop loss adjustment (move up, keep, or tighten)
- Target adjustment (realistic or too optimistic)
- Key risks (earnings, technical breakdown, market conditions)
- Specific action steps with price levels

Be direct and specific. Traders need clear decisions, not vague analysis."""
        
        # Build user prompt
        user_prompt = f"""Analyze these {len(trades_data)} ACTIVE TRADES and tell me what to do with each:

"""
        
        for i, trade in enumerate(trades_data, 1):
            user_prompt += f"""
{'═'*50}
{i}. {trade['symbol']} - ACTIVE TRADE (Day {trade['days_in_trade']})
{'═'*50}

ENTRY:
- Entered: {trade['entry_date']} at ${trade['entry_price']}
- Stop Loss: ${trade['stop_loss']}
- Target: ${trade['target']}
- Position: {trade['shares']} shares

CURRENT STATUS (REAL-TIME FROM TIINGO):
- Current Price: ${trade['current_price']:.2f} (LIVE)

POSITION STATUS:
- P&L: ${trade.get('pnl_per_share', 0):.2f} per share ({trade.get('pnl_percent', 0):+.1f}%)
- Total P&L: ${trade.get('pnl_total', 0):+,.2f}
- Distance to Stop: {trade.get('distance_to_stop_pct', 0):.1f}% away
- Distance to Target: {trade.get('distance_to_target_pct', 0):.1f}% away

TECHNICAL ANALYSIS (EOD + INTRADAY):
- RSI (14): {trade.get('rsi', 0):.1f}
- Volume: {trade.get('volume_ratio', 0):.1f}x average
- EMA20: ${trade.get('ema20', 0):.2f}
- EMA50: ${trade.get('ema50', 0):.2f} (or 'N/A' if {trade.get('ema50', 0)} == 0)
- Trend: {trade.get('trend', 'Unknown')}
- 20-Day High: ${trade.get('recent_high_20d', 0):.2f} (resistance)
- 20-Day Low: ${trade.get('recent_low_20d', 0):.2f} (support)
- Last 5 daily closes: {trade.get('recent_closes', [])}

"""
        
        user_prompt += """

For EACH trade, provide:

1. **RECOMMENDATION** (Hold / Exit / Take Partial Profits)
   - Clear action: what to do NOW

2. **STOP LOSS MANAGEMENT**
   - Keep current stop, move up, or tighten?
   - Specific price level if adjusting

3. **TARGET ASSESSMENT**
   - Is target still realistic?
   - Should I adjust target higher/lower?
   - Specific price level if adjusting

4. **KEY RISKS**
   - What could go wrong?
   - Upcoming earnings/events to watch
   - Technical levels to monitor

5. **ACTION PLAN**
   - Specific steps with price levels
   - Example: "Hold. Move stop to $23.50 (breakeven). Take 50% at $26, let rest run to $28."

Be specific with price levels. I need clear trading decisions."""
        
        # Call Claude API with prompt caching
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        response_text = message.content[0].text
        return response_text
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Claude API error: {e}")
        logger.error(f"Full traceback: {error_trace}")
        return f"❌ Error analyzing trades: {str(e)}\n\n**Error occurred while building Claude prompt or processing response.**\n\nPlease check that all trade data is valid (no None/null values)."
