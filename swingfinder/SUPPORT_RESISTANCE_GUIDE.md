# 🎯 Auto Support/Resistance Detection Guide

## Overview

**Auto Support/Resistance Detection** automatically identifies key price levels where stocks are likely to bounce (support) or reverse (resistance). This is a **FREE feature** that uses advanced pivot point detection to find the most significant levels based on historical price action.

---

## 🎯 What It Does

The S/R Detection feature:
1. **Identifies** key support and resistance levels using pivot point analysis
2. **Scores** each level based on strength (number of touches)
3. **Displays** levels visually on price charts with color-coded lines
4. **Calculates** distance to nearest levels and risk/reward ratios
5. **Alerts** when price is near key levels (within 2%)

---

## 📊 How It Works

### **Detection Algorithm:**

1. **Find Pivot Points**
   - Scans historical price data for swing highs (resistance) and swing lows (support)
   - Uses a rolling window (default: 10 periods) to identify local peaks and valleys

2. **Cluster Nearby Levels**
   - Groups levels within 2% of each other
   - Averages clustered levels to create clean zones

3. **Calculate Strength**
   - Counts how many times price touched each level (within 1%)
   - Assigns strength score: 0-100 based on touch count
   - More touches = stronger level

4. **Filter Relevant Levels**
   - Keeps only resistance above current price
   - Keeps only support below current price
   - Shows top 3 most significant levels in each direction

---

## 🎨 Visual Display

### **On Price Charts:**

**Resistance Lines (Red/Orange/Yellow):**
- 🔴 **Dark Red** - Strong resistance (80+ strength)
- 🟠 **Orange** - Moderate resistance (60-79 strength)
- 🟡 **Yellow** - Weak resistance (below 60 strength)

**Support Lines (Green):**
- 🟢 **Dark Green** - Strong support (80+ strength)
- 🟢 **Green** - Moderate support (60-79 strength)
- 🟡 **Light Green** - Weak support (below 60 strength)

**Line Thickness:**
- Thicker lines = stronger levels
- Thinner lines = weaker levels

---

## 📋 Information Displayed

### **Summary Metrics:**

1. **Current Price** - Latest closing price
   - Shows if price is near a key level (within 2%)

2. **Nearest Resistance**
   - Price of closest resistance above
   - Distance in percentage
   - Strength score (0-100)

3. **Nearest Support**
   - Price of closest support below
   - Distance in percentage
   - Strength score (0-100)

### **Detailed Level Cards:**

**Resistance Levels:**
- Price and distance from current price
- Number of touches (how many times price tested this level)
- Strength rating: Strong (80+), Moderate (60-79), Weak (<60)

**Support Levels:**
- Price and distance from current price
- Number of touches
- Strength rating

---

## 💡 Trading Insights

The feature provides automatic trading insights:

### **1. Near Resistance Alert**
- **Within 2%:** "⚠️ Near Resistance - Consider taking profits or waiting for breakout"
- **Within 5%:** "📊 Approaching Resistance - Watch for rejection or breakout"

### **2. Near Support Alert**
- **Within 2%:** "✅ Near Support - Potential bounce opportunity"
- **Within 5%:** "📊 Approaching Support - Watch for bounce or breakdown"

### **3. Risk/Reward Analysis**
- Calculates R:R ratio using nearest support (risk) and resistance (reward)
- **Good:** R:R ≥ 2:1 (🎯 Good Risk/Reward)
- **Moderate:** R:R ≥ 1:1 (⚖️ Moderate Risk/Reward)
- **Poor:** R:R < 1:1 (⚠️ Poor Risk/Reward - wait for better setup)

---

## 🚀 How to Use

### **Step 1: Open Analyzer**
- Go to **📊 Stock Analyzer** page
- Enter a stock symbol (e.g., AAPL, TSLA, NVDA)
- Click **"Analyze"**

### **Step 2: View S/R Levels on Chart**
- Scroll to the price chart
- Look for horizontal lines:
  - Red/Orange lines above price = Resistance
  - Green lines below price = Support
- Thicker, darker lines = stronger levels

### **Step 3: Review S/R Section**
- Scroll down to **"🎯 Auto Support/Resistance Detection"** section
- Check summary metrics:
  - Current price and proximity to levels
  - Nearest resistance and support
- Review detailed level cards for all detected levels

### **Step 4: Read Trading Insights**
- Check the **"💡 S/R Trading Insights"** section
- Follow recommendations based on price position
- Use R:R ratio to evaluate trade quality

---

## 📈 Trading Strategies Using S/R

### **Strategy 1: Support Bounce Entries**
**Goal:** Buy at support for bounce plays

**How to Use:**
1. Wait for price to approach strong support (within 2%)
2. Look for bullish confirmation (RSI oversold, bullish candlestick)
3. Enter when price bounces off support
4. Set stop loss just below support
5. Target nearest resistance for exit

**Example:**
- AAPL at $175, strong support at $172 (strength: 85)
- Price drops to $172.50 (within 2%)
- RSI at 32 (oversold)
- **Action:** Buy at $172.50, stop at $171, target resistance at $180

---

### **Strategy 2: Resistance Rejection Exits**
**Goal:** Take profits before resistance

**How to Use:**
1. Monitor existing positions as they approach resistance
2. If within 2% of strong resistance, consider taking profits
3. Or tighten stop loss to lock in gains
4. Wait for breakout confirmation before re-entering

**Example:**
- Holding TSLA from $240, now at $258
- Strong resistance at $260 (strength: 90)
- **Action:** Take profits at $259, or set trailing stop at $256

---

### **Strategy 3: Breakout Trades**
**Goal:** Trade breakouts above resistance

**How to Use:**
1. Identify strong resistance level
2. Wait for price to break above resistance with volume
3. Enter on pullback to broken resistance (now support)
4. Set stop below new support
5. Target next resistance level

**Example:**
- NVDA resistance at $500 (strength: 75)
- Price breaks to $505 on high volume
- Pullback to $501
- **Action:** Buy at $501, stop at $498, target $520

---

### **Strategy 4: Risk/Reward Filtering**
**Goal:** Only take trades with good R:R

**How to Use:**
1. Check R:R ratio in trading insights
2. Only enter if R:R ≥ 2:1
3. Use nearest support as stop loss
4. Use nearest resistance as profit target

**Example:**
- Current price: $50
- Nearest support: $48 (risk = $2)
- Nearest resistance: $56 (reward = $6)
- R:R = 3:1 ✅ **Good trade!**

---

## ⚙️ Customization

The S/R detection can be customized in `utils/indicators.py`:

```python
sr_levels = find_support_resistance(
    df, 
    window=10,      # Pivot detection window (default: 10)
    num_levels=3    # Number of levels to show (default: 3)
)
```

**Parameters:**
- `window`: Larger = fewer, stronger levels. Smaller = more levels, less significant
- `num_levels`: How many support/resistance levels to display

---

## 💰 Cost

**100% FREE!** No additional costs beyond your existing setup.

---

## ⚠️ Important Notes

### **Limitations:**
- S/R levels are based on historical data (not predictive)
- Levels can break - always use stop losses
- Strength score is relative (not absolute)
- Works best on liquid stocks with clear price action

### **Best Practices:**
- ✅ Combine with other indicators (RSI, MACD, volume)
- ✅ Use stronger levels (80+ strength) for higher probability
- ✅ Wait for confirmation before entering at levels
- ✅ Always use stop losses below support / above resistance
- ✅ Check multiple timeframes for confluence

### **Tips:**
- **Strong levels (80+):** High probability of holding
- **Moderate levels (60-79):** May hold, watch for confirmation
- **Weak levels (<60):** Less reliable, use with caution
- **Multiple touches:** More touches = stronger level
- **Near level (within 2%):** High probability of reaction

---

## 🎉 Summary

Auto Support/Resistance Detection gives you:
- ✅ Automatic identification of key price levels
- ✅ Visual display on charts with color-coded strength
- ✅ Detailed metrics and strength scores
- ✅ Trading insights and R:R calculations
- ✅ Alerts when price approaches levels

**Use it to:**
- Find better entry points at support
- Take profits before resistance
- Trade breakouts with confirmation
- Filter trades by risk/reward ratio

**Remember:** S/R levels are tools, not guarantees. Always combine with other analysis and use proper risk management!

