"""
Claude AI Watchlist Analyzer
Uses Claude API to analyze watchlist and recommend top 3-5 stocks to trade
"""

import os
from typing import List, Dict, Any
import anthropic
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta

from utils.tiingo_api import (
    fetch_tiingo_realtime_quote, tiingo_history,
    get_tiingo_sector, fetch_institutional_ownership, get_next_earnings_date,
)
from utils.fundamentals import get_tiingo_fundamentals_for_claude, format_fundamentals_for_prompt
from utils.indicators import detect_patterns
from utils.logger import get_logger

logger = get_logger(__name__)


def get_stock_news(symbol: str, days: int = 7, token: str = "") -> List[Dict[str, Any]]:
    """
    Fetch recent news articles for a stock with full context for Claude analysis.

    Strategy:
      1. Try Tiingo News API first (higher quality, ticker-specific).
         Falls back silently if the plan doesn't include it (403).
      2. Fall back to Yahoo Finance (yfinance) if Tiingo returns nothing.

    Args:
        symbol: Stock ticker symbol
        days: How many days back to look (default 7)
        token: Tiingo API token (optional — uses TIINGO_TOKEN env/secret if not passed)

    Returns:
        List of up to 5 structured article dicts with keys:
        title, description, category, sentiment, source, time_ago
    """
    import os
    import requests as _requests
    from utils.news_feed import categorize_news, analyze_sentiment, format_news_time

    # --- 1. Try Tiingo News API ---
    try:
        tiingo_token = (
            token
            or st.secrets.get("TIINGO_TOKEN")
            or st.secrets.get("TIINGO_API_KEY")
            or os.getenv("TIINGO_TOKEN")
            or os.getenv("TIINGO_API_KEY")
            or ""
        )
        if tiingo_token:
            cutoff_dt = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            url = "https://api.tiingo.com/tiingo/news"
            params = {
                "tickers": symbol.upper(),
                "startDate": cutoff_dt,
                "limit": 10,
                "sortBy": "publishedDate",
            }
            headers = {"Authorization": f"Token {tiingo_token}"}
            resp = _requests.get(url, params=params, headers=headers, timeout=8)

            if resp.status_code == 200:
                raw_articles = resp.json()
                articles = []
                for a in raw_articles[:5]:
                    title       = a.get("title", "") or ""
                    description = a.get("description", "") or ""
                    source      = a.get("source", "") or ""
                    published   = a.get("publishedDate", "") or ""
                    articles.append({
                        "title":       title,
                        "description": description[:300],
                        "category":    categorize_news(title, description),
                        "sentiment":   analyze_sentiment(title + " " + description),
                        "source":      source,
                        "time_ago":    format_news_time(published) if published else "",
                    })
                if articles:
                    logger.info(f"Tiingo news: {len(articles)} articles for {symbol}")
                    return articles
            elif resp.status_code == 403:
                logger.info(f"Tiingo News API not available on current plan — falling back to yfinance for {symbol}")
            else:
                logger.warning(f"Tiingo news returned {resp.status_code} for {symbol}")
    except Exception as e:
        logger.warning(f"Tiingo news fetch failed for {symbol}: {e}")

    # --- 2. Fallback: Yahoo Finance (yfinance) ---
    try:
        ticker = yf.Ticker(symbol)
        news_items = ticker.news

        if not news_items:
            return []

        cutoff_ts = (datetime.now() - timedelta(days=days)).timestamp()
        articles = []

        for item in news_items:
            pub_time  = item.get("providerPublishTime", 0)
            title     = item.get("title", "") or ""
            publisher = item.get("publisher", "") or ""
            if pub_time >= cutoff_ts and title:
                # Convert unix timestamp to ISO string for format_news_time
                try:
                    pub_iso = datetime.fromtimestamp(pub_time).isoformat()
                    time_ago = format_news_time(pub_iso)
                except Exception:
                    time_ago = ""
                articles.append({
                    "title":       title,
                    "description": "",   # yfinance doesn't provide article descriptions
                    "category":    categorize_news(title, ""),
                    "sentiment":   analyze_sentiment(title),
                    "source":      publisher,
                    "time_ago":    time_ago,
                })
            if len(articles) >= 5:
                break

        if articles:
            logger.info(f"yfinance news: {len(articles)} articles for {symbol}")
        return articles

    except Exception as e:
        logger.warning(f"yfinance news fetch also failed for {symbol}: {e}")
        return []


def _format_news_for_claude(articles: List[Dict[str, Any]], max_articles: int = 3) -> str:
    """
    Format structured news article dicts into a Claude-readable block.

    Each article shows: category | sentiment | source | recency
    followed by the headline and description (if available).

    Example output:
        📊 Earnings | 🟢 Bullish | Reuters | 2 hours ago
        "Apple beats Q3 EPS by 8%"
        → EPS $1.26 vs $1.15 estimate. Services revenue hit record $24B.
    """
    if not articles:
        return "No recent news found"
    lines = []
    for a in articles[:max_articles]:
        sentiment  = a.get("sentiment", {})
        s_emoji    = sentiment.get("emoji", "⚪")
        s_label    = sentiment.get("label", "Neutral")
        category   = a.get("category", "📰 General")
        source     = a.get("source", "")
        time_ago   = a.get("time_ago", "")
        title      = a.get("title", "")
        description = a.get("description", "")

        meta_parts = [category, f"{s_emoji} {s_label}"]
        if source:
            meta_parts.append(source)
        if time_ago:
            meta_parts.append(time_ago)
        meta = " | ".join(meta_parts)

        desc_line = f"\n     → {description[:200]}" if description else ""
        lines.append(f"   {meta}\n   \"{title}\"{desc_line}")
    return "\n".join(lines)


def _get_yf_market_intel(symbol: str, current_price: float = 0) -> str:
    """
    Fetch analyst consensus targets, short interest, and company name from yfinance.
    Returns a formatted text block ready to drop into a Claude prompt.
    Returns empty string on failure so callers can proceed safely.
    """
    try:
        info = yf.Ticker(symbol).info
        if not info:
            return ""

        lines = ["=== ANALYST & MARKET INTEL ==="]

        # Company name
        name = info.get("shortName") or info.get("longName", "")
        if name:
            lines.append(f"Company: {name}")

        # Analyst price targets
        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        target_low  = info.get("targetLowPrice")
        num_analysts = info.get("numberOfAnalystOpinions")
        rec_mean     = info.get("recommendationMean")

        rec_label = "N/A"
        if rec_mean is not None:
            if rec_mean <= 1.5:   rec_label = "Strong Buy"
            elif rec_mean <= 2.5: rec_label = "Buy"
            elif rec_mean <= 3.5: rec_label = "Hold"
            elif rec_mean <= 4.5: rec_label = "Sell"
            else:                 rec_label = "Strong Sell"

        if target_mean:
            upside = (
                round((target_mean - current_price) / current_price * 100, 1)
                if current_price else "N/A"
            )
            range_str = (
                f" (range ${target_low:.2f}–${target_high:.2f})"
                if target_low and target_high else ""
            )
            analysts_str = f" | {num_analysts} analysts" if num_analysts else ""
            upside_str   = f" | {upside:+.1f}% upside" if isinstance(upside, float) else ""
            lines.append(
                f"Analyst Target: ${target_mean:.2f}{range_str}"
                f"{analysts_str} | Consensus: {rec_label}{upside_str}"
            )

        # Short interest
        short_pct   = info.get("shortPercentOfFloat")
        short_ratio = info.get("shortRatio")
        if short_pct is not None:
            short_str = f"Short Interest: {short_pct * 100:.1f}% of float"
            if short_ratio:
                short_str += f" | Days to Cover: {short_ratio:.1f}"
            lines.append(short_str)

        return "\n".join(lines) if len(lines) > 1 else ""
    except Exception:
        return ""


def _get_institutional_pct(symbol: str, token: str) -> str:
    """
    Fetch total institutional ownership percentage from Tiingo.
    Returns a single formatted line or empty string on failure.
    """
    try:
        data = fetch_institutional_ownership(symbol, token)
        if not data:
            return ""
        if isinstance(data, list) and data:
            latest = sorted(data, key=lambda x: x.get("date", ""), reverse=True)[0]
        elif isinstance(data, dict):
            latest = data
        else:
            return ""
        total = latest.get("totalInstitutional") or latest.get("institutionalOwnership")
        if total is not None:
            return f"Institutional Ownership: {float(total):.1f}%"
        return ""
    except Exception:
        return ""


def get_market_context() -> Dict[str, Any]:
    """
    Fetch current market conditions using yfinance (SPY trend + VIX).
    Returns a dict with market trend and fear level to include in Claude prompts.
    """
    try:
        spy = yf.Ticker("SPY")
        spy_hist = spy.history(period="5d")

        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="2d")

        if spy_hist.empty:
            return {}

        spy_now = float(spy_hist["Close"].iloc[-1])
        spy_prev = float(spy_hist["Close"].iloc[-2]) if len(spy_hist) > 1 else spy_now
        spy_5d = float(spy_hist["Close"].iloc[0])

        spy_day_chg = ((spy_now - spy_prev) / spy_prev * 100) if spy_prev else 0
        spy_5d_chg = ((spy_now - spy_5d) / spy_5d * 100) if spy_5d else 0

        market_trend = (
            "UPTREND" if spy_5d_chg > 1
            else "DOWNTREND" if spy_5d_chg < -1
            else "SIDEWAYS"
        )

        current_vix = float(vix_hist["Close"].iloc[-1]) if not vix_hist.empty else 20.0
        fear_level = (
            "HIGH FEAR (avoid new longs)" if current_vix > 25
            else "MODERATE (trade carefully)" if current_vix > 18
            else "LOW FEAR (good for swing trades)"
        )

        return {
            "spy_price": round(spy_now, 2),
            "spy_day_change": round(spy_day_chg, 2),
            "spy_5d_change": round(spy_5d_chg, 2),
            "market_trend": market_trend,
            "vix": round(current_vix, 1),
            "fear_level": fear_level,
        }

    except Exception as e:
        logger.warning(f"Market context fetch failed: {e}")
        return {}


def get_stock_data_for_claude(symbol: str, stock_info: Dict, token: str) -> Dict[str, Any]:
    """
    Fetch comprehensive real-time data for a stock to send to Claude.
    Includes 52W high/low and 6-month trend for richer AI context.

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

        # Get 252 days of history for 52W/6M context; fall back to 20 if unavailable
        df = tiingo_history(symbol, token, days=252)

        if df is None or df.empty:
            return None

        # Calculate metrics using recent 20 bars for short-term indicators
        df_recent = df.tail(20)
        prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
        gap_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0

        # Volume analysis
        current_volume = quote.get('volume', 0)
        avg_volume = df_recent['Volume'].mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Calculate RSI (14-period) using full history for accuracy
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not rsi.empty else 50

        # Recent price action (last 5 days)
        recent_closes = df['Close'].tail(5).tolist()

        # --- 52-Week & 6-Month Trend Context ---
        high_52w = round(df['High'].tail(252).max(), 2)
        low_52w  = round(df['Low'].tail(252).min(), 2)
        pct_below_52w_high = round((high_52w - current_price) / high_52w * 100, 1) if high_52w else 0
        pct_above_52w_low  = round((current_price - low_52w) / low_52w * 100, 1) if low_52w else 0

        # 6-month trend: compare current price to price ~126 trading days ago
        price_6m_ago = round(float(df['Close'].iloc[-126]), 2) if len(df) >= 126 else round(float(df['Close'].iloc[0]), 2)
        trend_6m_pct = round((current_price - price_6m_ago) / price_6m_ago * 100, 1) if price_6m_ago else 0
        trend_6m_dir = "UP" if trend_6m_pct > 3 else "DOWN" if trend_6m_pct < -3 else "FLAT"

        # Calculate risk/reward
        entry = stock_info.get('entry', current_price)
        stop = stock_info.get('stop', 0)
        target = stock_info.get('target', 0)

        risk = abs(entry - stop) if stop > 0 else 0
        reward = abs(target - entry) if target > 0 else 0
        rr_ratio = reward / risk if risk > 0 else 0

        # Fetch recent news: Tiingo first, yfinance fallback
        news_headlines = get_stock_news(symbol, days=7, token=token)

        # Fetch Tiingo fundamentals (P/E, market cap, margins, debt, ROE…)
        fundamentals = get_tiingo_fundamentals_for_claude(symbol, token)

        # Chart pattern detection (use recent 60 bars for pattern lookback)
        top_pattern = None
        try:
            patterns = detect_patterns(df.tail(60))
            if patterns:
                top_pattern = patterns[0]
        except Exception:
            pass

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
            "notes": stock_info.get('notes', ''),
            "news_headlines": news_headlines,
            # 52W / 6M trend context
            "high_52w": high_52w,
            "low_52w": low_52w,
            "pct_below_52w_high": pct_below_52w_high,
            "pct_above_52w_low": pct_above_52w_low,
            "price_6m_ago": price_6m_ago,
            "trend_6m_pct": trend_6m_pct,
            "trend_6m_dir": trend_6m_dir,
            # Tiingo fundamentals
            "fundamentals": fundamentals,
            # Chart pattern
            "pattern": top_pattern,
        }

    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None


def quick_analyze_watchlist(watchlist: List[Dict], token: str, api_key: str) -> str:
    """
    Quick analysis of entire watchlist using Sonnet (fast scan).
    Returns top 3-5 picks with brief reasoning.
    Includes 52W/6M trend context and recent news per stock.
    Uses prompt caching on the system prompt for cost savings.

    Args:
        watchlist: Enhanced watchlist with entry/stop/target
        token: Tiingo API token
        api_key: Anthropic API key

    Returns:
        Claude's quick analysis
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

        # Fetch current market context (SPY + VIX)
        mkt = get_market_context()

        # --- System prompt (cached for cost savings) ---
        system_prompt = (
            "You are a professional swing trading analyst. You rank watchlist stocks by their "
            "immediate trading opportunity using ONLY the live data and news provided — NOT your training data. "
            "Treat all prices, indicators, and headlines as current real-time information. "
            "Ranking criteria: Risk:Reward (2:1 minimum), volume confirmation, RSI zone, "
            "news sentiment, 52-week trend position, and market context."
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

        # --- Per-stock data block ---
        stocks_block = ""
        for i, stock in enumerate(stocks_data, 1):
            news = stock.get("news_headlines", [])
            news_line = f"\n   News:\n{_format_news_for_claude(news, max_articles=2)}" if news else ""
            trend_arrow = "↑" if stock['trend_6m_dir'] == "UP" else "↓" if stock['trend_6m_dir'] == "DOWN" else "→"
            fund = stock.get("fundamentals", {})
            fund_line = ""
            if fund:
                pe   = f"P/E {fund['pe_ratio']:.1f}" if fund.get("pe_ratio") else ""
                mkt  = (f"MCap ${fund['market_cap']/1e9:.1f}B" if (fund.get("market_cap") or 0) >= 1e9
                        else f"MCap ${(fund.get('market_cap') or 0)/1e6:.0f}M")
                mgn  = f"NetMgn {fund['profit_margin_pct']:.1f}%" if fund.get("profit_margin_pct") is not None else ""
                roe  = f"ROE {fund['roe_pct']:.1f}%" if fund.get("roe_pct") is not None else ""
                de   = f"D/E {fund['debt_to_equity']:.2f}" if fund.get("debt_to_equity") is not None else ""
                parts = [x for x in [pe, mkt, mgn, roe, de] if x]
                if parts:
                    fund_line = f"\n   Fundamentals: {' | '.join(parts)}"

            pat = stock.get("pattern")
            pat_line = (
                f"\n   Pattern: {pat['type']} ({pat['bias']}, {pat['confidence']}% conf) — {pat['action']}"
                if pat else ""
            )

            stocks_block += (
                f"{i}. {stock['symbol']} ${stock['current_price']} | {stock['setup_type']}"
                f" | Entry: ${stock['entry']:.2f} Stop: ${stock['stop']:.2f} Target: ${stock['target']:.2f}"
                f" | R:R: {stock['rr_ratio']:.1f}:1 | RSI: {stock['rsi']:.0f}"
                f" | Vol: {stock['volume_ratio']:.1f}x | Gap: {stock['gap_percent']:+.1f}%\n"
                f"   52W: High ${stock['high_52w']} / Low ${stock['low_52w']}"
                f" | {stock['pct_below_52w_high']:.1f}% below 52W high"
                f" | {stock['pct_above_52w_low']:.1f}% above 52W low\n"
                f"   6-Month Trend: {trend_arrow} {stock['trend_6m_pct']:+.1f}% (was ${stock['price_6m_ago']})"
                f"{fund_line}"
                f"{pat_line}"
                f"{news_line}\n\n"
            )

        user_prompt = (
            f"{mkt_section}"
            f"=== WATCHLIST ({len(stocks_data)} stocks) ===\n\n"
            f"{stocks_block}"
            "Using the LIVE data and news above (not your training data), provide:\n"
            "1. Top 3-5 picks (ranked best to worst) with ticker and star rating ⭐\n"
            "2. Brief reason for each (1-2 sentences) — mention news or 52W trend if relevant\n"
            "3. Position size (full/half/small) based on market conditions and VIX\n"
            "4. Any stocks to avoid and why\n\n"
            "Be concise and actionable."
        )

        # Call Claude API with system prompt caching
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=900,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}  # Cache system prompt (~90% cost savings on repeats)
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
        return f"❌ Error analyzing watchlist: {str(e)}"


def deep_analyze_stocks(selected_stocks: List[Dict], token: str, api_key: str,
                        portfolio_context: str = "") -> str:
    """
    Deep analysis of selected stocks using Sonnet (detailed & thorough).
    Includes 52W/6M trend context, recent news, and live market backdrop.
    Uses prompt caching on the system prompt for cost savings.

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

        # Fetch live market context (SPY + VIX)
        mkt = get_market_context()

        # --- System prompt (cached for cost savings) ---
        system_prompt = (
            "You are an expert swing trading analyst with deep knowledge of technical analysis, "
            "risk management, and market psychology. "
            "Base your analysis ONLY on the live data and news provided — NOT your training data. "
            "Treat all prices, indicators, headlines, and market context as current real-time information.\n\n"
            "Your analysis should include:\n"
            "- Detailed technical breakdown (entry quality, stop placement, target logic)\n"
            "- 52-week trend position: is this stock near highs, lows, or mid-range?\n"
            "- 6-month momentum: is the bigger trend working for or against this setup?\n"
            "- Volume and institutional interest\n"
            "- News impact: does recent news support or threaten the setup?\n"
            "- Entry timing and specific confirmation levels\n"
            "- Risk assessment, position sizing, and what would invalidate the setup\n\n"
            "Be thorough but actionable. Give specific price levels and clear recommendations."
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

        # --- Per-stock blocks ---
        stocks_block = ""
        for i, stock in enumerate(stocks_data, 1):
            news = stock.get("news_headlines", [])
            news_section = (
                "RECENT NEWS (last 7 days — use this, not training data):\n"
                + _format_news_for_claude(news, max_articles=3) + "\n"
                if news else
                "RECENT NEWS: None found in last 7 days\n"
            )

            trend_arrow = "↑" if stock['trend_6m_dir'] == "UP" else "↓" if stock['trend_6m_dir'] == "DOWN" else "→"
            fund_block = format_fundamentals_for_prompt(stock.get("fundamentals", {}))
            fund_section = f"\n{fund_block}\n" if fund_block else ""
            pat = stock.get("pattern")
            pat_section = (
                f"\nCHART PATTERN DETECTED:\n"
                f"  {pat['type']} ({pat['bias']}, {pat['confidence']}% confidence)\n"
                f"  {pat['description']}\n"
                f"  Action: {pat['action']}\n"
                if pat else ""
            )
            stocks_block += (
                f"{'═'*52}\n"
                f"{i}. {stock['symbol']} — ${stock['current_price']}\n"
                f"{'═'*52}\n\n"
                f"SETUP:\n"
                f"  Type: {stock['setup_type']}\n"
                f"  Entry: ${stock['entry']:.2f} | Stop: ${stock['stop']:.2f} | Target: ${stock['target']:.2f}\n"
                f"  Risk:Reward: {stock['rr_ratio']:.2f}:1\n\n"
                f"52-WEEK TREND CONTEXT:\n"
                f"  52W High: ${stock['high_52w']} | 52W Low: ${stock['low_52w']}\n"
                f"  Current price is {stock['pct_below_52w_high']:.1f}% below 52W high\n"
                f"  Current price is {stock['pct_above_52w_low']:.1f}% above 52W low\n"
                f"  6-Month Trend: {trend_arrow} {stock['trend_6m_pct']:+.1f}% (price 6 months ago: ${stock['price_6m_ago']})\n\n"
                f"CURRENT MARKET DATA:\n"
                f"  Gap: {stock['gap_percent']:+.1f}% | Volume: {stock['volume_ratio']:.1f}x avg | RSI (14): {stock['rsi']:.1f}\n"
                f"  Last 5 closes: {stock['recent_closes']}\n"
                f"{pat_section}"
                f"{fund_section}"
                f"{news_section}\n"
                f"TRADER NOTES: {stock['notes'] if stock['notes'] else 'None'}\n\n"
            )

        portfolio_section = f"{portfolio_context}\n" if portfolio_context else ""

        user_prompt = (
            f"Please provide a DEEP ANALYSIS of these {len(stocks_data)} stocks from my watchlist.\n\n"
            f"{portfolio_section}"
            f"{mkt_section}"
            f"{stocks_block}"
            "For EACH stock, provide:\n\n"
            "1. **SETUP ANALYSIS** — entry quality, stop placement, target logic, R:R assessment\n"
            "2. **52W / 6M TREND POSITION** — where is this stock in its bigger picture? Is the trend working for or against the setup?\n"
            "3. **CHART PATTERN** — does the detected pattern (if any) add conviction or raise a red flag?\n"
            "4. **FUNDAMENTALS** — are the business fundamentals (margins, debt, ROE) a tailwind or headwind?\n"
            "5. **NEWS IMPACT** — does recent news support or threaten the setup? Is there a catalyst?\n"
            "6. **VOLUME CONVICTION** — what is volume telling us about institutional interest?\n"
            "7. **ENTRY TIMING** — Enter now / Wait for confirmation / Skip? Give specific levels.\n"
            "8. **POSITION SIZING** — Full / Half / Small, with reasoning\n"
            "9. **RISKS TO MONITOR** — what would invalidate this setup? Key levels to watch.\n\n"
            "Be thorough and specific. Use the LIVE data above — not your training data."
        )

        # Call Claude API with prompt caching
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}  # Cache system prompt (~90% cost savings on repeats)
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


def analyze_scanner_results(confirmed: List[Dict], token: str, api_key: str,
                            portfolio_context: str = "") -> str:
    """
    AI Scanner Summary — ranks confirmed scanner results and highlights top picks.
    Pulls 52W high/low + 6-month trend from Tiingo, news from yfinance, and
    SPY/VIX market context. Uses prompt caching to keep costs low.

    Args:
        confirmed: List of confirmed scanner result dicts
        token: Tiingo API token
        api_key: Anthropic API key

    Returns:
        Claude's ranked top 3-5 picks with reasoning
    """
    try:
        if not confirmed:
            return "❌ No scanner results to analyze."

        # Limit to top 12 by SmartScore so prompt stays concise
        top = sorted(confirmed, key=lambda x: x.get("SmartScore", 0), reverse=True)[:12]

        # Live market context — SPY trend + VIX via yfinance
        mkt = get_market_context()

        # Build the stock data section for the prompt
        stocks_section = ""
        for i, rec in enumerate(top, 1):
            symbol = rec["Symbol"]
            current_price = rec["Price"]

            # Fetch 252-day history for 52W high/low and 6-month trend
            h52w = l52w = pct_from_high = pct_from_low = trend_6m = "N/A"
            try:
                df = tiingo_history(symbol, token, days=252)
                if df is not None and not df.empty:
                    h52w = round(float(df["High"].tail(252).max()), 2)
                    l52w = round(float(df["Low"].tail(252).min()), 2)
                    pct_from_high = round((current_price - h52w) / h52w * 100, 1)
                    pct_from_low  = round((current_price - l52w) / l52w * 100, 1)
                    if len(df) >= 126:
                        price_6m = float(df["Close"].iloc[-126])
                        trend_6m = round((current_price - price_6m) / price_6m * 100, 1)
            except Exception:
                pass

            # Fetch structured news articles (title + description + category + sentiment + source + recency)
            news = get_stock_news(symbol, days=7, token=token)
            news_block = _format_news_for_claude(news, max_articles=3)

            # Analyst targets + short interest + company name (yfinance)
            market_intel = _get_yf_market_intel(symbol, current_price)

            # Tiingo fundamentals (cached — no extra cost after scanner pre-fetch)
            fund = get_tiingo_fundamentals_for_claude(symbol, token)
            fund_block = format_fundamentals_for_prompt(fund) if fund else ""
            fund_section = f"   {fund_block}\n" if fund_block else ""

            earnings_note = rec.get("EarningsWarning", "") or ""

            pat = rec.get("Pattern")
            pattern_note = (
                f" | Pattern: {pat['type']} ({pat['bias']}, {pat['confidence']}% conf)"
                if pat else ""
            )

            # Build volume signal string — direction matters (selling pressure ≠ buying conviction)
            vol_signal = rec.get("VolSignal", "Neutral")
            fib_zone = rec.get("FibZone", "N/A")
            fib_pos = rec.get("FibPosition")
            fib_str = (
                f"{fib_zone} ({fib_pos:.0f}% Fib)" if fib_pos is not None else fib_zone or "N/A"
            )

            stocks_section += (
                f"\n{i}. {symbol} — {rec['Setup']} | SmartScore: {rec.get('SmartScore', 'N/A')}"
                f" | Sector: {rec.get('Sector', 'N/A')}\n"
                f"   Price: ${current_price:.2f} | RSI: {rec['RSI14']}"
                f" | RelVol: {rec.get('RelVolume', 1.0):.1f}x ({vol_signal}) | FibZone: {fib_str}\n"
                f"   Entry: ${current_price:.2f} | Stop: ${rec['Stop']:.2f}"
                f" | Target: ${rec['Target']:.2f} | R:R: {rec.get('RR_Ratio', 0):.1f}:1\n"
                f"   52W High: ${h52w} ({pct_from_high}% below high)"
                f" | 52W Low: ${l52w} ({pct_from_low}% above low)\n"
                f"   6-Month Trend: {trend_6m}%"
                f"{pattern_note}"
                f"{' | ' + earnings_note if earnings_note else ''}\n"
                f"{('   ' + market_intel + chr(10)) if market_intel else ''}"
                f"{fund_section}"
                f"   Recent News:\n{news_block}\n"
            )

        # Market context block
        mkt_section = ""
        if mkt:
            mkt_section = (
                f"=== LIVE MARKET CONTEXT ===\n"
                f"SPY: ${mkt['spy_price']} | Today: {mkt['spy_day_change']:+.1f}%"
                f" | 5-Day: {mkt['spy_5d_change']:+.1f}%\n"
                f"Market Trend: {mkt['market_trend']}\n"
                f"VIX: {mkt['vix']} → {mkt['fear_level']}\n"
                f"(Real-time data — use this as your current backdrop, not your training data)\n\n"
            )

        system_prompt = """You are a professional swing trading analyst reviewing scanner results.

RANKING CRITERIA (most important first):
1. Risk:Reward — minimum 2:1, prefer 3:1+
2. Volume direction — RelVol 1.5x+ is only a positive signal if VolSignal is "Bullish" (buying on up candles). "Bearish" VolSignal means heavy selling/distribution — penalize long setups with Bearish volume even if RelVol looks high
3. RSI position — 35-50 for pullbacks, 55-65 for breakouts
4. Fibonacci zone — discount zone (below 38.2% Fib) entries are higher quality; premium zone = extended risk
5. Chart pattern — bullish patterns (Bull Flag, Cup & Handle, Double Bottom, Ascending Triangle) add conviction; bearish patterns (Bear Flag, Double Top, Head & Shoulders, Descending Triangle) are red flags on long setups
6. 6-Month trend — broader trend must support the setup direction
7. Distance from 52-Week High — within 3% of 52W high = extended, higher risk
8. News sentiment — recent news supporting or threatening the thesis; categorized news type (Earnings, Analyst, M&A) matters — earnings risk = avoid
9. Earnings risk — stocks with earnings in <7 days = avoid

REQUIRED OUTPUT FORMAT:
**TOP PICKS TODAY:**
1. [SYMBOL] — [why it ranks #1, 1-2 sentences] | Key Risk: [1 sentence]
2. [SYMBOL] — [why it ranks #2, 1-2 sentences] | Key Risk: [1 sentence]
(list up to 5)

**AVOID TODAY:**
- [SYMBOL] — [reason in 1 sentence]

**MARKET NOTE:** [1 sentence on whether conditions favor swing trading today]

Be direct and specific. Traders need decisions, not analysis."""

        portfolio_section = f"{portfolio_context}\n" if portfolio_context else ""

        user_prompt = (
            f"{portfolio_section}"
            f"{mkt_section}"
            f"Scanner found {len(top)} confirmed setups today. Rank the TOP 3-5:\n"
            f"{stocks_section}\n"
            f"Use the live news, 52W/6M trend, and market context above — not your training data."
        )

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1600,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )

        return message.content[0].text

    except Exception as e:
        logger.error(f"Scanner AI error: {e}")
        return f"❌ Error analyzing scanner results: {str(e)}"


def analyze_single_stock(symbol: str, stock_data: Dict[str, Any], token: str, api_key: str,
                         portfolio_context: str = "") -> str:
    """
    Deep AI analysis of a single stock from the Analyzer page.
    Includes 52W high/low, 6-month trend, recent news, and market context.

    Args:
        symbol: Stock ticker
        stock_data: Dict with keys: price, rsi, ema20, ema50, entry, stop, target,
                    rr_ratio, volume_ratio, setup_type, sector, fib_zone, atr
        token: Tiingo API token
        api_key: Anthropic API key

    Returns:
        Claude's detailed analysis string
    """
    try:
        current_price = stock_data.get("price", 0)

        # ── 52W high/low + 6-month trend from Tiingo ──
        h52w = l52w = pct_from_high = pct_from_low = trend_6m = "N/A"
        try:
            df = tiingo_history(symbol, token, days=252)
            if df is not None and not df.empty:
                h52w = round(float(df["High"].tail(252).max()), 2)
                l52w = round(float(df["Low"].tail(252).min()), 2)
                pct_from_high = round((current_price - h52w) / h52w * 100, 1)
                pct_from_low  = round((current_price - l52w) / l52w * 100, 1)
                if len(df) >= 126:
                    price_6m = float(df["Close"].iloc[-126])
                    trend_6m = round((current_price - price_6m) / price_6m * 100, 1)
        except Exception:
            pass

        # ── Recent news: Tiingo first, yfinance fallback ──
        news = get_stock_news(symbol, days=7, token=token)
        news_lines = _format_news_for_claude(news, max_articles=3)

        # ── Tiingo fundamentals ──
        fund = get_tiingo_fundamentals_for_claude(symbol, token)
        fund_block = format_fundamentals_for_prompt(fund)
        fund_section = f"\n{fund_block}\n" if fund_block else ""

        # ── Analyst targets + short interest + company name (yfinance) ──
        market_intel = _get_yf_market_intel(symbol, current_price)
        market_intel_section = f"\n{market_intel}\n" if market_intel else ""

        # ── Institutional ownership (Tiingo) ──
        inst_pct = _get_institutional_pct(symbol, token)
        inst_section = f"{inst_pct}\n" if inst_pct else ""

        # ── Exact next earnings date ──
        raw_earnings = get_next_earnings_date(symbol, token)
        earnings_str = (
            raw_earnings.split("T")[0]
            if raw_earnings and raw_earnings not in ("N/A", "Not Scheduled")
            else "Not scheduled"
        )

        # ── Live market context (SPY + VIX) ──
        mkt = get_market_context()
        mkt_section = ""
        if mkt:
            mkt_section = (
                f"=== LIVE MARKET CONTEXT ===\n"
                f"SPY: ${mkt['spy_price']} | Today: {mkt['spy_day_change']:+.1f}%"
                f" | 5-Day: {mkt['spy_5d_change']:+.1f}% | Trend: {mkt['market_trend']}\n"
                f"VIX: {mkt['vix']} → {mkt['fear_level']}\n\n"
            )

        system_prompt = """You are an expert swing trading analyst. You provide deep, specific analysis of individual stock setups.

Your analysis must use ONLY the data provided — not your training data. Treat all prices, fundamentals, and news as current real-time information.

Be specific with price levels. Give the trader clear decisions they can act on immediately."""

        portfolio_section = f"{portfolio_context}\n" if portfolio_context else ""

        user_prompt = (
            f"{portfolio_section}"
            f"{mkt_section}"
            f"=== STOCK: {symbol} ===\n"
            f"Current Price: ${current_price:.2f} | Setup: {stock_data.get('setup_type', 'N/A')}"
            f" | Sector: {stock_data.get('sector', 'N/A')}\n"
            f"Next Earnings: {earnings_str}\n\n"
            f"=== TRADE PLAN ===\n"
            f"Entry: ${stock_data.get('entry', 0):.2f} | Stop: ${stock_data.get('stop', 0):.2f}"
            f" | Target: ${stock_data.get('target', 0):.2f} | R:R: {stock_data.get('rr_ratio', 0):.1f}:1\n\n"
            f"=== TECHNICAL DATA ===\n"
            f"RSI (14): {stock_data.get('rsi', 0):.1f} | Volume: {stock_data.get('volume_ratio', 0):.1f}x avg"
            f" | ATR: ${stock_data.get('atr', 0):.2f}\n"
            f"EMA20: ${stock_data.get('ema20', 0):.2f} | EMA50: ${stock_data.get('ema50', 0):.2f}\n"
            f"Fib Zone: {stock_data.get('fib_zone', 'N/A')}\n\n"
            f"=== 6-MONTH TREND CONTEXT ===\n"
            f"52-Week High: ${h52w} ({pct_from_high}% below high)\n"
            f"52-Week Low:  ${l52w} ({pct_from_low}% above low)\n"
            f"6-Month Price Change: {trend_6m}%\n"
            f"{fund_section}"
            f"{market_intel_section}"
            f"{inst_section}"
            f"=== RECENT NEWS (Last 7 Days) ===\n"
            f"{news_lines}\n\n"
            f"Using ONLY the data above, provide:\n\n"
            f"**1. SETUP QUALITY** (⭐ rating 1-5 + 1 sentence why)\n"
            f"**2. RECOMMENDATION** (Enter Now / Wait for Confirmation / Skip)\n"
            f"   - If Wait: what exact price/signal confirms entry?\n"
            f"**3. ANALYST VIEW** — where do analysts see fair value vs current price? Does the target support the trade?\n"
            f"**4. FUNDAMENTALS CHECK** — do margins, debt, and ROE support this trade?\n"
            f"**5. SHORT INTEREST** — does short interest create squeeze risk or signal fundamental problems?\n"
            f"**6. NEWS IMPACT** — does recent news support or threaten this setup?\n"
            f"**7. TREND CONTEXT** — does the 6-month/52W picture confirm the trade?\n"
            f"**8. KEY RISK** — what is the #1 thing that could invalidate this?\n"
            f"**9. ACTION PLAN** — specific prices: entry trigger, stop level, first target\n\n"
            f"Be direct. Give specific price levels. No vague advice."
        )

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1800,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )

        return message.content[0].text

    except Exception as e:
        logger.error(f"Analyzer AI error for {symbol}: {e}")
        return f"❌ Error analyzing {symbol}: {str(e)}"


def review_single_trade(trade: Dict[str, Any], api_key: str) -> str:
    """
    Claude reviews a single completed journal trade.
    Gives a post-trade breakdown: what went well, what to improve, lesson learned.

    Args:
        trade: Journal trade dict (symbol, entry/exit prices, P&L, notes, etc.)
        api_key: Anthropic API key

    Returns:
        Claude's trade review as a string
    """
    try:
        symbol      = trade.get("symbol", "UNKNOWN")
        entry_price = trade.get("entry_price", trade.get("entry", 0))
        exit_price  = trade.get("exit_price", 0)
        shares      = trade.get("shares", 0)
        pnl         = trade.get("pnl_dollar", 0)
        pnl_pct     = trade.get("pnl_percent", 0)
        r_mult      = trade.get("r_multiple", 0)
        setup       = trade.get("setup_type", "Unknown")
        exit_reason = trade.get("exit_reason", "Unknown")
        entry_date  = trade.get("entry_date", trade.get("opened", "Unknown"))
        exit_date   = trade.get("exit_date", "Unknown")
        notes       = trade.get("notes", "")

        # Days held
        try:
            from datetime import datetime as _dt
            days_held = (_dt.fromisoformat(str(exit_date)) - _dt.fromisoformat(str(entry_date))).days
        except Exception:
            days_held = 0

        outcome = "WIN ✅" if pnl > 0 else "LOSS ❌"

        system_prompt = (
            "You are an expert swing trading coach reviewing a completed trade from a trader's journal. "
            "Your goal is to give honest, specific, actionable feedback — not just praise. "
            "Focus on process quality (did they follow good trading rules?) not just outcome. "
            "A losing trade executed perfectly is better than a winning trade taken recklessly."
        )

        user_prompt = (
            f"Please review this completed trade from my journal:\n\n"
            f"{'═'*48}\n"
            f"TRADE: {symbol} — {outcome}\n"
            f"{'═'*48}\n"
            f"Entry: ${entry_price:.2f} on {entry_date}\n"
            f"Exit:  ${exit_price:.2f} on {exit_date}\n"
            f"Shares: {shares} | Days held: {days_held}\n"
            f"P&L: ${pnl:+,.2f} ({pnl_pct:+.1f}%) | R-Multiple: {r_mult:.2f}R\n"
            f"Setup Type: {setup}\n"
            f"Exit Reason: {exit_reason}\n\n"
            f"MY NOTES:\n{notes if notes else 'No notes recorded.'}\n\n"
            "Please provide:\n\n"
            "**1. TRADE GRADE** (A / B / C / D — grade the PROCESS, not just the outcome)\n"
            "**2. WHAT WENT WELL** — 1-2 specific things done right\n"
            "**3. WHAT TO IMPROVE** — 1-2 honest critiques with specific suggestions\n"
            "**4. EXIT ANALYSIS** — was the exit reason good? Did they hold too long / exit too early?\n"
            "**5. KEY LESSON** — one concrete rule or habit to take away from this trade\n\n"
            "Be direct and specific. Grade honestly — a C or D is more useful than false praise."
        )

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=900,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )

        return message.content[0].text

    except Exception as e:
        logger.error(f"Claude trade review error: {e}")
        return f"❌ Error reviewing trade: {str(e)}"


def coach_trading_performance(trades: List[Dict[str, Any]], focus: str, api_key: str) -> str:
    """
    Claude coaches the trader based on their journal history.
    Supports four coaching modes: general, psychology, strategy, risk.

    Args:
        trades: List of journal trade dicts
        focus: Coaching mode — "general" | "psychology" | "strategy" | "risk"
        api_key: Anthropic API key

    Returns:
        Claude's coaching response as a string
    """
    try:
        if not trades:
            return "❌ No trades to analyze. Add some journal entries first."

        wins   = [t for t in trades if t.get("pnl_dollar", 0) > 0]
        losses = [t for t in trades if t.get("pnl_dollar", 0) <= 0]

        total_pnl   = sum(t.get("pnl_dollar", 0) for t in trades)
        win_rate    = (len(wins) / len(trades) * 100) if trades else 0
        avg_win     = sum(t.get("pnl_dollar", 0) for t in wins) / len(wins) if wins else 0
        avg_loss    = sum(t.get("pnl_dollar", 0) for t in losses) / len(losses) if losses else 0
        avg_r       = sum(t.get("r_multiple", 0) for t in trades) / len(trades) if trades else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # Summarise exit reason breakdown
        exit_counts: Dict[str, int] = {}
        setup_pnl:   Dict[str, float] = {}
        for t in trades:
            er = t.get("exit_reason", "Unknown")
            exit_counts[er] = exit_counts.get(er, 0) + 1
            st = t.get("setup_type", "Unknown")
            setup_pnl[st] = setup_pnl.get(st, 0) + t.get("pnl_dollar", 0)

        exit_lines = "\n".join(f"  {r}: {c}x" for r, c in sorted(exit_counts.items(), key=lambda x: -x[1]))
        setup_lines = "\n".join(f"  {s}: ${p:+,.2f}" for s, p in sorted(setup_pnl.items(), key=lambda x: -x[1]))

        # Last 10 trades detail
        trade_lines = ""
        for t in trades[-10:]:
            sym  = t.get("symbol", "")
            ep   = t.get("entry_price", t.get("entry", 0))
            xp   = t.get("exit_price", 0)
            pnl  = t.get("pnl_dollar", 0)
            pp   = t.get("pnl_percent", 0)
            rm   = t.get("r_multiple", 0)
            er   = t.get("exit_reason", "")
            st   = t.get("setup_type", "")
            nt   = t.get("notes", "")
            trade_lines += (
                f"  {sym}: ${ep:.2f}→${xp:.2f} | {pnl:+,.2f} ({pp:+.1f}%) | {rm:.2f}R"
                f" | {st} | Exit: {er}\n"
                + (f"    Notes: {nt}\n" if nt else "")
            )

        # Focus-specific coaching question
        focus_map = {
            "general": (
                "📊 General Performance Review",
                "1. What patterns do you see in my wins vs losses?\n"
                "2. What is my biggest weakness based on this data?\n"
                "3. What should I prioritize improving next?\n"
                "4. Any specific habits to build or break?"
            ),
            "psychology": (
                "🧠 Trading Psychology",
                "1. Do I cut winners short or let losers run?\n"
                "2. Do my exit reasons suggest emotional exits (revenge trading, panic, FOMO)?\n"
                "3. What emotional patterns do you see in the data?\n"
                "4. What discipline habits would help me most?"
            ),
            "strategy": (
                "📈 Strategy & Execution",
                "1. Which setup types are working best for me?\n"
                "2. Are my R-multiples consistent with my stated R:R targets?\n"
                "3. Am I entering and exiting at optimal prices?\n"
                "4. What strategy adjustments would improve my edge?"
            ),
            "risk": (
                "⚠️ Risk Management",
                "1. Am I respecting my stop losses (check exit reasons)?\n"
                "2. Is my average loss acceptable relative to my average win?\n"
                "3. Is my profit factor above 1.5 (minimum sustainable)?\n"
                "4. What risk management rules should I tighten?"
            ),
        }

        focus_title, focus_questions = focus_map.get(focus, focus_map["general"])

        system_prompt = (
            "You are an expert swing trading coach analyzing a trader's journal history. "
            "Be honest and direct — vague encouragement is worthless. "
            "Focus on the PROCESS data: R-multiples, exit reasons, setup P&L breakdown. "
            "Give specific, actionable rules and habit changes the trader can implement immediately."
        )

        user_prompt = (
            f"Please coach me on my swing trading performance.\n\n"
            f"{'═'*48}\n"
            f"COACHING FOCUS: {focus_title}\n"
            f"{'═'*48}\n\n"
            f"PERFORMANCE SUMMARY ({len(trades)} trades):\n"
            f"  Total P&L: ${total_pnl:+,.2f}\n"
            f"  Win Rate: {win_rate:.1f}% ({len(wins)} wins / {len(losses)} losses)\n"
            f"  Avg Win: ${avg_win:+,.2f} | Avg Loss: ${avg_loss:+,.2f}\n"
            f"  Profit Factor: {profit_factor:.2f}\n"
            f"  Avg R-Multiple: {avg_r:.2f}R\n\n"
            f"EXIT REASON BREAKDOWN:\n{exit_lines}\n\n"
            f"P&L BY SETUP TYPE:\n{setup_lines}\n\n"
            f"LAST 10 TRADES:\n{trade_lines}\n"
            f"COACHING QUESTIONS:\n{focus_questions}\n\n"
            "Be specific and honest. Give me 3-5 concrete action items I can apply to my next trade."
        )

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1200,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )

        return message.content[0].text

    except Exception as e:
        logger.error(f"Claude coaching error: {e}")
        return f"❌ Error generating coaching: {str(e)}"


def analyze_base_formations(results: List[Dict], token: str, api_key: str,
                            portfolio_context: str = "") -> str:
    """
    AI review of Base Formation Scanner results.
    For each candidate, fetches live news + 52W context, then asks Claude to
    rate each base and decide: Worth Stalking / Watch + Wait / Skip.

    Args:
        results:           List of base scanner result dicts (Symbol, Price, BaseScore,
                           Tier, Resistance, ATR14, EMA50_dist_pct, Details)
        token:             Tiingo API token
        api_key:           Anthropic API key
        portfolio_context: formatted portfolio risk context string

    Returns:
        Claude's stalking shortlist with reasoning
    """
    try:
        if not results:
            return "❌ No base formations to analyze."

        top = results[:8]  # cap at 8 to keep prompt cost manageable

        # ── Market context ──────────────────────────────────────────────────
        mkt = get_market_context()
        mkt_section = ""
        if mkt:
            mkt_section = (
                f"=== LIVE MARKET CONTEXT ===\n"
                f"SPY: ${mkt['spy_price']} | Today: {mkt['spy_day_change']:+.1f}%"
                f" | 5-Day: {mkt['spy_5d_change']:+.1f}%\n"
                f"Market Trend: {mkt['market_trend']}\n"
                f"VIX: {mkt['vix']} → {mkt['fear_level']}\n\n"
            )

        # ── Per-stock data block ─────────────────────────────────────────────
        stocks_section = ""
        for i, rec in enumerate(top, 1):
            symbol = rec["Symbol"]
            price  = rec["Price"]

            # 52W high/low and 6-month trend
            h52w = l52w = pct_from_high = pct_from_low = trend_6m = "N/A"
            try:
                df = tiingo_history(symbol, token, days=252)
                if df is not None and not df.empty:
                    h52w          = round(float(df["High"].tail(252).max()), 2)
                    l52w          = round(float(df["Low"].tail(252).min()), 2)
                    pct_from_high = round((price - h52w) / h52w * 100, 1)
                    pct_from_low  = round((price - l52w) / l52w * 100, 1)
                    if len(df) >= 126:
                        p6m     = float(df["Close"].iloc[-126])
                        trend_6m = round((price - p6m) / p6m * 100, 1)
            except Exception:
                pass

            # Recent news
            news_articles = get_stock_news(symbol, days=7, token=token)
            news_text = _format_news_for_claude(news_articles, max_articles=3)

            # Tiingo fundamentals
            fund = get_tiingo_fundamentals_for_claude(symbol, token)
            fund_block = format_fundamentals_for_prompt(fund) if fund else ""
            fund_section = f"{fund_block}\n" if fund_block else ""

            # Analyst targets + short interest + company name (yfinance)
            market_intel = _get_yf_market_intel(symbol, price)

            # Institutional ownership (Tiingo)
            inst_pct = _get_institutional_pct(symbol, token)

            # Sector + exact earnings date
            sector = get_tiingo_sector(symbol, token)
            raw_earnings = get_next_earnings_date(symbol, token)
            earnings_str = (
                raw_earnings.split("T")[0]
                if raw_earnings and raw_earnings not in ("N/A", "Not Scheduled")
                else "Not scheduled"
            )

            # Scoring breakdown as plain text
            details_text = "\n".join(f"  {d}" for d in rec.get("Details", []))

            stocks_section += (
                f"--- BASE #{i}: {symbol} ---\n"
                f"Sector: {sector} | Next Earnings: {earnings_str}\n"
                f"Price: ${price:.2f} | Base Score: {rec['BaseScore']}/10 | {rec['Tier']}\n"
                f"Resistance / Breakout trigger: ${rec['Resistance']:.2f}\n"
                f"EMA50 distance: {rec['EMA50_dist_pct']:+.1f}% | ATR14: ${rec['ATR14']:.2f}\n"
                f"Chandelier stop (2×ATR): ~${price - 2 * rec['ATR14']:.2f}\n"
                f"52W High: ${h52w} ({pct_from_high}% below) | 52W Low: ${l52w} ({pct_from_low}% above)\n"
                f"6-Month trend: {trend_6m}%\n"
                f"{(market_intel + chr(10)) if market_intel else ''}"
                f"{('Institutional: ' + inst_pct + chr(10)) if inst_pct else ''}"
                f"Scoring breakdown:\n{details_text}\n"
                f"{fund_section}"
                f"Recent news:\n{news_text}\n\n"
            )

        # ── Prompts ──────────────────────────────────────────────────────────
        system_prompt = """You are a professional swing trader who specializes in anticipation entries — \
getting into position BEFORE the breakout happens, not chasing stocks already moving.

You are reviewing base formation candidates: stocks that are coiling, tightening up, and \
building energy for a potential move. Your job is NOT to find stocks to buy right now. \
Your job is to decide which setups are worth STALKING — adding to a watchlist and monitoring \
daily for the breakout trigger.

For each candidate, evaluate:
1. Quality of the base — is the coiling tight and controlled, or loose and sloppy?
2. Where is price relative to resistance? Is the breakout trigger price logical and clean?
3. Does the 6-month trend and analyst consensus support a move to the upside?
4. Does the analyst target provide meaningful upside vs the breakout trigger?
5. Is short interest a tailwind (squeeze potential) or a warning sign of smart money shorting?
6. Are institutional owners a positive (smart money is in) or is ownership declining?
7. Is there any news or earnings risk that could disrupt the base before it resolves?
8. Do the fundamentals (margins, ROE, debt) support the company's ability to move higher?

Your output for each stock must be one of three verdicts:
✅ WORTH STALKING — add to watchlist, set alert at resistance
⏳ WATCH + WAIT — promising but needs more time to tighten up
❌ SKIP — base is not clean enough, pass on this one

After your verdict, give: entry zone, breakout trigger, stop level (never below Chandelier stop), \
estimated R:R using analyst target as the destination.

Be decisive. A trader reading this needs to know exactly what to do."""

        portfolio_section = f"{portfolio_context}\n" if portfolio_context else ""

        user_prompt = (
            f"{portfolio_section}"
            f"{mkt_section}"
            f"Base Formation Scanner found {len(top)} candidates. "
            f"Review each and give your stalking verdict:\n\n"
            f"{stocks_section}"
            f"End with a 'MARKET NOTE' on whether current conditions (trend, VIX) "
            f"favor anticipation entries, and a 'VIX GATE' note if VIX is near or above 20."
        )

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )

        return message.content[0].text

    except Exception as e:
        logger.error(f"Base formation AI error: {e}")
        return f"❌ Error analyzing base formations: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# Persistent follow-up chat  (shared across all analysis pages)
# ─────────────────────────────────────────────────────────────────────────────

def render_ai_chat(context_key: str, api_key: str, initial_analysis: str) -> None:
    """
    Render a persistent follow-up chat interface below any Claude analysis output.

    Conversation history is stored in st.session_state["chat_<context_key>"] so
    each analysis page keeps its own independent thread.

    Args:
        context_key:      Unique string key, e.g. "scanner", "base_scanner", "analyzer_AAPL"
        api_key:          Anthropic API key
        initial_analysis: The Claude analysis text used as context for follow-up questions
    """
    chat_key = f"chat_{context_key}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    history: list = st.session_state[chat_key]

    # ── Header + clear button ────────────────────────────────────────────────
    hcol, ccol = st.columns([5, 1])
    with hcol:
        st.markdown("##### 💬 Follow-up Chat")
    with ccol:
        if history and st.button("🗑️ Clear", key=f"clr_chat_{context_key}"):
            st.session_state[chat_key] = []
            st.rerun()

    # ── Message history ──────────────────────────────────────────────────────
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Chat input ───────────────────────────────────────────────────────────
    user_q = st.chat_input(
        "Ask a follow-up question about this analysis…",
        key=f"chat_input_{context_key}",
    )

    if user_q:
        history.append({"role": "user", "content": user_q})

        system = (
            "You are an expert swing trading analyst continuing a conversation. "
            "Use ONLY the data already provided in the analysis context below — do not introduce "
            "new prices, news, or facts from your training data. Be concise and specific.\n\n"
            f"=== ORIGINAL ANALYSIS ===\n{initial_analysis}"
        )

        messages_for_api = [
            {"role": m["role"], "content": m["content"]} for m in history
        ]

        with st.spinner("🤖 Thinking…"):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                resp = client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=800,
                    system=[{
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }],
                    messages=messages_for_api,
                )
                reply = resp.content[0].text
            except Exception as exc:
                reply = f"❌ Chat error: {exc}"

        history.append({"role": "assistant", "content": reply})
        st.session_state[chat_key] = history
        st.rerun()
