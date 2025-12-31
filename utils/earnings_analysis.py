"""
Earnings Analysis Module
Track earnings history, beat rates, and post-earnings moves
"""

import requests
import pandas as pd
import streamlit as st
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


@st.cache_data(ttl=86400, show_spinner=False)  # Cache for 24 hours
def get_earnings_history(ticker: str, token: str) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch earnings history from Tiingo fundamentals API.
    """
    try:
        # Get fundamental statements which include earnings data
        url = f"https://api.tiingo.com/tiingo/fundamentals/{ticker.lower()}/statements"
        headers = {"Authorization": f"Token {token}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        # Filter for quarterly data (earnings reports)
        quarterly_data = [d for d in data if d.get('quarter')]
        
        # Sort by date (most recent first)
        quarterly_data.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return quarterly_data[:8]  # Last 8 quarters (2 years)
        
    except Exception as e:
        return None


def analyze_earnings_performance(earnings_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze earnings performance metrics.
    """
    if not earnings_history or len(earnings_history) < 2:
        return {
            "beat_rate": 0,
            "total_reports": 0,
            "beats": 0,
            "misses": 0,
            "meets": 0,
            "avg_surprise": 0,
            "revenue_growth": 0,
            "earnings_growth": 0
        }
    
    total = len(earnings_history)
    beats = 0
    misses = 0
    meets = 0
    
    # Calculate revenue and earnings growth
    latest = earnings_history[0]
    year_ago = earnings_history[4] if len(earnings_history) > 4 else earnings_history[-1]
    
    latest_revenue = latest.get('revenue', 0)
    year_ago_revenue = year_ago.get('revenue', 1)
    revenue_growth = ((latest_revenue - year_ago_revenue) / year_ago_revenue * 100) if year_ago_revenue else 0
    
    latest_earnings = latest.get('netIncome', 0)
    year_ago_earnings = year_ago.get('netIncome', 1)
    earnings_growth = ((latest_earnings - year_ago_earnings) / year_ago_earnings * 100) if year_ago_earnings else 0
    
    # Note: We don't have actual vs estimate data from Tiingo fundamentals API
    # This is a simplified version - in production you'd use a dedicated earnings API
    
    return {
        "beat_rate": 0,  # Would need earnings estimates API
        "total_reports": total,
        "beats": beats,
        "misses": misses,
        "meets": meets,
        "avg_surprise": 0,
        "revenue_growth": round(revenue_growth, 1),
        "earnings_growth": round(earnings_growth, 1),
        "latest_revenue": latest_revenue,
        "latest_earnings": latest_earnings
    }


def get_upcoming_earnings_calendar(watchlist: List[str], token: str) -> List[Dict[str, Any]]:
    """
    Get upcoming earnings for watchlist stocks.
    """
    from utils.tiingo_api import get_next_earnings_date

    if not watchlist:
        return []

    upcoming = []

    for ticker in watchlist:
        try:
            earnings_date = get_next_earnings_date(ticker, token)
            if earnings_date and earnings_date != "N/A":
                # Parse date
                try:
                    date_obj = datetime.strptime(earnings_date, "%Y-%m-%d")
                    days_until = (date_obj - datetime.now()).days
                    
                    if days_until >= 0 and days_until <= 30:  # Next 30 days
                        upcoming.append({
                            "ticker": ticker,
                            "date": earnings_date,
                            "days_until": days_until
                        })
                except:
                    pass
        except:
            continue
    
    # Sort by date
    upcoming.sort(key=lambda x: x["days_until"])
    
    return upcoming


def calculate_earnings_quality_score(earnings_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate earnings quality score based on consistency and growth.
    """
    if not earnings_history or len(earnings_history) < 4:
        return {"score": 0, "grade": "N/A", "details": []}
    
    score = 0
    details = []
    
    # Check revenue growth consistency (30 points)
    revenues = [e.get('revenue', 0) for e in earnings_history[:4]]
    revenue_growth_rates = []
    
    for i in range(len(revenues) - 1):
        if revenues[i+1] > 0:
            growth = ((revenues[i] - revenues[i+1]) / revenues[i+1]) * 100
            revenue_growth_rates.append(growth)
    
    if revenue_growth_rates:
        avg_revenue_growth = sum(revenue_growth_rates) / len(revenue_growth_rates)
        
        if avg_revenue_growth > 15:
            score += 30
            details.append(f"✅ Strong revenue growth: {avg_revenue_growth:.1f}%")
        elif avg_revenue_growth > 5:
            score += 20
            details.append(f"✅ Moderate revenue growth: {avg_revenue_growth:.1f}%")
        elif avg_revenue_growth > 0:
            score += 10
            details.append(f"⚠️ Slow revenue growth: {avg_revenue_growth:.1f}%")
        else:
            details.append(f"❌ Declining revenue: {avg_revenue_growth:.1f}%")
    
    # Check profitability trend (30 points)
    net_incomes = [e.get('netIncome', 0) for e in earnings_history[:4]]
    profitable_quarters = sum(1 for ni in net_incomes if ni > 0)
    
    if profitable_quarters == 4:
        score += 30
        details.append("✅ Profitable in all recent quarters")
    elif profitable_quarters >= 3:
        score += 20
        details.append("✅ Mostly profitable")
    elif profitable_quarters >= 2:
        score += 10
        details.append("⚠️ Inconsistent profitability")
    else:
        details.append("❌ Mostly unprofitable")
    
    # Check earnings growth (40 points)
    if len(net_incomes) >= 4 and net_incomes[-1] > 0:
        earnings_growth = ((net_incomes[0] - net_incomes[-1]) / abs(net_incomes[-1])) * 100
        
        if earnings_growth > 20:
            score += 40
            details.append(f"✅ Excellent earnings growth: {earnings_growth:.1f}%")
        elif earnings_growth > 10:
            score += 30
            details.append(f"✅ Good earnings growth: {earnings_growth:.1f}%")
        elif earnings_growth > 0:
            score += 20
            details.append(f"⚠️ Modest earnings growth: {earnings_growth:.1f}%")
        else:
            score += 10
            details.append(f"❌ Declining earnings: {earnings_growth:.1f}%")
    
    # Determine grade
    if score >= 80:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 50:
        grade = "D"
    else:
        grade = "F"
    
    return {
        "score": score,
        "grade": grade,
        "details": details
    }


def format_earnings_table(earnings_history: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Format earnings history as a DataFrame for display.
    """
    if not earnings_history:
        return pd.DataFrame()
    
    data = []
    
    for e in earnings_history:
        quarter = e.get('quarter', 0)
        year = e.get('year', 0)
        revenue = e.get('revenue', 0)
        net_income = e.get('netIncome', 0)
        
        # Calculate margins
        profit_margin = (net_income / revenue * 100) if revenue > 0 else 0
        
        data.append({
            "Quarter": f"Q{quarter} {year}",
            "Revenue": f"${revenue/1e9:.2f}B" if revenue > 1e9 else f"${revenue/1e6:.2f}M",
            "Net Income": f"${net_income/1e9:.2f}B" if abs(net_income) > 1e9 else f"${net_income/1e6:.2f}M",
            "Profit Margin": f"{profit_margin:.1f}%"
        })
    
    return pd.DataFrame(data)


def get_earnings_risk_level(days_until_earnings: int) -> str:
    """
    Determine risk level based on proximity to earnings.
    """
    if days_until_earnings < 0:
        return "✅ Safe (No earnings soon)"
    elif days_until_earnings <= 3:
        return "🔴 High Risk (Earnings in 3 days)"
    elif days_until_earnings <= 7:
        return "🟡 Medium Risk (Earnings this week)"
    elif days_until_earnings <= 14:
        return "⚠️ Caution (Earnings in 2 weeks)"
    else:
        return "✅ Safe (Earnings 2+ weeks away)"

