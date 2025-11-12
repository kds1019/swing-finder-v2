# Fundamentals Scanner Guide 📊

## ⚠️ **IMPORTANT: TIINGO FUNDAMENTALS API**

The Fundamentals Scanner uses **Tiingo's Fundamentals API**, which is a **separate endpoint** from the price data API.

---

## 🔑 **SUBSCRIPTION REQUIREMENTS**

### **What You Need**:
- ✅ **Tiingo Power** subscription ($30/month) - **YOU HAVE THIS!**
- ✅ Fundamentals API access is **included** in Power tier

### **What Might Happen**:
- ⚠️ **Some stocks have no fundamental data**
- ⚠️ **Newer/smaller stocks** may not have data
- ⚠️ **ETFs** don't have fundamentals (they're funds, not companies)
- ⚠️ **REITs** may have limited data

---

## 📊 **WHY NO RESULTS?**

### **Possible Reasons**:

1. **Scanning ETFs/REITs** ❌
   - ETFs don't have P/E, ROE, etc.
   - They're funds, not companies
   - **Solution**: Scan stocks only

2. **Filters Too Strict** ❌
   - Profit Margin >10%, ROE >15%, Debt <0.5
   - Very few stocks pass all filters
   - **Solution**: Relax filters

3. **Small/New Companies** ❌
   - Tiingo may not have their data yet
   - Penny stocks often missing
   - **Solution**: Focus on larger stocks

4. **Market Closed** ✅ **NOT AN ISSUE!**
   - Fundamentals are historical data
   - Available 24/7
   - Market hours don't matter

---

## ✅ **HOW TO GET RESULTS**

### **Option 1: Scan Your Watchlist** (RECOMMENDED!)

```
1. Go to Scanner
2. Add quality stocks to watchlist:
   - AAPL, MSFT, GOOGL (tech)
   - JPM, BAC, WFC (finance)
   - JNJ, PFE, UNH (healthcare)
   - KO, PG, WMT (consumer)

3. Go to Fundamentals Scanner
4. Check "Scan Watchlist Only"
5. Relax filters:
   - Min Profit Margin: 5%
   - Min ROE: 10%
   - Max Debt/Equity: 1.0
   - Min Score: 50

6. Run scan
7. Should get 5-15 results!
```

### **Option 2: Scan All Stocks** (SLOWER!)

```
1. Uncheck "Scan Watchlist Only"
2. Set Max Stocks: 100 (start small!)
3. Relax filters (same as above)
4. Run scan
5. Wait 2-5 minutes
6. Should get 10-30 results
```

---

## 🎯 **RECOMMENDED FILTERS**

### **For Quality Stocks** (Strict):
- Min Profit Margin: **10%**
- Min ROE: **15%**
- Max Debt/Equity: **0.5**
- Min Current Ratio: **1.5**
- Min Score: **70**

**Expected Results**: 5-20 stocks (very high quality!)

### **For Good Stocks** (Moderate):
- Min Profit Margin: **5%**
- Min ROE: **10%**
- Max Debt/Equity: **1.0**
- Min Current Ratio: **1.0**
- Min Score: **60**

**Expected Results**: 20-50 stocks (good quality)

### **For Any Profitable Stock** (Relaxed):
- Min Profit Margin: **0%**
- Min ROE: **5%**
- Max Debt/Equity: **2.0**
- Min Current Ratio: **0.5**
- Min Score: **50**

**Expected Results**: 50-100 stocks (profitable companies)

---

## 📝 **TESTING STEPS**

### **Quick Test** (2 minutes):

1. **Add Known Stocks to Watchlist**:
   ```
   Scanner → Watchlist Management
   Add: AAPL, MSFT, GOOGL, NVDA, TSLA
   ```

2. **Run Fundamentals Scan**:
   ```
   Fundamentals → Scan Watchlist Only
   Use RELAXED filters
   Click "Run Scan"
   ```

3. **Expected Result**:
   ```
   Should find 3-5 stocks
   AAPL, MSFT, GOOGL should pass
   TSLA might fail (low profit margin)
   ```

4. **If No Results**:
   ```
   Check the scan summary:
   "Checked 5 tickers, Successfully scanned X, Found 0 matches, Errors: Y"
   
   If Errors = 5: API issue (check token)
   If Scanned = 5, Found = 0: Filters too strict
   ```

---

## 🔧 **TROUBLESHOOTING**

### **"Checked 10, Scanned 0, Errors 10"**
**Problem**: API not working
**Solutions**:
- Check TIINGO_TOKEN in secrets.toml
- Verify Tiingo Power subscription active
- Try again in a few minutes (API rate limit?)

### **"Checked 10, Scanned 10, Found 0"**
**Problem**: Filters too strict
**Solutions**:
- Lower Min Profit Margin to 0%
- Lower Min ROE to 5%
- Increase Max Debt to 2.0
- Lower Min Score to 40

### **"Checked 100, Scanned 20, Found 5"**
**Problem**: Many stocks don't have data
**Solutions**:
- This is NORMAL!
- ~20-30% of stocks have full fundamental data
- Focus on larger, established companies
- Use watchlist with known stocks

---

## 💡 **PRO TIPS**

### **1. Build Quality Watchlists**
```
Create watchlists by sector:
- Tech: AAPL, MSFT, GOOGL, NVDA, AMD
- Finance: JPM, BAC, WFC, GS, MS
- Healthcare: JNJ, PFE, UNH, ABBV, LLY
- Consumer: KO, PG, WMT, HD, NKE
```

### **2. Scan Each Watchlist**
```
Fundamentals Scanner
→ Select "Tech" watchlist
→ Run scan
→ Find best tech stocks
```

### **3. Use Results in Other Tools**
```
Fundamentals Scanner → Find quality stocks
↓
Add to "Quality" watchlist
↓
Strength Screener → Rank by RS
↓
Focus on top 5 strongest
↓
Analyzer → Deep dive
↓
Alerts → Set breakout alerts
```

---

## 📊 **WHAT THE SCANNER SHOWS**

When you get results, you'll see:

- **Score** (0-100): Overall fundamental quality
- **Grade** (A-F): Letter grade
- **Profit Margin**: How profitable (higher = better)
- **ROE**: Return on equity (higher = better)
- **Debt/Equity**: Debt level (lower = better)
- **Current Ratio**: Liquidity (higher = better)
- **Revenue**: Company size
- **Net Income**: Profitability

---

## ✅ **EXPECTED BEHAVIOR**

### **Normal Results**:
```
Scan 100 stocks:
- Successfully scanned: 20-40 (20-40%)
- Found matches: 5-20 (depending on filters)
- Errors: 60-80 (no data available)

This is NORMAL!
Many stocks don't have complete fundamental data.
```

### **Good Results**:
```
Scan watchlist of 20 quality stocks:
- Successfully scanned: 15-18 (75-90%)
- Found matches: 8-15 (depending on filters)
- Errors: 2-5 (some missing data)

This is IDEAL!
Focus on quality stocks with good data.
```

---

## 🎯 **BOTTOM LINE**

**The Fundamentals Scanner works, but**:
- ✅ Not all stocks have fundamental data
- ✅ Use watchlists with known stocks
- ✅ Relax filters if no results
- ✅ 20-40% success rate is normal
- ✅ Market hours don't matter

**Best Practice**:
1. Build watchlist of 20-50 quality stocks
2. Scan watchlist only
3. Use moderate filters
4. Expect 10-30 results
5. Focus on highest scores

---

**Try it now with relaxed filters on your watchlist!** 🚀

