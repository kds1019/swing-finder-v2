"""
Claude AI Active Trade Analyzer
Analyzes active trades with real-time data and provides actionable recommendations
"""

import anthropic
from typing import List, Dict
from utils.tiingo_api import tiingo_history
from utils.claude_analyzer import get_stock_news, get_market_context
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
        
        # Fetch 252 days for 52W/6M context; short-term indicators still use tail()
        df = tiingo_history(symbol, token, days=252)

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

        # Calculate RSI (14-period) on full history for accuracy
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not rsi.empty else 50

        # Volume analysis (20-day average)
        current_volume = df.iloc[-1]['Volume']
        avg_volume = df['Volume'].tail(20).mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Recent price action
        recent_closes = df['Close'].tail(5).tolist()

        # EMAs for trend context
        ema20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1] if len(df) >= 50 else None

        # Recent 20-day highs/lows
        recent_high = df['High'].tail(20).max()
        recent_low = df['Low'].tail(20).min()

        # Trend direction
        if ema50:
            trend = "Uptrend" if ema20 > ema50 else "Downtrend"
        else:
            trend = "Uptrend" if df['Close'].iloc[-1] > df['Close'].iloc[0] else "Downtrend"

        # --- 52-Week & 6-Month Trend Context ---
        high_52w = round(df['High'].tail(252).max(), 2)
        low_52w  = round(df['Low'].tail(252).min(), 2)
        pct_below_52w_high = round((high_52w - current_price) / high_52w * 100, 1) if high_52w else 0
        pct_above_52w_low  = round((current_price - low_52w) / low_52w * 100, 1) if low_52w else 0

        price_6m_ago = round(float(df['Close'].iloc[-126]), 2) if len(df) >= 126 else round(float(df['Close'].iloc[0]), 2)
        trend_6m_pct = round((current_price - price_6m_ago) / price_6m_ago * 100, 1) if price_6m_ago else 0
        trend_6m_dir = "UP" if trend_6m_pct > 3 else "DOWN" if trend_6m_pct < -3 else "FLAT"

        # Days in trade
        from datetime import datetime
        try:
            entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
            days_in_trade = (datetime.now() - entry_dt).days
        except Exception:
            days_in_trade = 0

        # Recent news: Tiingo first, yfinance fallback
        news_headlines = get_stock_news(symbol, days=7, token=token)

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
            # 52W / 6M trend context
            "high_52w": high_52w,
            "low_52w": low_52w,
            "pct_below_52w_high": pct_below_52w_high,
            "pct_above_52w_low": pct_above_52w_low,
            "price_6m_ago": price_6m_ago,
            "trend_6m_pct": trend_6m_pct,
            "trend_6m_dir": trend_6m_dir,
            "news_headlines": news_headlines,
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
        
        # Fetch live market context (SPY + VIX)
        mkt = get_market_context()

        # Build system prompt with caching
        system_prompt = (
            "You are an expert swing trading analyst specializing in active trade management. "
            "Base your analysis ONLY on the live data and news provided — NOT your training data. "
            "Treat all prices, P&L, indicators, headlines, and market context as current real-time information.\n\n"
            "Your role is to analyze ongoing trades and provide clear, actionable recommendations on:\n"
            "- Whether to HOLD, EXIT, or take PARTIAL PROFITS\n"
            "- Stop loss adjustment (trail up, keep, or tighten)\n"
            "- Target adjustment (realistic vs too optimistic given 52W position and news)\n"
            "- News impact: does recent news change the thesis?\n"
            "- Key risks: earnings, technical breakdown, market conditions\n"
            "- Specific action steps with exact price levels\n\n"
            "Be direct and specific. Traders need clear decisions, not vague analysis."
        )

        # --- Market context block ---
        mkt_section = ""
        if mkt:
            mkt_section = (
                f"=== LIVE MARKET CONTEXT (as of today) ===\n"
                f"SPY: ${mkt['spy_price']} | Day: {mkt['spy_day_change']:+.1f}% | 5-Day: {mkt['spy_5d_change']:+.1f}%\n"
                f"Market Trend: {mkt['market_trend']}\n"
                f"VIX: {mkt['vix']} → {mkt['fear_level']}\n\n"
            )

        # --- Per-trade blocks ---
        trades_block = ""
        for i, trade in enumerate(trades_data, 1):
            news = trade.get("news_headlines", [])
            news_section = ""
            if news:
                news_section = "RECENT NEWS (last 7 days — use this, not training data):\n"
                for h in news[:5]:
                    news_section += f"  • {h}\n"
            else:
                news_section = "RECENT NEWS: None found in last 7 days\n"

            trend_arrow = "↑" if trade['trend_6m_dir'] == "UP" else "↓" if trade['trend_6m_dir'] == "DOWN" else "→"
            pnl_sign = "+" if trade['pnl_total'] >= 0 else ""

            trades_block += (
                f"{'═'*52}\n"
                f"{i}. {trade['symbol']} — ACTIVE TRADE (Day {trade['days_in_trade']})\n"
                f"{'═'*52}\n\n"
                f"TRADE DETAILS:\n"
                f"  Entered: {trade['entry_date']} at ${trade['entry_price']:.2f} ({trade['shares']} shares)\n"
                f"  Current: ${trade['current_price']:.2f} | Stop: ${trade['stop_loss']:.2f} | Target: ${trade['target']:.2f}\n\n"
                f"P&L:\n"
                f"  Per Share: ${trade['pnl_per_share']:+.2f} ({trade['pnl_percent']:+.1f}%)\n"
                f"  Total: {pnl_sign}${abs(trade['pnl_total']):,.2f}\n\n"
                f"RISK METRICS:\n"
                f"  Distance to Stop: {trade['distance_to_stop_pct']:.1f}% | Distance to Target: {trade['distance_to_target_pct']:.1f}%\n\n"
                f"TECHNICAL:\n"
                f"  RSI: {trade['rsi']:.1f} | Volume: {trade['volume_ratio']:.1f}x avg | Trend: {trade['trend']}\n"
                f"  EMA20: ${trade['ema20']:.2f}"
                + (f" | EMA50: ${trade['ema50']:.2f}" if trade['ema50'] else "") + "\n"
                f"  Recent 20D Range: ${trade['recent_low_20d']:.2f} – ${trade['recent_high_20d']:.2f}\n"
                f"  Last 5 Closes: {trade['recent_closes']}\n\n"
                f"52-WEEK TREND CONTEXT:\n"
                f"  52W High: ${trade['high_52w']} | 52W Low: ${trade['low_52w']}\n"
                f"  {trade['pct_below_52w_high']:.1f}% below 52W high | {trade['pct_above_52w_low']:.1f}% above 52W low\n"
                f"  6-Month Trend: {trend_arrow} {trade['trend_6m_pct']:+.1f}% (was ${trade['price_6m_ago']} 6 months ago)\n\n"
                f"{news_section}\n"
            )

        user_prompt = (
            f"Analyze these {len(trades_data)} ACTIVE TRADES and tell me what to do with each.\n\n"
            f"{mkt_section}"
            f"{trades_block}"
            "For EACH trade, provide:\n\n"
            "1. **RECOMMENDATION** — Hold / Exit / Take Partial Profits (be decisive)\n"
            "2. **STOP LOSS MANAGEMENT** — Keep, trail up, or tighten? Give exact price level.\n"
            "3. **TARGET ASSESSMENT** — Is target still realistic given 52W position and news? Adjust if needed.\n"
            "4. **NEWS IMPACT** — Does recent news change the thesis or create a new risk?\n"
            "5. **KEY RISKS** — Technical levels, upcoming events, market conditions to watch.\n"
            "6. **ACTION PLAN** — Step-by-step with exact prices.\n"
            "   Example: 'Hold. Trail stop to $23.50 (breakeven). Take 50% at $26, let rest run to $28.'\n\n"
            "Use the LIVE data and news above — not your training data. Be specific with price levels."
        )
        
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
