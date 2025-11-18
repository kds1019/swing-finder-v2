import pandas as pd
import numpy as np

def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()

def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """
    RSI using Wilder's smoothing method (matches Webull, TradingView, most platforms).
    This is more accurate than EWM for RSI calculation.
    """
    delta = series.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Use Wilder's smoothing (RMA)
    avg_gain = gain.ewm(alpha=1/length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False).mean()

    # Avoid division by zero
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_values = 100 - (100 / (1 + rs))

    return rsi_values.fillna(50)

def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high_low = (df["High"] - df["Low"]).abs()
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, adjust=False).mean()

# ---------------- Compute Common Indicators (used by Scanner) ----------------
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adds EMA20, EMA50, RSI14, ATR14, BandPos20, HH20, and LL20 to Tiingo OHLC data."""
    if df.empty:
        return df

    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)

    # --- Moving averages ---
    df["EMA20"] = ema(close, 20)
    df["EMA50"] = ema(close, 50)

    # --- RSI & ATR ---
    df["RSI14"] = rsi(close, 14)
    df["ATR14"] = atr(df, 14)

    # --- Bollinger Band Position (0–1 between low/high) ---
    mean = close.rolling(20).mean()
    std = close.rolling(20).std()
    upper = mean + 2 * std
    lower = mean - 2 * std
    df["BandPos20"] = (close - lower) / (upper - lower)

    # --- 20-day highs/lows ---
    df["HH20"] = high.rolling(20).max()
    df["LL20"] = low.rolling(20).min()

    # --- Volume Analysis ---
    df["AvgVol20"] = df["Volume"].rolling(20).mean()
    df["RelVolume"] = df["Volume"] / df["AvgVol20"]

    return df


# ---------------- Fibonacci Retracement Calculation ----------------
def calculate_fibonacci_levels(df: pd.DataFrame, lookback: int = 20) -> dict:
    """
    Calculate Fibonacci retracement levels based on recent swing high/low.

    Args:
        df: DataFrame with OHLC data
        lookback: Number of periods to look back for swing high/low (default: 20)

    Returns:
        dict with:
            - swing_high: Recent swing high price
            - swing_low: Recent swing low price
            - fib_levels: Dict of Fibonacci levels (0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%)
            - current_fib_position: Current price position as percentage (0-100%)
            - zone: "discount" (0-50%) or "premium" (50-100%)
            - optimal_entry: Suggested entry price at nearest Fib level
    """
    if df.empty or len(df) < lookback:
        return None

    # Get recent swing high and low
    recent_data = df.tail(lookback)
    swing_high = float(recent_data["High"].max())
    swing_low = float(recent_data["Low"].min())
    current_price = float(df["Close"].iloc[-1])

    # Calculate range
    price_range = swing_high - swing_low

    if price_range <= 0:
        return None

    # Calculate Fibonacci retracement levels (from high to low)
    fib_ratios = {
        "0%": 1.000,      # Swing high (100% retracement = 0% from high)
        "23.6%": 0.764,   # 23.6% retracement
        "38.2%": 0.618,   # 38.2% retracement
        "50%": 0.500,     # 50% retracement (equilibrium)
        "61.8%": 0.382,   # 61.8% retracement (golden ratio)
        "78.6%": 0.214,   # 78.6% retracement
        "100%": 0.000,    # Swing low (100% retracement)
    }

    fib_levels = {}
    for label, ratio in fib_ratios.items():
        fib_levels[label] = swing_low + (price_range * ratio)

    # Calculate current price position as percentage (0% = swing low, 100% = swing high)
    current_fib_position = ((current_price - swing_low) / price_range) * 100
    current_fib_position = max(0, min(100, current_fib_position))  # Clamp to 0-100%

    # Determine zone
    zone = "discount" if current_fib_position <= 50 else "premium"

    # Find optimal entry (nearest Fib level below current price for pullbacks)
    entry_levels = [fib_levels["38.2%"], fib_levels["50%"], fib_levels["61.8%"]]
    optimal_entry = min(entry_levels, key=lambda x: abs(x - current_price))

    return {
        "swing_high": swing_high,
        "swing_low": swing_low,
        "fib_levels": fib_levels,
        "current_fib_position": current_fib_position,
        "zone": zone,
        "optimal_entry": optimal_entry,
        "price_range": price_range
    }


def get_fibonacci_zone_label(fib_position: float) -> str:
    """
    Get a descriptive label for the current Fibonacci position.

    Args:
        fib_position: Current position as percentage (0-100%)

    Returns:
        String label describing the zone
    """
    if fib_position <= 23.6:
        return "Deep Discount (0-23.6%)"
    elif fib_position <= 38.2:
        return "Strong Discount (23.6-38.2%)"
    elif fib_position <= 50:
        return "Discount Zone (38.2-50%)"
    elif fib_position <= 61.8:
        return "Equilibrium (50-61.8%)"
    elif fib_position <= 78.6:
        return "Premium Zone (61.8-78.6%)"
    else:
        return "Extended Premium (78.6-100%)"


# ---------------- Support/Resistance Detection ----------------
def find_support_resistance(df: pd.DataFrame, window: int = 10, num_levels: int = 3) -> dict:
    """
    Find key support and resistance levels using pivot points.
    Returns the most significant levels based on price action.
    """
    if len(df) < window * 2:
        return {"support": [], "resistance": []}

    highs = df["High"].rolling(window=window, center=True).max()
    lows = df["Low"].rolling(window=window, center=True).min()

    # Find pivot highs (resistance)
    resistance_levels = []
    for i in range(window, len(df) - window):
        if df["High"].iloc[i] == highs.iloc[i]:
            resistance_levels.append(float(df["High"].iloc[i]))

    # Find pivot lows (support)
    support_levels = []
    for i in range(window, len(df) - window):
        if df["Low"].iloc[i] == lows.iloc[i]:
            support_levels.append(float(df["Low"].iloc[i]))

    # Cluster nearby levels (within 2% of each other)
    def cluster_levels(levels, tolerance=0.02):
        if not levels:
            return []

        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]

        for level in levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] < tolerance:
                current_cluster.append(level)
            else:
                clusters.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [level]

        clusters.append(sum(current_cluster) / len(current_cluster))
        return clusters

    # Get clustered levels
    resistance = cluster_levels(resistance_levels)
    support = cluster_levels(support_levels)

    # Get current price to filter relevant levels
    current_price = float(df["Close"].iloc[-1])

    # Keep only resistance above current price (closest first)
    resistance = sorted([r for r in resistance if r > current_price])[:num_levels]

    # Keep only support below current price (closest first)
    support = sorted([s for s in support if s < current_price], reverse=True)[:num_levels]

    return {
        "resistance": [round(r, 2) for r in resistance],
        "support": [round(s, 2) for s in support]
    }


# ---------------- Volume Analysis ----------------
def analyze_volume(df: pd.DataFrame, lookback: int = 20) -> dict:
    """
    Analyze volume patterns for confirmation signals.
    """
    if len(df) < lookback:
        return {}

    recent = df.tail(lookback)

    # Average volume
    avg_volume = recent["Volume"].mean()
    current_volume = float(recent["Volume"].iloc[-1])

    # Relative volume
    rel_volume = current_volume / avg_volume if avg_volume > 0 else 1.0

    # Volume trend (increasing or decreasing)
    first_half_vol = recent["Volume"].iloc[:lookback//2].mean()
    second_half_vol = recent["Volume"].iloc[lookback//2:].mean()
    vol_trend = "Increasing" if second_half_vol > first_half_vol * 1.1 else \
                "Decreasing" if second_half_vol < first_half_vol * 0.9 else "Stable"

    # Volume on up days vs down days
    up_days = recent[recent["Close"] > recent["Close"].shift(1)]
    down_days = recent[recent["Close"] < recent["Close"].shift(1)]

    avg_vol_up = up_days["Volume"].mean() if len(up_days) > 0 else 0
    avg_vol_down = down_days["Volume"].mean() if len(down_days) > 0 else 0

    # Accumulation/Distribution signal
    if avg_vol_up > avg_vol_down * 1.2:
        vol_signal = "Accumulation"
    elif avg_vol_down > avg_vol_up * 1.2:
        vol_signal = "Distribution"
    else:
        vol_signal = "Neutral"

    return {
        "current_volume": int(current_volume),
        "avg_volume": int(avg_volume),
        "relative_volume": round(rel_volume, 2),
        "volume_trend": vol_trend,
        "volume_signal": vol_signal,
        "volume_surge": rel_volume > 1.5
    }


# ---------------- Relative Strength vs SPY ----------------
def calculate_relative_strength(ticker_df: pd.DataFrame, spy_df: pd.DataFrame, period: int = 20) -> dict:
    """
    Calculate relative strength vs SPY.
    > 1.0 = outperforming market
    < 1.0 = underperforming market
    """
    if len(ticker_df) < period or len(spy_df) < period:
        return {"rs_ratio": 1.0, "status": "Unknown"}

    ticker_return = (ticker_df["Close"].iloc[-1] / ticker_df["Close"].iloc[-period]) - 1
    spy_return = (spy_df["Close"].iloc[-1] / spy_df["Close"].iloc[-period]) - 1

    if spy_return == 0:
        rs_ratio = 1.0
    else:
        rs_ratio = (1 + ticker_return) / (1 + spy_return)

    # Determine status
    if rs_ratio > 1.1:
        status = "Strong Outperformer"
    elif rs_ratio > 1.02:
        status = "Outperforming"
    elif rs_ratio > 0.98:
        status = "In-line with Market"
    elif rs_ratio > 0.9:
        status = "Underperforming"
    else:
        status = "Weak Underperformer"

    return {
        "rs_ratio": round(rs_ratio, 2),
        "status": status,
        "ticker_return": round(ticker_return * 100, 2),
        "spy_return": round(spy_return * 100, 2)
    }


# ---------------- Pattern Recognition ----------------
def detect_bull_flag(df: pd.DataFrame, lookback: int = 20) -> dict:
    """
    Detect bull flag pattern: strong move up followed by tight consolidation.
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)

    # Split into two halves
    first_half = recent.head(lookback // 2)
    second_half = recent.tail(lookback // 2)

    # Check for strong initial move (>5% gain)
    initial_gain = (first_half["Close"].iloc[-1] / first_half["Close"].iloc[0]) - 1
    strong_move = initial_gain > 0.05

    # Check for tight consolidation (range < 5% of price)
    consolidation_range = (second_half["High"].max() - second_half["Low"].min()) / second_half["Close"].mean()
    tight_consolidation = consolidation_range < 0.05

    # Volume should decrease during consolidation
    first_half_vol = first_half["Volume"].mean()
    second_half_vol = second_half["Volume"].mean()
    volume_decrease = second_half_vol < first_half_vol * 0.8

    detected = strong_move and tight_consolidation
    confidence = 0

    if detected:
        confidence = 60
        if volume_decrease:
            confidence += 20
        if consolidation_range < 0.03:
            confidence += 10
        if initial_gain > 0.10:
            confidence += 10

    return {
        "detected": detected,
        "confidence": min(100, confidence),
        "initial_gain": round(initial_gain * 100, 1),
        "consolidation_range": round(consolidation_range * 100, 1)
    }


def detect_cup_and_handle(df: pd.DataFrame, lookback: int = 40) -> dict:
    """
    Detect cup and handle pattern: U-shaped recovery with small pullback.
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)

    # Divide into three parts: left side, bottom, right side
    third = lookback // 3
    left_side = recent.iloc[:third]
    bottom = recent.iloc[third:2*third]
    right_side = recent.iloc[2*third:]

    # Check for U-shape: decline then recovery
    left_high = left_side["High"].max()
    bottom_low = bottom["Low"].min()
    right_high = right_side["High"].max()

    # Cup depth (should be 12-33% typically)
    cup_depth = (left_high - bottom_low) / left_high
    valid_depth = 0.12 <= cup_depth <= 0.33

    # Right side should recover to near left side high
    recovery = right_high >= left_high * 0.95

    # Handle: small pullback at the end (last 25% of pattern)
    handle_start = len(recent) - (lookback // 4)
    handle = recent.iloc[handle_start:]
    handle_depth = (handle["High"].max() - handle["Low"].min()) / handle["Close"].mean()
    small_handle = handle_depth < 0.10

    detected = valid_depth and recovery and small_handle
    confidence = 0

    if detected:
        confidence = 70
        if 0.15 <= cup_depth <= 0.25:  # Ideal depth
            confidence += 15
        if right_high >= left_high * 0.98:  # Strong recovery
            confidence += 15

    return {
        "detected": detected,
        "confidence": min(100, confidence),
        "cup_depth": round(cup_depth * 100, 1),
        "recovery_pct": round((right_high / left_high - 1) * 100, 1)
    }


def detect_double_bottom(df: pd.DataFrame, lookback: int = 30) -> dict:
    """
    Detect double bottom pattern: two lows at similar price with peak in between.
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)

    # Find the two lowest points
    lows = recent.nsmallest(5, "Low")

    if len(lows) < 2:
        return {"detected": False}

    # Get the two lowest lows
    first_low_idx = lows.index[0]
    second_low_idx = lows.index[1]

    # Make sure they're in chronological order
    if first_low_idx > second_low_idx:
        first_low_idx, second_low_idx = second_low_idx, first_low_idx

    first_low = recent.loc[first_low_idx, "Low"]
    second_low = recent.loc[second_low_idx, "Low"]

    # Lows should be within 3% of each other
    low_similarity = abs(first_low - second_low) / first_low
    similar_lows = low_similarity < 0.03

    # There should be a peak between the two lows
    between = recent.loc[first_low_idx:second_low_idx]
    if len(between) > 0:
        peak = between["High"].max()
        peak_height = (peak - first_low) / first_low
        valid_peak = peak_height > 0.05  # At least 5% bounce
    else:
        valid_peak = False

    # Current price should be above the peak (breakout)
    current_price = recent["Close"].iloc[-1]
    breakout = current_price > peak * 1.01 if valid_peak else False

    detected = similar_lows and valid_peak
    confidence = 0

    if detected:
        confidence = 65
        if low_similarity < 0.02:  # Very similar lows
            confidence += 15
        if breakout:  # Already breaking out
            confidence += 20

    return {
        "detected": detected,
        "confidence": min(100, confidence),
        "low_similarity": round(low_similarity * 100, 1),
        "breakout": breakout
    }


def detect_ascending_triangle(df: pd.DataFrame, lookback: int = 30) -> dict:
    """
    Detect ascending triangle: flat resistance with rising support.
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)

    # Find resistance level (should be relatively flat)
    highs = recent["High"]
    resistance = highs.max()

    # Count how many times price touched resistance (within 2%)
    touches = sum(highs >= resistance * 0.98)
    multiple_touches = touches >= 2

    # Check if lows are rising (ascending support)
    first_half_lows = recent.head(lookback // 2)["Low"].mean()
    second_half_lows = recent.tail(lookback // 2)["Low"].mean()
    rising_lows = second_half_lows > first_half_lows * 1.02

    # Volume should contract during pattern
    first_half_vol = recent.head(lookback // 2)["Volume"].mean()
    second_half_vol = recent.tail(lookback // 2)["Volume"].mean()
    volume_contraction = second_half_vol < first_half_vol

    detected = multiple_touches and rising_lows
    confidence = 0

    if detected:
        confidence = 60
        if touches >= 3:
            confidence += 15
        if volume_contraction:
            confidence += 15
        if rising_lows and second_half_lows > first_half_lows * 1.05:
            confidence += 10

    return {
        "detected": detected,
        "confidence": min(100, confidence),
        "resistance_touches": touches,
        "support_rising": rising_lows
    }


def detect_patterns(df: pd.DataFrame) -> list:
    """
    Detect all chart patterns and return list of detected patterns.
    """
    patterns = []

    # Bull Flag
    bull_flag = detect_bull_flag(df, lookback=20)
    if bull_flag["detected"]:
        patterns.append({
            "type": "Bull Flag",
            "confidence": bull_flag["confidence"],
            "bias": "Bullish",
            "description": f"Strong move up ({bull_flag['initial_gain']}%) followed by tight consolidation",
            "action": "Buy breakout above consolidation high with volume"
        })

    # Cup and Handle
    cup_handle = detect_cup_and_handle(df, lookback=40)
    if cup_handle["detected"]:
        patterns.append({
            "type": "Cup and Handle",
            "confidence": cup_handle["confidence"],
            "bias": "Bullish",
            "description": f"U-shaped recovery ({cup_handle['cup_depth']}% depth) with handle",
            "action": "Buy breakout above handle high"
        })

    # Double Bottom
    double_bottom = detect_double_bottom(df, lookback=30)
    if double_bottom["detected"]:
        patterns.append({
            "type": "Double Bottom",
            "confidence": double_bottom["confidence"],
            "bias": "Bullish",
            "description": f"Two lows at similar price ({double_bottom['low_similarity']}% apart)",
            "action": "Buy breakout above middle peak" if not double_bottom["breakout"] else "Already breaking out!"
        })

    # Ascending Triangle
    asc_triangle = detect_ascending_triangle(df, lookback=30)
    if asc_triangle["detected"]:
        patterns.append({
            "type": "Ascending Triangle",
            "confidence": asc_triangle["confidence"],
            "bias": "Bullish",
            "description": f"Flat resistance with {asc_triangle['resistance_touches']} touches, rising support",
            "action": "Buy breakout above resistance with volume surge"
        })

    # Sort by confidence
    patterns.sort(key=lambda x: x["confidence"], reverse=True)

    return patterns


# ---------------- Gap Detection ----------------
def detect_gaps(df: pd.DataFrame, min_gap_pct: float = 2.0, lookback: int = 60) -> dict:
    """
    Detect price gaps that could act as support/resistance.
    Returns unfilled gaps within lookback period.
    """
    if len(df) < 2:
        return {"gap_ups": [], "gap_downs": [], "nearest_gap": None}

    recent = df.tail(lookback) if len(df) > lookback else df
    gaps_up = []
    gaps_down = []
    current_price = float(df["Close"].iloc[-1])

    for i in range(1, len(recent)):
        prev_high = float(recent.iloc[i-1]["High"])
        prev_low = float(recent.iloc[i-1]["Low"])
        curr_high = float(recent.iloc[i]["High"])
        curr_low = float(recent.iloc[i]["Low"])
        curr_date = recent.iloc[i]["Date"] if "Date" in recent.columns else i

        # Gap Up (current low > previous high)
        if curr_low > prev_high:
            gap_size = ((curr_low - prev_high) / prev_high) * 100
            if gap_size >= min_gap_pct:
                # Check if gap is still unfilled
                subsequent = recent.iloc[i:]
                filled = any(subsequent["Low"] <= prev_high)

                if not filled:
                    gaps_up.append({
                        "date": str(curr_date),
                        "gap_low": round(curr_low, 2),
                        "gap_high": round(prev_high, 2),
                        "size_pct": round(gap_size, 1),
                        "filled": False,
                        "type": "gap_up"
                    })

        # Gap Down (current high < previous low)
        elif curr_high < prev_low:
            gap_size = ((prev_low - curr_high) / prev_low) * 100
            if gap_size >= min_gap_pct:
                # Check if gap is still unfilled
                subsequent = recent.iloc[i:]
                filled = any(subsequent["High"] >= prev_low)

                if not filled:
                    gaps_down.append({
                        "date": str(curr_date),
                        "gap_high": round(prev_low, 2),
                        "gap_low": round(curr_high, 2),
                        "size_pct": round(gap_size, 1),
                        "filled": False,
                        "type": "gap_down"
                    })

    # Find nearest unfilled gap to current price
    all_gaps = gaps_up + gaps_down
    nearest_gap = None
    min_distance = float('inf')

    for gap in all_gaps:
        gap_mid = (gap["gap_high"] + gap["gap_low"]) / 2
        distance = abs(current_price - gap_mid)
        if distance < min_distance:
            min_distance = distance
            nearest_gap = gap

    return {
        "gap_ups": gaps_up,
        "gap_downs": gaps_down,
        "nearest_gap": nearest_gap,
        "total_unfilled": len(all_gaps)
    }


# ---------------- Correlation & Beta Analysis ----------------
def calculate_beta_and_correlation(ticker_df: pd.DataFrame, spy_df: pd.DataFrame, period: int = 60) -> dict:
    """
    Calculate beta and correlation with SPY.
    Beta > 1 = more volatile than market
    Beta < 1 = less volatile than market
    Correlation shows how closely stock moves with market
    """
    if len(ticker_df) < period or len(spy_df) < period:
        return {"beta": None, "correlation": None, "interpretation": "Insufficient data"}

    # Align dataframes by date if possible
    ticker_recent = ticker_df.tail(period).copy()
    spy_recent = spy_df.tail(period).copy()

    # Calculate returns
    ticker_returns = ticker_recent["Close"].pct_change().dropna()
    spy_returns = spy_recent["Close"].pct_change().dropna()

    # Make sure they're the same length
    min_len = min(len(ticker_returns), len(spy_returns))
    ticker_returns = ticker_returns.tail(min_len)
    spy_returns = spy_returns.tail(min_len)

    if len(ticker_returns) < 20:
        return {"beta": None, "correlation": None, "interpretation": "Insufficient data"}

    # Calculate correlation
    correlation = ticker_returns.corr(spy_returns)

    # Calculate beta (covariance / variance)
    covariance = ticker_returns.cov(spy_returns)
    spy_variance = spy_returns.var()
    beta = covariance / spy_variance if spy_variance != 0 else 1.0

    # Interpretation
    if correlation > 0.7:
        corr_interp = "Moves strongly with market"
    elif correlation > 0.3:
        corr_interp = "Moderately correlated with market"
    elif correlation > -0.3:
        corr_interp = "Independent of market"
    else:
        corr_interp = "Moves opposite to market"

    if beta > 1.5:
        beta_interp = "High volatility (1.5x+ market)"
    elif beta > 1.0:
        beta_interp = "More volatile than market"
    elif beta > 0.5:
        beta_interp = "Less volatile than market"
    else:
        beta_interp = "Low volatility"

    return {
        "beta": round(beta, 2),
        "correlation": round(correlation, 2),
        "correlation_interpretation": corr_interp,
        "beta_interpretation": beta_interp,
        "interpretation": f"{corr_interp}. {beta_interp}."
    }
