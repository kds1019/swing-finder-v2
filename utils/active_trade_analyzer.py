"""
Claude AI Active Trade Analyzer
Analyzes active trades with real-time data and provides actionable recommendations
"""

import anthropic
from typing import List, Dict
from utils.tiingo_api import fetch_tiingo_realtime_quote, tiingo_history, fetch_tiingo_intraday
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
        # Active trades uses 'opened' field, not 'entry_date'
        entry_date = trade.get('opened') or trade.get('entry_date', 'Unknown')

        # DEBUG: Log what we have
        logger.info(f"Fetching data for {symbol}: entry={entry}, stop={stop}, target={target}, shares={shares}, date={entry_date}")

        # Validate required fields
        if not symbol:
            logger.error("No symbol provided")
            return None
        if entry == 0:
            logger.error(f"{symbol}: No entry price (entry=0)")
            return None
        if stop == 0:
            logger.error(f"{symbol}: No stop loss (stop=0)")
            return None
        if target == 0:
            logger.error(f"{symbol}: No target (target=0)")
            return None
        
        # Get real-time quote
        logger.info(f"{symbol}: Fetching real-time quote from Tiingo...")
        quote = fetch_tiingo_realtime_quote(symbol, token)
        if not quote:
            logger.error(f"{symbol}: fetch_tiingo_realtime_quote returned None or empty - Trying historical data instead...")
            # Fallback to historical data if real-time fails
            df_fallback = tiingo_history(symbol, token, days=5)
            if df_fallback is None or df_fallback.empty:
                logger.error(f"{symbol}: Both real-time and historical data failed")
                return None
            current_price = float(df_fallback.iloc[-1]['Close'])
            logger.info(f"{symbol}: Got current price ${current_price} from historical data (fallback)")
        else:
            current_price = quote.get('last') or quote.get('tngoLast', 0)
            if current_price == 0:
                logger.error(f"{symbol}: Current price is 0 from quote: {quote}")
                return None
            logger.info(f"{symbol}: Got current price ${current_price}")

        # Get intraday data (today's price action) - OPTIONAL
        logger.info(f"{symbol}: Fetching intraday data from Tiingo...")
        intraday_df = fetch_tiingo_intraday(symbol, token)

        # Calculate today's metrics from intraday (if available)
        if intraday_df is not None and not intraday_df.empty:
            try:
                today_open = intraday_df['open'].iloc[0]
                today_high = intraday_df['high'].max()
                today_low = intraday_df['low'].min()
                intraday_change_pct = ((current_price - today_open) / today_open * 100) if today_open > 0 else 0
                logger.info(f"{symbol}: Got intraday data - Open: ${today_open}, High: ${today_high}, Low: ${today_low}")
            except:
                # Intraday might have wrong columns, use fallback
                today_open = current_price
                today_high = current_price
                today_low = current_price
                intraday_change_pct = 0
                logger.warning(f"{symbol}: Intraday data malformed, using fallback")
        else:
            # No intraday data - use current price as fallback
            today_open = current_price
            today_high = current_price
            today_low = current_price
            intraday_change_pct = 0
            logger.warning(f"{symbol}: No intraday data available (might require premium Tiingo plan), using current price as fallback")

        # Get historical data (last 20 days for context)
        logger.info(f"{symbol}: Fetching historical data (20 days) from Tiingo...")
        df = tiingo_history(symbol, token, days=20)

        if df is None or df.empty:
            logger.error(f"{symbol}: tiingo_history returned None or empty DataFrame")
            logger.error(f"{symbol}: This usually means Tiingo API failed or symbol doesn't exist")
            return None
        logger.info(f"{symbol}: Got {len(df)} days of historical data")
        
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
            "trend": trend,
            "today_open": round(today_open, 2),
            "today_high": round(today_high, 2),
            "today_low": round(today_low, 2),
            "intraday_change_pct": round(intraday_change_pct, 2)
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

TODAY'S INTRADAY ACTION (REAL-TIME):
- Open: ${trade['today_open']:.2f}
- Current: ${trade['current_price']:.2f} (LIVE from Tiingo)
- Today's High: ${trade['today_high']:.2f}
- Today's Low: ${trade['today_low']:.2f}
- Intraday Change: {trade['intraday_change_pct']:+.1f}%

POSITION STATUS:
- P&L: ${trade['pnl_per_share']} per share ({trade['pnl_percent']:+.1f}%)
- Total P&L: ${trade['pnl_total']:+,.2f}
- Distance to Stop: {trade['distance_to_stop_pct']:.1f}% away
- Distance to Target: {trade['distance_to_target_pct']:.1f}% away

TECHNICAL ANALYSIS (EOD + INTRADAY):
- RSI (14): {trade['rsi']:.1f}
- Volume: {trade['volume_ratio']:.1f}x average
- EMA20: ${trade['ema20']:.2f}
- EMA50: ${trade['ema50']:.2f if trade['ema50'] else 'N/A'}
- Trend: {trade['trend']}
- 20-Day High: ${trade['recent_high_20d']:.2f} (resistance)
- 20-Day Low: ${trade['recent_low_20d']:.2f} (support)
- Last 5 daily closes: {trade['recent_closes']}

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
