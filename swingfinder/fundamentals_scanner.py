"""
Fundamentals Scanner - Find Quality Stocks
Filter stocks by P/E, debt, profitability, growth
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from utils.tiingo_api import tiingo_all_us_tickers, tiingo_history
from utils.fundamentals import (
    get_fundamentals, get_daily_metrics, calculate_fundamental_score,
    extract_key_metrics, format_large_number
)
from utils.storage import load_json, load_watchlist


def show_fundamentals_scanner():
    """Main fundamentals scanner page."""
    
    st.title("📊 Fundamentals Scanner")
    st.markdown("**Find quality stocks using fundamental analysis**")
    
    # Get API token
    TIINGO_TOKEN = st.secrets.get("TIINGO_TOKEN", "")
    if not TIINGO_TOKEN:
        st.error("⚠️ TIINGO_TOKEN not found in secrets!")
        st.stop()
    
    # Sidebar filters
    with st.sidebar:
        st.subheader("🔍 Fundamental Filters")
        
        st.markdown("### Profitability")
        min_profit_margin = st.slider("Min Profit Margin (%)", 0, 50, 5, 5)
        min_roe = st.slider("Min ROE (%)", 0, 50, 5, 5)

        st.markdown("### Debt")
        max_debt_equity = st.slider("Max Debt/Equity", 0.0, 5.0, 2.0, 0.5)

        st.markdown("### Liquidity")
        min_current_ratio = st.slider("Min Current Ratio", 0.0, 3.0, 0.5, 0.5)

        st.markdown("### Quality Score")
        min_score = st.slider("Min Fundamental Score", 0, 100, 40, 10)

        st.markdown("---")

        st.markdown("### Price Range")
        col1, col2 = st.columns(2)
        with col1:
            min_price = st.number_input("Min Price ($)", 0.0, 1000.0, 10.0, 5.0)
        with col2:
            max_price = st.number_input("Max Price ($)", 0.0, 10000.0, 60.0, 10.0)

        st.markdown("---")

        st.markdown("### Stock Universe")
        use_watchlist = st.checkbox("Scan Watchlist Only", value=False)

        st.markdown("**Options:**")
        st.markdown("- ✅ **Unchecked** = Scan 275 quality stocks (S&P 500 + NASDAQ 100)")
        st.markdown("- 📋 **Checked** = Scan only your watchlist")

        # Watchlist selector if multiple exist
        selected_watchlist_name = None
        if use_watchlist:
            if hasattr(st, 'session_state') and 'watchlists' in st.session_state:
                all_watchlists = st.session_state.watchlists
                if all_watchlists and len(all_watchlists) > 1:
                    selected_watchlist_name = st.selectbox(
                        "Select watchlist:",
                        options=list(all_watchlists.keys()),
                        index=0
                    )

        if not use_watchlist:
            max_stocks = st.number_input("Max Stocks to Scan", 50, 500, 275, 25)
            st.caption("💡 Tip: 275 = scan all quality stocks, 100 = faster scan")
        else:
            max_stocks = None  # No limit for watchlist

        run_scan = st.button("🚀 Run Fundamental Scan", use_container_width=True)

    # Main content
    if run_scan:
        try:
            st.info(f"🚀 Starting scan... (Watchlist mode: {use_watchlist}, Max stocks: {max_stocks})")

            with st.spinner("🔍 Scanning for quality stocks..."):
                results = run_fundamental_scan(
                    TIINGO_TOKEN,
                    min_profit_margin,
                    min_roe,
                    max_debt_equity,
                    min_current_ratio,
                    min_score,
                    use_watchlist,
                    min_price=min_price,
                    max_price=max_price,
                    max_stocks=max_stocks,
                    selected_watchlist=selected_watchlist_name
                )

            if results:
                st.success(f"✅ Found {len(results)} stocks matching your criteria!")

                # Display results
                display_results(results)
            else:
                st.warning("No stocks found matching your criteria. Try relaxing the filters.")

        except Exception as e:
            st.error(f"❌ Error running scan: {e}")
            import traceback
            st.code(traceback.format_exc())
    else:
        # Show instructions
        st.info("👈 Set your filters in the sidebar and click 'Run Fundamental Scan'")
        
        st.markdown("""
        ### 📊 What This Scanner Does
        
        **Finds quality stocks based on fundamental metrics:**
        
        - **Profitability**: Profit margin, ROE (Return on Equity)
        - **Debt Levels**: Debt/Equity ratio
        - **Liquidity**: Current ratio (ability to pay short-term debts)
        - **Quality Score**: Overall fundamental health (0-100)
        
        ### 🎯 Recommended Settings

        **🔍 Find ANY Profitable Stock** (Most Results):
        - Profit Margin: **0%**
        - ROE: **0%**
        - Debt/Equity: **5.0**
        - Current Ratio: **0.0**
        - Score: **0**
        - **Expected:** 50-100 stocks

        **⚡ Good Companies** (Recommended - DEFAULT):
        - Profit Margin: **5%**
        - ROE: **5%**
        - Debt/Equity: **2.0**
        - Current Ratio: **0.5**
        - Score: **40**
        - **Expected:** 30-50 stocks

        **💎 Quality Companies** (Strict):
        - Profit Margin: **10%**
        - ROE: **12%**
        - Debt/Equity: **1.0**
        - Current Ratio: **1.0**
        - Score: **60**
        - **Expected:** 10-20 stocks

        **🏆 Elite Companies** (Very Strict):
        - Profit Margin: **15%**
        - ROE: **15%**
        - Debt/Equity: **0.5**
        - Current Ratio: **1.5**
        - Score: **70**
        - **Expected:** 5-10 stocks
        """)


def run_fundamental_scan(
    token: str,
    min_profit_margin: float,
    min_roe: float,
    max_debt_equity: float,
    min_current_ratio: float,
    min_score: int,
    use_watchlist: bool,
    max_stocks: int = None,
    selected_watchlist: str = None
) -> list:
    """
    Run the fundamental scan and return matching stocks.
    """
    results = []
    
    # Get stock universe
    if use_watchlist:
        # Use selected watchlist if specified
        if selected_watchlist and hasattr(st, 'session_state') and 'watchlists' in st.session_state:
            tickers = st.session_state.watchlists.get(selected_watchlist, [])
        else:
            tickers = load_watchlist()

        if not tickers:
            st.warning("Your watchlist is empty! Add stocks to watchlist first.")
            return []
    else:
        # Use the quality universe (275 stocks) instead of broken Tiingo search
        universe_path = Path("utils/filtered_universe.json")

        try:
            if universe_path.exists():
                with open(universe_path, 'r') as f:
                    universe_data = json.load(f)
                all_tickers = [t["ticker"] for t in universe_data.get("tickers", [])]
                st.info(f"📊 Using quality universe: {len(all_tickers)} stocks (S&P 500 + NASDAQ 100 + popular stocks)")
            else:
                # Fallback to Tiingo search (but it's broken)
                st.warning("⚠️ Quality universe not found. Using Tiingo search (may miss major stocks)...")
                all_tickers = tiingo_all_us_tickers(token)
        except Exception as e:
            st.error(f"❌ Error loading ticker universe: {e}")
            return []

        if not all_tickers:
            st.error("Could not fetch ticker list")
            return []

        # Limit to max_stocks if specified
        if max_stocks and max_stocks < len(all_tickers):
            tickers = all_tickers[:max_stocks]
            st.info(f"🎯 Scanning first {len(tickers)} stocks from universe")
        else:
            tickers = all_tickers
            st.info(f"🎯 Scanning all {len(tickers)} stocks")
    
    # Progress bar
    progress = st.progress(0)
    status = st.empty()

    total = len(tickers)
    results = []
    scanned = 0
    errors = 0

    for i, ticker in enumerate(tickers):
        try:
            status.text(f"Scanning {ticker}... ({i+1}/{total}) - Found: {len(results)}, Errors: {errors}")
            progress.progress((i + 1) / total)

            # Get fundamentals
            fundamentals = get_fundamentals(ticker, token)

            if not fundamentals or not fundamentals.get("quarterly"):
                errors += 1
                continue

            scanned += 1
            
            # Extract metrics
            metrics = extract_key_metrics(fundamentals)
            
            if not metrics:
                continue
            
            # Calculate score
            score_data = calculate_fundamental_score(fundamentals)
            
            # Apply filters
            if metrics.get("profit_margin", 0) < min_profit_margin:
                continue
            
            if metrics.get("roe", 0) < min_roe:
                continue
            
            if metrics.get("debt_to_equity", 999) > max_debt_equity:
                continue
            
            if metrics.get("current_ratio", 0) < min_current_ratio:
                continue
            
            if score_data["score"] < min_score:
                continue
            
            # Passed all filters!
            results.append({
                "ticker": ticker,
                "score": score_data["score"],
                "grade": score_data["grade"],
                "profit_margin": metrics.get("profit_margin", 0),
                "roe": metrics.get("roe", 0),
                "debt_equity": metrics.get("debt_to_equity", 0),
                "current_ratio": metrics.get("current_ratio", 0),
                "revenue": metrics.get("revenue", 0),
                "net_income": metrics.get("net_income", 0),
                "details": score_data["details"]
            })
            
        except Exception as e:
            errors += 1
            continue

    progress.empty()
    status.empty()

    # Show scan summary
    st.info(f"📊 Scan Complete: Checked {total} tickers, Successfully scanned {scanned}, Found {len(results)} matches, Errors: {errors}")

    # Sort by score (highest first)
    results.sort(key=lambda x: x["score"], reverse=True)

    return results


def display_results(results: list):
    """Display scan results in a nice format."""
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Stocks", len(results))
    
    with col2:
        avg_score = sum(r["score"] for r in results) / len(results)
        st.metric("Avg Score", f"{avg_score:.0f}")
    
    with col3:
        a_grade = len([r for r in results if r["grade"] == "A"])
        st.metric("A-Grade Stocks", a_grade)
    
    with col4:
        avg_roe = sum(r["roe"] for r in results) / len(results)
        st.metric("Avg ROE", f"{avg_roe:.1f}%")
    
    st.divider()
    
    # Results table
    df = pd.DataFrame(results)
    
    # Format for display
    display_df = pd.DataFrame({
        "Ticker": df["ticker"],
        "Score": df["score"],
        "Grade": df["grade"],
        "Profit %": df["profit_margin"].round(1),
        "ROE %": df["roe"].round(1),
        "D/E": df["debt_equity"].round(2),
        "Current": df["current_ratio"].round(2),
        "Revenue": df["revenue"].apply(format_large_number),
    })
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )
    
    # Detailed view
    st.divider()
    st.subheader("📋 Detailed Analysis")
    
    selected_ticker = st.selectbox(
        "Select a stock for detailed view:",
        options=df["ticker"].tolist()
    )
    
    if selected_ticker:
        stock_data = next(r for r in results if r["ticker"] == selected_ticker)
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown(f"### {selected_ticker}")
            st.markdown(f"**Fundamental Score**: {stock_data['score']}/100 (Grade: {stock_data['grade']})")
            
            st.markdown("#### Key Metrics")
            st.markdown(f"- **Profit Margin**: {stock_data['profit_margin']:.1f}%")
            st.markdown(f"- **ROE**: {stock_data['roe']:.1f}%")
            st.markdown(f"- **Debt/Equity**: {stock_data['debt_equity']:.2f}")
            st.markdown(f"- **Current Ratio**: {stock_data['current_ratio']:.2f}")
        
        with col_b:
            st.markdown("#### Score Breakdown")
            for detail in stock_data["details"]:
                st.markdown(f"- {detail}")
        
        # Add to watchlist button
        if st.button(f"➕ Add {selected_ticker} to Watchlist"):
            from utils.storage import save_json
            watchlist = load_json("data/watchlist.json") or []
            if selected_ticker not in watchlist:
                watchlist.append(selected_ticker)
                save_json(watchlist, "data/watchlist.json")  # Fixed: data first, then path
                st.success(f"✅ Added {selected_ticker} to watchlist!")
            else:
                st.info(f"{selected_ticker} is already in your watchlist")


if __name__ == "__main__":
    show_fundamentals_scanner()

