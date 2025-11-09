# SwingFinder - Testing Guide

## 🧪 How to Test Your New Features

---

## 🚀 **Step 1: Start the App**

```bash
streamlit run app.py
```

Or use your batch file:
```bash
run-swing-finder.bat
```

---

## 📊 **Step 2: Test the Scanner**

### **A. Test Sensitivity Slider**

1. Go to **Scanner** page
2. Look in the **sidebar** for "Filter Sensitivity"
3. Try different levels:
   - **Level 1** (Very Strict) - Should get 0-10 results
   - **Level 3** (Balanced) - Should get 20-50 results
   - **Level 5** (Relaxed) - Should get 50-100+ results

**Expected**: More results as you increase sensitivity

---

### **B. Test Smart Mode Fix**

1. Enable **Smart Mode** in sidebar
2. Check the market bias (should show Uptrend/Downtrend/Neutral)
3. Run a scan

**Expected**: 
- In **Uptrend**: Should get MORE results (filters are looser)
- In **Downtrend**: Should get FEWER results (filters are stricter)

**Before the fix**: It was backwards!

---

### **C. Check New Scanner Columns**

After running a scan, look for these new columns:

- **RelVolume**: Should show numbers like 1.2, 0.8, 2.5
  - >1.0 = Above average volume (good!)
  - <1.0 = Below average volume
  
- **VolSignal**: Should show:
  - "Accumulation" (bullish - institutions buying)
  - "Distribution" (bearish - institutions selling)
  - "Neutral"

- **Support**: Price levels below current price
  - Example: [42.50, 40.25]
  
- **Resistance**: Price levels above current price
  - Example: [45.80, 47.20]

**Expected**: All columns should have data (not empty)

---

### **D. Verify Stop/Target Adjustments**

1. Look at a stock with Support/Resistance levels
2. Check if **Stop** is near a support level
3. Check if **Target** is near a resistance level

**Expected**: Stops and targets should align with actual chart levels, not just ATR math

---

## 📈 **Step 3: Test the Analyzer**

### **A. Test Multi-Model Forecast**

1. Go to **Analyzer** page
2. Enter a ticker (e.g., AAPL, MSFT, TSLA)
3. Scroll to the forecast section

**Look for**:
- **Multi-Model Forecast** (not "TinyToy Forecast")
- **Confidence**: Should show a percentage (e.g., 75%)
- **Range**: Should show low-high range (e.g., $175-$180)
- **5-day outlook**: Should show prediction for 5 days ahead

**Expected**: More detailed forecast with confidence score

---

### **B. Test Entry Checklist**

1. Still in Analyzer
2. Look for "✅ Entry Checklist" section

**Should show**:
- ✅ or ❌ for each condition:
  - Trend (EMA20 > EMA50)
  - RSI (45-65 range)
  - Volume (>1.0x average)
  - Earnings (none soon)
  - Volume Signal
  
- **Support levels** (if any)
- **Resistance levels** (if any)
- **Entry Trigger**: Specific price to enter

**Example**:
```
✅ Trend: EMA20 > EMA50
✅ RSI: 58.2 (ideal: 45-65)
⚠️ Volume: 0.8x avg
✅ Earnings: None soon
✅ Volume Signal: Accumulation

📍 Support: $42.50, $40.25
📍 Resistance: $45.80, $47.20

🎯 Entry Trigger: Break above $45.80 with volume > 1.5x average
```

**Expected**: Clear checklist with specific entry price

---

### **C. Verify Support/Resistance on Chart**

1. Scroll to the price chart
2. Look for horizontal lines or annotations

**Expected**: Support and resistance levels should be visible on chart

---

## 💼 **Step 4: Test Active Trades**

### **A. Test Performance Analytics Dashboard**

1. Go to **Active Trades** page
2. Look at the top of the page

**If you have closed trades**, you should see:
- **Win Rate**: Percentage with W/L count
- **Total P&L**: Dollar amount (green if positive, red if negative)
- **Avg R-Multiple**: Average R per trade
- **Profit Factor**: Ratio of avg win to avg loss
- **Best Trade**: Largest win

**Color coding**:
- Green = Good
- Orange = Moderate
- Red = Needs improvement

**If you DON'T have closed trades**: This section won't appear (that's normal)

---

### **B. Test Trade Management Plan**

1. If you have an open trade, find it in the list
2. Look for **"📋 Trade Management Plan"** expander
3. Click to expand

**Should show**:
- Current position status (Entry, Stop, Target, Current Price, R-multiple)
- Specific actions based on R-level:
  - "At +1R: Move stop to breakeven"
  - "At +2R: Take 50% off, move stop to +1R"
  - "Down 0.5R: Review thesis"
- Exit rules (stop loss, target, time stop)

**Example**:
```
Trade Management Plan for AAPL

Entry: $175.50 | Stop: $172.80 | Target: $180.20
Current: $177.30 | Unrealized R: +0.65R

⏸️ At +0.5R: Hold and monitor
   - Let it run toward +1R
   - Watch for volume confirmation

Exit Rules:
- Stop Loss: $172.80 (no exceptions)
- Target: $180.20 (take remaining position)
- Time Stop: If no progress in 5 days, consider exit
```

**Expected**: Specific, actionable plan for each trade

---

### **C. Test Trade Journal (If You Close a Trade)**

1. Close a trade (mark as CLOSED)
2. Check if `data/trade_journal.json` file was created
3. Open the file to see the journal entry

**Should contain**:
- Symbol, entry/exit dates and prices
- P&L in dollars and percentage
- R-multiple achieved
- Exit reason
- Setup type
- Notes

**Expected**: Automatic journaling of closed trades

---

## 🔍 **Step 5: Verify RSI Matches Webull**

### **Compare RSI Values**

1. Pick a stock (e.g., AAPL)
2. Check RSI in SwingFinder Scanner
3. Check same stock in Webull screener
4. Compare RSI values

**Expected**: Should be within 1-2 points (much closer than before)

**Before the fix**: Could differ by 5+ points

---

## ✅ **Quick Checklist**

Use this to verify everything works:

### Scanner
- [ ] Sensitivity slider appears in sidebar
- [ ] Changing sensitivity changes number of results
- [ ] Smart Mode gives MORE results in uptrend (not fewer)
- [ ] RelVolume column shows in results
- [ ] VolSignal column shows in results
- [ ] Support/Resistance levels appear
- [ ] Stops align with support levels

### Analyzer
- [ ] Multi-Model Forecast shows (not TinyToy)
- [ ] Confidence percentage displays
- [ ] Forecast range shows (low-high)
- [ ] Entry Checklist appears
- [ ] Checklist shows ✅ or ❌ for each item
- [ ] Entry Trigger shows specific price
- [ ] Support/Resistance levels listed

### Active Trades
- [ ] Performance Analytics shows at top (if closed trades exist)
- [ ] Win Rate, P&L, Avg R, Profit Factor display
- [ ] Trade Management Plan expander appears for each trade
- [ ] Plan shows specific actions at each R-level
- [ ] Closed trades create journal entries

---

## 🐛 **Common Issues & Solutions**

### **Issue**: Sensitivity slider doesn't appear
**Solution**: Refresh the page (Ctrl+R or Cmd+R)

### **Issue**: No results even at sensitivity 5
**Solution**: 
- Check your price/volume filters
- Try disabling Smart Mode
- Verify API token is working

### **Issue**: Entry Checklist doesn't show
**Solution**: Make sure you entered a valid ticker symbol

### **Issue**: Performance Analytics doesn't show
**Solution**: This only appears if you have closed trades in the journal

### **Issue**: Support/Resistance levels are empty
**Solution**: Some stocks don't have clear pivot points - this is normal

### **Issue**: RSI still doesn't match Webull exactly
**Solution**: Small differences (1-2 points) are normal due to timing/data differences

---

## 📊 **What to Look For**

### **Good Signs** ✅
- Scanner gives 20-100 results at sensitivity 3
- Smart Mode increases results in uptrend
- Entry Checklist shows clear conditions
- Trade Management Plan gives specific actions
- Performance Analytics tracks your stats

### **Red Flags** 🚩
- Scanner gives 0 results at all sensitivity levels → Check filters
- Smart Mode decreases results in uptrend → Bug (report it!)
- Entry Checklist all ❌ → Stock isn't ready to trade
- No performance data after closing trades → Check journal file

---

## 🎯 **Real-World Test Scenario**

### **Complete Workflow Test**

1. **Scanner**:
   - Set sensitivity to 3
   - Enable Smart Mode
   - Run scan
   - Pick a stock with "Accumulation" volume signal
   - Note the Support/Resistance levels

2. **Analyzer**:
   - Enter that stock symbol
   - Check Entry Checklist
   - Wait for all ✅ conditions
   - Note the Entry Trigger price

3. **Active Trades**:
   - Add the trade (if you enter)
   - Check Trade Management Plan
   - Follow the specific rules
   - Close trade when target/stop hit
   - Verify journal entry created

**Expected**: Smooth workflow from scan → analysis → trade → journal

---

## 📝 **Feedback**

As you test, note:
- What works well?
- What's confusing?
- What's missing?
- Any bugs or errors?

This will help with future improvements!

---

## 🎉 **You're Ready!**

Start testing and enjoy your improved SwingFinder app!

**Remember**: 
- Sensitivity slider = control your results
- Entry Checklist = know when to enter
- Trade Management Plan = know what to do
- Performance Analytics = track your edge

**Happy Trading! 📈**

