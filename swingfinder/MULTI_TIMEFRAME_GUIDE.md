# 📊 Multi-Timeframe Analysis Guide

## Overview

The **Multi-Timeframe Analysis (MTF)** feature allows you to analyze a stock across multiple timeframes simultaneously to confirm trend strength and improve trade timing. This is a **FREE feature** that uses your existing Tiingo API data.

---

## 🎯 What It Does

Multi-Timeframe Analysis:
1. **Analyzes** the same stock across 3 timeframes: Daily, Weekly, and 4-Hour
2. **Calculates** key indicators (EMA20/50, RSI, MACD) for each timeframe
3. **Determines** trend direction and momentum for each timeframe
4. **Calculates** trend alignment score (% of timeframes that agree)
5. **Provides** trading recommendations based on timeframe alignment

---

## 🚀 How to Use

### Step 1: Navigate to Analyzer
- Go to **Analyzer** page
- Enter a stock symbol (e.g., AAPL)
- Click **"Analyze"**

### Step 2: Enable Multi-Timeframe View
- Scroll down past the main chart and Fibonacci analysis
- Check the box: **"📊 Show Multi-Timeframe Analysis"**
- Wait 2-3 seconds for data to load

### Step 3: Review the Analysis
- **Trend Alignment Score** - Shows % of timeframes in agreement
- **Recommendation** - Trading signal based on MTF analysis
- **Individual Timeframes** - Detailed view of each timeframe
- **Insights** - Specific observations and warnings

---

## 📊 Understanding the Timeframes

### 📅 Daily Timeframe
- **Purpose:** Primary timeframe for swing trading
- **Best For:** Entry timing and short-term trend
- **Lookback:** 200 days of data
- **Key Use:** Confirms immediate trend direction

### 📊 Weekly Timeframe
- **Purpose:** Higher timeframe confirmation
- **Best For:** Overall trend direction and major support/resistance
- **Lookback:** ~2 years of data
- **Key Use:** Validates swing trade direction

### ⏰ 4-Hour Timeframe
- **Purpose:** Intraday trend and entry precision
- **Best For:** Fine-tuning entry points
- **Lookback:** 30 days of data
- **Key Use:** Confirms short-term momentum

---

## 🎯 Trend Alignment Score

The alignment score shows what % of timeframes agree on trend direction:

### 100% Alignment (All Bullish)
- **Signal:** 🟢 **STRONG BUY**
- **Meaning:** All timeframes in uptrend
- **Action:** High-conviction setup, strong entry signal
- **Example:** Daily ↑, Weekly ↑, 4-Hour ↑

### 66-99% Alignment (Majority Bullish)
- **Signal:** 🟢 **BUY** or 🟡 **CAUTIOUS BUY**
- **Meaning:** 2 out of 3 timeframes bullish
- **Action:** Good setup if weekly is bullish
- **Example:** Daily ↑, Weekly ↑, 4-Hour ↓

### 33-65% Alignment (Mixed)
- **Signal:** 🟡 **NEUTRAL**
- **Meaning:** Timeframes disagree
- **Action:** Wait for clarity or short-term trade only
- **Example:** Daily ↑, Weekly ↓, 4-Hour ↑

### 0-32% Alignment (Majority Bearish)
- **Signal:** 🔴 **AVOID** or 🔴 **WEAK SETUP**
- **Meaning:** Most timeframes bearish
- **Action:** Look for better opportunities
- **Example:** Daily ↓, Weekly ↓, 4-Hour ↑

---

## 💡 Trading Recommendations

### 🟢 STRONG BUY SIGNAL
- **Criteria:** 100% alignment (all timeframes bullish)
- **Meaning:** Perfect setup with all timeframes confirming
- **Action:** High-conviction entry, larger position size
- **Risk:** Lower (all timeframes aligned)

### 🟢 BUY SIGNAL
- **Criteria:** 66%+ alignment with weekly uptrend
- **Meaning:** Good swing trade setup
- **Action:** Standard entry, normal position size
- **Risk:** Moderate (one timeframe may be against you)

### 🟡 CAUTIOUS BUY
- **Criteria:** 66%+ alignment but weekly downtrend
- **Meaning:** Mixed signals, higher risk
- **Action:** Smaller position, tighter stops
- **Risk:** Higher (weekly resistance)

### 🟡 NEUTRAL
- **Criteria:** 33-65% alignment
- **Meaning:** No clear direction
- **Action:** Wait for better setup or day trade only
- **Risk:** High (conflicting signals)

### 🔴 AVOID / WEAK SETUP
- **Criteria:** <33% alignment
- **Meaning:** Most timeframes bearish
- **Action:** Skip this trade, find better opportunities
- **Risk:** Very high (trend against you)

---

## 📈 How to Interpret Each Timeframe

### For Each Timeframe, You'll See:

**Trend:**
- 🟢 **Uptrend** - EMA20 > EMA50 (bullish)
- 🔴 **Downtrend** - EMA20 < EMA50 (bearish)

**RSI (Relative Strength Index):**
- **> 70** - Overbought (potential pullback)
- **50-70** - Strong momentum
- **30-50** - Neutral/weak momentum
- **< 30** - Oversold (potential bounce)

**Momentum:**
- **Strong** - RSI > 60 (bullish momentum)
- **Neutral** - RSI 40-60 (balanced)
- **Weak** - RSI < 40 (bearish momentum)

**EMA20 & EMA50:**
- Shows current moving average values
- Compare to current price for trend confirmation

---

## 💡 Multi-Timeframe Insights

The MTF feature provides automatic insights:

### ✅ Perfect Alignment
- All timeframes bullish
- High-conviction setup

### ❌ Perfect Misalignment
- All timeframes bearish
- Avoid this trade

### ✅ Weekly Uptrend
- Higher timeframe supports swing trades
- Good for multi-day holds

### ⚠️ Weekly Downtrend
- Higher timeframe resistance
- Be cautious, use tight stops

### ⚠️ Timeframe Divergence
- Daily bullish but weekly bearish
- Short-term trade only, don't hold long

### 💡 Pullback Opportunity
- Weekly uptrend with daily pullback
- Watch for reversal back to weekly trend

### ⚠️ Overbought
- Daily RSI > 70
- Consider waiting for pullback

### 💡 Oversold
- Daily RSI < 30
- Potential bounce opportunity

---

## 🎓 Trading Strategies Using MTF

### Strategy 1: High-Conviction Entries
**Goal:** Only trade when all timeframes align

**Rules:**
1. Wait for 100% alignment (all timeframes bullish)
2. Enter on daily pullback within weekly uptrend
3. Use larger position size (higher confidence)
4. Hold for weekly target

**Example:**
- Weekly: Uptrend, RSI 55
- Daily: Uptrend, RSI 45 (pullback)
- 4-Hour: Uptrend, RSI 50
- **Action:** Strong buy signal, enter on daily pullback

### Strategy 2: Pullback Trading
**Goal:** Buy pullbacks in strong weekly uptrends

**Rules:**
1. Weekly must be in uptrend
2. Daily shows pullback (downtrend or low RSI)
3. 4-Hour shows reversal signs
4. Enter when daily starts to turn up

**Example:**
- Weekly: Uptrend, RSI 60
- Daily: Downtrend, RSI 35 (oversold)
- 4-Hour: Starting to turn up
- **Action:** Wait for daily reversal, then enter

### Strategy 3: Avoid Weak Setups
**Goal:** Filter out low-probability trades

**Rules:**
1. Skip if alignment < 50%
2. Skip if weekly is in downtrend
3. Skip if daily RSI > 75 (overbought)
4. Only trade high-alignment setups

**Example:**
- Weekly: Downtrend
- Daily: Uptrend (counter-trend)
- 4-Hour: Mixed
- **Action:** Skip this trade, find better setup

---

## ⚠️ Important Notes

### Limitations
- **4-Hour data** may be limited for some stocks (requires Tiingo Power plan)
- **Weekly data** updates slower (once per week)
- **Alignment** doesn't guarantee success, just improves probability

### Best Practices
- ✅ Always check weekly trend before swing trading
- ✅ Use MTF to confirm scanner signals
- ✅ Wait for high alignment (66%+) for best setups
- ✅ Combine MTF with Fibonacci and support/resistance
- ✅ Use tighter stops when alignment is low

### When to Use MTF
- ✅ Before entering a swing trade
- ✅ To confirm scanner results
- ✅ When deciding position size
- ✅ To identify pullback opportunities
- ✅ To avoid weak setups

---

## 💰 Cost

**FREE!** Multi-Timeframe Analysis uses:
- Your existing Tiingo API subscription ($30/month)
- No additional API costs
- No extra fees

---

## 🚀 Next Steps

After reviewing MTF analysis:
1. **High Alignment (75%+)** → Enter with confidence
2. **Moderate Alignment (50-75%)** → Smaller position, tighter stops
3. **Low Alignment (<50%)** → Skip or wait for better setup
4. **Combine with Fibonacci** → Look for discount zone + high alignment
5. **Check Entry Checklist** → Confirm all entry criteria

**Remember:** MTF improves probability but doesn't guarantee success. Always use proper risk management!

