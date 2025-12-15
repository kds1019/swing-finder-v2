# 📊 Backtesting Feature Guide

## Overview

The **Backtesting Engine** allows you to test your scanner settings on historical data to validate performance before risking real money. This is a **FREE feature** that uses your existing Tiingo API data.

---

## 🎯 What It Does

The backtester:
1. **Simulates** running your scanner on past data (3 months to 2 years)
2. **Identifies** all setups that would have been flagged by your scanner
3. **Tracks** what would have happened if you traded every setup
4. **Calculates** win rate, average return, profit factor, and more
5. **Shows** best/worst trades, monthly performance, and exit reasons

---

## 🚀 How to Use

### Step 1: Navigate to Backtest Page
- Click **"Backtest"** in the sidebar navigation

### Step 2: Configure Settings

**Ticker Selection:**
- **Watchlist** - Test on your saved watchlist stocks
- **Full Universe** - Test on 100 stocks from the scanner universe
- **Custom List** - Enter specific tickers (e.g., AAPL, TSLA, NVDA)

**Test Period:**
- 3 Months (90 days)
- 6 Months (180 days)
- **1 Year (365 days)** ← Recommended
- 2 Years (730 days)

**Scanner Settings:**
- **Setup Mode:** Pullback, Breakout, or Both
- **Sensitivity:** 1-5 (matches scanner sensitivity)
- **Price Range:** Min/Max price filters
- **Min Volume:** Minimum daily volume

**Trade Management:**
- **Max Hold Days:** How long to hold each trade (default: 5 days)
- **Stop Loss:** ATR multiplier for stop (default: 1.5x ATR)
- **Take Profit:** R-multiple for target (default: 2R)

### Step 3: Run Backtest
- Click **"🚀 Run Backtest"** button
- Wait 1-2 minutes for results (depends on number of stocks)

### Step 4: Analyze Results
- Review **Overview** tab for key metrics
- Check **Performance** tab for charts and trends
- Browse **All Trades** tab for detailed trade list
- Read **Settings** tab for recommendations

---

## 📊 Key Metrics Explained

### Win Rate
- **What:** Percentage of winning trades
- **Good:** 50%+ (above breakeven)
- **Excellent:** 60%+ (strong edge)

### Average Return
- **What:** Average % return per trade
- **Good:** +1% to +2%
- **Excellent:** +2%+

### Profit Factor
- **What:** Gross Profit ÷ Gross Loss
- **Good:** 1.5+ (making $1.50 for every $1 lost)
- **Excellent:** 2.0+ (making $2 for every $1 lost)

### Avg R-Multiple
- **What:** Average risk/reward multiple
- **Good:** 0.5R+ (making half your risk on average)
- **Excellent:** 1.0R+ (making your full risk on average)

### Expectancy
- **What:** Average $ per trade (theoretical)
- **Good:** Positive (any amount above $0)
- **Excellent:** $5+ per trade

---

## 💡 How to Interpret Results

### ✅ Excellent Strategy (Trade with Confidence)
- Win Rate: 60%+
- Avg Return: +2%+
- Profit Factor: 2.0+
- **Action:** Use these settings for live trading!

### 👍 Good Strategy (Positive Expectancy)
- Win Rate: 50-60%
- Avg Return: +1% to +2%
- Profit Factor: 1.5-2.0
- **Action:** Consider optimizing further, but strategy is viable

### ⚠️ Needs Improvement
- Win Rate: 40-50%
- Avg Return: 0% to +1%
- Profit Factor: 1.0-1.5
- **Action:** Adjust sensitivity or focus on one setup type

### ❌ Poor Performance
- Win Rate: <40%
- Avg Return: Negative
- Profit Factor: <1.0
- **Action:** Change setup mode, sensitivity, or filters

---

## 🔧 Optimization Tips

### 1. Adjust Sensitivity
- **Lower (1-2):** Fewer but higher quality setups
- **Higher (4-5):** More setups but lower quality
- **Sweet Spot:** Usually 2-3 for best balance

### 2. Focus on Best Setup Type
- Check "Performance by Setup Type" in Performance tab
- If Pullbacks win 65% but Breakouts win 45%, focus on Pullbacks only

### 3. Optimize Price Range
- **$30-60:** Often better trends, less volatility
- **$10-20:** More volatile, higher risk/reward
- Test different ranges to find your edge

### 4. Test Different Hold Periods
- **3-5 days:** Quick profits, more trades
- **7-10 days:** Bigger moves, fewer trades
- Match hold period to your trading style

### 5. Adjust Risk Management
- **Tighter stops (1-1.5 ATR):** Less risk, more stop-outs
- **Wider stops (2-2.5 ATR):** More risk, fewer stop-outs
- Find balance between risk and win rate

---

## 📈 Example Use Cases

### Use Case 1: Validate Your Current Settings
**Goal:** Prove your scanner settings work before trading real money

**Steps:**
1. Set backtest to match your current scanner settings
2. Run on 1 year of data
3. Check if win rate > 50% and profit factor > 1.5
4. If yes → Trade with confidence!
5. If no → Optimize settings

### Use Case 2: Compare Pullback vs Breakout
**Goal:** Determine which setup type performs better

**Steps:**
1. Run backtest with "Pullback" mode
2. Note win rate and avg return
3. Run backtest with "Breakout" mode
4. Compare results
5. Focus on the better-performing setup type

### Use Case 3: Find Optimal Sensitivity
**Goal:** Find the sensitivity level with best risk/reward

**Steps:**
1. Run backtest with Sensitivity = 1
2. Run backtest with Sensitivity = 3
3. Run backtest with Sensitivity = 5
4. Compare total trades, win rate, and profit factor
5. Choose sensitivity with best balance

---

## ⚠️ Important Notes

### Limitations
- **Past performance ≠ future results** - Backtest shows historical edge, not guaranteed future profits
- **No slippage/commissions** - Real trading has costs not included in backtest
- **Perfect execution** - Assumes you trade every setup (in reality you may miss some)
- **Data quality** - Results depend on Tiingo data accuracy

### Best Practices
- ✅ Test on at least 6-12 months of data
- ✅ Test on 20+ stocks for statistical significance
- ✅ Compare multiple settings to find optimal configuration
- ✅ Use results to build confidence, not as guarantee
- ✅ Paper trade first before going live

---

## 🎓 Learning from Results

### High Win Rate but Low Avg Return
- **Diagnosis:** Taking profits too early
- **Fix:** Increase take profit target (2.5R or 3R)

### Low Win Rate but High Avg Return
- **Diagnosis:** Letting winners run, cutting losers
- **Fix:** This can work! Ensure profit factor > 1.5

### Many "Time Exit" trades
- **Diagnosis:** Setups not reaching target or stop
- **Fix:** Adjust hold days or tighten targets

### Many "Stop Loss" exits
- **Diagnosis:** Stops too tight or poor setups
- **Fix:** Widen stops or lower sensitivity

---

## 💰 Cost

**FREE!** The backtesting engine uses:
- Your existing Tiingo API subscription ($30/month)
- Python computation (runs locally)
- No additional API costs or fees

---

## 🚀 Next Steps

After backtesting:
1. **Optimize** your settings based on results
2. **Paper trade** with optimized settings for 2-4 weeks
3. **Start small** with real money (1-2 positions)
4. **Scale up** as you gain confidence

**Remember:** Backtesting builds confidence and helps optimize, but always start small with real money!

