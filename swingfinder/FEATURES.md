# 🚀 SwingFinder Features Guide

Complete guide to all features in SwingFinder - your AI-powered swing trading assistant.

---

## 📊 Core Features

### **1. Multi-Scanner System**
- **Momentum Scanner** - Finds stocks with strong upward momentum
- **Reversal Scanner** - Identifies potential trend reversals
- **Breakout Scanner** - Detects stocks breaking key resistance levels
- **Pullback Scanner** - Finds healthy pullbacks in uptrends
- **Volume Surge Scanner** - Spots unusual volume activity
- **Relative Strength Scanner** - Compares stocks to market performance

**How to Use:**
1. Go to "Scanner" page
2. Select scanner type from dropdown
3. Adjust filters (price, volume, market cap)
4. Click "Run Scanner"
5. Results show top opportunities with scores

---

### **2. Active Trades Management**
Track and manage your open positions with:
- Entry price, stop loss, target prices
- Real-time P&L tracking
- Position sizing calculator
- Risk/reward ratios
- Trade notes and setup types
- **Cloud persistence** - trades sync across devices

**How to Use:**
1. Go to "Active Trades" page
2. Click "Add New Trade"
3. Enter ticker, entry, stop, targets
4. Track in real-time
5. Close trade when complete (auto-saves to journal)

---

### **3. Alert System**
Get notified when opportunities arise:
- **Price Alerts** - Alert when price crosses threshold
- **Indicator Alerts** - RSI, MACD, EMA crossovers
- **Volume Alerts** - Unusual volume spikes
- **Email Notifications** - Sent to your email
- **Cloud Persistence** - Alerts survive app restarts

**How to Use:**
1. Go to "Alerts" page
2. Click "Create New Alert"
3. Choose alert type (price/indicator)
4. Set conditions and thresholds
5. Enter notification email
6. Alerts check every 15 minutes

---

### **4. Backtesting**
Test strategies on historical data:
- Test any ticker with your entry/exit rules
- See historical performance
- Win rate, average gain/loss
- Drawdown analysis
- Optimize stop loss and target levels

**How to Use:**
1. Go to "Backtest" page
2. Enter ticker symbol
3. Set date range
4. Define entry/exit rules
5. Run backtest
6. Analyze results

---

### **5. AI Trade Coaching**
Get personalized trade analysis from GPT:
- **Trade Plan Generator** - Creates detailed entry/exit plans
- **Risk Analysis** - Evaluates trade risk
- **Setup Validation** - Confirms if setup is valid
- **Exit Strategy** - Suggests when to take profits/cut losses

**How to Use:**
1. In Active Trades, click "Copy to GPT"
2. Choose prompt type
3. Paste into ChatGPT
4. Get AI analysis and recommendations

---

## 🔧 Technical Features

### **Multi-Timeframe Analysis**
- View 5min, 15min, 1hr, 4hr, daily, weekly charts
- Align entries with higher timeframe trends
- Spot divergences across timeframes

### **Support & Resistance**
- Automatic S/R level detection
- Fibonacci retracement levels
- Key pivot points
- Volume-weighted levels

### **Technical Indicators**
- Moving Averages (EMA 20, 50, 200)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Volume analysis
- Bollinger Bands
- ATR (Average True Range)

---

## ☁️ Cloud Features

### **Cloud Persistence**
All your data syncs to GitHub Gist:
- ✅ Active Trades
- ✅ Trade Journal
- ✅ Watchlists
- ✅ Alerts
- ✅ Survives app restarts on Streamlit Cloud

### **Mobile Access**
- Responsive design works on phones/tablets
- Touch-friendly interface
- All features available on mobile

---

## 📈 Data Sources

### **Free Data (No API Key Required)**
- Yahoo Finance - Price data, fundamentals
- Public market data

### **Premium Data (Tiingo API)**
- Real-time intraday data
- Extended historical data
- Sector rotation analysis
- Earnings data
- News feed

**Setup:** Add `TIINGO_API_KEY` to `.streamlit/secrets.toml`

---

## 🎯 Best Practices

### **Scanner Usage**
1. Run multiple scanners to find different setups
2. Cross-reference results across scanners
3. Check higher timeframe trends before entering
4. Verify volume confirms the move

### **Trade Management**
1. Always set stop loss BEFORE entering
2. Use position sizing calculator
3. Take partial profits at targets
4. Trail stops on winners
5. Journal every trade (wins AND losses)

### **Alert Setup**
1. Set alerts at key levels (support/resistance)
2. Use indicator alerts for confirmation
3. Don't over-alert (quality > quantity)
4. Review and clean up old alerts weekly

---

## 📚 Documentation Files

- **README.md** - Quick start guide
- **FEATURES.md** - This file (complete feature guide)
- **ALERTS_CLOUD_PERSISTENCE_FIX.md** - Alert persistence setup
- **CLOUD_PERSISTENCE_SETUP.md** - Cloud storage setup
- **ALERTS_SETUP.md** - Email alert configuration

---

## 🆘 Troubleshooting

### **Scanners Not Returning Results**
- Check filters aren't too restrictive
- Verify Tiingo API key is set
- Try different scanner types
- Reduce minimum volume/price requirements

### **Alerts Not Triggering**
- Verify email settings in secrets.toml
- Check alert conditions are realistic
- Ensure alerts are marked "active"
- Check alert log for errors

### **Data Not Persisting**
- Verify GIST_ID in secrets.toml
- Check GITHUB_GIST_TOKEN is valid
- Ensure token has "gist" scope
- Check Streamlit Cloud logs for errors

---

## 🚀 Coming Soon

- Options flow integration
- Earnings calendar
- Sector rotation dashboard
- Advanced pattern recognition
- Portfolio analytics
- Trade replay feature

---

**Need Help?** Check the individual guide files or create an issue on GitHub.

