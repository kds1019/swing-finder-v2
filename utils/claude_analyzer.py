"""
Claude AI Watchlist Analyzer
Uses Claude API to analyze watchlist and recommend top 3-5 stocks to trade
"""

import os
from typing import List, Dict, Any
import anthropic
import streamlit as st

from utils.tiingo_api import fetch_tiingo_realtime_quote, tiingo_history
from utils.logger import get_logger

logger = get_logger(__name__)


def get_stock_data_for_claude(symbol: str, stock_info: Dict, token: str) -> Dict[str, Any]:
    """
    Fetch comprehensive real-time data for a stock to send to Claude.
    
    Args:
        symbol: Stock ticker
        stock_info: Enhanced watchlist entry with entry/stop/target
        token: Tiingo API token
    
    Returns:
        Dictionary with all relevant stock data
    """
    try:
        # Get real-time quote
        quote = fetch_tiingo_realtime_quote(symbol, token)
        current_price = quote.get('last') or quote.get('tngoLast', 0)
        
        # Get historical data (last 20 days)
        df = tiingo_history(symbol, token, days=20)
        
        if df is None or df.empty:
            return None
        
        # Calculate metrics
        prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
        gap_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
        
        # Volume analysis
        current_volume = quote.get('volume', 0)
        avg_volume = df['Volume'].mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Calculate RSI (simple 14-period)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not rsi.empty else 50
        
        # Recent price action (last 5 days)
        recent_closes = df['Close'].tail(5).tolist()
        
        # Calculate risk/reward
        entry = stock_info.get('entry', current_price)
        stop = stock_info.get('stop', 0)
        target = stock_info.get('target', 0)
        
        risk = abs(entry - stop) if stop > 0 else 0
        reward = abs(target - entry) if target > 0 else 0
        rr_ratio = reward / risk if risk > 0 else 0
        
        return {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "gap_percent": round(gap_pct, 2),
            "volume_ratio": round(volume_ratio, 2),
            "rsi": round(current_rsi, 1),
            "setup_type": stock_info.get('setup_type', 'N/A'),
            "entry": entry,
            "stop": stop,
            "target": target,
            "rr_ratio": round(rr_ratio, 2),
            "recent_closes": [round(c, 2) for c in recent_closes],
            "notes": stock_info.get('notes', '')
        }
    
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None


def analyze_watchlist_with_claude(watchlist: List[Dict], token: str, api_key: str) -> str:
    """
    Send watchlist data to Claude for analysis and get top 3-5 recommendations.
    
    Args:
        watchlist: Enhanced watchlist with entry/stop/target
        token: Tiingo API token
        api_key: Anthropic API key
    
    Returns:
        Claude's analysis as formatted text
    """
    try:
        # Fetch real-time data for all stocks
        stocks_data = []
        for stock in watchlist[:20]:  # Limit to 20 stocks to avoid token limits
            symbol = stock.get('symbol')
            if not symbol:
                continue
            
            data = get_stock_data_for_claude(symbol, stock, token)
            if data:
                stocks_data.append(data)
        
        if not stocks_data:
            return "❌ No stock data available to analyze."
        
        # Build prompt for Claude
        prompt = f"""You are an expert swing trading analyst. I need you to analyze my watchlist and recommend the TOP 3-5 stocks to trade TODAY.

Here is my watchlist with current market data:

"""
        
        for i, stock in enumerate(stocks_data, 1):
            prompt += f"""
{i}. {stock['symbol']} - ${stock['current_price']}
   Setup Type: {stock['setup_type']}
   Entry: ${stock['entry']:.2f} | Stop: ${stock['stop']:.2f} | Target: ${stock['target']:.2f}
   Risk:Reward: {stock['rr_ratio']:.2f}:1
   Gap: {stock['gap_percent']:+.1f}%
   Volume: {stock['volume_ratio']:.1f}x average
   RSI: {stock['rsi']:.1f}
   Last 5 closes: {stock['recent_closes']}
   Notes: {stock['notes']}
"""
        
        prompt += """

Please analyze these stocks and provide:

1. **Your Top 3-5 Picks** (ranked from best to worst)
2. **For each pick, explain:**
   - Why you chose it (setup quality, R:R, volume, momentum)
   - Entry confirmation or wait signal
   - Any risks or concerns
   - Position sizing suggestion (full size, half size, small size)

3. **Stocks to AVOID** from this list and why

Be concise but thorough. Focus on actionable insights for swing trading (1-2 week holds).
"""
        
        # Call Claude API
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract response
        response_text = message.content[0].text
        
        return response_text
    
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return f"❌ Error analyzing watchlist: {str(e)}"

