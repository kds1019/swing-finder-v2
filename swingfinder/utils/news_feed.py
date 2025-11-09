"""
Real-Time News Feed using Tiingo News API
Fetch and analyze news with sentiment for watchlist stocks
"""

import requests
import pandas as pd
import streamlit as st
from typing import List, Dict, Any
from datetime import datetime, timedelta


@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes
def get_news_for_ticker(ticker: str, token: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch latest news for a specific ticker from Tiingo.
    """
    try:
        url = f"https://api.tiingo.com/tiingo/news"
        headers = {"Authorization": f"Token {token}"}
        params = {
            "tickers": ticker.upper(),
            "limit": limit,
            "sortBy": "publishedDate"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            return []
        
        news = response.json()
        return news
        
    except Exception as e:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_news_for_watchlist(tickers: List[str], token: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch latest news for multiple tickers (watchlist).
    """
    try:
        url = f"https://api.tiingo.com/tiingo/news"
        headers = {"Authorization": f"Token {token}"}
        params = {
            "tickers": ",".join([t.upper() for t in tickers]),
            "limit": limit,
            "sortBy": "publishedDate"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            return []
        
        news = response.json()
        return news
        
    except Exception as e:
        return []


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze sentiment of news text using TextBlob.
    Returns sentiment score and label.
    """
    try:
        from textblob import TextBlob
        
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        
        # Classify sentiment
        if polarity > 0.1:
            label = "Bullish"
            emoji = "🟢"
            color = "green"
        elif polarity < -0.1:
            label = "Bearish"
            emoji = "🔴"
            color = "red"
        else:
            label = "Neutral"
            emoji = "⚪"
            color = "gray"
        
        return {
            "score": round(polarity, 2),
            "label": label,
            "emoji": emoji,
            "color": color
        }
        
    except Exception as e:
        return {
            "score": 0,
            "label": "Unknown",
            "emoji": "⚪",
            "color": "gray"
        }


def format_news_time(published_date: str) -> str:
    """
    Format news timestamp to relative time (e.g., "2 hours ago").
    """
    try:
        # Parse ISO format
        news_time = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
        now = datetime.now(news_time.tzinfo)
        
        diff = now - news_time
        
        if diff.days > 0:
            if diff.days == 1:
                return "1 day ago"
            else:
                return f"{diff.days} days ago"
        
        hours = diff.seconds // 3600
        if hours > 0:
            if hours == 1:
                return "1 hour ago"
            else:
                return f"{hours} hours ago"
        
        minutes = diff.seconds // 60
        if minutes > 0:
            if minutes == 1:
                return "1 minute ago"
            else:
                return f"{minutes} minutes ago"
        
        return "Just now"
        
    except Exception as e:
        return "Unknown"


def extract_tickers_from_news(news_item: Dict[str, Any]) -> List[str]:
    """
    Extract ticker symbols from news item.
    """
    tickers = news_item.get("tickers", [])
    if isinstance(tickers, list):
        return tickers
    return []


def categorize_news(title: str, description: str) -> str:
    """
    Categorize news by type (earnings, merger, product, etc.).
    """
    text = (title + " " + description).lower()
    
    if any(word in text for word in ["earnings", "eps", "revenue", "profit", "quarter"]):
        return "📊 Earnings"
    elif any(word in text for word in ["merger", "acquisition", "acquire", "buyout"]):
        return "🤝 M&A"
    elif any(word in text for word in ["product", "launch", "release", "unveil"]):
        return "🚀 Product"
    elif any(word in text for word in ["lawsuit", "investigation", "sec", "fraud"]):
        return "⚖️ Legal"
    elif any(word in text for word in ["upgrade", "downgrade", "rating", "analyst"]):
        return "📈 Analyst"
    elif any(word in text for word in ["ceo", "executive", "resign", "appoint"]):
        return "👔 Management"
    else:
        return "📰 General"


def get_news_summary(news_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for news list.
    """
    if not news_list:
        return {
            "total": 0,
            "bullish": 0,
            "bearish": 0,
            "neutral": 0,
            "avg_sentiment": 0
        }
    
    sentiments = []
    bullish = 0
    bearish = 0
    neutral = 0
    
    for news in news_list:
        title = news.get("title", "")
        description = news.get("description", "")
        text = title + " " + description
        
        sentiment = analyze_sentiment(text)
        sentiments.append(sentiment["score"])
        
        if sentiment["label"] == "Bullish":
            bullish += 1
        elif sentiment["label"] == "Bearish":
            bearish += 1
        else:
            neutral += 1
    
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
    
    return {
        "total": len(news_list),
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
        "avg_sentiment": round(avg_sentiment, 2)
    }


def filter_news_by_timeframe(news_list: List[Dict[str, Any]], hours: int = 24) -> List[Dict[str, Any]]:
    """
    Filter news to only include items from last N hours.
    """
    cutoff = datetime.now() - timedelta(hours=hours)
    filtered = []
    
    for news in news_list:
        try:
            published = news.get("publishedDate", "")
            news_time = datetime.fromisoformat(published.replace('Z', '+00:00'))
            
            if news_time.replace(tzinfo=None) >= cutoff:
                filtered.append(news)
        except:
            continue
    
    return filtered


def get_breaking_news(news_list: List[Dict[str, Any]], hours: int = 1) -> List[Dict[str, Any]]:
    """
    Get breaking news (last 1 hour by default).
    """
    return filter_news_by_timeframe(news_list, hours)


def format_news_card(news_item: Dict[str, Any]) -> str:
    """
    Format a news item as HTML card.
    """
    title = news_item.get("title", "No title")
    description = news_item.get("description", "")
    url = news_item.get("url", "#")
    published = news_item.get("publishedDate", "")
    source = news_item.get("source", "Unknown")
    
    # Get sentiment
    text = title + " " + description
    sentiment = analyze_sentiment(text)
    
    # Get category
    category = categorize_news(title, description)
    
    # Format time
    time_ago = format_news_time(published)
    
    # Get tickers
    tickers = extract_tickers_from_news(news_item)
    ticker_badges = " ".join([f"<span style='background:#e3f2fd;padding:2px 8px;border-radius:4px;font-size:12px;'>{t}</span>" for t in tickers[:3]])
    
    card_html = f"""
    <div style='background:white;border-radius:8px;padding:16px;margin:12px 0;border-left:4px solid {sentiment["color"]};box-shadow:0 2px 4px rgba(0,0,0,0.1);'>
        <div style='display:flex;justify-content:space-between;align-items:start;margin-bottom:8px;'>
            <div style='flex:1;'>
                <div style='font-size:12px;color:#666;margin-bottom:4px;'>
                    {category} • {source} • {time_ago}
                </div>
                <h4 style='margin:0 0 8px 0;color:#333;'>
                    <a href='{url}' target='_blank' style='color:#0066cc;text-decoration:none;'>{title}</a>
                </h4>
                <p style='margin:0 0 8px 0;color:#666;font-size:14px;'>{description[:200]}...</p>
                <div style='display:flex;gap:8px;align-items:center;'>
                    {ticker_badges}
                </div>
            </div>
            <div style='margin-left:16px;text-align:center;'>
                <div style='font-size:24px;'>{sentiment["emoji"]}</div>
                <div style='font-size:12px;color:{sentiment["color"]};font-weight:600;'>{sentiment["label"]}</div>
            </div>
        </div>
    </div>
    """
    
    return card_html

