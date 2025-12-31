"""
Backtesting Engine for SwingFinder
Test scanner strategies on historical data to validate performance
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from utils.tiingo_api import tiingo_history
from utils.indicators import compute_indicators


def classify_setup(last: pd.Series) -> str:
    """
    Classify setup type based on EMA and RSI.
    Matches logic from scanner.py.
    """
    try:
        ema20 = float(last["EMA20"])
        ema50 = float(last["EMA50"])
        rsi = float(last["RSI14"])
    except Exception:
        return "Neutral"

    ema_up = ema20 > ema50

    if ema_up and rsi >= 50:
        return "Breakout"
    elif ema_up and rsi < 50:
        return "Pullback"
    elif not ema_up and rsi < 60:
        return "Pullback"
    else:
        return "Neutral"


def passes_filters(last: pd.Series, sensitivity: int, setup_type: str,
                   price_min: float, price_max: float, min_volume: int) -> bool:
    """
    Apply scanner filters based on sensitivity level.
    Matches logic from scanner.py.
    """
    try:
        px = float(last["Close"])
        vol = float(last["Volume"])
        rsi = float(last.get("RSI14", 50))
        ema20 = float(last.get("EMA20", np.nan))
        ema50 = float(last.get("EMA50", np.nan))
        band = float(last.get("BandPos20", 0.5))

        # Basic sanity filters
        if pd.isna(px) or pd.isna(vol):
            return False
        if px < price_min or px > price_max:
            return False
        if vol < min_volume:
            return False

        # Sensitivity-based thresholds
        sensitivity_map = {
            1: {"breakout_rsi": 65, "breakout_band": 0.70, "pullback_rsi_max": 40, "pullback_band": 0.30},
            2: {"breakout_rsi": 60, "breakout_band": 0.65, "pullback_rsi_max": 45, "pullback_band": 0.35},
            3: {"breakout_rsi": 55, "breakout_band": 0.55, "pullback_rsi_max": 50, "pullback_band": 0.45},
            4: {"breakout_rsi": 52, "breakout_band": 0.50, "pullback_rsi_max": 52, "pullback_band": 0.50},
            5: {"breakout_rsi": 50, "breakout_band": 0.45, "pullback_rsi_max": 55, "pullback_band": 0.55},
        }

        thresholds = sensitivity_map.get(sensitivity, sensitivity_map[3])

        # Apply setup-specific filters
        if setup_type == "Breakout":
            return (ema20 > ema50 and
                    rsi >= thresholds["breakout_rsi"] and
                    band >= thresholds["breakout_band"])
        elif setup_type == "Pullback":
            return (ema20 > ema50 and
                    rsi <= thresholds["pullback_rsi_max"] and
                    band <= thresholds["pullback_band"])
        else:
            return ema20 > ema50

    except Exception:
        return False


@st.cache_data(ttl=3600, show_spinner=False)
def backtest_strategy(
    tickers: List[str],
    token: str,
    lookback_days: int = 365,
    setup_mode: str = "Both",
    sensitivity: int = 3,
    price_min: float = 10.0,
    price_max: float = 60.0,
    min_volume: int = 500000,
    hold_days: int = 5,
    stop_loss_atr_mult: float = 1.5,
    take_profit_r_mult: float = 2.0
) -> Dict[str, Any]:
    """
    Backtest scanner strategy on historical data.
    
    Args:
        tickers: List of tickers to test
        token: Tiingo API token
        lookback_days: How many days of history to test
        setup_mode: "Pullback", "Breakout", or "Both"
        sensitivity: Scanner sensitivity (1-5)
        price_min/max: Price filters
        min_volume: Minimum volume filter
        hold_days: How many days to hold each trade
        stop_loss_atr_mult: Stop loss multiplier (e.g., 1.5x ATR)
        take_profit_r_mult: Take profit multiplier (e.g., 2R)
    
    Returns:
        Dictionary with backtest results
    """
    
    all_trades = []
    failed_tickers = []
    
    # Test each ticker
    for ticker in tickers:
        try:
            # Fetch historical data
            df = tiingo_history(ticker, token, lookback_days + 60)  # Extra buffer for indicators
            
            if df is None or len(df) < 60:
                failed_tickers.append(ticker)
                continue
            
            # Compute indicators
            df = compute_indicators(df)
            
            # Simulate scanning each day
            for i in range(60, len(df) - hold_days):  # Need buffer for indicators and exit
                row = df.iloc[i]
                
                # Check if this setup would have been flagged by scanner
                setup_type = classify_setup(row)
                
                # Apply setup mode filter
                if setup_mode == "Pullback" and setup_type != "Pullback":
                    continue
                elif setup_mode == "Breakout" and setup_type != "Breakout":
                    continue
                
                # Apply scanner filters
                if not passes_filters(row, sensitivity, setup_type, price_min, price_max, min_volume):
                    continue
                
                # This would have been a scanner hit! Simulate the trade
                entry_price = float(row["Close"])
                entry_date = row["Date"]
                atr = float(row["ATR14"])
                
                # Calculate stop and target
                stop_price = entry_price - (stop_loss_atr_mult * atr)
                risk = entry_price - stop_price
                target_price = entry_price + (take_profit_r_mult * risk)
                
                # Simulate holding for N days or until stop/target hit
                exit_price = None
                exit_date = None
                exit_reason = "Time"
                
                for j in range(i + 1, min(i + 1 + hold_days, len(df))):
                    future_row = df.iloc[j]
                    low = float(future_row["Low"])
                    high = float(future_row["High"])
                    close = float(future_row["Close"])
                    
                    # Check stop loss
                    if low <= stop_price:
                        exit_price = stop_price
                        exit_date = future_row["Date"]
                        exit_reason = "Stop Loss"
                        break
                    
                    # Check take profit
                    if high >= target_price:
                        exit_price = target_price
                        exit_date = future_row["Date"]
                        exit_reason = "Take Profit"
                        break
                
                # If no stop/target hit, exit at close after hold_days
                if exit_price is None:
                    exit_row = df.iloc[min(i + hold_days, len(df) - 1)]
                    exit_price = float(exit_row["Close"])
                    exit_date = exit_row["Date"]
                    exit_reason = "Time Exit"
                
                # Calculate trade result
                pnl = exit_price - entry_price
                pnl_pct = (pnl / entry_price) * 100
                r_multiple = pnl / risk if risk > 0 else 0
                
                trade = {
                    "ticker": ticker,
                    "setup_type": setup_type,
                    "entry_date": entry_date,
                    "entry_price": entry_price,
                    "exit_date": exit_date,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "r_multiple": r_multiple,
                    "hold_days": (pd.to_datetime(exit_date) - pd.to_datetime(entry_date)).days,
                    "stop_price": stop_price,
                    "target_price": target_price,
                    "atr": atr
                }
                
                all_trades.append(trade)
                
        except Exception as e:
            failed_tickers.append(ticker)
            continue
    
    # Calculate statistics
    if not all_trades:
        return {
            "total_trades": 0,
            "failed_tickers": failed_tickers,
            "error": "No trades found with these settings"
        }
    
    trades_df = pd.DataFrame(all_trades)
    
    # Win/Loss stats
    wins = trades_df[trades_df["pnl"] > 0]
    losses = trades_df[trades_df["pnl"] <= 0]

    win_rate = (len(wins) / len(trades_df)) * 100 if len(trades_df) > 0 else 0
    avg_win = wins["pnl_pct"].mean() if len(wins) > 0 else 0
    avg_loss = losses["pnl_pct"].mean() if len(losses) > 0 else 0
    avg_return = trades_df["pnl_pct"].mean()

    # R-multiple stats
    avg_r = trades_df["r_multiple"].mean()

    # Best/Worst trades
    best_trade = trades_df.loc[trades_df["pnl_pct"].idxmax()].to_dict() if len(trades_df) > 0 else None
    worst_trade = trades_df.loc[trades_df["pnl_pct"].idxmin()].to_dict() if len(trades_df) > 0 else None

    # Exit reason breakdown
    exit_reasons = trades_df["exit_reason"].value_counts().to_dict()

    # Setup type breakdown
    setup_breakdown = trades_df.groupby("setup_type").agg({
        "pnl_pct": ["count", "mean"],
        "pnl": "sum"
    }).to_dict()

    # Monthly performance
    trades_df["entry_month"] = pd.to_datetime(trades_df["entry_date"]).dt.to_period("M")
    monthly_stats = trades_df.groupby("entry_month").agg({
        "pnl_pct": ["count", "mean", "sum"],
        "pnl": "sum"
    }).reset_index()
    monthly_stats["entry_month"] = monthly_stats["entry_month"].astype(str)

    # Profit factor (gross profit / gross loss)
    gross_profit = wins["pnl"].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses["pnl"].sum()) if len(losses) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # Expectancy (average $ per trade)
    expectancy = trades_df["pnl"].mean()

    # Max consecutive wins/losses
    trades_df["win"] = trades_df["pnl"] > 0
    trades_df["streak"] = (trades_df["win"] != trades_df["win"].shift()).cumsum()
    win_streaks = trades_df[trades_df["win"]].groupby("streak").size()
    loss_streaks = trades_df[~trades_df["win"]].groupby("streak").size()
    max_win_streak = win_streaks.max() if len(win_streaks) > 0 else 0
    max_loss_streak = loss_streaks.max() if len(loss_streaks) > 0 else 0

    return {
        "total_trades": len(trades_df),
        "win_rate": win_rate,
        "total_wins": len(wins),
        "total_losses": len(losses),
        "avg_return": avg_return,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "avg_r_multiple": avg_r,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "exit_reasons": exit_reasons,
        "setup_breakdown": setup_breakdown,
        "monthly_stats": monthly_stats.to_dict("records"),
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "max_win_streak": int(max_win_streak),
        "max_loss_streak": int(max_loss_streak),
        "all_trades": trades_df.to_dict("records"),
        "failed_tickers": failed_tickers,
        "tested_tickers": len(tickers) - len(failed_tickers)
    }

