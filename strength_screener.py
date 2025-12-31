"""
Relative Strength Screener
Find strongest and weakest stocks in your watchlist
"""

import streamlit as st
import plotly.graph_objects as go
from utils.relative_strength import (
    rank_watchlist_by_strength, get_top_performers, get_bottom_performers,
    format_rs_table, calculate_rs_score
)
from utils.storage import load_json, load_watchlist


def show_strength_screener():
    """Main relative strength screener page."""
    
    st.title("🏆 Relative Strength Screener")
    st.markdown("**Find the strongest and weakest stocks in your watchlist**")
    
    # Get API token
    TIINGO_TOKEN = st.secrets.get("TIINGO_TOKEN", "")
    if not TIINGO_TOKEN:
        st.error("⚠️ TIINGO_TOKEN not found in secrets!")
        st.stop()
    
    # Load watchlist with selector if multiple exist
    all_watchlists = {}
    selected_watchlist_name = None

    if hasattr(st, 'session_state') and 'watchlists' in st.session_state:
        all_watchlists = st.session_state.watchlists

    if all_watchlists and len(all_watchlists) > 1:
        # Show watchlist selector in sidebar
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 📁 Watchlist")
            selected_watchlist_name = st.selectbox(
                "Select watchlist:",
                options=list(all_watchlists.keys()),
                index=0
            )
        watchlist = all_watchlists.get(selected_watchlist_name, [])
    else:
        watchlist = load_watchlist()

    if not watchlist:
        st.warning("⚠️ Your watchlist is empty! Add stocks to see relative strength.")
        st.info("👈 Go to Scanner → Watchlist Management → Add stocks")
        st.stop()
    
    # Sidebar settings
    with st.sidebar:
        st.subheader("⚙️ Settings")
        
        period = st.selectbox(
            "Timeframe",
            [("1 Month", 20), ("3 Months", 60), ("6 Months", 120), ("1 Year", 250)],
            index=1,
            format_func=lambda x: x[0]
        )[1]
        
        show_top_n = st.slider("Show Top N", 5, 20, 10)
        show_bottom_n = st.slider("Show Bottom N", 5, 20, 5)
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Rank all stocks
    with st.spinner("📊 Ranking stocks by relative strength..."):
        ranked_stocks = rank_watchlist_by_strength(watchlist, TIINGO_TOKEN, period)
    
    if not ranked_stocks:
        st.error("Could not calculate relative strength. Please try again.")
        st.stop()
    
    # Summary metrics
    st.subheader("📊 Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Stocks", len(ranked_stocks))
    
    with col2:
        strong_count = sum(1 for s in ranked_stocks if s["rs_ratio"] > 0)
        st.metric("Outperforming SPY", strong_count)
    
    with col3:
        avg_rs = sum(s["rs_ratio"] for s in ranked_stocks) / len(ranked_stocks)
        st.metric("Avg RS Ratio", f"{avg_rs:+.1f}%")
    
    with col4:
        top_stock = ranked_stocks[0]
        st.metric("Top Performer", f"{top_stock['ticker']} ({top_stock['rs_ratio']:+.1f}%)")
    
    st.divider()
    
    # Top performers
    st.subheader(f"🔥 Top {show_top_n} Performers")
    
    top_stocks = ranked_stocks[:show_top_n]
    
    # Display as cards
    for i, stock in enumerate(top_stocks, 1):
        rs_score = calculate_rs_score(stock["rs_ratio"], stock["momentum"])
        
        col_a, col_b = st.columns([3, 1])
        
        with col_a:
            st.markdown(
                f"<div style='background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);padding:16px;border-radius:10px;color:white;margin:8px 0;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<div>"
                f"<h3 style='margin:0;'>#{i} {stock['ticker']} {stock['emoji']}</h3>"
                f"<p style='margin:4px 0 0 0;font-size:14px;'>RS Ratio: {stock['rs_ratio']:+.1f}% | Momentum: {stock['momentum']:+.1f}%</p>"
                f"</div>"
                f"<div style='text-align:right;'>"
                f"<div style='font-size:24px;font-weight:bold;'>{stock['ticker_return']:+.1f}%</div>"
                f"<div style='font-size:12px;'>vs SPY: {stock['spy_return']:+.1f}%</div>"
                f"</div>"
                f"</div></div>",
                unsafe_allow_html=True
            )
        
        with col_b:
            st.markdown(
                f"<div style='background:#f8f9fa;padding:16px;border-radius:10px;text-align:center;margin:8px 0;'>"
                f"<div style='font-size:12px;color:#666;'>RS Score</div>"
                f"<div style='font-size:32px;font-weight:bold;color:#667eea;'>{rs_score}</div>"
                f"<div style='font-size:12px;color:#666;'>/100</div></div>",
                unsafe_allow_html=True
            )
    
    st.divider()
    
    # Bottom performers
    st.subheader(f"❄️ Bottom {show_bottom_n} Performers")
    
    bottom_stocks = ranked_stocks[-show_bottom_n:]
    bottom_stocks.reverse()  # Show weakest first
    
    for i, stock in enumerate(bottom_stocks, 1):
        rs_score = calculate_rs_score(stock["rs_ratio"], stock["momentum"])
        
        col_a, col_b = st.columns([3, 1])
        
        with col_a:
            st.markdown(
                f"<div style='background:linear-gradient(135deg, #f093fb 0%, #f5576c 100%);padding:16px;border-radius:10px;color:white;margin:8px 0;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<div>"
                f"<h3 style='margin:0;'>{stock['ticker']} {stock['emoji']}</h3>"
                f"<p style='margin:4px 0 0 0;font-size:14px;'>RS Ratio: {stock['rs_ratio']:+.1f}% | Momentum: {stock['momentum']:+.1f}%</p>"
                f"</div>"
                f"<div style='text-align:right;'>"
                f"<div style='font-size:24px;font-weight:bold;'>{stock['ticker_return']:+.1f}%</div>"
                f"<div style='font-size:12px;'>vs SPY: {stock['spy_return']:+.1f}%</div>"
                f"</div>"
                f"</div></div>",
                unsafe_allow_html=True
            )
        
        with col_b:
            st.markdown(
                f"<div style='background:#f8f9fa;padding:16px;border-radius:10px;text-align:center;margin:8px 0;'>"
                f"<div style='font-size:12px;color:#666;'>RS Score</div>"
                f"<div style='font-size:32px;font-weight:bold;color:#f5576c;'>{rs_score}</div>"
                f"<div style='font-size:12px;color:#666;'>/100</div></div>",
                unsafe_allow_html=True
            )
    
    st.divider()
    
    # Full table
    st.subheader("📋 Complete Rankings")
    
    rs_df = format_rs_table(ranked_stocks)
    st.dataframe(rs_df, use_container_width=True, height=400)
    
    # Chart
    st.divider()
    st.subheader("📊 RS Ratio Distribution")
    
    fig = go.Figure()
    
    tickers = [s["ticker"] for s in ranked_stocks]
    rs_ratios = [s["rs_ratio"] for s in ranked_stocks]
    colors = ['green' if r > 0 else 'red' for r in rs_ratios]
    
    fig.add_trace(go.Bar(
        x=tickers,
        y=rs_ratios,
        marker_color=colors,
        text=[f"{r:+.1f}%" for r in rs_ratios],
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Relative Strength vs SPY",
        xaxis_title="Ticker",
        yaxis_title="RS Ratio (%)",
        height=500,
        showlegend=False,
        hovermode='x'
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="SPY Baseline")
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Trading recommendations
    st.divider()
    st.subheader("💡 Trading Recommendations")
    
    col_rec1, col_rec2 = st.columns(2)
    
    with col_rec1:
        st.markdown("### ✅ Focus On (Strong RS)")
        strong_stocks = [s for s in ranked_stocks if s["rs_ratio"] > 5]
        if strong_stocks:
            for stock in strong_stocks[:5]:
                st.markdown(f"- **{stock['ticker']}**: {stock['rs_ratio']:+.1f}% RS - {stock['strength']}")
        else:
            st.info("No stocks with strong relative strength")
    
    with col_rec2:
        st.markdown("### ⚠️ Avoid (Weak RS)")
        weak_stocks = [s for s in ranked_stocks if s["rs_ratio"] < -5]
        if weak_stocks:
            for stock in weak_stocks[:5]:
                st.markdown(f"- **{stock['ticker']}**: {stock['rs_ratio']:+.1f}% RS - {stock['strength']}")
        else:
            st.info("No stocks with weak relative strength")


if __name__ == "__main__":
    show_strength_screener()

