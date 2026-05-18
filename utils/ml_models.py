"""
Advanced ML Models for Price Prediction
Uses Random Forest and Gradient Boosting for more accurate forecasts.
Training window: up to 2 years of daily bars.
VIX is included as a market-fear feature.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

# Minimum bars required before we'll attempt training
_MIN_BARS = 60


def _fetch_vix_history(start_date: str, end_date: str) -> pd.Series:
    """
    Fetch VIX daily close from Yahoo Finance and return as a date-indexed Series.
    Returns empty Series on failure so callers can proceed without VIX.
    """
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        hist = vix.history(start=start_date, end=end_date)
        if hist.empty:
            return pd.Series(dtype=float)
        series = hist["Close"].copy()
        idx = pd.to_datetime(series.index).normalize()
        series.index = idx.tz_convert(None) if idx.tz is not None else idx
        series.name = "vix"
        return series
    except Exception:
        return pd.Series(dtype=float)


def prepare_features(df: pd.DataFrame, lookback: int = 500) -> tuple:
    """
    Prepare features for ML models using up to `lookback` bars of history.
    Returns (X, y, feature_names).

    Features include:
    - OHLCV raw values
    - Technical indicators: RSI14, EMA20, EMA50, MACD (if present)
    - Derived: price_change %, volume_change %, high-low range
    - Rolling MAs: 5, 10, 20-day
    - Rolling volatility: 10-day std
    - Lag features: close & volume at 1, 2, 3, 5 days ago
    - VIX (market fear index) — aligned by date via Yahoo Finance
    """
    if len(df) < _MIN_BARS:
        return None, None, None

    recent = df.tail(lookback).copy()

    # Normalise date index to timezone-naive dates for VIX merge
    # Normalise to timezone-naive dates — handle both tz-aware and tz-naive indexes
    idx = pd.to_datetime(recent.index).normalize()
    recent.index = idx.tz_convert(None) if idx.tz is not None else idx

    # ── Fetch VIX aligned to the stock's date range ──────────────────────────
    start_str = recent.index[0].strftime("%Y-%m-%d")
    end_str   = (recent.index[-1] + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    vix_series = _fetch_vix_history(start_str, end_str)

    # Create features DataFrame
    features = pd.DataFrame(index=recent.index)

    # Price-based features
    features["close"]  = recent["Close"]
    features["high"]   = recent["High"]
    features["low"]    = recent["Low"]
    features["volume"] = recent["Volume"]

    # Technical indicators (if available)
    if "RSI14" in recent.columns:
        features["rsi"]   = recent["RSI14"]
    if "MACD" in recent.columns:
        features["macd"]  = recent["MACD"]
    if "EMA20" in recent.columns:
        features["ema20"] = recent["EMA20"]
    if "EMA50" in recent.columns:
        features["ema50"] = recent["EMA50"]

    # Derived features
    features["price_change"]  = recent["Close"].pct_change()
    features["volume_change"] = recent["Volume"].pct_change()
    features["high_low_range"]= (recent["High"] - recent["Low"]) / recent["Close"]

    # Rolling moving averages
    features["ma5"]  = recent["Close"].rolling(5).mean()
    features["ma10"] = recent["Close"].rolling(10).mean()
    features["ma20"] = recent["Close"].rolling(20).mean()

    # Rolling volatility (10-day std of close)
    features["volatility"] = recent["Close"].rolling(10).std()

    # Lag features
    for lag in [1, 2, 3, 5]:
        features[f"close_lag_{lag}"]  = recent["Close"].shift(lag)
        features[f"volume_lag_{lag}"] = recent["Volume"].shift(lag)

    # ── Merge VIX (forward-fill gaps; drop column if no overlap to avoid wiping rows) ─
    if not vix_series.empty:
        vix_aligned = vix_series.reindex(features.index, method="ffill")
        if vix_aligned.notna().sum() >= len(features) * 0.5:
            # Only add VIX if it covers at least half the rows; fill remaining NaN with median
            features["vix"] = vix_aligned.fillna(vix_aligned.median())
        # else: skip VIX silently — models train fine without it

    # Drop NaN rows then reset to a clean integer index to avoid DatetimeIndex
    # expansion bugs when aligning X and y with .loc
    features = features.dropna().reset_index(drop=True)

    if len(features) < 20:
        return None, None, None

    # Target: next day's close (shift by -1, last row becomes NaN)
    # Align X and y purely by position — drop the last row from both
    y = features["close"].shift(-1).iloc[:-1].values   # shape (n-1,)
    X = features.iloc[:-1].values                      # shape (n-1, n_features)

    feature_names = features.columns.tolist()
    return X, y, feature_names


def random_forest_forecast(df: pd.DataFrame, days_ahead: int = 5) -> Dict[str, Any]:
    """
    Use Random Forest to forecast future prices.
    """
    try:
        from sklearn.ensemble import RandomForestRegressor
        
        X, y, feature_names = prepare_features(df, lookback=500)

        if X is None or len(X) < 20:
            return {"success": False, "error": "Insufficient data"}

        # Train/test split (use last 20% for validation)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Train Random Forest
        rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_train, y_train)
        
        # Validation score
        train_score = rf_model.score(X_train, y_train)
        test_score = rf_model.score(X_test, y_test)
        
        # Predict next day
        last_features = X[-1].reshape(1, -1)
        next_day_pred = rf_model.predict(last_features)[0]
        
        # Simple projection for days_ahead
        current_price = df["Close"].iloc[-1]
        daily_change = (next_day_pred - current_price) / current_price
        forecast_price = current_price * (1 + daily_change * days_ahead)
        
        # Feature importance
        importances = rf_model.feature_importances_
        top_features = sorted(
            zip(feature_names, importances),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "success": True,
            "forecast_price": round(forecast_price, 2),
            "next_day_price": round(next_day_pred, 2),
            "confidence": round(test_score * 100, 1),
            "train_score": round(train_score * 100, 1),
            "top_features": top_features,
            "model_type": "Random Forest"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def gradient_boosting_forecast(df: pd.DataFrame, days_ahead: int = 5) -> Dict[str, Any]:
    """
    Use Gradient Boosting to forecast future prices.
    """
    try:
        from sklearn.ensemble import GradientBoostingRegressor
        
        X, y, feature_names = prepare_features(df, lookback=500)

        if X is None or len(X) < 20:
            return {"success": False, "error": "Insufficient data"}

        # Train/test split
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Train Gradient Boosting
        gb_model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        gb_model.fit(X_train, y_train)
        
        # Validation score
        train_score = gb_model.score(X_train, y_train)
        test_score = gb_model.score(X_test, y_test)
        
        # Predict next day
        last_features = X[-1].reshape(1, -1)
        next_day_pred = gb_model.predict(last_features)[0]
        
        # Simple projection for days_ahead
        current_price = df["Close"].iloc[-1]
        daily_change = (next_day_pred - current_price) / current_price
        forecast_price = current_price * (1 + daily_change * days_ahead)
        
        # Feature importance
        importances = gb_model.feature_importances_
        top_features = sorted(
            zip(feature_names, importances),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "success": True,
            "forecast_price": round(forecast_price, 2),
            "next_day_price": round(next_day_pred, 2),
            "confidence": round(test_score * 100, 1),
            "train_score": round(train_score * 100, 1),
            "top_features": top_features,
            "model_type": "Gradient Boosting"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def ensemble_ml_forecast(df: pd.DataFrame, days_ahead: int = 5) -> Dict[str, Any]:
    """
    Combine Random Forest and Gradient Boosting for ensemble prediction.
    """
    rf_result = random_forest_forecast(df, days_ahead)
    gb_result = gradient_boosting_forecast(df, days_ahead)
    
    if not rf_result["success"] or not gb_result["success"]:
        return {
            "success": False,
            "error": "One or more models failed",
            "rf_error": rf_result.get("error"),
            "gb_error": gb_result.get("error")
        }
    
    # Ensemble: weighted average based on confidence
    rf_weight = rf_result["confidence"] / (rf_result["confidence"] + gb_result["confidence"])
    gb_weight = gb_result["confidence"] / (rf_result["confidence"] + gb_result["confidence"])
    
    ensemble_price = (rf_result["forecast_price"] * rf_weight + 
                     gb_result["forecast_price"] * gb_weight)
    
    ensemble_confidence = (rf_result["confidence"] + gb_result["confidence"]) / 2
    
    # Prediction range
    forecast_low = min(rf_result["forecast_price"], gb_result["forecast_price"])
    forecast_high = max(rf_result["forecast_price"], gb_result["forecast_price"])
    
    return {
        "success": True,
        "ensemble_price": round(ensemble_price, 2),
        "forecast_low": round(forecast_low, 2),
        "forecast_high": round(forecast_high, 2),
        "confidence": round(ensemble_confidence, 1),
        "rf_prediction": rf_result["forecast_price"],
        "gb_prediction": gb_result["forecast_price"],
        "rf_confidence": rf_result["confidence"],
        "gb_confidence": gb_result["confidence"],
        "agreement": round(abs(rf_result["forecast_price"] - gb_result["forecast_price"]) / ensemble_price * 100, 1)
    }

