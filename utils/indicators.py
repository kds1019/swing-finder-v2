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
    """Adds EMA20, EMA50, EMA200, RSI14, ATR14, BandPos20, HH20, and LL20 to Tiingo OHLC data."""
    if df.empty:
        return df

    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)

    # --- Moving averages ---
    df["EMA20"] = ema(close, 20)
    df["EMA50"] = ema(close, 50)
    df["EMA200"] = ema(close, 200)

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

    Uses find_pivot_points() to identify the most recent *significant* swing
    high and low instead of simple max/min of the window, which avoids
    picking up intraday wicks and single-bar spikes as the swing anchor.

    Falls back to window max/min if fewer than 2 pivots are found.

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

    recent_data = df.tail(lookback)

    # ── Pivot-based swing anchor ──────────────────────────────────────────
    # Use a smaller left/right window so we get enough pivots in a 20-bar slice.
    pivots = find_pivot_points(recent_data, left_bars=2, right_bars=2)
    phs = pivots["pivot_highs"]
    pls = pivots["pivot_lows"]

    if phs:
        # Most recent significant pivot high
        swing_high = float(max(phs, key=lambda p: p["bar"])["price"])
    else:
        # Fallback: highest high in window
        swing_high = float(recent_data["High"].max())

    if pls:
        # Most recent significant pivot low
        swing_low = float(max(pls, key=lambda p: p["bar"])["price"])
    else:
        # Fallback: lowest low in window
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

    Enhanced version with strength scoring and proximity alerts.
    """
    if len(df) < window * 2:
        return {
            "support": [],
            "resistance": [],
            "support_details": [],
            "resistance_details": [],
            "nearest_support": None,
            "nearest_resistance": None,
            "price_near_level": False
        }

    highs = df["High"].rolling(window=window, center=True).max()
    lows = df["Low"].rolling(window=window, center=True).min()

    # Find pivot highs (resistance) with touch count
    resistance_levels = []
    for i in range(window, len(df) - window):
        if df["High"].iloc[i] == highs.iloc[i]:
            level = float(df["High"].iloc[i])
            # Count how many times price touched this level (within 1%)
            touches = sum(abs(df["High"] - level) / level < 0.01)
            resistance_levels.append({"price": level, "touches": touches, "index": i})

    # Find pivot lows (support) with touch count
    support_levels = []
    for i in range(window, len(df) - window):
        if df["Low"].iloc[i] == lows.iloc[i]:
            level = float(df["Low"].iloc[i])
            # Count how many times price touched this level (within 1%)
            touches = sum(abs(df["Low"] - level) / level < 0.01)
            support_levels.append({"price": level, "touches": touches, "index": i})

    # Cluster nearby levels (within 2% of each other)
    def cluster_levels_with_strength(levels, tolerance=0.02):
        if not levels:
            return []

        levels = sorted(levels, key=lambda x: x["price"])
        clusters = []
        current_cluster = [levels[0]]

        for level in levels[1:]:
            if abs(level["price"] - current_cluster[-1]["price"]) / current_cluster[-1]["price"] < tolerance:
                current_cluster.append(level)
            else:
                # Average price and sum touches for strength
                avg_price = sum(l["price"] for l in current_cluster) / len(current_cluster)
                total_touches = sum(l["touches"] for l in current_cluster)
                clusters.append({
                    "price": avg_price,
                    "touches": total_touches,
                    "strength": min(100, total_touches * 20)  # Strength score 0-100
                })
                current_cluster = [level]

        # Add last cluster
        avg_price = sum(l["price"] for l in current_cluster) / len(current_cluster)
        total_touches = sum(l["touches"] for l in current_cluster)
        clusters.append({
            "price": avg_price,
            "touches": total_touches,
            "strength": min(100, total_touches * 20)
        })
        return clusters

    # Get clustered levels with strength
    resistance_clusters = cluster_levels_with_strength(resistance_levels)
    support_clusters = cluster_levels_with_strength(support_levels)

    # Get current price to filter relevant levels
    current_price = float(df["Close"].iloc[-1])

    # Keep only resistance above current price (closest first)
    resistance_above = [r for r in resistance_clusters if r["price"] > current_price]
    resistance_above = sorted(resistance_above, key=lambda x: x["price"])[:num_levels]

    # Keep only support below current price (closest first)
    support_below = [s for s in support_clusters if s["price"] < current_price]
    support_below = sorted(support_below, key=lambda x: x["price"], reverse=True)[:num_levels]

    # Calculate distance to nearest levels
    nearest_support = support_below[0] if support_below else None
    nearest_resistance = resistance_above[0] if resistance_above else None

    # Check if price is near a level (within 2%)
    price_near_level = False
    if nearest_support and abs(current_price - nearest_support["price"]) / current_price < 0.02:
        price_near_level = True
    if nearest_resistance and abs(current_price - nearest_resistance["price"]) / current_price < 0.02:
        price_near_level = True

    return {
        "resistance": [round(r["price"], 2) for r in resistance_above],
        "support": [round(s["price"], 2) for s in support_below],
        "resistance_details": [
            {
                "price": round(r["price"], 2),
                "touches": r["touches"],
                "strength": r["strength"],
                "distance_pct": round(((r["price"] - current_price) / current_price) * 100, 2)
            }
            for r in resistance_above
        ],
        "support_details": [
            {
                "price": round(s["price"], 2),
                "touches": s["touches"],
                "strength": s["strength"],
                "distance_pct": round(((current_price - s["price"]) / current_price) * 100, 2)
            }
            for s in support_below
        ],
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "price_near_level": price_near_level,
        "current_price": round(current_price, 2)
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


# ---------------- Pivot Point Engine ----------------
def find_pivot_points(df: pd.DataFrame, left_bars: int = 3, right_bars: int = 3) -> dict:
    """
    Find true pivot highs and lows using left/right bar comparison.

    A pivot HIGH at bar i requires:
        High[i] >= High[i-1..i-left_bars]  AND  High[i] >= High[i+1..i+right_bars]

    A pivot LOW at bar i requires:
        Low[i]  <= Low[i-1..i-left_bars]   AND  Low[i]  <= Low[i+1..i+right_bars]

    Returns dict with:
        pivot_highs: list of {"bar": int, "price": float}  (chronological)
        pivot_lows:  list of {"bar": int, "price": float}  (chronological)
    """
    n = len(df)
    pivot_highs = []
    pivot_lows  = []

    highs = df["High"].values
    lows  = df["Low"].values

    for i in range(left_bars, n - right_bars):
        h = highs[i]
        lo = lows[i]

        # Pivot high: must be >= all bars in the window (allows ties on one side)
        if (all(h >= highs[i - j] for j in range(1, left_bars + 1)) and
                all(h >= highs[i + j] for j in range(1, right_bars + 1))):
            pivot_highs.append({"bar": i, "price": float(h)})

        # Pivot low: must be <= all bars in the window
        if (all(lo <= lows[i - j] for j in range(1, left_bars + 1)) and
                all(lo <= lows[i + j] for j in range(1, right_bars + 1))):
            pivot_lows.append({"bar": i, "price": float(lo)})

    return {"pivot_highs": pivot_highs, "pivot_lows": pivot_lows}


# ---------------- Pattern Recognition ----------------
def detect_bull_flag(df: pd.DataFrame, lookback: int = 40) -> dict:
    """
    Bull Flag: a pivot high (pole top) followed by a tight, slightly-downward
    consolidation channel before price breaks higher.

    Uses real pivot points:
      1. Find the most recent pivot high within lookback bars.
      2. Verify the move INTO that pivot high was >= 5% (the pole).
      3. After the pivot high, check that price consolidates in a narrow range
         (< 8% of the pivot-high price) with no new pivot high.
      4. Volume should dry up during the flag.
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)
    pivots = find_pivot_points(recent, left_bars=3, right_bars=3)
    phs = pivots["pivot_highs"]

    if not phs:
        return {"detected": False}

    # Use the most recent pivot high as the pole top
    pole_top = phs[-1]
    pole_bar  = pole_top["bar"]
    pole_price = pole_top["price"]

    # Need at least 3 bars of pole and 5 bars of flag
    if pole_bar < 3 or (len(recent) - 1 - pole_bar) < 5:
        return {"detected": False}

    pole_start_price = float(recent["Close"].iloc[max(0, pole_bar - 5)])
    initial_gain = (pole_price - pole_start_price) / pole_start_price if pole_start_price > 0 else 0
    strong_pole  = initial_gain >= 0.05

    # Flag = bars after the pivot high up to now
    flag_bars = recent.iloc[pole_bar:]
    flag_high  = float(flag_bars["High"].max())
    flag_low   = float(flag_bars["Low"].min())
    flag_range = (flag_high - flag_low) / pole_price if pole_price > 0 else 1

    tight_flag = flag_range < 0.08

    # Flag should not make a new high above the pole
    no_new_high = flag_high <= pole_price * 1.01

    # Volume dry-up during flag
    pole_bars_slice = recent.iloc[max(0, pole_bar - 5):pole_bar + 1]
    vol_pole = pole_bars_slice["Volume"].mean() if len(pole_bars_slice) > 0 else 1
    vol_flag = flag_bars["Volume"].mean() if len(flag_bars) > 0 else vol_pole
    volume_decrease = vol_flag < vol_pole * 0.85

    detected = strong_pole and tight_flag and no_new_high
    confidence = 0
    if detected:
        confidence = 65
        if volume_decrease:        confidence += 15
        if flag_range < 0.05:      confidence += 10
        if initial_gain >= 0.10:   confidence += 10

    return {
        "detected": detected,
        "confidence": min(100, confidence),
        "initial_gain": round(initial_gain * 100, 1),
        "consolidation_range": round(flag_range * 100, 1),
    }


def detect_cup_and_handle(df: pd.DataFrame, lookback: int = 60) -> dict:
    """
    Cup and Handle: uses pivot points to find a real left-rim high, cup-bottom low,
    and right-rim recovery before a small handle pullback.

      1. Find a significant pivot high (left rim) and the deepest pivot low after it (cup bottom).
      2. Verify the right side recovers to >= 92% of the left rim.
      3. Verify cup depth is 12–40%.
      4. The last 20% of bars form a tight handle (< 10% range).
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)
    pivots = find_pivot_points(recent, left_bars=3, right_bars=3)
    phs = pivots["pivot_highs"]
    pls = pivots["pivot_lows"]

    if len(phs) < 1 or len(pls) < 1:
        return {"detected": False}

    # Left rim = first significant pivot high
    left_rim    = phs[0]
    left_bar    = left_rim["bar"]
    left_price  = left_rim["price"]

    # Cup bottom = deepest pivot low AFTER the left rim
    lows_after = [p for p in pls if p["bar"] > left_bar]
    if not lows_after:
        return {"detected": False}
    cup_bottom = min(lows_after, key=lambda p: p["price"])
    bottom_bar  = cup_bottom["bar"]
    bottom_price = cup_bottom["price"]

    cup_depth = (left_price - bottom_price) / left_price if left_price > 0 else 0
    valid_depth = 0.12 <= cup_depth <= 0.40

    # Right side recovery: max high after cup bottom
    right_slice = recent.iloc[bottom_bar:]
    if right_slice.empty:
        return {"detected": False}
    right_high = float(right_slice["High"].max())
    recovery   = right_high >= left_price * 0.92

    # Handle: last 20% of bars should be tight (< 10% range)
    handle_start = max(bottom_bar, len(recent) - max(5, lookback // 5))
    handle_bars  = recent.iloc[handle_start:]
    if handle_bars.empty:
        return {"detected": False}
    handle_range = (float(handle_bars["High"].max()) - float(handle_bars["Low"].min())) / left_price
    small_handle = handle_range < 0.10

    detected = valid_depth and recovery and small_handle
    confidence = 0
    if detected:
        confidence = 70
        if 0.15 <= cup_depth <= 0.30:      confidence += 15
        if right_high >= left_price * 0.97: confidence += 15

    return {
        "detected": detected,
        "confidence": min(100, confidence),
        "cup_depth": round(cup_depth * 100, 1),
        "recovery_pct": round((right_high / left_price - 1) * 100, 1),
    }


def detect_double_bottom(df: pd.DataFrame, lookback: int = 50) -> dict:
    """
    Double Bottom: two real pivot lows at similar price levels separated by a
    meaningful bounce, with current price approaching or above the peak between them.

      1. Find all pivot lows in the window.
      2. Identify any two pivot lows within 4% of each other separated by >= 5 bars.
      3. Verify a meaningful peak (>= 5%) exists between the two lows.
      4. Breakout = current price > that peak.
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)
    pivots = find_pivot_points(recent, left_bars=3, right_bars=3)
    pls = pivots["pivot_lows"]

    if len(pls) < 2:
        return {"detected": False}

    best = None  # (similarity, first_low, second_low, peak)
    for i in range(len(pls) - 1):
        for j in range(i + 1, len(pls)):
            p1, p2 = pls[i], pls[j]
            if p2["bar"] - p1["bar"] < 5:
                continue  # too close together
            similarity = abs(p1["price"] - p2["price"]) / p1["price"]
            if similarity >= 0.04:
                continue  # lows too different

            # Peak between them
            between = recent.iloc[p1["bar"]:p2["bar"] + 1]
            if between.empty:
                continue
            peak = float(between["High"].max())
            peak_height = (peak - min(p1["price"], p2["price"])) / min(p1["price"], p2["price"])
            if peak_height < 0.05:
                continue  # no meaningful bounce

            if best is None or similarity < best[0]:
                best = (similarity, p1, p2, peak)

    if best is None:
        return {"detected": False}

    similarity, p1, p2, peak = best
    current_price = float(recent["Close"].iloc[-1])
    breakout = current_price > peak * 1.005

    confidence = 65
    if similarity < 0.02:  confidence += 15
    if breakout:           confidence += 20

    return {
        "detected": True,
        "confidence": min(100, confidence),
        "low_similarity": round(similarity * 100, 1),
        "breakout": breakout,
    }


def detect_ascending_triangle(df: pd.DataFrame, lookback: int = 50) -> dict:
    """
    Ascending Triangle: flat pivot highs (resistance) with progressively higher
    pivot lows (rising support).

      1. Find pivot highs within 2.5% of each other (flat resistance).
      2. Require >= 2 such pivot highs.
      3. Confirm pivot lows are trending upward.
      4. Bonus: volume contraction.
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)
    pivots = find_pivot_points(recent, left_bars=3, right_bars=3)
    phs = pivots["pivot_highs"]
    pls = pivots["pivot_lows"]

    if len(phs) < 2 or len(pls) < 2:
        return {"detected": False}

    # Find the highest pivot high as the resistance zone
    resistance = max(phs, key=lambda p: p["price"])["price"]
    flat_highs  = [p for p in phs if abs(p["price"] - resistance) / resistance <= 0.025]
    multiple_touches = len(flat_highs) >= 2

    # Pivot lows should be rising
    pl_prices = [p["price"] for p in pls]
    rising_lows = len(pl_prices) >= 2 and pl_prices[-1] > pl_prices[0] * 1.01

    # Volume contraction
    mid = len(recent) // 2
    vol_first  = recent.iloc[:mid]["Volume"].mean()
    vol_second = recent.iloc[mid:]["Volume"].mean()
    volume_contraction = vol_second < vol_first

    detected = multiple_touches and rising_lows
    confidence = 0
    if detected:
        confidence = 62
        if len(flat_highs) >= 3:     confidence += 15
        if volume_contraction:        confidence += 13
        n = len(pl_prices)
        if n >= 2 and pl_prices[-1] > pl_prices[0] * 1.04:
            confidence += 10

    return {
        "detected": detected,
        "confidence": min(100, confidence),
        "resistance_touches": len(flat_highs),
        "support_rising": rising_lows,
    }


def detect_bearish_flag(df: pd.DataFrame, lookback: int = 40) -> dict:
    """
    Bear Flag: a pivot low (pole bottom) followed by a tight, slightly-upward
    drift before price breaks lower again.

      1. Find the most recent pivot low within lookback bars.
      2. Verify the move INTO that pivot low was >= 5% decline.
      3. After the pivot low, check tight consolidation (< 8%) with slight upward drift.
      4. Volume dries up during flag.
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)
    pivots = find_pivot_points(recent, left_bars=3, right_bars=3)
    pls = pivots["pivot_lows"]

    if not pls:
        return {"detected": False}

    pole_bottom = pls[-1]
    pole_bar    = pole_bottom["bar"]
    pole_price  = pole_bottom["price"]

    if pole_bar < 3 or (len(recent) - 1 - pole_bar) < 5:
        return {"detected": False}

    pole_start_price = float(recent["Close"].iloc[max(0, pole_bar - 5)])
    initial_drop = (pole_start_price - pole_price) / pole_start_price if pole_start_price > 0 else 0
    strong_pole  = initial_drop >= 0.05

    flag_bars = recent.iloc[pole_bar:]
    flag_high  = float(flag_bars["High"].max())
    flag_low   = float(flag_bars["Low"].min())
    flag_range = (flag_high - flag_low) / pole_price if pole_price > 0 else 1
    tight_flag = flag_range < 0.08

    # Flag drifts slightly upward (bearish flag retraces up)
    upward_drift = float(flag_bars["Close"].iloc[-1]) > float(flag_bars["Close"].iloc[0])

    # No new low below pole
    no_new_low = flag_low >= pole_price * 0.99

    vol_pole = recent.iloc[max(0, pole_bar - 5):pole_bar + 1]["Volume"].mean()
    vol_flag = flag_bars["Volume"].mean() if len(flag_bars) > 0 else vol_pole
    volume_decrease = vol_flag < vol_pole * 0.85

    detected = strong_pole and tight_flag and upward_drift and no_new_low
    confidence = 0
    if detected:
        confidence = 65
        if volume_decrease:      confidence += 15
        if flag_range < 0.05:    confidence += 10
        if initial_drop >= 0.10: confidence += 10

    return {
        "detected": detected,
        "confidence": min(100, confidence),
        "initial_drop": round(initial_drop * 100, 1),
        "consolidation_range": round(flag_range * 100, 1),
    }


def detect_double_top(df: pd.DataFrame, lookback: int = 50) -> dict:
    """
    Double Top: two real pivot highs at similar price levels separated by a
    meaningful trough, with current price approaching or below that trough.

      1. Find all pivot highs in the window.
      2. Identify any two pivot highs within 4% of each other separated by >= 5 bars.
      3. Verify a meaningful trough (>= 5% drop) exists between them.
      4. Breakdown = current price < that trough.
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)
    pivots = find_pivot_points(recent, left_bars=3, right_bars=3)
    phs = pivots["pivot_highs"]

    if len(phs) < 2:
        return {"detected": False}

    best = None
    for i in range(len(phs) - 1):
        for j in range(i + 1, len(phs)):
            p1, p2 = phs[i], phs[j]
            if p2["bar"] - p1["bar"] < 5:
                continue
            similarity = abs(p1["price"] - p2["price"]) / p1["price"]
            if similarity >= 0.04:
                continue

            between = recent.iloc[p1["bar"]:p2["bar"] + 1]
            if between.empty:
                continue
            trough = float(between["Low"].min())
            trough_depth = (max(p1["price"], p2["price"]) - trough) / max(p1["price"], p2["price"])
            if trough_depth < 0.05:
                continue

            if best is None or similarity < best[0]:
                best = (similarity, p1, p2, trough)

    if best is None:
        return {"detected": False}

    similarity, p1, p2, trough = best
    current_price = float(recent["Close"].iloc[-1])
    breakdown = current_price < trough * 0.995

    confidence = 65
    if similarity < 0.02:  confidence += 15
    if breakdown:          confidence += 20

    return {
        "detected": True,
        "confidence": min(100, confidence),
        "high_similarity": round(similarity * 100, 1),
        "breakdown": breakdown,
    }


def detect_head_and_shoulders(df: pd.DataFrame, lookback: int = 60) -> dict:
    """
    Head & Shoulders: three pivot highs where the middle (head) is highest,
    outer two (shoulders) are at similar levels, and price is near/below the neckline.

      1. Require at least 3 pivot highs.
      2. For every combination of 3 pivots: check head > both shoulders by >= 2%.
      3. Shoulders within 6% of each other.
      4. Neckline = average of the two troughs between the peaks.
      5. Breakdown = price < neckline.
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)
    pivots = find_pivot_points(recent, left_bars=3, right_bars=3)
    phs = pivots["pivot_highs"]

    if len(phs) < 3:
        return {"detected": False}

    best = None
    for i in range(len(phs) - 2):
        ls, head, rs = phs[i], phs[i + 1], phs[i + 2]
        # Head must be clearly above both shoulders
        if not (head["price"] > ls["price"] * 1.02 and head["price"] > rs["price"] * 1.02):
            continue
        # Shoulders at similar level
        shoulder_sim = abs(ls["price"] - rs["price"]) / ls["price"]
        if shoulder_sim >= 0.06:
            continue

        # Neckline from troughs between peaks
        left_trough  = float(recent.iloc[ls["bar"]:head["bar"] + 1]["Low"].min())
        right_trough = float(recent.iloc[head["bar"]:rs["bar"] + 1]["Low"].min())
        neckline = (left_trough + right_trough) / 2

        if best is None or shoulder_sim < best[0]:
            best = (shoulder_sim, ls, head, rs, neckline)

    if best is None:
        return {"detected": False}

    shoulder_sim, ls, head, rs, neckline = best
    current_price = float(recent["Close"].iloc[-1])
    near_neckline = current_price <= neckline * 1.04
    breakdown     = current_price < neckline * 0.99

    if not near_neckline:
        return {"detected": False}

    confidence = 65
    if shoulder_sim < 0.03:  confidence += 15
    if breakdown:             confidence += 20

    return {
        "detected": True,
        "confidence": min(100, confidence),
        "shoulder_similarity": round(shoulder_sim * 100, 1),
        "breakdown": breakdown,
        "neckline": round(neckline, 2),
    }


def detect_descending_triangle(df: pd.DataFrame, lookback: int = 50) -> dict:
    """
    Descending Triangle: flat pivot lows (support zone) with progressively lower
    pivot highs (declining resistance).

      1. Find pivot lows within 2.5% of each other (flat support).
      2. Require >= 2 such pivot lows.
      3. Confirm pivot highs are trending downward.
      4. Bonus: volume contraction.
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)
    pivots = find_pivot_points(recent, left_bars=3, right_bars=3)
    phs = pivots["pivot_highs"]
    pls = pivots["pivot_lows"]

    if len(pls) < 2 or len(phs) < 2:
        return {"detected": False}

    # Flat support: pivot lows within 2.5% of the lowest
    support = min(pls, key=lambda p: p["price"])["price"]
    flat_lows = [p for p in pls if abs(p["price"] - support) / support <= 0.025]
    multiple_touches = len(flat_lows) >= 2

    # Declining pivot highs
    ph_prices = [p["price"] for p in phs]
    declining_highs = len(ph_prices) >= 2 and ph_prices[-1] < ph_prices[0] * 0.99

    mid = len(recent) // 2
    vol_first  = recent.iloc[:mid]["Volume"].mean()
    vol_second = recent.iloc[mid:]["Volume"].mean()
    volume_contraction = vol_second < vol_first

    detected = multiple_touches and declining_highs
    confidence = 0
    if detected:
        confidence = 62
        if len(flat_lows) >= 3:   confidence += 15
        if volume_contraction:     confidence += 13
        if ph_prices[-1] < ph_prices[0] * 0.95:
            confidence += 10

    return {
        "detected": detected,
        "confidence": min(100, confidence),
        "support_touches": len(flat_lows),
        "highs_declining": declining_highs,
    }


def detect_patterns(df: pd.DataFrame) -> list:
    """
    Detect all chart patterns (bullish and bearish) and return sorted by confidence.
    """
    patterns = []

    # ── Bullish patterns ────────────────────────────────────────────────────
    bull_flag = detect_bull_flag(df, lookback=20)
    if bull_flag["detected"]:
        patterns.append({
            "type": "Bull Flag",
            "confidence": bull_flag["confidence"],
            "bias": "Bullish",
            "description": f"Strong move up ({bull_flag['initial_gain']}%) followed by tight consolidation",
            "action": "Buy breakout above consolidation high with volume",
        })

    cup_handle = detect_cup_and_handle(df, lookback=40)
    if cup_handle["detected"]:
        patterns.append({
            "type": "Cup and Handle",
            "confidence": cup_handle["confidence"],
            "bias": "Bullish",
            "description": f"U-shaped recovery ({cup_handle['cup_depth']}% depth) with handle",
            "action": "Buy breakout above handle high",
        })

    double_bottom = detect_double_bottom(df, lookback=30)
    if double_bottom["detected"]:
        patterns.append({
            "type": "Double Bottom",
            "confidence": double_bottom["confidence"],
            "bias": "Bullish",
            "description": f"Two lows at similar price ({double_bottom['low_similarity']}% apart)",
            "action": "Buy breakout above middle peak" if not double_bottom["breakout"] else "Already breaking out!",
        })

    asc_triangle = detect_ascending_triangle(df, lookback=30)
    if asc_triangle["detected"]:
        patterns.append({
            "type": "Ascending Triangle",
            "confidence": asc_triangle["confidence"],
            "bias": "Bullish",
            "description": f"Flat resistance with {asc_triangle['resistance_touches']} touches, rising support",
            "action": "Buy breakout above resistance with volume surge",
        })

    # ── Bearish patterns ────────────────────────────────────────────────────
    bear_flag = detect_bearish_flag(df, lookback=20)
    if bear_flag["detected"]:
        patterns.append({
            "type": "Bear Flag",
            "confidence": bear_flag["confidence"],
            "bias": "Bearish",
            "description": f"Strong drop ({bear_flag['initial_drop']}%) followed by tight upward drift",
            "action": "Avoid long — breakdown below consolidation low targets further downside",
        })

    double_top = detect_double_top(df, lookback=30)
    if double_top["detected"]:
        patterns.append({
            "type": "Double Top",
            "confidence": double_top["confidence"],
            "bias": "Bearish",
            "description": f"Two highs at similar price ({double_top['high_similarity']}% apart)",
            "action": "Avoid long — breakdown below trough confirms reversal" if not double_top["breakdown"] else "Already breaking down!",
        })

    hs = detect_head_and_shoulders(df, lookback=40)
    if hs["detected"]:
        patterns.append({
            "type": "Head & Shoulders",
            "confidence": hs["confidence"],
            "bias": "Bearish",
            "description": f"Classic reversal — neckline at ${hs['neckline']}, shoulders within {hs['shoulder_similarity']}%",
            "action": "Avoid long — break below neckline signals trend reversal" if not hs["breakdown"] else "Neckline broken — high risk!",
        })

    desc_triangle = detect_descending_triangle(df, lookback=30)
    if desc_triangle["detected"]:
        patterns.append({
            "type": "Descending Triangle",
            "confidence": desc_triangle["confidence"],
            "bias": "Bearish",
            "description": f"Flat support with {desc_triangle['support_touches']} touches, declining highs",
            "action": "Avoid long — breakdown below support triggers measured move lower",
        })

    # Sort by confidence (highest first)
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
