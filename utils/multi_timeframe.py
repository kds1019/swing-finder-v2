"""
Multi-Timeframe Analysis for SwingFinder
Analyze key indicators across multiple timeframes (Daily, Weekly, 4-Hour)
"""

import pandas as pd
import streamlit as st
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
from utils.tiingo_api import tiingo_history, fetch_tiingo_intraday


@st.cache_data(ttl=60 * 30, show_spinner=False)
def fetch_timeframe_data(symbol: str, token: str, timeframe: str, days: int = 365) -> Optional[pd.DataFrame]:
    """
    Fetch data for a specific timeframe from Tiingo.

    Args:
        symbol: Stock ticker
        token: Tiingo API token
        timeframe: 'daily', 'weekly', or '4hour'
        days: Lookback period in days

    Returns:
        DataFrame with OHLCV data or None if error
    """
    try:
        if timeframe == 'daily':
            # Use existing tiingo_history function for daily data
            df = tiingo_history(symbol, token, days)
            if df is None or df.empty:
                return None
            return df

        elif timeframe == 'weekly':
            # Fetch daily data and resample to weekly
            df = tiingo_history(symbol, token, days)
            if df is None or df.empty:
                return None

            # Resample to weekly
            df_weekly = df.set_index('Date').resample('W').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).reset_index()

            return df_weekly

        elif timeframe == '4hour':
            # Use existing fetch_tiingo_intraday function
            df = fetch_tiingo_intraday(symbol, token, timeframe="4hour", lookback_days=days)
            if df is None or df.empty:
                return None

            # The intraday function returns only date and close
            # We need to create a properly formatted DataFrame
            # For indicators, we only need Close prices anyway
            df_formatted = pd.DataFrame()
            df_formatted['Date'] = pd.to_datetime(df['date'])
            df_formatted['Close'] = df['close'].astype(float)
            df_formatted['Open'] = df['close'].astype(float)  # Use close as open (not ideal but works for indicators)
            df_formatted['High'] = df['close'].astype(float)  # Use close as high
            df_formatted['Low'] = df['close'].astype(float)   # Use close as low

            # Sort by date
            df_formatted = df_formatted.sort_values('Date').reset_index(drop=True)

            return df_formatted

        else:
            return None

    except Exception as e:
        print(f"Error fetching {timeframe} data for {symbol}: {e}")
        return None


def calculate_mtf_indicators(df: pd.DataFrame) -> Dict:
    """
    Calculate key indicators for a timeframe.

    Returns dict with:
        - ema20, ema50
        - rsi14
        - macd, macd_signal, macd_hist
        - trend (Uptrend/Downtrend)
        - momentum (Strong/Weak/Neutral)
    """
    if df is None or df.empty:
        print(f"MTF Indicators: DataFrame is None or empty")
        return None

    # Need at least 26 bars for MACD (26-period EMA)
    if len(df) < 26:
        print(f"MTF Indicators: Not enough data ({len(df)} rows, need at least 26)")
        return None

    try:
        # Make a copy to avoid modifying the original
        df = df.copy()

        # Ensure we have the Close column
        if "Close" not in df.columns and "close" in df.columns:
            df["Close"] = df["close"]

        if "Close" not in df.columns:
            print(f"MTF Indicators: No Close column found. Columns: {df.columns.tolist()}")
            return None

        close = df["Close"].astype(float)
        print(f"MTF Indicators: Processing {len(df)} rows of data")
        
        # EMAs
        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        rsi14 = rsi.iloc[-1]
        
        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = macd - macd_signal
        
        macd_val = macd.iloc[-1]
        macd_signal_val = macd_signal.iloc[-1]
        macd_hist_val = macd_hist.iloc[-1]
        
        # Trend determination
        trend = "Uptrend" if ema20 > ema50 else "Downtrend"
        
        # Momentum determination
        if rsi14 > 60:
            momentum = "Strong"
        elif rsi14 < 40:
            momentum = "Weak"
        else:
            momentum = "Neutral"
        
        return {
            "ema20": round(ema20, 2),
            "ema50": round(ema50, 2),
            "rsi14": round(rsi14, 2),
            "macd": round(macd_val, 4),
            "macd_signal": round(macd_signal_val, 4),
            "macd_hist": round(macd_hist_val, 4),
            "trend": trend,
            "momentum": momentum,
            "price": round(close.iloc[-1], 2)
        }
    
    except Exception as e:
        import traceback
        print(f"Error calculating MTF indicators: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None


def get_multi_timeframe_analysis(symbol: str, token: str) -> Dict:
    """
    Get multi-timeframe analysis for a symbol across Daily, Weekly, and 4-Hour timeframes.

    Returns dict with:
        - daily: indicators for daily timeframe
        - weekly: indicators for weekly timeframe
        - four_hour: indicators for 4-hour timeframe
        - alignment: overall trend alignment score
        - recommendation: trading recommendation based on MTF analysis
    """
    # Fetch data for each timeframe
    print(f"Fetching daily data for {symbol}...")
    daily_df = fetch_timeframe_data(symbol, token, "daily", days=200)
    print(f"Daily data: {len(daily_df) if daily_df is not None else 0} rows")

    print(f"Fetching weekly data for {symbol}...")
    weekly_df = fetch_timeframe_data(symbol, token, "weekly", days=730)  # ~2 years for weekly
    print(f"Weekly data: {len(weekly_df) if weekly_df is not None else 0} rows")

    print(f"Fetching 4-hour data for {symbol}...")
    four_hour_df = fetch_timeframe_data(symbol, token, "4hour", days=60)  # 60 days for more data points
    print(f"4-hour data: {len(four_hour_df) if four_hour_df is not None else 0} rows")
    if four_hour_df is not None and not four_hour_df.empty:
        print(f"4-hour data columns: {four_hour_df.columns.tolist()}")
        print(f"4-hour data sample:\n{four_hour_df.head()}")

    # Calculate indicators for each timeframe
    daily_indicators = calculate_mtf_indicators(daily_df) if daily_df is not None and not daily_df.empty else None
    weekly_indicators = calculate_mtf_indicators(weekly_df) if weekly_df is not None and not weekly_df.empty else None
    four_hour_indicators = calculate_mtf_indicators(four_hour_df) if four_hour_df is not None and not four_hour_df.empty else None

    print(f"Indicators calculated - Daily: {daily_indicators is not None}, Weekly: {weekly_indicators is not None}, 4-Hour: {four_hour_indicators is not None}")

    # Calculate alignment score (how many timeframes agree on trend)
    alignment_score = 0
    uptrend_count = 0
    total_timeframes = 0

    for indicators in [daily_indicators, weekly_indicators, four_hour_indicators]:
        if indicators:
            total_timeframes += 1
            if indicators["trend"] == "Uptrend":
                uptrend_count += 1

    if total_timeframes > 0:
        alignment_score = (uptrend_count / total_timeframes) * 100

    # Generate recommendation
    recommendation = _generate_mtf_recommendation(
        daily_indicators, weekly_indicators, four_hour_indicators, alignment_score
    )

    return {
        "daily": daily_indicators,
        "weekly": weekly_indicators,
        "four_hour": four_hour_indicators,
        "alignment_score": round(alignment_score, 1),
        "recommendation": recommendation
    }


def _generate_mtf_recommendation(daily: Dict, weekly: Dict, four_hour: Dict, alignment: float) -> str:
    """Generate trading recommendation based on multi-timeframe analysis."""

    if not daily:
        return "⚠️ Insufficient data for analysis"

    # All timeframes bullish
    if alignment >= 100:
        return "🟢 **STRONG BUY SIGNAL** - All timeframes aligned bullish. High-conviction setup."

    # Majority bullish
    elif alignment >= 66:
        if weekly and weekly["trend"] == "Uptrend":
            return "🟢 **BUY SIGNAL** - Weekly uptrend confirmed. Good swing trade setup."
        else:
            return "🟡 **CAUTIOUS BUY** - Mixed signals. Wait for weekly confirmation."

    # Mixed signals
    elif alignment >= 33:
        if daily and daily["trend"] == "Uptrend" and daily["momentum"] == "Strong":
            return "🟡 **NEUTRAL** - Daily strong but higher timeframes mixed. Short-term trade only."
        else:
            return "🟡 **NEUTRAL** - Mixed timeframe signals. Wait for clarity."

    # Majority bearish
    else:
        if weekly and weekly["trend"] == "Downtrend":
            return "🔴 **AVOID** - Weekly downtrend. Not a good swing trade setup."
        else:
            return "🔴 **WEAK SETUP** - Most timeframes bearish. Look for better opportunities."


def format_mtf_display(mtf_data: Dict) -> str:
    """Format multi-timeframe data for display in Streamlit."""

    if not mtf_data:
        return "No multi-timeframe data available"

    output = []

    # Header
    output.append(f"**Trend Alignment:** {mtf_data['alignment_score']:.0f}%")
    output.append(f"{mtf_data['recommendation']}\n")

    # Timeframe details
    timeframes = [
        ("📅 **Daily**", mtf_data.get("daily")),
        ("📊 **Weekly**", mtf_data.get("weekly")),
        ("⏰ **4-Hour**", mtf_data.get("four_hour"))
    ]

    for label, data in timeframes:
        if data:
            trend_emoji = "🟢" if data["trend"] == "Uptrend" else "🔴"
            output.append(f"{label}")
            output.append(f"  {trend_emoji} {data['trend']} | RSI: {data['rsi14']:.1f} | Momentum: {data['momentum']}")
            output.append(f"  EMA20: ${data['ema20']:.2f} | EMA50: ${data['ema50']:.2f}")
            output.append(f"  MACD: {data['macd']:.4f} | Signal: {data['macd_signal']:.4f}\n")
        else:
            output.append(f"{label}")
            output.append(f"  ⚠️ Data unavailable\n")

    return "\n".join(output)


