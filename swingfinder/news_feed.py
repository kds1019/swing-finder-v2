"""
Real-Time News Feed Page
Breaking news with sentiment analysis for watchlist stocks
"""

import streamlit as st
from utils.news_feed import (
    get_news_for_ticker, get_news_for_watchlist, get_news_summary,
    filter_news_by_timeframe, get_breaking_news, format_news_card,
    analyze_sentiment
)
from utils.storage import load_json, load_watchlist


def show_news_feed():
    """Main news feed page."""
    
    st.title("📰 Real-Time News Feed")
    st.markdown("**Breaking news with sentiment analysis for your watchlist**")
    
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
        st.warning("⚠️ Your watchlist is empty! Add stocks to see news.")
        st.info("👈 Go to Scanner → Watchlist Management → Add stocks")
        st.stop()
    
    # Sidebar filters
    with st.sidebar:
        st.subheader("🔍 News Filters")
        
        # Ticker selection
        selected_tickers = st.multiselect(
            "Select Tickers",
            options=watchlist,
            default=watchlist[:5] if len(watchlist) > 5 else watchlist
        )
        
        # Timeframe
        timeframe = st.selectbox(
            "Timeframe",
            ["Last Hour", "Last 4 Hours", "Last 24 Hours", "Last 3 Days", "Last Week"],
            index=2
        )
        
        timeframe_hours = {
            "Last Hour": 1,
            "Last 4 Hours": 4,
            "Last 24 Hours": 24,
            "Last 3 Days": 72,
            "Last Week": 168
        }
        
        hours = timeframe_hours[timeframe]
        
        # Sentiment filter
        sentiment_filter = st.selectbox(
            "Sentiment",
            ["All", "Bullish Only", "Bearish Only", "Neutral Only"]
        )
        
        # News limit
        max_news = st.slider("Max News Items", 10, 100, 50, 10)
        
        # Refresh button
        if st.button("🔄 Refresh News", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Fetch news
    if not selected_tickers:
        st.warning("Please select at least one ticker from the sidebar")
        st.stop()
    
    with st.spinner("📡 Fetching latest news..."):
        news_list = get_news_for_watchlist(selected_tickers, TIINGO_TOKEN, limit=max_news)
    
    if not news_list:
        st.warning("No news found for selected tickers")
        st.stop()
    
    # Filter by timeframe
    filtered_news = filter_news_by_timeframe(news_list, hours)
    
    # Filter by sentiment
    if sentiment_filter != "All":
        sentiment_filtered = []
        for news in filtered_news:
            title = news.get("title", "")
            description = news.get("description", "")
            text = title + " " + description
            sentiment = analyze_sentiment(text)
            
            if sentiment_filter == "Bullish Only" and sentiment["label"] == "Bullish":
                sentiment_filtered.append(news)
            elif sentiment_filter == "Bearish Only" and sentiment["label"] == "Bearish":
                sentiment_filtered.append(news)
            elif sentiment_filter == "Neutral Only" and sentiment["label"] == "Neutral":
                sentiment_filtered.append(news)
        
        filtered_news = sentiment_filtered
    
    # Get summary
    summary = get_news_summary(filtered_news)
    
    # Display summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total News", summary["total"])
    
    with col2:
        st.metric("🟢 Bullish", summary["bullish"])
    
    with col3:
        st.metric("🔴 Bearish", summary["bearish"])
    
    with col4:
        st.metric("⚪ Neutral", summary["neutral"])
    
    with col5:
        sentiment_score = summary["avg_sentiment"]
        sentiment_label = "Bullish" if sentiment_score > 0.1 else "Bearish" if sentiment_score < -0.1 else "Neutral"
        st.metric("Avg Sentiment", sentiment_label)
    
    st.divider()
    
    # Breaking news section
    breaking = get_breaking_news(filtered_news, hours=1)
    if breaking:
        st.subheader("🚨 Breaking News (Last Hour)")
        for news in breaking[:5]:
            st.markdown(format_news_card(news), unsafe_allow_html=True)
        st.divider()
    
    # All news
    st.subheader(f"📰 All News ({timeframe})")
    
    if not filtered_news:
        st.info("No news found for selected filters")
    else:
        # Tabs for different views
        tab1, tab2 = st.tabs(["📋 Feed View", "📊 By Ticker"])
        
        with tab1:
            # Display all news as cards
            for news in filtered_news:
                st.markdown(format_news_card(news), unsafe_allow_html=True)
        
        with tab2:
            # Group news by ticker
            ticker_news = {}
            for news in filtered_news:
                tickers = news.get("tickers", [])
                for ticker in tickers:
                    if ticker in selected_tickers:
                        if ticker not in ticker_news:
                            ticker_news[ticker] = []
                        ticker_news[ticker].append(news)
            
            # Display by ticker
            for ticker in sorted(ticker_news.keys()):
                with st.expander(f"📈 {ticker} ({len(ticker_news[ticker])} news items)"):
                    ticker_summary = get_news_summary(ticker_news[ticker])
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("🟢 Bullish", ticker_summary["bullish"])
                    with col_b:
                        st.metric("🔴 Bearish", ticker_summary["bearish"])
                    with col_c:
                        st.metric("⚪ Neutral", ticker_summary["neutral"])
                    
                    st.markdown("---")
                    
                    for news in ticker_news[ticker][:10]:  # Show top 10 per ticker
                        st.markdown(format_news_card(news), unsafe_allow_html=True)


def show_news_widget(ticker: str, token: str, limit: int = 5):
    """
    Compact news widget for use in other pages (e.g., Analyzer).
    """
    news_list = get_news_for_ticker(ticker, token, limit=limit)
    
    if not news_list:
        st.info(f"No recent news for {ticker}")
        return
    
    st.markdown(f"### 📰 Latest News for {ticker}")
    
    # Summary
    summary = get_news_summary(news_list)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🟢 Bullish", summary["bullish"])
    with col2:
        st.metric("🔴 Bearish", summary["bearish"])
    with col3:
        st.metric("⚪ Neutral", summary["neutral"])
    
    st.markdown("---")
    
    # Display news
    for news in news_list:
        st.markdown(format_news_card(news), unsafe_allow_html=True)


if __name__ == "__main__":
    show_news_feed()

