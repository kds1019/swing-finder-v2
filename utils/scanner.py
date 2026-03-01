"""
Background Scanner for SwingFinder
Monitors watchlist and sends alerts when conditions are met
"""

import streamlit as st
import pandas as pd
from datetime import datetime, time
from typing import List, Dict, Any
from utils.tiingo_api import fetch_tiingo_realtime_quote, tiingo_history
from utils.alerts import send_premarket_alert, send_breakout_alert
from utils.storage import load_json
from utils.logger import get_logger

logger = get_logger(__name__)


def is_market_hours() -> bool:
    """Check if currently in market hours (9:30am - 4:00pm ET)."""
    now = datetime.now()
    # Note: This is simplified - you may want to use pytz for proper ET timezone
    current_time = now.time()
    market_open = time(9, 30)
    market_close = time(16, 0)
    
    # Check if weekday (0 = Monday, 6 = Sunday)
    is_weekday = now.weekday() < 5
    
    return is_weekday and market_open <= current_time <= market_close


def is_premarket_hours() -> bool:
    """Check if currently in pre-market hours (4:00am - 9:30am ET)."""
    now = datetime.now()
    current_time = now.time()
    premarket_start = time(4, 0)
    market_open = time(9, 30)
    
    is_weekday = now.weekday() < 5
    
    return is_weekday and premarket_start <= current_time < market_open


def load_watchlist_with_entries() -> List[Dict[str, Any]]:
    """
    Load watchlist with saved entry/stop/target points.
    Returns list of dicts with symbol and trade plan.
    """
    try:
        # Try loading enhanced watchlist first (has entry/stop/target data)
        watchlist = load_json("data/watchlist_enhanced.json", default=[])

        if watchlist and isinstance(watchlist, list):
            return watchlist

        # Fallback to regular watchlist.json (Scanner format)
        watchlist = load_json("data/watchlist.json", default=[])

        # Handle Scanner format (dict of named watchlists)
        if isinstance(watchlist, dict):
            # Get first watchlist or 'Unnamed'
            first_key = list(watchlist.keys())[0] if watchlist else None
            if first_key:
                symbols = watchlist[first_key]
                return [{'symbol': sym} if isinstance(sym, str) else sym for sym in symbols]

        # Handle list format
        elif isinstance(watchlist, list):
            # Convert to list of dicts if it's just a list of symbols
            if watchlist and isinstance(watchlist[0], str):
                return [{'symbol': sym} for sym in watchlist]
            return watchlist

        return []

    except Exception as e:
        logger.warning(f"Error loading watchlist: {e}")
        return []


def check_premarket_gaps(TIINGO_TOKEN: str, gap_threshold: float = 2.0) -> List[Dict[str, Any]]:
    """
    Check watchlist for pre-market gaps.
    
    Args:
        TIINGO_TOKEN: Tiingo API token
        gap_threshold: Minimum gap % to trigger alert (default 2%)
    
    Returns:
        List of stocks with significant gaps
    """
    watchlist = load_watchlist_with_entries()
    gaps = []
    
    for item in watchlist:
        symbol = item.get('symbol') if isinstance(item, dict) else item
        
        try:
            # Get historical data for previous close
            df = tiingo_history(symbol, TIINGO_TOKEN, days=5)
            if df is None or df.empty:
                continue
            
            prev_close = df['Close'].iloc[-1]
            
            # Get current pre-market price
            quote = fetch_tiingo_realtime_quote(symbol, TIINGO_TOKEN)
            current_price = quote.get('last') or quote.get('tngoLast')
            
            if not current_price:
                continue
            
            # Calculate gap
            change_pct = ((current_price - prev_close) / prev_close) * 100
            
            # Check if gap exceeds threshold
            if abs(change_pct) >= gap_threshold:
                gaps.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'prev_close': prev_close,
                    'change_pct': change_pct,
                    'setup_type': item.get('setup_type'),
                    'entry': item.get('entry')
                })
                
                logger.info(f"📊 Pre-market gap detected: {symbol} {change_pct:+.2f}%")
        
        except Exception as e:
            logger.warning(f"Error checking pre-market for {symbol}: {e}")
            continue
    
    return gaps


def check_breakouts(TIINGO_TOKEN: str) -> List[Dict[str, Any]]:
    """
    Check watchlist for breakouts (entry points triggered).
    
    Args:
        TIINGO_TOKEN: Tiingo API token
    
    Returns:
        List of stocks that triggered entry points
    """
    watchlist = load_watchlist_with_entries()
    breakouts = []
    
    # Load alert history to avoid duplicate alerts
    alert_history = load_json("data/alert_log.json", default=[])
    alerted_today = set()
    
    # Get today's date
    today = datetime.now().date().isoformat()
    
    # Find stocks already alerted today
    for log_entry in alert_history:
        if log_entry.get('triggered_at', '').startswith(today):
            if 'breakout_' in log_entry.get('alert_id', ''):
                symbol = log_entry.get('ticker')
                if symbol:
                    alerted_today.add(symbol)
    
    for item in watchlist:
        if not isinstance(item, dict):
            continue
        
        symbol = item.get('symbol')
        entry_price = item.get('entry')
        
        # Skip if no entry point set or already alerted today
        if not entry_price or symbol in alerted_today:
            continue
        
        try:
            # Get current price
            quote = fetch_tiingo_realtime_quote(symbol, TIINGO_TOKEN)
            current_price = quote.get('last') or quote.get('tngoLast')
            
            if not current_price:
                continue
            
            # Check if entry triggered (price >= entry)
            if current_price >= entry_price:
                # Get volume data
                df = tiingo_history(symbol, TIINGO_TOKEN, days=20)
                volume_ratio = None
                
                if df is not None and not df.empty and 'Volume' in df.columns:
                    avg_volume = df['Volume'].tail(20).mean()
                    current_volume = quote.get('volume', 0)
                    if avg_volume > 0 and current_volume > 0:
                        volume_ratio = current_volume / avg_volume
                
                breakouts.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'setup_type': item.get('setup_type', 'Breakout'),
                    'stop': item.get('stop'),
                    'target': item.get('target'),
                    'volume_ratio': volume_ratio,
                    'notes': item.get('notes')
                })
                
                logger.info(f"🚨 Breakout detected: {symbol} @ ${current_price:.2f} (entry: ${entry_price:.2f})")
        
        except Exception as e:
            logger.warning(f"Error checking breakout for {symbol}: {e}")
            continue
    
    return breakouts

