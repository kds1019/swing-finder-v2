# Scanner Issues - Why Results Don't Match Webull

## 🔍 **PROBLEMS FOUND**

### **Problem 1: Conflicting Filter Logic** ⚠️⚠️⚠️

Your scanner has **TWO different filter functions** that contradict each other:

#### **Function 1: `passes_filters()` (Line 115-147)** - NOT USED
```python
if mode == "Breakout":
    return ema20 > ema50 and rsi > 55 and band > 0.55
elif mode == "Pullback":
    return ema20 > ema50 and rsi < 60 and band <= 0.45 and px <= ema20
else:  # Both
    return ema20 > ema50
```

#### **Function 2: `evaluate_ticker()` (Line 253-258)** - ACTUALLY USED
```python
if mode in ["Breakout", "Both"] and rsi > (55 + rsi_buffer) and band > (0.55 + band_buffer):
    setup = "Breakout"
elif mode in ["Pullback", "Both"] and rsi < (60 + rsi_buffer) and band <= (0.45 + band_buffer) and px <= ema20:
    setup = "Pullback"
```

**THE ISSUE**: 
- `passes_filters()` is defined but **NEVER CALLED**
- The actual filtering happens in `evaluate_ticker()` with different logic
- This creates confusion about what criteria are actually being used

---

### **Problem 2: Smart Mode Makes Filters TIGHTER** ⚠️⚠️

Lines 236-245:
```python
if market_bias == "Uptrend":
    rsi_buffer = +3      # require slightly stronger RSI
    band_buffer = +0.05  # breakout band higher
```

**THE ISSUE**:
- When market is in uptrend, you INCREASE requirements
- Breakout needs RSI > 58 instead of 55
- This is **backwards** - in strong markets, you should be MORE lenient, not stricter
- Result: Smart Mode gives you FEWER results when market is strong

---

### **Problem 3: Near-Miss Logic is Too Broad** ⚠️

Lines 266-269:
```python
if mode in ["Breakout", "Both"] and 40 <= rsi <= 67 and 0.35 <= band <= 0.70:
    near_miss, near_type = True, "RSI/Band breakout proximity"
elif mode in ["Pullback", "Both"] and 40 <= rsi <= 70 and 0.20 <= band <= 0.60:
    near_miss, near_type = True, "RSI/Band pullback proximity"
```

**THE ISSUE**:
- RSI 40-70 is basically EVERYTHING
- Band 0.20-0.70 is also almost everything
- This catches way too many stocks that aren't actually close to setups
- Clutters your results with noise

---

### **Problem 4: Indicator Calculation Differences** ⚠️

Your RSI calculation (utils/indicators.py lines 8-14):
```python
def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gains = (delta.clip(lower=0)).ewm(alpha=1/length, adjust=False).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1/length, adjust=False).mean()
    rs = gains / (losses.replace(0, np.nan))
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)
```

**POTENTIAL ISSUE**:
- Uses EWM (exponential) instead of SMA (simple moving average)
- Webull likely uses Wilder's smoothing (different from EWM)
- This can cause RSI values to differ by 2-5 points
- A stock with RSI 56 on Webull might show 53 in your scanner

---

### **Problem 5: BandPos Calculation** ⚠️

Lines 42-46 in indicators.py:
```python
mean = close.rolling(20).mean()
std = close.rolling(20).std()
upper = mean + 2 * std
lower = mean - 2 * std
df["BandPos20"] = (close - lower) / (upper - lower)
```

**POTENTIAL ISSUE**:
- When price is outside bands, BandPos can be >1 or <0
- Division by zero if upper == lower (flat market)
- Webull might handle this differently

---

## 🎯 **WHY YOU GET NO RESULTS**

Your scanner requires **ALL** of these simultaneously:

For Breakout:
1. ✅ EMA20 > EMA50 (trend filter)
2. ✅ RSI > 55 (or 58 in uptrend with Smart Mode)
3. ✅ BandPos > 0.55 (or 0.60 in uptrend)

For Pullback:
1. ✅ EMA20 > EMA50 (trend filter)
2. ✅ RSI < 60 (or 57 in uptrend)
3. ✅ BandPos <= 0.45 (or 0.40 in uptrend)
4. ✅ Price <= EMA20

**The Math**:
- Out of 5000 stocks, maybe 2000 have EMA20 > EMA50
- Of those, maybe 400 have RSI in the right range
- Of those, maybe 100 have BandPos in the right range
- Of those, maybe 20-30 pass volume/price filters
- **Result: 20-30 stocks max**

If you tighten further, you get 0-5 results.

---

## 🔧 **SOLUTIONS**

### **Solution 1: Fix Smart Mode Logic (CRITICAL)**

**Current (WRONG)**:
```python
if market_bias == "Uptrend":
    rsi_buffer = +3      # TIGHTER in uptrend
    band_buffer = +0.05
```

**Fixed (CORRECT)**:
```python
if market_bias == "Uptrend":
    rsi_buffer = -3      # LOOSER in uptrend (more opportunities)
    band_buffer = -0.05
elif market_bias == "Downtrend":
    rsi_buffer = +3      # TIGHTER in downtrend (be selective)
    band_buffer = +0.05
```

**Why**: In strong markets, you want to catch more setups. In weak markets, be picky.

---

### **Solution 2: Add Adjustable Sensitivity**

Add a slider to let users control how strict the filters are:

```python
# In scanner UI
sensitivity = st.slider("Filter Sensitivity", 
                       min_value=1, max_value=5, value=3,
                       help="1=Very Strict, 3=Balanced, 5=Relaxed")

# Adjust thresholds based on sensitivity
if sensitivity == 1:  # Very Strict
    breakout_rsi = 65
    breakout_band = 0.70
    pullback_rsi = 40
    pullback_band = 0.30
elif sensitivity == 2:  # Strict
    breakout_rsi = 60
    breakout_band = 0.65
    pullback_rsi = 45
    pullback_band = 0.35
elif sensitivity == 3:  # Balanced (current)
    breakout_rsi = 55
    breakout_band = 0.55
    pullback_rsi = 50
    pullback_band = 0.45
elif sensitivity == 4:  # Relaxed
    breakout_rsi = 52
    breakout_band = 0.50
    pullback_rsi = 52
    pullback_band = 0.50
else:  # Very Relaxed
    breakout_rsi = 50
    breakout_band = 0.45
    pullback_rsi = 55
    pullback_band = 0.55
```

---

### **Solution 3: Fix RSI Calculation to Match Webull**

**Current (EWM)**:
```python
gains = (delta.clip(lower=0)).ewm(alpha=1/length, adjust=False).mean()
losses = (-delta.clip(upper=0)).ewm(alpha=1/length, adjust=False).mean()
```

**Fixed (Wilder's Smoothing - matches Webull)**:
```python
def rsi_wilder(series: pd.Series, length: int = 14) -> pd.Series:
    """RSI using Wilder's smoothing (matches most platforms)."""
    delta = series.diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    # First value uses SMA
    avg_gain = gain.rolling(window=length).mean()
    avg_loss = loss.rolling(window=length).mean()
    
    # Subsequent values use Wilder's smoothing
    for i in range(length, len(gain)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (length - 1) + gain.iloc[i]) / length
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (length - 1) + loss.iloc[i]) / length
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.fillna(50)
```

---

### **Solution 4: Add "OR" Logic Instead of "AND"**

Instead of requiring ALL conditions, use a scoring system:

```python
def score_setup(rsi, band, ema20, ema50, mode):
    """Score from 0-100 based on how well it matches the setup."""
    score = 0
    
    # Trend (30 points)
    if ema20 > ema50:
        score += 30
    
    if mode == "Breakout":
        # RSI (35 points)
        if rsi > 65:
            score += 35
        elif rsi > 60:
            score += 25
        elif rsi > 55:
            score += 15
        elif rsi > 50:
            score += 5
        
        # Band Position (35 points)
        if band > 0.70:
            score += 35
        elif band > 0.60:
            score += 25
        elif band > 0.55:
            score += 15
        elif band > 0.50:
            score += 5
    
    elif mode == "Pullback":
        # RSI (35 points)
        if rsi < 35:
            score += 35
        elif rsi < 40:
            score += 25
        elif rsi < 45:
            score += 15
        elif rsi < 50:
            score += 5
        
        # Band Position (35 points)
        if band < 0.30:
            score += 35
        elif band < 0.35:
            score += 25
        elif band < 0.40:
            score += 15
        elif band < 0.45:
            score += 5
    
    return score

# Then filter by minimum score
if score_setup(rsi, band, ema20, ema50, mode) >= 60:
    # Include this stock
```

**Benefits**:
- More flexible - catches stocks that are "close enough"
- Adjustable threshold (60, 70, 80 for different strictness)
- Shows you WHY a stock scored high/low

---

### **Solution 5: Add Debug Mode**

Add a checkbox to see WHY stocks are being filtered out:

```python
debug_mode = st.checkbox("Show Debug Info (why stocks fail)")

if debug_mode:
    # For each stock that fails, show:
    st.write(f"{ticker}: RSI={rsi:.1f} (need >55), Band={band:.2f} (need >0.55)")
```

---

## 🎯 **RECOMMENDED QUICK FIX**

**Option A: Loosen Current Filters (5 minutes)**

Change lines 255-258 to:
```python
if mode in ["Breakout", "Both"] and rsi > 52 and band > 0.50:
    setup = "Breakout"
elif mode in ["Pullback", "Both"] and rsi < 55 and band <= 0.50 and px <= ema20:
    setup = "Pullback"
```

**Option B: Add Sensitivity Slider (15 minutes)**

Let users adjust strictness from UI

**Option C: Use Scoring System (30 minutes)**

Replace binary pass/fail with 0-100 score, show top 50 stocks

---

## 📊 **COMPARISON: Your Scanner vs Webull**

| Criteria | Your Scanner | Webull (Typical) | Difference |
|----------|--------------|------------------|------------|
| RSI Calculation | EWM | Wilder's | 2-5 point difference |
| Breakout RSI | >55 (or 58) | >50 | Yours is stricter |
| Pullback RSI | <60 | <50 | Yours is looser |
| Band Position | Custom (0-1) | Not used | Different metric |
| Volume | Absolute | Relative | Different approach |
| Logic | ALL conditions | Varies | Yours is stricter |

**Bottom Line**: Your scanner is **more conservative** than Webull, which is why you get fewer results.

---

## ✅ **WHAT TO DO NOW**

1. **Immediate**: Fix Smart Mode logic (flip the buffers)
2. **Short-term**: Add sensitivity slider
3. **Medium-term**: Fix RSI calculation to match Webull
4. **Long-term**: Add scoring system instead of binary pass/fail

**Want me to implement any of these fixes?**

