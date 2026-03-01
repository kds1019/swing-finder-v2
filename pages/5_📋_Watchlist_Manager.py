"""
Enhanced Watchlist Manager
Manage watchlist with entry/stop/target points for alert system
"""

import streamlit as st
import os
import json
from utils.storage import load_json, save_json, load_gist_json, save_gist_json

# Page config
st.set_page_config(page_title="Watchlist Manager - SwingFinder", page_icon="📋", layout="wide")

# Load Tiingo token
try:
    TIINGO_TOKEN = st.secrets.get("TIINGO_TOKEN") or st.secrets.get("TIINGO_API_KEY")
except:
    from dotenv import load_dotenv
    load_dotenv()
    TIINGO_TOKEN = os.getenv("TIINGO_TOKEN") or os.getenv("TIINGO_API_KEY")

# Header
st.title("📋 Watchlist Manager")
st.markdown("**Manage your watchlist with entry/stop/target points for the alert system**")

# Show which Scanner watchlist is being used
try:
    gist_id = st.secrets.get("GIST_ID") or os.getenv("GIST_ID")
    if gist_id:
        data = load_gist_json(gist_id, "watchlist.json")
        if isinstance(data, dict):
            watchlist_names = list(data.keys())
            active_name = st.session_state.get("active_watchlist", watchlist_names[0] if watchlist_names else "Unnamed")

            st.info(f"📂 **Synced with Scanner Watchlist:** '{active_name}' ({len(data.get(active_name, []))} stocks)")
            st.caption("💡 Stocks added/removed here will sync with the Scanner page")
except:
    pass

# Load watchlist
def load_watchlist_enhanced():
    """Load watchlist with entry/stop/target data from Scanner's format."""
    try:
        # Try loading from Gist first (Scanner format)
        gist_id = st.secrets.get("GIST_ID") or os.getenv("GIST_ID")
        if gist_id:
            try:
                data = load_gist_json(gist_id, "watchlist.json")

                # Scanner format: {"Unnamed": ["AAPL", "MSFT"], "Tech": ["NVDA"]}
                if isinstance(data, dict):
                    # Get the active watchlist from session state or use first one
                    active_name = st.session_state.get("active_watchlist")

                    # If no active watchlist, use the first one
                    if not active_name or active_name not in data:
                        active_name = list(data.keys())[0] if data else None

                    if active_name and active_name in data:
                        symbols = data[active_name]
                        # Convert to enhanced format
                        return [{'symbol': sym} if isinstance(sym, str) else sym for sym in symbols]

                # Already in enhanced format (list of dicts)
                elif isinstance(data, list):
                    return [{'symbol': sym} if isinstance(sym, str) else sym for sym in data]
            except:
                pass

        # Fallback to local
        data = load_json("data/watchlist.json", default=[])

        # Handle Scanner format
        if isinstance(data, dict):
            # Get first watchlist
            first_key = list(data.keys())[0] if data else None
            if first_key:
                symbols = data[first_key]
                return [{'symbol': sym} if isinstance(sym, str) else sym for sym in symbols]

        # Handle enhanced format
        elif isinstance(data, list):
            return [{'symbol': sym} if isinstance(sym, str) else sym for sym in data]

        return []
    except:
        return []

def save_watchlist_enhanced(watchlist):
    """Save watchlist maintaining compatibility with Scanner format."""
    # Save enhanced data locally (for alerts system)
    save_json(watchlist, "data/watchlist_enhanced.json")

    # Also update Scanner's format in Gist
    gist_id = st.secrets.get("GIST_ID") or os.getenv("GIST_ID")
    if gist_id:
        try:
            # Load existing Scanner watchlists
            existing_data = load_gist_json(gist_id, "watchlist.json")

            # If it's Scanner format (dict), update the active watchlist
            if isinstance(existing_data, dict):
                active_name = st.session_state.get("active_watchlist")
                if not active_name:
                    active_name = list(existing_data.keys())[0] if existing_data else "Unnamed"

                # Extract just symbols for Scanner compatibility
                symbols = [item.get('symbol') if isinstance(item, dict) else item for item in watchlist]
                existing_data[active_name] = symbols

                # Save back to Gist in Scanner format
                save_gist_json(gist_id, "watchlist.json", existing_data)
            else:
                # Save in enhanced format
                save_gist_json(gist_id, "watchlist.json", watchlist)
        except:
            pass

# Load watchlist
if 'watchlist_enhanced' not in st.session_state:
    st.session_state.watchlist_enhanced = load_watchlist_enhanced()

watchlist = st.session_state.watchlist_enhanced

# Tabs
tab1, tab2 = st.tabs(["📊 Watchlist", "➕ Add Stock"])

# ============================================================================
# TAB 1: Watchlist View
# ============================================================================
with tab1:
    if not watchlist:
        st.info("📭 Your watchlist is empty. Add stocks in the 'Add Stock' tab.")
    else:
        st.markdown(f"**{len(watchlist)} stocks in watchlist**")
        
        # Display each stock
        for idx, item in enumerate(watchlist):
            symbol = item.get('symbol') if isinstance(item, dict) else item
            
            with st.expander(f"**{symbol}**", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Edit form
                    setup_type = st.text_input(
                        "Setup Type",
                        value=item.get('setup_type', '') if isinstance(item, dict) else '',
                        key=f"setup_{idx}",
                        placeholder="e.g. Bull Flag, Cup and Handle"
                    )
                    
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        entry = st.number_input(
                            "Entry Price",
                            value=float(item.get('entry', 0.0)) if isinstance(item, dict) and item.get('entry') else 0.0,
                            min_value=0.0,
                            step=0.01,
                            key=f"entry_{idx}",
                            format="%.2f"
                        )
                    
                    with col_b:
                        stop = st.number_input(
                            "Stop Loss",
                            value=float(item.get('stop', 0.0)) if isinstance(item, dict) and item.get('stop') else 0.0,
                            min_value=0.0,
                            step=0.01,
                            key=f"stop_{idx}",
                            format="%.2f"
                        )
                    
                    with col_c:
                        target = st.number_input(
                            "Target",
                            value=float(item.get('target', 0.0)) if isinstance(item, dict) and item.get('target') else 0.0,
                            min_value=0.0,
                            step=0.01,
                            key=f"target_{idx}",
                            format="%.2f"
                        )
                    
                    notes = st.text_area(
                        "Notes",
                        value=item.get('notes', '') if isinstance(item, dict) else '',
                        key=f"notes_{idx}",
                        placeholder="Optional notes about this setup"
                    )
                    
                    # Calculate R:R if all values present
                    if entry > 0 and stop > 0 and target > 0:
                        risk = abs(entry - stop)
                        reward = abs(target - entry)
                        rr_ratio = reward / risk if risk > 0 else 0
                        
                        st.info(f"**Risk/Reward:** {rr_ratio:.2f}:1")
                    
                    # Save button
                    if st.button("💾 Save Changes", key=f"save_{idx}"):
                        watchlist[idx] = {
                            'symbol': symbol,
                            'setup_type': setup_type,
                            'entry': entry if entry > 0 else None,
                            'stop': stop if stop > 0 else None,
                            'target': target if target > 0 else None,
                            'notes': notes
                        }
                        save_watchlist_enhanced(watchlist)
                        st.session_state.watchlist_enhanced = watchlist
                        st.success(f"✅ Saved {symbol}")
                        st.rerun()
                
                with col2:
                    st.markdown("###")
                    if st.button("🗑️ Remove", key=f"remove_{idx}"):
                        watchlist.pop(idx)
                        save_watchlist_enhanced(watchlist)
                        st.session_state.watchlist_enhanced = watchlist
                        st.success(f"Removed {symbol}")
                        st.rerun()

# ============================================================================
# TAB 2: Add Stock
# ============================================================================
with tab2:
    st.subheader("Add New Stock to Watchlist")
    
    symbol_input = st.text_input("Stock Symbol", placeholder="e.g. AAPL").upper()
    
    if symbol_input:
        # Check if already in watchlist
        existing_symbols = [item.get('symbol') if isinstance(item, dict) else item for item in watchlist]
        
        if symbol_input in existing_symbols:
            st.warning(f"⚠️ {symbol_input} is already in your watchlist")
        else:
            st.success(f"✅ {symbol_input} is available to add")
            
            setup_type = st.text_input("Setup Type (optional)", placeholder="e.g. Bull Flag")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                entry = st.number_input("Entry Price (optional)", min_value=0.0, step=0.01, format="%.2f")
            with col2:
                stop = st.number_input("Stop Loss (optional)", min_value=0.0, step=0.01, format="%.2f")
            with col3:
                target = st.number_input("Target (optional)", min_value=0.0, step=0.01, format="%.2f")
            
            notes = st.text_area("Notes (optional)", placeholder="Why are you watching this stock?")
            
            if st.button("➕ Add to Watchlist", use_container_width=True):
                new_item = {
                    'symbol': symbol_input,
                    'setup_type': setup_type if setup_type else None,
                    'entry': entry if entry > 0 else None,
                    'stop': stop if stop > 0 else None,
                    'target': target if target > 0 else None,
                    'notes': notes if notes else None
                }
                
                watchlist.append(new_item)
                save_watchlist_enhanced(watchlist)
                st.session_state.watchlist_enhanced = watchlist
                st.success(f"✅ Added {symbol_input} to watchlist!")
                st.balloons()
                st.rerun()

