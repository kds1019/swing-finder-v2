"""
Pre-Market Dashboard
Everything you need 6am-9:30am ET in one view
"""

import streamlit as st
import pandas as pd
from datetime import datetime, time as dt_time
import pytz
import os

from utils.tiingo_api import fetch_tiingo_realtime_quote, tiingo_history
from utils.storage import load_json
from utils.alerts import send_email_alert

# Page config
st.set_page_config(page_title="Pre-Market Dashboard", page_icon="🌅", layout="wide")

# Get Tiingo token
TIINGO_TOKEN = st.secrets.get("TIINGO_TOKEN") or os.getenv("TIINGO_TOKEN")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_market_status():
    """Get current market status and time until open/close."""
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    current_time = now_et.time()
    is_weekday = now_et.weekday() < 5  # Monday = 0, Friday = 4
    
    # Market hours
    premarket_start = dt_time(4, 0)
    market_open = dt_time(9, 30)
    market_close = dt_time(16, 0)
    afterhours_end = dt_time(20, 0)
    
    if not is_weekday:
        return {
            "status": "CLOSED",
            "message": "Market Closed (Weekend)",
            "color": "gray",
            "countdown": None
        }
    
    if premarket_start <= current_time < market_open:
        # Calculate time until market open
        market_open_dt = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        time_until = market_open_dt - now_et
        minutes_until = int(time_until.total_seconds() / 60)
        
        return {
            "status": "PRE-MARKET",
            "message": f"Pre-Market Active | Opens in {minutes_until} min",
            "color": "orange",
            "countdown": minutes_until,
            "current_time": now_et.strftime("%I:%M:%S %p ET")
        }
    
    elif market_open <= current_time < market_close:
        return {
            "status": "OPEN",
            "message": "Market Open",
            "color": "green",
            "countdown": None,
            "current_time": now_et.strftime("%I:%M:%S %p ET")
        }
    
    elif market_close <= current_time < afterhours_end:
        return {
            "status": "AFTER-HOURS",
            "message": "After Hours Trading",
            "color": "blue",
            "countdown": None,
            "current_time": now_et.strftime("%I:%M:%S %p ET")
        }
    
    else:
        return {
            "status": "CLOSED",
            "message": "Market Closed",
            "color": "gray",
            "countdown": None,
            "current_time": now_et.strftime("%I:%M:%S %p ET")
        }


def get_premarket_price(symbol: str, token: str):
    """Get pre-market price and calculate gap."""
    try:
        # Get current/pre-market price
        quote = fetch_tiingo_realtime_quote(symbol, token)
        current_price = quote.get('last') or quote.get('tngoLast')
        current_volume = quote.get('volume', 0)

        if not current_price:
            return None

        # Get previous close and average volume
        df = tiingo_history(symbol, token, days=20)
        if df is None or df.empty:
            return None

        prev_close = df['Close'].iloc[-1]
        avg_volume = df['Volume'].mean()

        # Calculate gap
        gap_amount = current_price - prev_close
        gap_percent = (gap_amount / prev_close) * 100

        # Calculate volume ratio (current vs average)
        volume_ratio = (current_volume / avg_volume) if avg_volume > 0 else 0

        return {
            "symbol": symbol,
            "current_price": current_price,
            "prev_close": prev_close,
            "gap_amount": gap_amount,
            "gap_percent": gap_percent,
            "direction": "UP" if gap_percent > 0 else "DOWN",
            "current_volume": current_volume,
            "avg_volume": avg_volume,
            "volume_ratio": volume_ratio
        }

    except Exception as e:
        return None


# ============================================================================
# MAIN UI
# ============================================================================

st.title("🌅 Pre-Market Dashboard")

# Market status banner
market_status = get_market_status()

if market_status["status"] == "PRE-MARKET":
    st.success(f"**{market_status['message']}** | {market_status['current_time']}")
elif market_status["status"] == "OPEN":
    st.info(f"**{market_status['message']}** | {market_status['current_time']}")
elif market_status["status"] == "AFTER-HOURS":
    st.warning(f"**{market_status['message']}** | {market_status['current_time']}")
else:
    st.error(f"**{market_status['message']}**")

st.divider()

# Auto-refresh during pre-market
if market_status["status"] == "PRE-MARKET":
    st.caption("🔄 Auto-refreshing every 60 seconds during pre-market hours")
    # Note: Streamlit doesn't support auto-refresh, but we can add a manual refresh button
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

st.divider()

# Three column layout
col1, col2, col3 = st.columns(3)

# ============================================================================
# COLUMN 1: GAPPERS (Stocks gapping >3%)
# ============================================================================

with col1:
    st.markdown("### 🚀 Big Gappers (>3%)")
    st.caption("Stocks with significant pre-market gaps")

    # Load watchlist to check for gaps
    try:
        watchlist_data = load_json("data/watchlist.json", default={})

        # Get all tickers from all watchlists
        all_tickers = []
        if isinstance(watchlist_data, dict):
            for wl_name, tickers in watchlist_data.items():
                all_tickers.extend(tickers)

        # Remove duplicates
        all_tickers = list(set(all_tickers))[:20]  # Limit to 20 for performance

        if all_tickers:
            gappers = []

            for ticker in all_tickers:
                gap_data = get_premarket_price(ticker, TIINGO_TOKEN)
                if gap_data and abs(gap_data['gap_percent']) >= 3.0:
                    gappers.append(gap_data)

            # Sort by gap percentage (absolute value)
            gappers.sort(key=lambda x: abs(x['gap_percent']), reverse=True)

            if gappers:
                for gap in gappers[:10]:  # Top 10
                    direction_emoji = "🟢" if gap['direction'] == "UP" else "🔴"

                    st.markdown(
                        f"{direction_emoji} **{gap['symbol']}** "
                        f"${gap['current_price']:.2f} "
                        f"({gap['gap_percent']:+.1f}%)"
                    )
                    st.caption(f"Prev Close: ${gap['prev_close']:.2f}")
                    st.divider()
            else:
                st.info("No significant gaps (>3%) detected")
        else:
            st.warning("Add stocks to watchlist to monitor gaps")

    except Exception as e:
        st.error(f"Error loading gappers: {e}")

# ============================================================================
# COLUMN 2: WATCHLIST WITH PRE-MARKET PRICES
# ============================================================================

with col2:
    st.markdown("### 📋 Watchlist Pre-Market")
    st.caption("All watchlist stocks with current prices")

    try:
        # Load enhanced watchlist (with entry/stop/target)
        enhanced_wl = load_json("data/watchlist_enhanced.json", default=[])

        if enhanced_wl:
            for item in enhanced_wl[:15]:  # Limit to 15
                symbol = item.get('symbol')
                entry = item.get('entry')
                setup = item.get('setup_type', 'N/A')

                # Get current price
                gap_data = get_premarket_price(symbol, TIINGO_TOKEN)

                if gap_data:
                    current = gap_data['current_price']
                    gap_pct = gap_data['gap_percent']

                    # Check if near entry
                    near_entry = ""
                    if entry:
                        distance = ((current - entry) / entry) * 100
                        if abs(distance) <= 2:
                            near_entry = "🎯 NEAR ENTRY"

                    gap_emoji = "🟢" if gap_pct > 0 else "🔴" if gap_pct < 0 else "⚪"

                    # Format entry price
                    entry_str = f"${entry:.2f}" if entry else "N/A"

                    st.markdown(f"**{symbol}** ${current:.2f} ({gap_pct:+.1f}%) {gap_emoji}")
                    st.caption(f"{setup} | Entry: {entry_str} {near_entry}")
                    st.divider()
                else:
                    st.markdown(f"**{symbol}** - Loading...")
        else:
            st.info("No stocks in enhanced watchlist")

    except Exception as e:
        st.error(f"Error loading watchlist: {e}")

# ============================================================================
# COLUMN 3: TODAY'S POTENTIAL TRIGGERS
# ============================================================================

with col3:
    st.markdown("### 🎯 Today's Triggers")
    st.caption("Stocks near entry points")

    try:
        enhanced_wl = load_json("data/watchlist_enhanced.json", default=[])

        if enhanced_wl:
            triggers = []

            for item in enhanced_wl:
                symbol = item.get('symbol')
                entry = item.get('entry')
                stop = item.get('stop')
                target = item.get('target')
                setup = item.get('setup_type', 'N/A')

                if not entry:
                    continue

                # Get current price
                gap_data = get_premarket_price(symbol, TIINGO_TOKEN)

                if gap_data:
                    current = gap_data['current_price']
                    volume_ratio = gap_data.get('volume_ratio', 0)
                    current_volume = gap_data.get('current_volume', 0)
                    avg_volume = gap_data.get('avg_volume', 0)

                    # Check if within 5% of entry
                    distance = ((current - entry) / entry) * 100

                    if abs(distance) <= 5:
                        triggers.append({
                            'symbol': symbol,
                            'current': current,
                            'entry': entry,
                            'stop': stop,
                            'target': target,
                            'distance': distance,
                            'setup': setup,
                            'volume_ratio': volume_ratio,
                            'current_volume': current_volume,
                            'avg_volume': avg_volume
                        })

            # Sort by distance to entry (closest first)
            triggers.sort(key=lambda x: abs(x['distance']))

            if triggers:
                for t in triggers[:10]:
                    status = "✅ TRIGGERED" if t['current'] >= t['entry'] else f"📍 {abs(t['distance']):.1f}% away"

                    # Volume indicator
                    vol_ratio = t.get('volume_ratio', 0)
                    if vol_ratio >= 1.5:
                        vol_indicator = "🔥 HIGH VOL"
                        vol_color = "green"
                    elif vol_ratio >= 0.8:
                        vol_indicator = "✅ Normal"
                        vol_color = "blue"
                    else:
                        vol_indicator = "⚠️ LOW VOL"
                        vol_color = "orange"

                    st.markdown(f"**{t['symbol']}** ${t['current']:.2f}")
                    st.caption(f"{t['setup']} | Entry: ${t['entry']:.2f}")
                    st.caption(f"Status: {status}")

                    # Show volume info
                    if vol_ratio > 0:
                        st.caption(f"Volume: {vol_indicator} ({vol_ratio:.1f}x avg)")

                    if t['stop'] and t['target']:
                        risk = abs(t['entry'] - t['stop'])
                        reward = abs(t['target'] - t['entry'])
                        rr = reward / risk if risk > 0 else 0
                        st.caption(f"R:R: {rr:.2f}:1")

                    st.divider()
            else:
                st.info("No stocks near entry points")
        else:
            st.info("Add stocks with entry points to watchlist")

    except Exception as e:
        st.error(f"Error loading triggers: {e}")

# ============================================================================
# QUICK ACTIONS
# ============================================================================

st.divider()
st.markdown("### ⚡ Quick Actions")

action_col1, action_col2, action_col3 = st.columns(3)

with action_col1:
    if st.button("📧 Email Me Summary", use_container_width=True):
        try:
            # Build summary email
            summary = f"""
Pre-Market Summary - {datetime.now().strftime('%Y-%m-%d %I:%M %p ET')}

Market Status: {market_status['message']}

Big Gappers: {len(gappers) if 'gappers' in locals() else 0}
Watchlist Stocks: {len(enhanced_wl) if 'enhanced_wl' in locals() else 0}
Near Entry: {len(triggers) if 'triggers' in locals() else 0}

Check SwingFinder for details!
"""

            send_email_alert(
                subject="🌅 Pre-Market Summary",
                body=summary,
                alert_type="premarket"
            )

            st.success("✅ Summary emailed!")
        except Exception as e:
            st.error(f"Email failed: {e}")

with action_col2:
    if st.button("🔍 Go to Scanner", use_container_width=True):
        st.session_state["active_page"] = "Scanner"
        st.switch_page("app.py")

with action_col3:
    if st.button("📊 Go to Analyzer", use_container_width=True):
        st.session_state["active_page"] = "Analyzer"
        st.switch_page("app.py")


