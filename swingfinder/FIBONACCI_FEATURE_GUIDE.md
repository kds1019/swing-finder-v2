# 📊 Fibonacci Retracement Feature Guide

## ✅ **What Was Added**

Your SwingFinder app now includes **full Fibonacci retracement analysis** to help you find better entry prices in the "discount zone" (0-50% Fibonacci retracement).

---

## 🎯 **What is Fibonacci Retracement?**

Fibonacci retracement is a technical analysis tool that uses horizontal lines to indicate areas of support or resistance at the key Fibonacci levels before the price continues in the original direction.

### **Key Fibonacci Levels:**
- **0%** - Swing High (recent peak)
- **23.6%** - First retracement level
- **38.2%** - Strong support/resistance level
- **50%** - Equilibrium (halfway point)
- **61.8%** - Golden ratio (strongest level)
- **78.6%** - Deep retracement
- **100%** - Swing Low (recent bottom)

### **Discount vs Premium Zones:**
- **💎 Discount Zone (0-50%):** Price is in the lower half of the range - better risk/reward for entries
- **⚠️ Premium Zone (50-100%):** Price is in the upper half of the range - higher risk, less favorable entries

---

## 🚀 **New Features Added**

### **1. Fibonacci Calculation (utils/indicators.py)**
- Automatically calculates Fibonacci levels based on recent 20-day swing high/low
- Determines current price position as percentage (0-100%)
- Identifies discount vs premium zone
- Suggests optimal entry price at nearest Fib level

### **2. Smart Score Adjustment (scanner.py)**
Your Smart Score now includes Fibonacci weighting:
- **Deep Discount (≤38.2%):** +15 points
- **Discount Zone (38.2-50%):** +10 points
- **Premium Zone (61.8-78.6%):** -10 points
- **Extended Premium (≥78.6%):** -15 points

### **3. Fibonacci Badges on Cards (scanner.py)**
Every result card now shows:
- **💎 Discount Entry (XX% Fib)** - Green badge for discount zone
- **⚠️ Premium Zone (XX% Fib)** - Orange badge for premium zone

### **4. Optional Fibonacci Filter (scanner.py)**
New checkbox in the scanner UI:
- **"💎 Only show Discount Zone entries (below 50% Fib)"**
- **Default: OFF** (shows all results)
- **When enabled:** Filters to only show discount zone entries

### **5. Fibonacci Lines on Charts (analyzer.py)**
The analyzer now displays:
- **Horizontal Fibonacci lines** at each key level (23.6%, 38.2%, 50%, 61.8%, 78.6%)
- **Color-coded zones:**
  - Light green background for discount zone (0-50%)
  - Light red background for premium zone (50-100%)
- **Zone labels** on the chart

### **6. Fibonacci Metrics Section (analyzer.py)**
New metrics display showing:
- **Fibonacci Position:** Current price as % of range
- **Current Zone:** Discount or Premium
- **Optimal Entry:** Suggested entry price at nearest Fib level
- **Swing Range:** High/Low prices used for calculation
- **Key Fibonacci Levels:** All 7 Fib levels with prices

---

## 📖 **How to Use**

### **Scenario 1: Building a Watchlist (Default Behavior)**
1. Run the scanner with default settings (Fib filter OFF)
2. You'll see ALL results with Fibonacci badges
3. Results in discount zone get 💎 badge and higher Smart Score
4. Results in premium zone get ⚠️ badge and lower Smart Score
5. Add ALL interesting stocks to your watchlist
6. Focus on the 💎 discount entries first
7. Monitor the ⚠️ premium entries for pullbacks

### **Scenario 2: Finding Only Best Entries (Filtered)**
1. Enable the checkbox: **"💎 Only show Discount Zone entries"**
2. Run the scanner
3. You'll only see stocks in the discount zone (0-50% Fib)
4. All results will have 💎 badges
5. Sort by Smart Score to find the best setups
6. Trade the top 5-10 highest-scoring discount entries

### **Scenario 3: Analyzing a Specific Stock**
1. Send a stock to the Analyzer
2. View the chart with Fibonacci lines overlaid
3. Check the Fibonacci Metrics section:
   - Is it in the discount or premium zone?
   - How close is current price to optimal entry?
   - What are the key support/resistance levels (Fib levels)?
4. Use this info to time your entry better

---

## 💡 **Trading Strategy with Fibonacci**

### **For Pullback Setups:**
1. Wait for stock to pull back into discount zone (below 50% Fib)
2. Look for entries at **38.2%** or **50%** Fibonacci levels
3. Set stop below **61.8%** or swing low
4. Target previous swing high or higher

### **For Breakout Setups:**
1. Prefer breakouts that occur FROM the discount zone (stronger)
2. Avoid breakouts from extended premium zone (weaker, more likely to fail)
3. Use Fibonacci levels as profit targets on the way up

### **Risk Management:**
- **Best entries:** Deep discount zone (0-38.2%)
- **Good entries:** Discount zone (38.2-50%)
- **Caution:** Equilibrium (50-61.8%)
- **Avoid:** Premium zone (61.8-100%) unless strong catalyst

---

## 🎨 **Visual Guide**

### **Scanner Results:**
```
┌─────────────────────────────────┐
│ AAPL                    $175.50 │
│ ⭐ Smart: 85                    │
│ 💎 Discount Entry (42% Fib)    │  ← Green badge
│ Setup: Pullback | RSI: 48      │
│ 🛡️ Stop: $172.00               │
│ 🎯 Target: $182.00             │
└─────────────────────────────────┘
```

### **Analyzer Chart:**
```
Premium Zone (50-100%) ⚠️ [Light Red Background]
─────────────────────────────────────────────
0%    (Swing High)     $180.00  [Red line]
23.6%                  $177.00  [Orange line]
38.2%                  $175.00  [Yellow line]
50%   (Equilibrium)    $172.50  [Blue line]
─────────────────────────────────────────────
Discount Zone (0-50%) 💎 [Light Green Background]
─────────────────────────────────────────────
61.8% (Golden Ratio)   $170.00  [Green line]
78.6%                  $167.00  [Dark Green]
100%  (Swing Low)      $165.00  [Bright Green]
```

---

## ✅ **What's Next?**

The Fibonacci feature is now fully implemented! Here's what you can do:

1. **Test it out:** Run a scan and see the Fibonacci badges on cards
2. **Try the filter:** Enable the discount zone filter to see only best entries
3. **Analyze stocks:** Send stocks to analyzer to see Fibonacci lines on charts
4. **Build watchlist:** Use Fibonacci to identify better entry points

**Recommendation:** Start by running a scan with the filter OFF to see all results, then enable the filter when you want to focus only on the best discount zone entries.

---

## 🔧 **Files Modified**

1. **utils/indicators.py** - Added Fibonacci calculation functions
2. **scanner.py** - Added Fibonacci to Smart Score, badges, and filter
3. **analyzer.py** - Added Fibonacci lines to charts and metrics section

---

**Happy Trading! 🎯📈**

