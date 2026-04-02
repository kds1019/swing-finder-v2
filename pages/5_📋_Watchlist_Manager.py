"""
Enhanced Watchlist Manager
Manage watchlist with entry/stop/target points for alert system
"""

import streamlit as st
import os
import json
from datetime import datetime
from utils.storage import load_json, save_json, load_gist_json, save_gist_json
from utils.watchlist_hygiene import get_cleanup_preview, clean_watchlist_daily
from utils.claude_analyzer import analyze_watchlist_with_claude

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

# Check if Gist is configured
gist_id = st.secrets.get("GIST_ID") or os.getenv("GIST_ID")
github_token = st.secrets.get("GITHUB_GIST_TOKEN") or os.getenv("GITHUB_GIST_TOKEN")

if gist_id and github_token:
    st.success("✅ Cloud sync enabled - Your watchlist is saved to GitHub Gist and won't be lost!")
    try:
        data = load_gist_json(gist_id, "watchlist.json")
        if isinstance(data, dict):
            watchlist_names = list(data.keys())
            active_name = st.session_state.get("active_watchlist", watchlist_names[0] if watchlist_names else "Unnamed")
            st.info(f"📂 **Synced with Scanner Watchlist:** '{active_name}' ({len(data.get(active_name, []))} stocks)")
    except:
        pass
else:
    st.error("⚠️ **Cloud sync NOT configured** - Your watchlist will be LOST when Streamlit Cloud redeploys!")
    with st.expander("🔧 How to Enable Cloud Sync (REQUIRED to keep your data)", expanded=True):
        st.markdown("""
        **Why you need this:** Streamlit Cloud deletes local files on every redeploy. Without cloud sync, your watchlist disappears!

        **Quick Setup (5 minutes):**

        1. **Create GitHub Token:**
           - Go to https://github.com/settings/tokens
           - Click "Generate new token (classic)"
           - Name: "SwingFinder Watchlist"
           - Check ONLY: `gist` scope
           - Click "Generate token" and **copy it**

        2. **Create Gist:**
           - Go to https://gist.github.com/
           - Create new Gist (any name, any content)
           - Copy the Gist ID from URL (e.g., `abc123def456`)

        3. **Add to Streamlit Secrets:**
           - In Streamlit Cloud: App Settings → Secrets
           - Add these lines:
           ```
           GITHUB_GIST_TOKEN = "paste_your_token_here"
           GIST_ID = "paste_your_gist_id_here"
           ```
           - Save and redeploy

        **Done!** Your watchlist will now survive redeploys.
        """)

# Load watchlist
def load_watchlist_enhanced():
    """Load watchlist with entry/stop/target data from Scanner's format."""
    try:
        # Try loading from Gist first
        gist_id = st.secrets.get("GIST_ID") or os.getenv("GIST_ID")
        github_token = st.secrets.get("GITHUB_GIST_TOKEN") or os.getenv("GITHUB_GIST_TOKEN")

        if gist_id and github_token:
            # Try enhanced watchlist first (has entry/stop/target data)
            try:
                data = load_gist_json(gist_id, "watchlist_enhanced.json")
                if data and isinstance(data, list):
                    return data
            except:
                pass

            # Fallback to Scanner format
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

    # Save to GitHub Gist for cloud persistence
    gist_id = st.secrets.get("GIST_ID") or os.getenv("GIST_ID")
    github_token = st.secrets.get("GITHUB_GIST_TOKEN") or os.getenv("GITHUB_GIST_TOKEN")

    if gist_id and github_token:
        try:
            # Save enhanced watchlist to Gist (with entry/stop/target data)
            save_gist_json(gist_id, "watchlist_enhanced.json", watchlist)

            # Also update Scanner's format in Gist for compatibility
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
        except Exception as e:
            # Fail silently if Gist not configured
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

# ============================================================================
# WATCHLIST AUTO-CLEANUP
# ============================================================================

st.divider()

# ============================================================================
# AI WATCHLIST ANALYZER (CLAUDE) - Built-in AI Analysis
# ============================================================================

st.markdown("## 🤖 AI Watchlist Analysis (Claude)")
st.caption("Get Claude's top 3-5 stock picks from your watchlist with real-time market data")

# Check if Claude API key is configured
# Try multiple possible key names for flexibility
anthropic_key = (
    st.secrets.get("swingfinder_key") or
    st.secrets.get("ANTHROPIC_API_KEY") or
    os.getenv("ANTHROPIC_API_KEY") or
    os.getenv("swingfinder_key")
)
tiingo_token = st.secrets.get("TIINGO_TOKEN") or os.getenv("TIINGO_TOKEN")

if not anthropic_key:
    st.warning("⚠️ Claude API not configured. Add your Claude API key to Streamlit secrets to enable AI analysis.")
    with st.expander("🔧 How to Add Claude API Key"):
        st.markdown("""
        1. Go to Streamlit Cloud → App Settings → Secrets
        2. Add this line (use either key name):
        ```
        swingfinder_key = "sk-ant-your-key-here"
        ```
        OR
        ```
        ANTHROPIC_API_KEY = "sk-ant-your-key-here"
        ```
        3. Save and redeploy
        """)
else:
    st.success("✅ Claude AI enabled")

    if st.button("🤖 Analyze Watchlist with AI", type="primary", use_container_width=True):
        watchlist = load_json("data/watchlist_enhanced.json", default=[])

    if not watchlist:
                st.error("❌ No stocks in watchlist to analyze")
        elif not tiingo_token:
            st.error("❌ Tiingo API token not configured")
        else:
            with st.spinner("🤖 Claude is analyzing your watchlist with real-time data..."):
                # Call Claude analyzer
                analysis = analyze_watchlist_with_claude(
                    watchlist=watchlist,
                    token=tiingo_token,
                    api_key=anthropic_key
                )

                # Display results
                st.markdown("### 🎯 Claude's Analysis")
                st.markdown(analysis)

                # Save to session state for persistence
                st.session_state['claude_analysis'] = analysis
                st.session_state['claude_analysis_time'] = datetime.now().strftime("%Y-%m-%d %I:%M %p")

    # Show previous analysis if available
    if 'claude_analysis' in st.session_state:
        st.divider()
        st.caption(f"💾 Last analysis: {st.session_state.get('claude_analysis_time', 'Unknown')}")
        with st.expander("📊 View Last Analysis", expanded=False):
            st.markdown(st.session_state['claude_analysis'])

        if not watchlist:
            st.error("❌ No stocks in watchlist to analyze")
        elif not tiingo_token:
            st.error("❌ Tiingo API token not configured")
        else:
            with st.spinner("🤖 Claude is analyzing your watchlist with real-time data..."):
                # Call Claude analyzer
                analysis = analyze_watchlist_with_claude(
                    watchlist=watchlist,
                    token=tiingo_token,
                    api_key=anthropic_key
                )

                # Display results
                st.markdown("### 🎯 Claude's Analysis")
                st.markdown(analysis)

                # Save to session state for persistence
                st.session_state['claude_analysis'] = analysis
                st.session_state['claude_analysis_time'] = datetime.now().strftime("%Y-%m-%d %I:%M %p")

    # Show previous analysis if available
    if 'claude_analysis' in st.session_state:
        st.divider()
        st.caption(f"💾 Last analysis: {st.session_state.get('claude_analysis_time', 'Unknown')}")
        with st.expander("📊 View Last Analysis", expanded=False):
            st.markdown(st.session_state['claude_analysis'])

st.divider()
st.markdown("## 🧹 Watchlist Auto-Cleanup")
st.caption("Automatically remove invalid setups to keep your watchlist clean and focused")

# Explain cleanup criteria
with st.expander("ℹ️ What Gets Removed?", expanded=False):
    st.markdown("""
    The cleanup system removes stocks that meet any of these criteria:

    **1. Broke Below Stop Loss**
    - Stock price dropped below your stop loss
    - Setup is invalidated (bearish breakdown)
    - Example: Entry $150, Stop $145, Current $143 ❌

    **2. Ran Away (Missed Opportunity)**
    - Stock ran >10% above your entry price
    - Too late to chase the entry
    - Example: Entry $100, Current $112 ❌

    **3. Dead Money (No Movement)**
    - Less than 2% price movement in 14 days
    - Stock is consolidating too long
    - Example: 14 days ago $50, Current $50.50 (1% move) ❌

    **What Stays:**
    - ✅ Stocks still valid (above stop, near entry, moving)
    - ✅ Stocks without entry/stop set (manual review needed)
    """)

# Preview cleanup
st.markdown("### 🔍 Preview Cleanup")

if st.button("🔍 Preview What Will Be Removed", use_container_width=True):
    with st.spinner("Analyzing watchlist..."):
        try:
            preview = get_cleanup_preview(TIINGO_TOKEN)

            to_remove = preview['to_remove']
            to_keep = preview['to_keep']

            if to_remove:
                st.warning(f"⚠️ **{len(to_remove)} stocks** will be removed:")

                for stock in to_remove:
                    symbol = stock['symbol']
                    current = stock.get('current_price', 0)
                    entry = stock.get('entry', 0)
                    stop = stock.get('stop', 0)
                    reason = stock.get('removal_reason', 'Unknown')

                    st.markdown(f"""
                    **{symbol}** - ${current:.2f}
                    - Entry: ${entry:.2f} | Stop: ${stop:.2f}
                    - Reason: {reason}
                    """)
                    st.divider()

                st.success(f"✅ **{len(to_keep)} stocks** will remain in watchlist")
            else:
                st.success("✅ All stocks are valid! Nothing to remove.")
                st.info(f"📊 {len(to_keep)} stocks in watchlist")

        except Exception as e:
            st.error(f"Error previewing cleanup: {e}")

# Manual cleanup button
st.markdown("### 🧹 Run Cleanup Now")

col1, col2 = st.columns(2)

with col1:
    if st.button("🧹 Clean Watchlist Now", type="primary", use_container_width=True):
        with st.spinner("Cleaning watchlist..."):
            try:
                results = clean_watchlist_daily(TIINGO_TOKEN, send_email=False)

                removed = results['removed']
                kept = results['kept']

                if removed:
                    st.success(f"✅ Cleanup complete! Removed {len(removed)} stocks, kept {len(kept)} stocks")

                    with st.expander("📋 View Removed Stocks"):
                        for stock in removed:
                            symbol = stock['symbol']
                            reason = stock.get('removal_reason', 'Unknown')
                            st.markdown(f"- **{symbol}**: {reason}")

                    st.info("🔄 Refresh the page to see updated watchlist")

                    if st.button("🔄 Refresh Page"):
                        st.rerun()
                else:
                    st.success("✅ All stocks are valid! Nothing was removed.")
                    st.info(f"📊 {len(kept)} stocks remain in watchlist")

            except Exception as e:
                st.error(f"Error during cleanup: {e}")

with col2:
    if st.button("📧 Clean & Email Report", use_container_width=True):
        with st.spinner("Cleaning watchlist and sending email..."):
            try:
                results = clean_watchlist_daily(TIINGO_TOKEN, send_email=True)

                removed = results['removed']
                kept = results['kept']

                if removed:
                    st.success(f"✅ Cleanup complete! Removed {len(removed)} stocks, kept {len(kept)} stocks")
                    st.success("📧 Email report sent!")

                    if st.button("🔄 Refresh Page", key="refresh2"):
                        st.rerun()
                else:
                    st.success("✅ All stocks are valid! Nothing was removed.")
                    st.info("📧 No email sent (nothing to report)")

            except Exception as e:
                st.error(f"Error during cleanup: {e}")

# Cleanup configuration
st.divider()
st.markdown("### ⚙️ Cleanup Settings")

with st.expander("Configure Cleanup Rules", expanded=False):
    st.markdown("""
    **Current Settings:**
    - Stop Loss Buffer: 0% (remove immediately when below stop)
    - Runaway Threshold: 10% above entry
    - Dead Money Period: 14 days
    - Dead Money Threshold: <2% movement

    💡 These settings can be adjusted in `utils/watchlist_hygiene.py`
    """)

