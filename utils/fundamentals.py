"""
Tiingo Fundamentals API Integration
Fetch and analyze fundamental data for stocks
"""

import datetime as dt
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


@st.cache_data(ttl=86400, show_spinner=False)
def get_tiingo_fundamentals_for_claude(ticker: str, token: str) -> Dict[str, Any]:
    """
    Fetch combined Tiingo fundamentals suitable for passing to Claude prompts.

    Pulls TWO endpoints and merges them:
      1. /tiingo/fundamentals/<ticker>/daily  → P/E, P/B, market cap, enterprise value
      2. /tiingo/fundamentals/<ticker>/statements → revenue, net income, debt, cash, ROE, etc.

    Returns a clean flat dict (empty dict on any failure — never raises).
    Requires Tiingo Power Plan or higher.
    """
    result: Dict[str, Any] = {}

    headers = {"Authorization": f"Token {token}"}

    # ── 1. Daily metrics (most recent available) ───────────────────────────────
    try:
        start = (dt.date.today() - dt.timedelta(days=45)).isoformat()
        url = f"https://api.tiingo.com/tiingo/fundamentals/{ticker.lower()}/daily"
        r = requests.get(url, headers=headers, params={"startDate": start}, timeout=10)
        if r.ok:
            data = r.json()
            if data and isinstance(data, list):
                latest = data[-1]          # most recent row
                result["market_cap"]     = latest.get("marketCap")
                result["enterprise_val"] = latest.get("enterpriseVal")
                result["pe_ratio"]       = latest.get("peRatio")
                result["pb_ratio"]       = latest.get("pbRatio")
                result["trailing_peg"]   = latest.get("trailingPEG1Y")
    except Exception:
        pass

    # ── 2. Latest quarterly statements ────────────────────────────────────────
    try:
        url = f"https://api.tiingo.com/tiingo/fundamentals/{ticker.lower()}/statements"
        r = requests.get(url, headers=headers, timeout=10)
        if r.ok:
            data = r.json()
            if data and isinstance(data, list):
                quarterly = [d for d in data if d.get("quarter")]
                if quarterly:
                    q    = quarterly[0]          # most recent quarter
                    stmt = q.get("statementData", {})

                    income   = {item["dataCode"]: item["value"]
                                for item in stmt.get("incomeStatement", [])}
                    balance  = {item["dataCode"]: item["value"]
                                for item in stmt.get("balanceSheet", [])}
                    cashflow = {item["dataCode"]: item["value"]
                                for item in stmt.get("cashFlow", [])}

                    result["quarter"]       = f"Q{q.get('quarter')} {q.get('year')}"
                    result["revenue"]       = income.get("revenue")
                    result["gross_profit"]  = income.get("grossProfit")
                    result["net_income"]    = income.get("netIncComStock") or income.get("netinc")
                    result["eps"]           = income.get("epsdil") or income.get("eps")
                    result["total_assets"]  = balance.get("totalAssets")
                    result["total_debt"]    = balance.get("debt")
                    result["total_equity"]  = balance.get("equity")
                    result["cash"]          = balance.get("cashAndEq")
                    result["current_assets"]  = balance.get("assetsCurrent")
                    result["current_liabilities"] = balance.get("liabilitiesCurrent")
                    result["op_cash_flow"]  = cashflow.get("ncfo")
                    result["free_cash_flow"] = cashflow.get("freeCashFlow")

                    # ── Calculated ratios ──────────────────────────────────────
                    rev  = result.get("revenue") or 0
                    ni   = result.get("net_income") or 0
                    eq   = result.get("total_equity") or 0
                    debt = result.get("total_debt") or 0
                    ca   = result.get("current_assets") or 0
                    cl   = result.get("current_liabilities") or 0

                    result["profit_margin_pct"] = round(ni / rev * 100, 1) if rev else None
                    result["roe_pct"]           = round(ni / eq * 100, 1)  if eq  else None
                    result["debt_to_equity"]    = round(debt / eq, 2)      if eq  else None
                    result["current_ratio"]     = round(ca / cl, 2)        if cl  else None
                    result["gross_margin_pct"]  = (
                        round((result.get("gross_profit") or 0) / rev * 100, 1) if rev else None
                    )
    except Exception:
        pass

    return result


def format_fundamentals_for_prompt(f: Dict[str, Any]) -> str:
    """
    Format a get_tiingo_fundamentals_for_claude() result into a compact
    text block ready to drop into a Claude prompt.
    Returns empty string if no data available.
    """
    if not f:
        return ""

    def _fmt_num(v, suffix="", prefix="") -> str:
        """Format large numbers with B/M suffixes."""
        if v is None:
            return "N/A"
        try:
            v = float(v)
            if abs(v) >= 1e9:
                return f"{prefix}{v / 1e9:.2f}B{suffix}"
            if abs(v) >= 1e6:
                return f"{prefix}{v / 1e6:.1f}M{suffix}"
            return f"{prefix}{v:,.0f}{suffix}"
        except Exception:
            return "N/A"

    def _pct(v) -> str:
        return f"{v:.1f}%" if v is not None else "N/A"

    def _ratio(v) -> str:
        return f"{v:.2f}" if v is not None else "N/A"

    lines = [f"=== FUNDAMENTALS ({f.get('quarter', 'Latest')}) ==="]
    lines.append(
        f"Market Cap: {_fmt_num(f.get('market_cap'), prefix='$')}"
        f" | P/E: {_ratio(f.get('pe_ratio'))}"
        f" | P/B: {_ratio(f.get('pb_ratio'))}"
        f" | EPS: {_fmt_num(f.get('eps'), prefix='$')}"
    )
    lines.append(
        f"Revenue: {_fmt_num(f.get('revenue'), prefix='$')}"
        f" | Gross Margin: {_pct(f.get('gross_margin_pct'))}"
        f" | Net Margin: {_pct(f.get('profit_margin_pct'))}"
    )
    lines.append(
        f"Net Income: {_fmt_num(f.get('net_income'), prefix='$')}"
        f" | Op Cash Flow: {_fmt_num(f.get('op_cash_flow'), prefix='$')}"
        f" | Free Cash Flow: {_fmt_num(f.get('free_cash_flow'), prefix='$')}"
    )
    lines.append(
        f"Debt/Equity: {_ratio(f.get('debt_to_equity'))}"
        f" | Current Ratio: {_ratio(f.get('current_ratio'))}"
        f" | ROE: {_pct(f.get('roe_pct'))}"
        f" | Cash: {_fmt_num(f.get('cash'), prefix='$')}"
    )
    return "\n".join(lines)


def calculate_fundamental_score(fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate a fundamental quality score (0-100) based on key metrics.
    Higher score = better fundamentals.

    Accepts TWO dict formats:
      • Flat dict from get_tiingo_fundamentals_for_claude()
        — detected by presence of 'profit_margin_pct' key
      • Raw statements dict from get_fundamentals()
        — detected by presence of 'quarterly' key
    """
    score = 0
    details = []

    if not fundamentals:
        return {"score": 0, "grade": "N/A", "details": ["No fundamental data available"]}

    # ── Format A: flat dict (get_tiingo_fundamentals_for_claude output) ──────
    if "profit_margin_pct" in fundamentals or "roe_pct" in fundamentals:
        try:
            profit_margin = fundamentals.get("profit_margin_pct")
            if profit_margin is not None:
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

            de = fundamentals.get("debt_to_equity")
            if de is not None:
                if de < 0.3:
                    score += 25
                    details.append(f"✅ Low debt: D/E = {de:.2f}")
                elif de < 0.7:
                    score += 15
                    details.append(f"✅ Moderate debt: D/E = {de:.2f}")
                elif de < 1.5:
                    score += 5
                    details.append(f"⚠️ High debt: D/E = {de:.2f}")
                else:
                    details.append(f"❌ Very high debt: D/E = {de:.2f}")

            cr = fundamentals.get("current_ratio")
            if cr is not None:
                if cr > 2:
                    score += 20
                    details.append(f"✅ Strong liquidity: Current ratio = {cr:.2f}")
                elif cr > 1:
                    score += 10
                    details.append(f"✅ Adequate liquidity: Current ratio = {cr:.2f}")
                else:
                    details.append(f"❌ Poor liquidity: Current ratio = {cr:.2f}")

            roe = fundamentals.get("roe_pct")
            if roe is not None and roe > 0:
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

    # ── Format B: raw statements dict (get_fundamentals() output) ────────────
    elif fundamentals.get("quarterly"):
        quarterly = fundamentals["quarterly"]
        statement_data = quarterly.get("statementData", {})

        income_statement = {item['dataCode']: item['value']
                           for item in statement_data.get('incomeStatement', [])}
        balance_sheet = {item['dataCode']: item['value']
                        for item in statement_data.get('balanceSheet', [])}
        try:
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

            total_debt = balance_sheet.get("debt", 0) or 0
            total_equity = balance_sheet.get("equity", 1) or 1
            if total_equity > 0:
                de = total_debt / total_equity
                if de < 0.3:
                    score += 25
                    details.append(f"✅ Low debt: D/E = {de:.2f}")
                elif de < 0.7:
                    score += 15
                    details.append(f"✅ Moderate debt: D/E = {de:.2f}")
                elif de < 1.5:
                    score += 5
                    details.append(f"⚠️ High debt: D/E = {de:.2f}")
                else:
                    details.append(f"❌ Very high debt: D/E = {de:.2f}")

            ca = balance_sheet.get("assetsCurrent", 0) or 0
            cl = balance_sheet.get("liabilitiesCurrent", 1) or 1
            if cl > 0:
                cr = ca / cl
                if cr > 2:
                    score += 20
                    details.append(f"✅ Strong liquidity: Current ratio = {cr:.2f}")
                elif cr > 1:
                    score += 10
                    details.append(f"✅ Adequate liquidity: Current ratio = {cr:.2f}")
                else:
                    details.append(f"❌ Poor liquidity: Current ratio = {cr:.2f}")

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

    else:
        return {"score": 0, "grade": "N/A", "details": ["No fundamental data available"]}

    grade = "A" if score >= 80 else "B" if score >= 70 else "C" if score >= 60 else "D" if score >= 50 else "F"
    return {"score": score, "grade": grade, "details": details}


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

