"""
Watchlist Auto-Cleanup System
Automatically removes invalid/dead setups from watchlist
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import streamlit as st

from utils.tiingo_api import fetch_tiingo_realtime_quote, tiingo_history
from utils.storage import load_json, save_json
from utils.alerts import send_email_alert
from utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

CLEANUP_CONFIG = {
    "stop_loss_buffer": 0.0,        # Remove immediately when below stop
    "runaway_threshold": 10.0,      # Remove if >10% above entry
    "dead_money_days": 14,          # Check 14-day movement
    "dead_money_threshold": 2.0,    # Remove if <2% movement in 14 days
    "send_email_report": True,      # Email cleanup report
}


# ============================================================================
# CLEANUP LOGIC
# ============================================================================

def check_broke_below_stop(stock: Dict, current_price: float) -> Tuple[bool, str]:
    """
    Check if stock broke below stop loss.
    
    Returns:
        (should_remove, reason)
    """
    stop = stock.get('stop')
    
    if not stop:
        return False, ""
    
    buffer = CLEANUP_CONFIG['stop_loss_buffer']
    
    if current_price < (stop - buffer):
        distance = ((stop - current_price) / stop) * 100
        reason = f"Broke below stop (${stop:.2f}) by {distance:.1f}% - Setup invalidated"
        return True, reason
    
    return False, ""


def check_ran_away(stock: Dict, current_price: float) -> Tuple[bool, str]:
    """
    Check if stock ran too far above entry (missed opportunity).
    
    Returns:
        (should_remove, reason)
    """
    entry = stock.get('entry')
    
    if not entry:
        return False, ""
    
    threshold = CLEANUP_CONFIG['runaway_threshold']
    distance_pct = ((current_price - entry) / entry) * 100
    
    if distance_pct > threshold:
        reason = f"Ran {distance_pct:.1f}% above entry (${entry:.2f}) - Missed opportunity"
        return True, reason
    
    return False, ""


def check_dead_money(stock: Dict, token: str) -> Tuple[bool, str]:
    """
    Check if stock has minimal movement (dead money).
    
    Returns:
        (should_remove, reason)
    """
    symbol = stock.get('symbol')
    days = CLEANUP_CONFIG['dead_money_days']
    threshold = CLEANUP_CONFIG['dead_money_threshold']
    
    try:
        # Get historical data
        df = tiingo_history(symbol, token, days=days + 5)
        
        if df is None or len(df) < days:
            return False, ""
        
        # Get price from N days ago and current price
        price_old = df['Close'].iloc[-(days + 1)]
        price_current = df['Close'].iloc[-1]
        
        # Calculate movement
        movement_pct = abs((price_current - price_old) / price_old) * 100
        
        if movement_pct < threshold:
            reason = f"Dead money - Only {movement_pct:.1f}% movement in {days} days"
            return True, reason
        
        return False, ""
    
    except Exception as e:
        logger.warning(f"Error checking dead money for {symbol}: {e}")
        return False, ""


def clean_watchlist_daily(token: str, send_email: bool = True) -> Dict[str, Any]:
    """
    Run daily watchlist cleanup.
    
    Returns:
        Dictionary with cleanup results
    """
    logger.info("Starting watchlist cleanup...")
    
    # Load enhanced watchlist
    watchlist = load_json("data/watchlist_enhanced.json", default=[])
    
    if not watchlist:
        logger.info("Watchlist is empty, nothing to clean")
        return {
            "removed": [],
            "kept": [],
            "total_removed": 0,
            "total_kept": 0
        }
    
    removed_stocks = []
    kept_stocks = []
    
    for stock in watchlist:
        symbol = stock.get('symbol')
        
        if not symbol:
            continue
        
        try:
            # Get current price
            quote = fetch_tiingo_realtime_quote(symbol, token)
            current_price = quote.get('last') or quote.get('tngoLast')
            
            if not current_price:
                logger.warning(f"Could not get price for {symbol}, keeping in watchlist")
                kept_stocks.append(stock)
                continue
            
            # Check removal criteria
            should_remove = False
            removal_reason = ""
            
            # Check 1: Broke below stop
            broke_stop, reason = check_broke_below_stop(stock, current_price)
            if broke_stop:
                should_remove = True
                removal_reason = reason
            
            # Check 2: Ran away (only if didn't break stop)
            if not should_remove:
                ran_away, reason = check_ran_away(stock, current_price)
                if ran_away:
                    should_remove = True
                    removal_reason = reason
            
            # Check 3: Dead money (only if passed other checks)
            if not should_remove:
                dead, reason = check_dead_money(stock, token)
                if dead:
                    should_remove = True
                    removal_reason = reason
            
            # Add to appropriate list
            if should_remove:
                removed_stocks.append({
                    **stock,
                    'current_price': current_price,
                    'removal_reason': removal_reason
                })
                logger.info(f"Removing {symbol}: {removal_reason}")
            else:
                kept_stocks.append(stock)
                logger.info(f"Keeping {symbol}")
        
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            kept_stocks.append(stock)  # Keep on error
    
    # Save cleaned watchlist
    save_json(kept_stocks, "data/watchlist_enhanced.json")
    
    # Prepare results
    results = {
        "removed": removed_stocks,
        "kept": kept_stocks,
        "total_removed": len(removed_stocks),
        "total_kept": len(kept_stocks),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Send email report
    if send_email and CLEANUP_CONFIG['send_email_report'] and removed_stocks:
        send_cleanup_email_report(results)
    
    logger.info(f"Cleanup complete: Removed {len(removed_stocks)}, Kept {len(kept_stocks)}")

    return results


def send_cleanup_email_report(results: Dict[str, Any]):
    """Send email report of cleanup results."""
    removed = results['removed']
    kept = results['kept']
    timestamp = results['timestamp']

    # Build email body
    email_body = f"""
🧹 Watchlist Cleanup Report
Date: {timestamp}

{'='*50}
REMOVED STOCKS ({len(removed)}):
{'='*50}

"""

    for i, stock in enumerate(removed, 1):
        symbol = stock['symbol']
        current = stock.get('current_price', 0)
        entry = stock.get('entry', 0)
        stop = stock.get('stop', 0)
        reason = stock.get('removal_reason', 'Unknown')

        email_body += f"""
{i}. {symbol} - ${current:.2f}
   Entry: ${entry:.2f} | Stop: ${stop:.2f}
   Reason: {reason}
"""

    email_body += f"""

{'='*50}
REMAINING STOCKS ({len(kept)}):
{'='*50}

"""

    kept_symbols = [s.get('symbol') for s in kept]
    email_body += ", ".join(kept_symbols)

    email_body += f"""


Your watchlist is now clean and focused!

Total Removed: {len(removed)}
Total Remaining: {len(kept)}

Check SwingFinder for details.
"""

    try:
        send_email_alert(
            subject=f"🧹 Watchlist Cleanup - {len(removed)} stocks removed",
            body=email_body,
            alert_type="watchlist_cleanup"
        )
        logger.info("Cleanup email report sent")
    except Exception as e:
        logger.error(f"Failed to send cleanup email: {e}")


def get_cleanup_preview(token: str) -> Dict[str, Any]:
    """
    Preview what would be removed without actually removing.
    Useful for manual cleanup button.
    """
    logger.info("Generating cleanup preview...")

    # Load enhanced watchlist
    watchlist = load_json("data/watchlist_enhanced.json", default=[])

    if not watchlist:
        return {
            "to_remove": [],
            "to_keep": [],
            "total_to_remove": 0,
            "total_to_keep": 0
        }

    to_remove = []
    to_keep = []

    for stock in watchlist:
        symbol = stock.get('symbol')

        if not symbol:
            continue

        try:
            # Get current price
            quote = fetch_tiingo_realtime_quote(symbol, token)
            current_price = quote.get('last') or quote.get('tngoLast')

            if not current_price:
                to_keep.append(stock)
                continue

            # Check removal criteria
            should_remove = False
            removal_reason = ""

            # Check all criteria
            broke_stop, reason = check_broke_below_stop(stock, current_price)
            if broke_stop:
                should_remove = True
                removal_reason = reason

            if not should_remove:
                ran_away, reason = check_ran_away(stock, current_price)
                if ran_away:
                    should_remove = True
                    removal_reason = reason

            if not should_remove:
                dead, reason = check_dead_money(stock, token)
                if dead:
                    should_remove = True
                    removal_reason = reason

            # Add to appropriate list
            if should_remove:
                to_remove.append({
                    **stock,
                    'current_price': current_price,
                    'removal_reason': removal_reason
                })
            else:
                to_keep.append(stock)

        except Exception as e:
            logger.error(f"Error previewing {symbol}: {e}")
            to_keep.append(stock)

    return {
        "to_remove": to_remove,
        "to_keep": to_keep,
        "total_to_remove": len(to_remove),
        "total_to_keep": len(to_keep)
    }

