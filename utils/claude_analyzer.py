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


def quick_analyze_watchlist(watchlist: List[Dict], token: str, api_key: str) -> str:
    """
    Quick analysis of entire watchlist using Haiku (fast & cheap).
    Returns top 3-5 picks with brief reasoning.

    Args:
        watchlist: Enhanced watchlist with entry/stop/target
        token: Tiingo API token
        api_key: Anthropic API key

    Returns:
        Claude's quick analysis (Haiku)
    """
    try:
        # Fetch real-time data for all stocks
        stocks_data = []
        for stock in watchlist[:20]:  # Limit to 20 stocks
            symbol = stock.get('symbol')
            if not symbol:
                continue

            data = get_stock_data_for_claude(symbol, stock, token)
            if data:
                stocks_data.append(data)

        if not stocks_data:
            return "❌ No stock data available to analyze."

        # Build prompt for quick analysis
        prompt = f"""You are a swing trading analyst. Quickly analyze this watchlist and give me the TOP 3-5 stocks to trade TODAY.

WATCHLIST ({len(stocks_data)} stocks):

"""

        for i, stock in enumerate(stocks_data, 1):
            prompt += f"""{i}. {stock['symbol']} ${stock['current_price']} | {stock['setup_type']} | Entry: ${stock['entry']:.2f} Stop: ${stock['stop']:.2f} Target: ${stock['target']:.2f} | R:R: {stock['rr_ratio']:.1f}:1 | Gap: {stock['gap_percent']:+.1f}% | Vol: {stock['volume_ratio']:.1f}x | RSI: {stock['rsi']:.0f}
"""

        prompt += """

Provide:
1. Top 3-5 picks (ranked)
2. Brief reason for each (1-2 sentences)
3. Position size (full/half/small)
4. Stocks to avoid

Be concise. Focus on actionable insights."""

        # Call Claude API with Haiku (fast & cheap)
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Quick analysis with Sonnet (Haiku unavailable in API)
            max_tokens=800,  # Keep it brief for speed
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text
        return response_text

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return f"❌ Error analyzing watchlist: {str(e)}"


def deep_analyze_stocks(selected_stocks: List[Dict], token: str, api_key: str) -> str:
    """
    Deep analysis of selected stocks using Sonnet (detailed & thorough).
    With prompt caching for cost savings on repeated analyses.

    Args:
        selected_stocks: List of selected stocks to analyze in detail
        token: Tiingo API token
        api_key: Anthropic API key

    Returns:
        Claude's deep analysis (Sonnet with caching)
    """
    try:
        # Fetch real-time data for selected stocks only
        stocks_data = []
        for stock in selected_stocks:
            symbol = stock.get('symbol')
            if not symbol:
                continue

            data = get_stock_data_for_claude(symbol, stock, token)
            if data:
                stocks_data.append(data)

        if not stocks_data:
            return "❌ No stock data available to analyze."

        # Build system prompt (this will be cached for cost savings)
        system_prompt = """You are an expert swing trading analyst with deep knowledge of technical analysis, risk management, and market psychology.

Your analysis should include:
- Detailed technical breakdown (support/resistance, indicators, patterns)
- Volume analysis and institutional interest
- Entry timing and price levels
- Risk assessment and position sizing
- Market context and correlation

Be thorough but actionable. Provide specific price levels and clear recommendations."""

        # Build user prompt with stock data
        user_prompt = f"""Please provide a DEEP ANALYSIS of these {len(stocks_data)} stocks from my watchlist:

"""

        for i, stock in enumerate(stocks_data, 1):
            user_prompt += f"""
{'═'*50}
{i}. {stock['symbol']} - ${stock['current_price']}
{'═'*50}

SETUP:
- Type: {stock['setup_type']}
- Entry: ${stock['entry']:.2f}
- Stop: ${stock['stop']:.2f}
- Target: ${stock['target']:.2f}
- Risk:Reward: {stock['rr_ratio']:.2f}:1

CURRENT MARKET DATA:
- Gap: {stock['gap_percent']:+.1f}%
- Volume: {stock['volume_ratio']:.1f}x average volume
- RSI (14): {stock['rsi']:.1f}
- Last 5 closes: {stock['recent_closes']}

TRADER NOTES:
{stock['notes'] if stock['notes'] else 'None'}

"""

        user_prompt += """

For EACH stock, provide:

1. **SETUP ANALYSIS**
   - Technical breakdown (entry quality, stop placement, target logic)
   - Risk:Reward assessment

2. **VOLUME CONVICTION**
   - What volume is telling us (institutional interest, conviction level)

3. **TECHNICAL INDICATORS**
   - RSI interpretation
   - Moving average context
   - Price action analysis

4. **ENTRY TIMING**
   - Enter now, wait, or skip?
   - Specific confirmation levels

5. **POSITION SIZING**
   - Full / Half / Small position
   - Reasoning for size

6. **RISKS TO MONITOR**
   - What could invalidate this setup?
   - Key levels to watch

Be thorough and specific. Focus on actionable trading decisions."""

        # Call Claude API with prompt caching
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}  # Cache system prompt
                }
            ],
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        # Extract response
        response_text = message.content[0].text

        return response_text

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return f"❌ Error analyzing stocks: {str(e)}"

