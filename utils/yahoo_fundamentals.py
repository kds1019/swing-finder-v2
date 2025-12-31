"""
Yahoo Finance Fundamentals Integration
Fetch and analyze fundamental data for stocks using yfinance
"""

import yfinance as yf
import streamlit as st
from typing import Dict, Any, Optional


@st.cache_data(ttl=86400, show_spinner=False)  # Cache for 24 hours
def get_yahoo_fundamentals(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fetch fundamental data for a ticker from Yahoo Finance.
    Returns key financial metrics.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Check if we got valid data
        if not info or 'marketCap' not in info:
            return None
        
        return {
            "market_cap": info.get('marketCap', 0),
            "revenue": info.get('totalRevenue', 0),
            "net_income": info.get('netIncomeToCommon', 0),
            "total_debt": info.get('totalDebt', 0),
            "total_equity": info.get('totalStockholderEquity', 0),
            "current_assets": info.get('totalCurrentAssets', 0),
            "current_liabilities": info.get('totalCurrentLiabilities', 0),
            "current_ratio": info.get('currentRatio', 0),
            "profit_margin": info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0,
            "roe": info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0,
            "debt_to_equity": info.get('debtToEquity', 0),
        }
        
    except Exception as e:
        return None


def calculate_yahoo_fundamental_score(fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate a fundamental quality score (0-100) based on key metrics from Yahoo Finance.
    Higher score = better fundamentals
    """
    if not fundamentals:
        return {"score": 0, "grade": "N/A", "details": ["No fundamental data available"]}
    
    score = 0
    details = []
    
    try:
        # Profitability (30 points) - Profit Margin
        profit_margin = fundamentals.get("profit_margin", 0)
        if profit_margin > 20:
            score += 30
            details.append(f"✅ Excellent profit margin: {profit_margin:.1f}%")
        elif profit_margin > 10:
            score += 20
            details.append(f"✅ Good profit margin: {profit_margin:.1f}%")
        elif profit_margin > 0:
            score += 10
            details.append(f"⚠️ Low profit margin: {profit_margin:.1f}%")
        else:
            details.append(f"❌ Negative profit margin: {profit_margin:.1f}%")
        
        # Debt levels (25 points) - Debt to Equity
        debt_to_equity = fundamentals.get("debt_to_equity", 0)
        if debt_to_equity == 0:
            # No debt data available, give neutral score
            score += 12
            details.append(f"⚠️ Debt/Equity data unavailable")
        elif debt_to_equity < 30:
            score += 25
            details.append(f"✅ Low debt: D/E = {debt_to_equity:.1f}%")
        elif debt_to_equity < 70:
            score += 15
            details.append(f"✅ Moderate debt: D/E = {debt_to_equity:.1f}%")
        elif debt_to_equity < 150:
            score += 5
            details.append(f"⚠️ High debt: D/E = {debt_to_equity:.1f}%")
        else:
            details.append(f"❌ Very high debt: D/E = {debt_to_equity:.1f}%")
        
        # Liquidity (20 points) - Current Ratio
        current_ratio = fundamentals.get("current_ratio", 0)
        if current_ratio > 2:
            score += 20
            details.append(f"✅ Strong liquidity: Current ratio = {current_ratio:.2f}")
        elif current_ratio > 1:
            score += 10
            details.append(f"✅ Adequate liquidity: Current ratio = {current_ratio:.2f}")
        elif current_ratio > 0:
            details.append(f"❌ Poor liquidity: Current ratio = {current_ratio:.2f}")
        else:
            details.append(f"⚠️ Liquidity data unavailable")
        
        # Return on Equity (25 points)
        roe = fundamentals.get("roe", 0)
        if roe > 20:
            score += 25
            details.append(f"✅ Excellent ROE: {roe:.1f}%")
        elif roe > 15:
            score += 15
            details.append(f"✅ Good ROE: {roe:.1f}%")
        elif roe > 10:
            score += 10
            details.append(f"⚠️ Moderate ROE: {roe:.1f}%")
        elif roe > 0:
            score += 5
            details.append(f"⚠️ Low ROE: {roe:.1f}%")
        else:
            details.append(f"❌ Negative/No ROE: {roe:.1f}%")
        
    except Exception as e:
        details.append(f"⚠️ Error calculating metrics: {str(e)[:50]}")
    
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

