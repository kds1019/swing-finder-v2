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


def prepare_features(df: pd.DataFrame, lookback: int = 500, days_ahead: int = 5) -> tuple:
    """
    Prepare features for ML models using up to `lookback` bars of history.
    Returns (X, y, feature_names).

    Target: `days_ahead`-period forward return  (close[t+N]/close[t] - 1).
    The model predicts this return directly — no post-hoc scaling is applied.

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
        return None, None, None, None

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

    if len(features) < max(20, days_ahead + 1):
        return None, None, None, None

    # ── Target: N-day forward return (compute while close is still raw $) ────
    # Must be done BEFORE normalization so the ratio uses real price values.
    fwd_close  = features["close"].shift(-days_ahead)   # NaN for last N rows
    fwd_return = fwd_close / features["close"] - 1      # fractional return
    y = fwd_return.iloc[:-days_ahead].values             # shape (n - N,)

    # ── Target distribution diagnostics ─────────────────────────────────────
    # Computed here, before normalization changes the features, so y is still
    # the raw forward-return array in fractional form.
    _cap = 0.04 * days_ahead                             # sanity cap threshold
    y_stats = {
        "n_samples":    int(len(y)),
        "n_features":   int(features.shape[1] - 1),     # -1: close not yet dropped
        "mean_pct":     round(float(np.mean(y))   * 100, 3),
        "std_pct":      round(float(np.std(y))    * 100, 3),
        "min_pct":      round(float(np.min(y))    * 100, 3),
        "p25_pct":      round(float(np.percentile(y, 25)) * 100, 3),
        "median_pct":   round(float(np.median(y)) * 100, 3),
        "p75_pct":      round(float(np.percentile(y, 75)) * 100, 3),
        "max_pct":      round(float(np.max(y))    * 100, 3),
        "pct_positive": round(float(np.mean(y > 0)) * 100, 1),
        "pct_capped":   round(float(np.mean(np.abs(y) >= _cap)) * 100, 1),
        "days_ahead":   days_ahead,
    }

    # ── Normalize features to dimensionless ratios ───────────────────────────
    # Raw dollar prices drift by 20-80% over a 2-year training window.
    # A model trained on absolute prices learns price level, not dynamics.
    # Expressing every price feature as a ratio to the row's own close makes
    # the features scale-invariant across stocks and across time.
    c = features["close"]                                        # reference price

    # Price features → ratio to current close (value of 0 means "at close")
    for col in ["high", "low", "ma5", "ma10", "ma20"]:
        if col in features.columns:
            features[col] = features[col] / c - 1
    for col in ["ema20", "ema50"]:
        if col in features.columns:
            features[col] = features[col] / c - 1
    if "macd" in features.columns:
        features["macd"] = features["macd"] / c          # MACD is in price units
    if "volatility" in features.columns:
        features["volatility"] = features["volatility"] / c   # relative std
    for lag in [1, 2, 3, 5]:
        col = f"close_lag_{lag}"
        if col in features.columns:
            features[col] = features[col] / c - 1        # N-day return to that lag

    # Volume features → ratio to 20-day rolling mean volume
    vol_ref = features["volume"].rolling(20, min_periods=5).mean().bfill()
    features["volume"] = features["volume"] / vol_ref
    for lag in [1, 2, 3, 5]:
        col = f"volume_lag_{lag}"
        if col in features.columns:
            features[col] = features[col] / vol_ref

    # Clean up any inf/NaN introduced by division (edge case: zero volume)
    features = features.replace([np.inf, -np.inf], np.nan).fillna(0)

    # Drop raw close — it is 1.0 everywhere after normalization (no information)
    features = features.drop(columns=["close"])

    # ── Build X (chronological order preserved — no shuffle) ─────────────────
    feature_names = features.columns.tolist()
    X = features.iloc[:-days_ahead].values               # shape (n - N, n_features)
    return X, y, feature_names, y_stats


def random_forest_forecast(df: pd.DataFrame, days_ahead: int = 5) -> Dict[str, Any]:
    """
    Use Random Forest to forecast future prices.
    Target is the `days_ahead`-period forward return predicted directly —
    no linear/compound scaling applied after prediction.
    """
    try:
        from sklearn.ensemble import RandomForestRegressor

        X, y, feature_names, y_stats = prepare_features(df, lookback=500, days_ahead=days_ahead)

        if X is None or len(X) < 20:
            return {"success": False, "error": "Insufficient data"}

        # Chronological train/test split — first 80% trains, last 20% validates.
        # No shuffle: shuffling a time series leaks future bars into training.
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # No feature scaling for RF — decision trees are scale-invariant.
        # Train Random Forest
        rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_train, y_train)

        # Validation score — clamp R² to [0, 1] before using anywhere.
        # R² can be negative when the model is worse than a flat-line predictor;
        # a negative value would invert blend weights and show nonsensical confidence.
        train_score = rf_model.score(X_train, y_train)
        test_score  = float(np.clip(rf_model.score(X_test, y_test), 0.0, 1.0))

        # Predict N-day forward return from the most-recent feature row
        last_features    = X[-1].reshape(1, -1)
        predicted_return = float(rf_model.predict(last_features)[0])

        # Sanity cap: ±4% per day max (artifacts beyond this aren't credible)
        max_move         = 0.04 * days_ahead
        predicted_return = float(np.clip(predicted_return, -max_move, max_move))

        current_price  = float(df["Close"].iloc[-1])
        forecast_price = current_price * (1 + predicted_return)

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
            "predicted_return": round(predicted_return * 100, 2),   # % for display
            "r2_score": test_score,                                 # raw clamped R² for weighting
            "confidence": round(test_score * 100, 1),               # display-only percentage
            "train_score": round(float(np.clip(train_score, 0.0, 1.0)) * 100, 1),
            "top_features": top_features,
            "model_type": "Random Forest",
            "y_stats": y_stats,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def gradient_boosting_forecast(df: pd.DataFrame, days_ahead: int = 5) -> Dict[str, Any]:
    """
    Use Gradient Boosting to forecast future prices.
    Target is the `days_ahead`-period forward return predicted directly —
    no linear/compound scaling applied after prediction.
    """
    try:
        from sklearn.ensemble import GradientBoostingRegressor

        X, y, feature_names, y_stats = prepare_features(df, lookback=500, days_ahead=days_ahead)

        if X is None or len(X) < 20:
            return {"success": False, "error": "Insufficient data"}

        # Chronological train/test split — first 80% trains, last 20% validates.
        # No shuffle: shuffling a time series leaks future bars into training.
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Feature scaling for GB: StandardScaler fitted on train only.
        # Fit on X_train → transform X_train, X_test, and final prediction row
        # with the same parameters to prevent data leakage.
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test  = scaler.transform(X_test)

        # Train Gradient Boosting
        gb_model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        gb_model.fit(X_train, y_train)

        # Validation score — clamp R² to [0, 1] before using anywhere.
        # R² can be negative when the model is worse than a flat-line predictor;
        # a negative value would invert blend weights and show nonsensical confidence.
        train_score = gb_model.score(X_train, y_train)
        test_score  = float(np.clip(gb_model.score(X_test, y_test), 0.0, 1.0))

        # Predict N-day forward return from the most-recent feature row.
        # Apply the same scaler fitted on X_train — must NOT refit on this row.
        last_features    = scaler.transform(X[-1].reshape(1, -1))
        predicted_return = float(gb_model.predict(last_features)[0])

        # Sanity cap: ±4% per day max (artifacts beyond this aren't credible)
        max_move         = 0.04 * days_ahead
        predicted_return = float(np.clip(predicted_return, -max_move, max_move))

        current_price  = float(df["Close"].iloc[-1])
        forecast_price = current_price * (1 + predicted_return)

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
            "predicted_return": round(predicted_return * 100, 2),   # % for display
            "r2_score": test_score,                                 # raw clamped R² for weighting
            "confidence": round(test_score * 100, 1),               # display-only percentage
            "train_score": round(float(np.clip(train_score, 0.0, 1.0)) * 100, 1),
            "top_features": top_features,
            "model_type": "Gradient Boosting",
            "y_stats": y_stats,
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
    
    # Ensemble: weighted average using clamped R² scores [0, 1] as blend weights.
    # Using r2_score (not confidence) avoids the ×100 artefact and guarantees
    # weights stay in [0, 1] with no sign-flip risk.
    rf_r2 = rf_result["r2_score"]   # already clamped to [0, 1]
    gb_r2 = gb_result["r2_score"]
    total_r2 = rf_r2 + gb_r2

    if total_r2 < 1e-9:
        # Both models performed at chance level — fall back to equal weighting
        rf_weight = gb_weight = 0.5
    else:
        rf_weight = rf_r2 / total_r2
        gb_weight = gb_r2 / total_r2

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
        "agreement": round(abs(rf_result["forecast_price"] - gb_result["forecast_price"]) / ensemble_price * 100, 1),
        "y_stats": rf_result.get("y_stats"),   # same data for both models; RF copy forwarded
    }

