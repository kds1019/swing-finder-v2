"""
Target Calculation with Fibonacci Extension
Ensures minimum 2:1 R:R ratio for all trade setups
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict


def calculate_fibonacci_target(
    df: pd.DataFrame,
    entry_price: float,
    stop_loss: float,
    lookback_bars: int = 20,
    min_rr_ratio: float = 2.0,
    max_rr_ratio: float = 2.5
) -> Dict[str, float]:
    """
    Calculate target using Fibonacci 1.618 extension from RECENT swing (15-20 bars).

    Args:
        df: DataFrame with OHLC data
        entry_price: Proposed entry price
        stop_loss: Stop loss price
        lookback_bars: Number of bars for RECENT swing (15-20, not 60!)
        min_rr_ratio: Minimum acceptable R:R ratio (default 2.0)
        max_rr_ratio: Maximum R:R cap for swing trades (default 2.5)

    Returns:
        Dictionary with:
            - fib_target: Fibonacci 1.618 extension target
            - fib_rr: R:R ratio for Fibonacci target
            - min_target: Minimum 2:1 R:R target
            - capped_target: Maximum 2.5:1 R:R target (25% above entry cap)
            - final_target: The target after all checks
            - final_rr: Final R:R ratio
            - warning: Warning message if adjustments were made
    """

    # Ensure we have enough data (use 15-20 bars for RECENT swing)
    if len(df) < lookback_bars:
        lookback_bars = max(15, len(df))  # Minimum 15 bars

    # Get the RECENT swing window (last 15-20 bars only)
    lookback_window = df.tail(lookback_bars)

    # Find swing high and swing low in the RECENT period
    swing_high = float(lookback_window['High'].max())
    swing_low = float(lookback_window['Low'].min())
    
    # Calculate swing range
    swing_range = swing_high - swing_low

    # Calculate Fibonacci 1.618 extension target from RECENT swing
    # Target = swing_high + (1.618 * swing_range)
    fib_target = swing_high + (1.618 * swing_range)

    # Calculate risk (entry to stop)
    risk = abs(entry_price - stop_loss)

    # Calculate Fibonacci R:R ratio
    fib_reward = abs(fib_target - entry_price)
    fib_rr = fib_reward / risk if risk > 0 else 0

    # Calculate minimum 2:1 R:R target (floor only - no ceiling!)
    min_target = entry_price + (min_rr_ratio * risk)

    # FINAL TARGET LOGIC (simplified - no caps!):
    warning = ""

    # Only check if Fib target is below 2:1 minimum
    if fib_rr < min_rr_ratio:
        # Too close - use 2:1 minimum
        final_target = min_target
        final_rr = min_rr_ratio
        warning = f"Fib target too close ({fib_rr:.1f}:1) - using 2:1 minimum"
    else:
        # Use Fibonacci target as-is - let it run!
        final_target = fib_target
        final_rr = fib_rr
        warning = ""

    return {
        "fib_target": round(fib_target, 2),
        "fib_rr": round(fib_rr, 2),
        "min_target": round(min_target, 2),
        "final_target": round(final_target, 2),
        "final_rr": round(final_rr, 2),
        "warning": warning,
        "swing_high": round(swing_high, 2),
        "swing_low": round(swing_low, 2),
        "swing_range": round(swing_range, 2),
        "lookback_bars": lookback_bars
    }


def calculate_scanner_target(
    df: pd.DataFrame,
    current_price: float,
    stop_loss: float,
    setup_type: str = "Breakout",
    lookback_bars: int = 20
) -> Tuple[float, float, bool]:
    """
    Calculate target for scanner cards with Fibonacci extension from RECENT swing.

    Args:
        df: DataFrame with OHLC data
        current_price: Current stock price
        stop_loss: Calculated stop loss
        setup_type: "Breakout" or "Pullback"
        lookback_bars: Lookback period for RECENT swing (15-20 bars)

    Returns:
        Tuple of (target_price, rr_ratio, has_warning)
    """

    # Use the Fibonacci calculator with SHORT recent swing
    result = calculate_fibonacci_target(
        df=df,
        entry_price=current_price,
        stop_loss=stop_loss,
        lookback_bars=lookback_bars,  # 20 bars for recent swing
        min_rr_ratio=2.0,
        max_rr_ratio=2.5
    )

    return (
        result["final_target"],
        result["final_rr"],
        bool(result["warning"])  # True if adjustments were made
    )


def format_target_display(target_data: Dict[str, float]) -> str:
    """
    Format target calculation results for display.
    
    Args:
        target_data: Dictionary from calculate_fibonacci_target()
    
    Returns:
        Formatted string for display
    """
    
    if target_data["warning"]:
        # Fibonacci target was weak
        return f"""
**Target Calculation:**
- Fib Target: ${target_data['fib_target']:.2f} (R:R {target_data['fib_rr']:.2f}:1) ⚠️ **Below 2:1**
- Min 2:1 Target: ${target_data['min_target']:.2f}
- **Using Min Target** (higher R:R)

**Swing Analysis:**
- Swing High: ${target_data['swing_high']:.2f}
- Swing Low: ${target_data['swing_low']:.2f}
- Swing Range: ${target_data['swing_range']:.2f}
"""
    else:
        # Fibonacci target is good
        return f"""
**Target Calculation:**
- Fib Target: ${target_data['fib_target']:.2f} (R:R {target_data['fib_rr']:.2f}:1) ✅
- Min 2:1 Target: ${target_data['min_target']:.2f}
- **Using Fib Target** (better R:R)

**Swing Analysis:**
- Swing High: ${target_data['swing_high']:.2f}
- Swing Low: ${target_data['swing_low']:.2f}
- Swing Range: ${target_data['swing_range']:.2f}
"""

