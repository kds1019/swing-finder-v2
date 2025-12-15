# 📊 SwingFinder Trading Rules & Strategy Guide

This guide explains **exactly how SwingFinder builds trade plans** and what rules it uses to find setups.

---

## 🎯 Core Trading Philosophy

SwingFinder is built for **swing trading** - holding positions for **days to weeks** (not day trading).

**Key Principles:**
- ✅ **Trend-following** - Only trade stocks in uptrends (EMA20 > EMA50)
- ✅ **Risk management** - Always use stops (1.5× ATR below entry)
- ✅ **2:1 Reward/Risk** - Target is 2× the risk amount
- ✅ **Quality over quantity** - Strict filters to avoid noise

---

## 📐 Technical Indicators Used

### **1. Moving Averages (Trend Direction)**
- **EMA20** (20-day Exponential Moving Average) - Short-term trend
- **EMA50** (50-day Exponential Moving Average) - Long-term trend
- **Rule:** Stock MUST have EMA20 > EMA50 to qualify (uptrend confirmation)

### **2. RSI14 (Momentum)**
- **RSI14** (14-day Relative Strength Index) - Measures momentum
- **Range:** 0-100
- **Oversold:** < 30 (too weak)
- **Overbought:** > 70 (too strong)
- **Sweet spot:** 40-67 for most setups

### **3. Bollinger Band Position (Price Location)**
- **BandPos20** - Where price sits within the 20-day Bollinger Bands
- **0.0** = At lower band (oversold)
- **0.5** = At middle (neutral)
- **1.0** = At upper band (overbought)

### **4. ATR14 (Volatility)**
- **ATR14** (14-day Average True Range) - Measures volatility
- **Used for:** Stop loss and target calculations
- **Stop:** Entry - (1.5 × ATR)
- **Target:** Entry + (2 × Risk)

### **5. Support/Resistance Levels**
- **HH20** - Highest high in last 20 days (resistance)
- **LL20** - Lowest low in last 20 days (support)

---

## 🔍 Setup Types (What SwingFinder Looks For)

### **1. Breakout Setup 💥**

**What it is:** Stock breaking above resistance with strong momentum

**Requirements:**
- ✅ EMA20 > EMA50 (uptrend)
- ✅ RSI14 > 55 (strong momentum)
- ✅ BandPos20 > 0.55 (price in upper half of range)

**Entry Strategy:**
- Wait for price to **break and hold above resistance** on strong volume
- Enter after a confirmed push/close above that zone
- Stop just below the breakout base or last consolidation low

**Example:** Stock at $50, resistance at $52. Wait for close above $52 with volume, enter at $52.50

---

### **2. Pullback Setup 📉**

**What it is:** Stock in uptrend pulling back to support, ready to bounce

**Requirements:**
- ✅ EMA20 > EMA50 (uptrend)
- ✅ RSI14 < 60 (momentum cooling off)
- ✅ BandPos20 ≤ 0.45 (price in lower half of range)
- ✅ Price ≤ EMA20 (pulled back to moving average support)

**Entry Strategy:**
- Let the dip **stabilize near support/EMA20**
- Look for a **green reversal candle** on rising volume
- Enter **above the reversal high**
- Stop below the swing low

**Example:** Stock at $50, pulls back to $47 (EMA20). Wait for green candle, enter at $48

---

### **3. Near Miss (Watch List) 👀**

**What it is:** Stock that's CLOSE to a setup but not quite there yet

**Criteria:**
- RSI between 40-67 (reasonable momentum)
- BandPos between 0.20-0.70 (not extreme)
- Within 15% of resistance (breakout proximity)
- Within 4× ATR of support (pullback proximity)

**Action:** Add to watchlist, monitor for confirmation

---

## 🎲 Smart Score (0-100)

SwingFinder calculates a **Smart Score** to rank setups by quality.

**Scoring Breakdown:**

**Base Score:** 50 (neutral)

**For Breakout Setups:**
- +25 points max for strong RSI (higher = better)
- +15 points max for high band position (higher = better)

**For Pullback Setups:**
- +25 points max for deeper dip (lower RSI = better)
- +15 points max for lower band position (lower = better)

**Trend Bonus:**
- +10 points if EMA20 > EMA50 (uptrend)
- -10 points if EMA20 < EMA50 (downtrend)

**Smart Mode Bonus (if enabled):**
- +10 points if stock is in favored sector
- -5 points if stock is NOT in favored sector

**Final Score:** Clamped to 0-100

**Interpretation:**
- **80-100:** Excellent setup (A grade)
- **70-79:** Good setup (B grade)
- **60-69:** Decent setup (C grade)
- **50-59:** Marginal setup (D grade)
- **0-49:** Weak setup (F grade)

---

## 🛡️ Risk Management Rules

### **Stop Loss Calculation:**
```
Stop = Entry Price - (1.5 × ATR14)
```

**Example:** Entry at $50, ATR = $2
- Stop = $50 - (1.5 × $2) = $50 - $3 = **$47**

### **Target Calculation:**
```
Risk = Entry - Stop
Target = Entry + (2 × Risk)
```

**Example:** Entry at $50, Stop at $47
- Risk = $50 - $47 = $3
- Target = $50 + (2 × $3) = $50 + $6 = **$56**

**This gives you a 2:1 Reward/Risk ratio**

---

## 🔢 Filter Settings

### **Basic Filters (Applied to ALL stocks):**

**Price Range:**
- Minimum: $5.00 (avoid penny stocks)
- Maximum: $500.00 (avoid expensive stocks)

**Volume:**
- Minimum: 500,000 shares/day (avoid illiquid stocks)

**Data Quality:**
- Must have at least 60 days of price history
- Must have valid price and volume data

### **Mode-Specific Filters:**

**Breakout Mode:**
- EMA20 > EMA50 ✅
- RSI14 > 55 ✅
- BandPos20 > 0.55 ✅

**Pullback Mode:**
- EMA20 > EMA50 ✅
- RSI14 < 60 ✅
- BandPos20 ≤ 0.45 ✅
- Price ≤ EMA20 ✅

**Both Mode:**
- EMA20 > EMA50 ✅ (only requirement - catches everything trending up)

---

## 🧠 Smart Mode (Advanced)

When enabled, Smart Mode adds **market context** to improve filtering.

### **Market Bias Detection:**
- Analyzes SPY (S&P 500) to determine overall market trend
- **Uptrend:** Market is strong → Be MORE lenient with filters (catch more opportunities)
- **Downtrend:** Market is weak → Be MORE strict with filters (avoid traps)

### **Filter Adjustments:**

**In Uptrend Markets:**
- RSI requirement: -3 points (e.g., 55 → 52 for breakouts)
- Band requirement: -0.05 (e.g., 0.55 → 0.50)
- **Result:** More setups qualify

**In Downtrend Markets:**
- RSI requirement: +3 points (e.g., 55 → 58 for breakouts)
- Band requirement: +0.05 (e.g., 0.55 → 0.60)
- **Result:** Fewer setups qualify (only the strongest)

### **Sector Rotation:**
- Identifies which sectors are leading (Technology, Healthcare, etc.)
- Boosts Smart Score for stocks in strong sectors
- Helps you focus on where the money is flowing

---

## 📊 Fundamental Score (Watchlist Only)

For watchlist stocks, SwingFinder adds a **Fundamental Score** using Yahoo Finance data.

**Scoring (0-100):**

**Profitability (30 points):**
- Profit Margin > 20%: 30 points
- Profit Margin > 10%: 20 points
- Profit Margin > 0%: 10 points

**Debt Levels (25 points):**
- Debt/Equity < 30%: 25 points
- Debt/Equity < 70%: 15 points
- Debt/Equity < 150%: 5 points

**Liquidity (20 points):**
- Current Ratio > 2.0: 20 points
- Current Ratio > 1.0: 10 points

**Return on Equity (25 points):**
- ROE > 20%: 25 points
- ROE > 15%: 15 points
- ROE > 10%: 10 points
- ROE > 0%: 5 points

**Grades:** A (80+), B (70+), C (60+), D (50+), F (<50)

---

## 🎯 How to Use SwingFinder Effectively

### **Step 1: Run the Scanner**
1. Set your price range (e.g., $5-$100)
2. Set minimum volume (e.g., 500,000)
3. Choose mode: Breakout, Pullback, or Both
4. Click "Run Scan"

### **Step 2: Review Results**
- **Confirmed Setups** tab: Ready to trade NOW
- **Near Misses** tab: Watch for confirmation
- Sort by Smart Score (highest = best quality)

### **Step 3: Analyze the Setup**
- Click "Analyze" to see detailed chart
- Review entry guidance (breakout vs pullback strategy)
- Check support/resistance levels
- Verify stop and target make sense

### **Step 4: Plan Your Trade**
- Entry: Follow the setup guidance
- Stop: Use the calculated stop loss
- Target: Use the calculated target (2:1 R/R)
- Position size: Risk 1-2% of account per trade

### **Step 5: Execute & Monitor**
- Enter the trade when conditions are met
- Set your stop loss immediately
- Monitor in "Active Trades" tab
- Exit at target or if stop is hit

---

## ⚠️ Important Notes

**What SwingFinder Does:**
- ✅ Finds high-probability swing trade setups
- ✅ Calculates stops and targets
- ✅ Ranks setups by quality
- ✅ Provides entry guidance

**What SwingFinder Does NOT Do:**
- ❌ Guarantee profits (no system does)
- ❌ Tell you WHEN to enter (you decide timing)
- ❌ Replace your own analysis (it's a tool, not a crystal ball)
- ❌ Work in all market conditions (best in trending markets)

**Best Practices:**
- 📊 Always verify setups on a chart before trading
- 🛡️ ALWAYS use stop losses (never skip this!)
- 💰 Risk only 1-2% of your account per trade
- 📈 Trade with the trend (don't fight the market)
- 🧘 Be patient - wait for quality setups
- 📝 Keep a trading journal to track what works

---

## 🚀 Summary

SwingFinder uses **proven technical analysis** to find swing trade setups:

1. **Trend Filter:** Only uptrends (EMA20 > EMA50)
2. **Setup Detection:** Breakouts (momentum) or Pullbacks (dips)
3. **Quality Scoring:** Smart Score ranks best opportunities
4. **Risk Management:** 1.5× ATR stops, 2:1 R/R targets
5. **Market Context:** Smart Mode adjusts for market conditions

**The goal:** Find high-probability setups with favorable risk/reward in trending stocks.

---

**Happy Trading! 🎯📈**

