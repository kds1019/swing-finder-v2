"""
Relative Strength Analysis
Find strongest stocks vs market and sector
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import List, Dict, Any
from utils.tiingo_api import tiingo_history


@st.cache_data(ttl=3600, show_spinner=False)
def calculate_relative_strength_rank(ticker: str, spy_df: pd.DataFrame, token: str, period: int = 60) -> Dict[str, Any]:
    """
    Calculate relative strength vs SPY over specified period.
    Returns RS rank and performance metrics.
    """
    try:
        # Get ticker data
        ticker_df = tiingo_history(ticker, token, period + 10)
        
        if ticker_df is None or len(ticker_df) < period:
            return None
        
        # Align dataframes
        ticker_recent = ticker_df.tail(period)
        spy_recent = spy_df.tail(period)
        
        # Calculate returns
        ticker_return = (ticker_recent["Close"].iloc[-1] / ticker_recent["Close"].iloc[0] - 1) * 100
        spy_return = (spy_recent["Close"].iloc[-1] / spy_recent["Close"].iloc[0] - 1) * 100
        
        # Relative strength
        rs_ratio = ticker_return - spy_return
        
        # Calculate momentum (last 20 days vs previous 40 days)
        if len(ticker_recent) >= 60:
            recent_20 = ticker_recent.tail(20)
            previous_40 = ticker_recent.iloc[-60:-20]
            
            recent_return = (recent_20["Close"].iloc[-1] / recent_20["Close"].iloc[0] - 1) * 100
            previous_return = (previous_40["Close"].iloc[-1] / previous_40["Close"].iloc[0] - 1) * 100
            
            momentum = recent_return - previous_return
        else:
            momentum = 0
        
        # Classify strength
        if rs_ratio > 10:
            strength = "Very Strong"
            emoji = "🔥"
            color = "darkgreen"
        elif rs_ratio > 5:
            strength = "Strong"
            emoji = "💪"
            color = "green"
        elif rs_ratio > 0:
            strength = "Above Market"
            emoji = "✅"
            color = "lightgreen"
        elif rs_ratio > -5:
            strength = "Below Market"
            emoji = "⚠️"
            color = "orange"
        else:
            strength = "Weak"
            emoji = "❌"
            color = "red"
        
        return {
            "ticker": ticker,
            "ticker_return": round(ticker_return, 2),
            "spy_return": round(spy_return, 2),
            "rs_ratio": round(rs_ratio, 2),
            "momentum": round(momentum, 2),
            "strength": strength,
            "emoji": emoji,
            "color": color
        }
        
    except Exception as e:
        return None


def rank_watchlist_by_strength(watchlist: List[str], token: str, period: int = 60) -> List[Dict[str, Any]]:
    """
    Rank all watchlist stocks by relative strength.
    """
    # Get SPY data
    spy_df = tiingo_history("SPY", token, period + 10)
    
    if spy_df is None:
        return []
    
    results = []
    
    for ticker in watchlist:
        rs_data = calculate_relative_strength_rank(ticker, spy_df, token, period)
        if rs_data:
            results.append(rs_data)
    
    # Sort by RS ratio (highest first)
    results.sort(key=lambda x: x["rs_ratio"], reverse=True)
    
    return results


def get_top_performers(watchlist: List[str], token: str, period: int = 60, top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Get top N performing stocks from watchlist.
    """
    ranked = rank_watchlist_by_strength(watchlist, token, period)
    return ranked[:top_n]


def get_bottom_performers(watchlist: List[str], token: str, period: int = 60, bottom_n: int = 10) -> List[Dict[str, Any]]:
    """
    Get bottom N performing stocks from watchlist.
    """
    ranked = rank_watchlist_by_strength(watchlist, token, period)
    return ranked[-bottom_n:]


def calculate_rs_score(rs_ratio: float, momentum: float) -> int:
    """
    Calculate RS score (0-100) based on relative strength and momentum.
    """
    # RS ratio component (0-60 points)
    if rs_ratio > 20:
        rs_points = 60
    elif rs_ratio > 10:
        rs_points = 50
    elif rs_ratio > 5:
        rs_points = 40
    elif rs_ratio > 0:
        rs_points = 30
    elif rs_ratio > -5:
        rs_points = 20
    else:
        rs_points = 10
    
    # Momentum component (0-40 points)
    if momentum > 10:
        momentum_points = 40
    elif momentum > 5:
        momentum_points = 30
    elif momentum > 0:
        momentum_points = 20
    elif momentum > -5:
        momentum_points = 10
    else:
        momentum_points = 0
    
    return rs_points + momentum_points


def format_rs_table(rs_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Format RS data as DataFrame for display.
    """
    if not rs_data:
        return pd.DataFrame()
    
    data = []
    
    for item in rs_data:
        rs_score = calculate_rs_score(item["rs_ratio"], item["momentum"])
        
        data.append({
            "Ticker": item["ticker"],
            "RS Ratio": f"{item['rs_ratio']:+.1f}%",
            "Ticker Return": f"{item['ticker_return']:+.1f}%",
            "SPY Return": f"{item['spy_return']:+.1f}%",
            "Momentum": f"{item['momentum']:+.1f}%",
            "RS Score": rs_score,
            "Strength": f"{item['emoji']} {item['strength']}"
        })
    
    return pd.DataFrame(data)


@st.cache_data(ttl=3600, show_spinner=False)
def get_multi_timeframe_strength(ticker: str, token: str) -> Dict[str, Any]:
    """
    Calculate relative strength across multiple timeframes.
    """
    spy_df = tiingo_history("SPY", token, 250)
    
    if spy_df is None:
        return None
    
    timeframes = {
        "1_week": 5,
        "1_month": 20,
        "3_months": 60,
        "6_months": 120,
        "1_year": 250
    }
    
    results = {}
    
    for name, period in timeframes.items():
        rs_data = calculate_relative_strength_rank(ticker, spy_df, token, period)
        if rs_data:
            results[name] = {
                "rs_ratio": rs_data["rs_ratio"],
                "strength": rs_data["strength"],
                "emoji": rs_data["emoji"]
            }
    
    return results


def analyze_strength_trend(multi_tf_data: Dict[str, Any]) -> str:
    """
    Analyze if strength is improving or deteriorating across timeframes.
    """
    if not multi_tf_data:
        return "Unknown"
    
    # Get RS ratios in order (short to long term)
    timeframes = ["1_week", "1_month", "3_months", "6_months", "1_year"]
    rs_values = [multi_tf_data.get(tf, {}).get("rs_ratio", 0) for tf in timeframes if tf in multi_tf_data]
    
    if len(rs_values) < 3:
        return "Insufficient data"
    
    # Check if improving (short-term > long-term)
    short_term_avg = sum(rs_values[:2]) / 2 if len(rs_values) >= 2 else rs_values[0]
    long_term_avg = sum(rs_values[-2:]) / 2 if len(rs_values) >= 2 else rs_values[-1]
    
    if short_term_avg > long_term_avg + 5:
        return "🚀 Accelerating (Getting Stronger)"
    elif short_term_avg > long_term_avg:
        return "📈 Improving"
    elif short_term_avg < long_term_avg - 5:
        return "📉 Decelerating (Getting Weaker)"
    elif short_term_avg < long_term_avg:
        return "⚠️ Weakening"
    else:
        return "➡️ Stable"

