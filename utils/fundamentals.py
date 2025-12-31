"""
Tiingo Fundamentals API Integration
Fetch and analyze fundamental data for stocks
"""

import requests
import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional


@st.cache_data(ttl=86400, show_spinner=False)  # Cache for 24 hours
def get_fundamentals(ticker: str, token: str) -> Optional[Dict[str, Any]]:
    """
    Fetch fundamental data for a ticker from Tiingo.
    Returns latest quarterly and annual data.
    
    API Endpoints:
    - Statements: https://api.tiingo.com/tiingo/fundamentals/{ticker}/statements
    - Daily Metrics: https://api.tiingo.com/tiingo/fundamentals/{ticker}/daily
    """
    try:
        # Get latest statements (quarterly and annual)
        url = f"https://api.tiingo.com/tiingo/fundamentals/{ticker.lower()}/statements"
        headers = {"Authorization": f"Token {token}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if not data:
            return None
        
        # Get most recent quarterly and annual data
        quarterly_data = [d for d in data if d.get('quarter')]
        annual_data = [d for d in data if d.get('year') and not d.get('quarter')]
        
        latest_quarterly = quarterly_data[0] if quarterly_data else None
        latest_annual = annual_data[0] if annual_data else None
        
        return {
            "quarterly": latest_quarterly,
            "annual": latest_annual,
            "all_data": data
        }
        
    except Exception as e:
        st.warning(f"Could not fetch fundamentals for {ticker}: {e}")
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def get_daily_metrics(ticker: str, token: str) -> Optional[pd.DataFrame]:
    """
    Fetch daily fundamental metrics (P/E, P/B, market cap, etc.)
    """
    try:
        url = f"https://api.tiingo.com/tiingo/fundamentals/{ticker.lower()}/daily"
        headers = {"Authorization": f"Token {token}"}
        params = {"startDate": "2020-01-01"}  # Get last 5 years
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if not data:
            return None
        
        df = pd.DataFrame(data)
        return df
        
    except Exception as e:
        return None


def calculate_fundamental_score(fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate a fundamental quality score (0-100) based on key metrics.
    Higher score = better fundamentals
    """
    score = 0
    max_score = 100
    details = []

    if not fundamentals or not fundamentals.get("quarterly"):
        return {"score": 0, "grade": "N/A", "details": ["No fundamental data available"]}

    quarterly = fundamentals["quarterly"]
    statement_data = quarterly.get("statementData", {})

    # Convert arrays to dictionaries
    income_statement = {item['dataCode']: item['value']
                       for item in statement_data.get('incomeStatement', [])}
    balance_sheet = {item['dataCode']: item['value']
                    for item in statement_data.get('balanceSheet', [])}

    # Extract key metrics from balance sheet and income statement
    try:
        # Profitability (30 points)
        net_income = income_statement.get("netIncComStock", 0) or income_statement.get("netinc", 0) or 0
        revenue = income_statement.get("revenue", 1) or 1
        
        if revenue > 0:
            profit_margin = (net_income / revenue) * 100
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
        
        # Debt levels (25 points)
        total_debt = balance_sheet.get("debt", 0) or 0
        total_equity = balance_sheet.get("equity", 1) or 1
        
        if total_equity > 0:
            debt_to_equity = total_debt / total_equity
            if debt_to_equity < 0.3:
                score += 25
                details.append(f"✅ Low debt: D/E = {debt_to_equity:.2f}")
            elif debt_to_equity < 0.7:
                score += 15
                details.append(f"✅ Moderate debt: D/E = {debt_to_equity:.2f}")
            elif debt_to_equity < 1.5:
                score += 5
                details.append(f"⚠️ High debt: D/E = {debt_to_equity:.2f}")
            else:
                details.append(f"❌ Very high debt: D/E = {debt_to_equity:.2f}")
        
        # Liquidity (20 points)
        current_assets = balance_sheet.get("assetsCurrent", 0) or 0
        current_liabilities = balance_sheet.get("liabilitiesCurrent", 1) or 1
        
        if current_liabilities > 0:
            current_ratio = current_assets / current_liabilities
            if current_ratio > 2:
                score += 20
                details.append(f"✅ Strong liquidity: Current ratio = {current_ratio:.2f}")
            elif current_ratio > 1:
                score += 10
                details.append(f"✅ Adequate liquidity: Current ratio = {current_ratio:.2f}")
            else:
                details.append(f"❌ Poor liquidity: Current ratio = {current_ratio:.2f}")
        
        # Return on Equity (25 points)
        if total_equity > 0 and net_income > 0:
            roe = (net_income / total_equity) * 100
            if roe > 20:
                score += 25
                details.append(f"✅ Excellent ROE: {roe:.1f}%")
            elif roe > 15:
                score += 15
                details.append(f"✅ Good ROE: {roe:.1f}%")
            elif roe > 10:
                score += 10
                details.append(f"⚠️ Moderate ROE: {roe:.1f}%")
            else:
                details.append(f"❌ Low ROE: {roe:.1f}%")
        
    except Exception as e:
        details.append(f"⚠️ Error calculating some metrics: {e}")
    
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


def extract_key_metrics(fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key financial metrics from fundamentals data.
    Tiingo returns data in statementData with arrays of {dataCode, value} objects.
    """
    if not fundamentals or not fundamentals.get("quarterly"):
        return {}

    quarterly = fundamentals["quarterly"]
    statement_data = quarterly.get("statementData", {})

    # Convert arrays to dictionaries for easy lookup
    income_statement = {item['dataCode']: item['value']
                       for item in statement_data.get('incomeStatement', [])}
    balance_sheet = {item['dataCode']: item['value']
                    for item in statement_data.get('balanceSheet', [])}
    cash_flow = {item['dataCode']: item['value']
                for item in statement_data.get('cashFlow', [])}

    metrics = {}

    try:
        # Income Statement (using correct Tiingo field names)
        metrics["revenue"] = income_statement.get("revenue", 0) or 0
        metrics["net_income"] = income_statement.get("netIncComStock", 0) or income_statement.get("netinc", 0) or 0
        metrics["gross_profit"] = income_statement.get("grossProfit", 0) or 0
        metrics["operating_income"] = income_statement.get("opinc", 0) or income_statement.get("ebit", 0) or 0

        # Balance Sheet (using correct Tiingo field names)
        metrics["total_assets"] = balance_sheet.get("totalAssets", 0) or 0
        metrics["total_liabilities"] = balance_sheet.get("totalLiabilities", 0) or 0
        metrics["total_equity"] = balance_sheet.get("equity", 0) or 0
        metrics["total_debt"] = balance_sheet.get("debt", 0) or 0
        metrics["current_assets"] = balance_sheet.get("assetsCurrent", 0) or 0
        metrics["current_liabilities"] = balance_sheet.get("liabilitiesCurrent", 0) or 0
        metrics["cash"] = balance_sheet.get("cashAndEq", 0) or 0

        # Cash Flow
        metrics["operating_cash_flow"] = cash_flow.get("ncfo", 0) or cash_flow.get("ncf", 0) or 0
        
        # Calculated Ratios
        if metrics["revenue"] > 0:
            metrics["profit_margin"] = (metrics["net_income"] / metrics["revenue"]) * 100
            metrics["gross_margin"] = (metrics["gross_profit"] / metrics["revenue"]) * 100
        else:
            metrics["profit_margin"] = 0
            metrics["gross_margin"] = 0
        
        if metrics["total_equity"] > 0:
            metrics["debt_to_equity"] = metrics["total_debt"] / metrics["total_equity"]
            metrics["roe"] = (metrics["net_income"] / metrics["total_equity"]) * 100
        else:
            metrics["debt_to_equity"] = 0
            metrics["roe"] = 0
        
        if metrics["current_liabilities"] > 0:
            metrics["current_ratio"] = metrics["current_assets"] / metrics["current_liabilities"]
        else:
            metrics["current_ratio"] = 0
        
        if metrics["total_assets"] > 0:
            metrics["roa"] = (metrics["net_income"] / metrics["total_assets"]) * 100
        else:
            metrics["roa"] = 0
        
    except Exception as e:
        pass
    
    return metrics


def format_large_number(num: float) -> str:
    """Format large numbers with B/M/K suffixes."""
    if num >= 1_000_000_000:
        return f"${num/1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"${num/1_000_000:.2f}M"
    elif num >= 1_000:
        return f"${num/1_000:.2f}K"
    else:
        return f"${num:.2f}"


def compare_to_peers(ticker: str, metric_value: float, metric_name: str) -> str:
    """
    Compare a metric to industry averages (simplified version).
    In production, you'd fetch actual peer data.
    """
    # Simplified industry averages (you can expand this)
    industry_averages = {
        "profit_margin": 10,
        "roe": 15,
        "debt_to_equity": 0.5,
        "current_ratio": 1.5
    }
    
    avg = industry_averages.get(metric_name, 0)
    
    if not avg:
        return "N/A"
    
    if metric_name in ["profit_margin", "roe", "current_ratio"]:
        # Higher is better
        if metric_value > avg * 1.2:
            return "Above Average ✅"
        elif metric_value > avg * 0.8:
            return "Average"
        else:
            return "Below Average ⚠️"
    else:
        # Lower is better (debt)
        if metric_value < avg * 0.8:
            return "Better than Average ✅"
        elif metric_value < avg * 1.2:
            return "Average"
        else:
            return "Worse than Average ⚠️"

