"""
Claude AI Active Trade Analyzer
Analyzes active trades with real-time data and provides actionable recommendations
"""

import anthropic
from typing import List, Dict
from utils.tiingo_api import fetch_tiingo_realtime_quote, tiingo_history
from utils.logger import get_logger

logger = get_logger(__name__)


def get_active_trade_data(trade: Dict, token: str) -> Dict:
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
        entry_date = trade.get('entry_date', 'Unknown')
        
        # Get real-time quote
        quote = fetch_tiingo_realtime_quote(symbol, token)
        current_price = quote.get('last') or quote.get('tngoLast', 0)
        
        # Get historical data (last 20 days)
        df = tiingo_history(symbol, token, days=20)
        
        if df is None or df.empty:
            return None
        
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
        current_volume = quote.get('volume', 0)
        avg_volume = df['Volume'].mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Recent price action
        recent_closes = df['Close'].tail(5).tolist()
        
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
            "entry_date": entry_date
        }
    
    except Exception as e:
        logger.error(f"Error fetching trade data for {trade.get('symbol')}: {e}")
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
        for trade in selected_trades:
            data = get_active_trade_data(trade, token)
            if data:
                trades_data.append(data)
        
        if not trades_data:
            return "❌ No trade data available to analyze."
        
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

CURRENT STATUS:
- Current Price: ${trade['current_price']}
- P&L: ${trade['pnl_per_share']} per share ({trade['pnl_percent']:+.1f}%)
- Total P&L: ${trade['pnl_total']:+,.2f}
- Distance to Stop: {trade['distance_to_stop_pct']:.1f}% away
- Distance to Target: {trade['distance_to_target_pct']:.1f}% away

TECHNICAL:
- RSI: {trade['rsi']:.1f}
- Volume: {trade['volume_ratio']:.1f}x average
- Last 5 closes: {trade['recent_closes']}

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
        logger.error(f"Claude API error: {e}")
        return f"❌ Error analyzing trades: {str(e)}"
