
import pandas as pd
import numpy as np

def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()

def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gains = (delta.clip(lower=0)).ewm(alpha=1/length, adjust=False).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1/length, adjust=False).mean()
    rs = gains / (losses.replace(0, np.nan))
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)

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

    return df
