# 📉 Dynamic Indicator-Based Alerts Guide

## Overview

**Dynamic Indicator-Based Alerts** allow you to get notified when technical indicators cross specific thresholds or when important crossovers occur. This is a **FREE feature** that automatically monitors your watchlist stocks and sends email notifications when conditions are met.

---

## 🎯 What It Does

The Indicator Alerts feature:
1. **Monitors** technical indicators in real-time (every 2 hours via GitHub Actions)
2. **Detects** when indicators cross thresholds or when crossovers occur
3. **Sends** email notifications when alert conditions are triggered
4. **Tracks** alert history so you can see past triggers

---

## 📊 Alert Types

### 1. 📉 Indicator Alert
Monitor any technical indicator and get notified when it crosses a threshold.

**Supported Indicators:**
- **RSI14** - Relative Strength Index (0-100)
- **ATR14** - Average True Range (volatility)
- **BandPos20** - Bollinger Band Position (0-1)
- **Volume** - Trading volume

**Conditions:**
- **Above** - Triggers when indicator is above threshold
- **Below** - Triggers when indicator is below threshold
- **Crosses Above** - Triggers when indicator crosses from below to above threshold
- **Crosses Below** - Triggers when indicator crosses from above to below threshold

**Example Use Cases:**
- Alert when RSI crosses above 70 (overbought)
- Alert when RSI crosses below 30 (oversold)
- Alert when volume exceeds 5,000,000 shares
- Alert when BandPos crosses above 0.8 (near upper band)

---

### 2. 🔀 EMA Crossover Alert
Get notified when EMA20 crosses EMA50 (major trend change signal).

**Types:**
- **🟢 Bullish (Golden Cross)** - EMA20 crosses ABOVE EMA50
  - Signals potential uptrend starting
  - Good for swing trade entries
  
- **🔴 Bearish (Death Cross)** - EMA20 crosses BELOW EMA50
  - Signals potential downtrend starting
  - Warning to exit positions or avoid entries

**Example Use Cases:**
- Alert when AAPL forms a golden cross (bullish signal)
- Alert when TSLA forms a death cross (bearish warning)

---

### 3. 📊 MACD Signal Alert
Get notified when MACD crosses its signal line (momentum change).

**Types:**
- **🟢 Bullish Signal** - MACD crosses ABOVE signal line
  - Momentum turning positive
  - Potential buy signal
  
- **🔴 Bearish Signal** - MACD crosses BELOW signal line
  - Momentum turning negative
  - Potential sell signal

**Example Use Cases:**
- Alert when NVDA MACD turns bullish
- Alert when SPY MACD turns bearish

---

## 🚀 How to Create Alerts

### Step 1: Navigate to Alerts Page
- Go to **🔔 Alert Management** page
- Click **"➕ Create Alert"** tab

### Step 2: Select Stock and Alert Type
- **Select Stock** - Choose from your watchlist
- **Alert Type** - Choose one of:
  - 📉 Indicator Alert (RSI, ATR, etc.)
  - 🔀 EMA Crossover Alert
  - 📊 MACD Signal Alert

### Step 3: Configure Alert Settings

#### For Indicator Alerts:
1. **Select Indicator** - RSI14, ATR14, BandPos20, or Volume
2. **Select Condition** - above, below, crosses_above, crosses_below
3. **Set Threshold** - The value to trigger the alert

**Example:**
- Indicator: RSI14
- Condition: crosses_below
- Threshold: 30
- **Result:** Alert when RSI drops below 30 (oversold)

#### For EMA Crossover Alerts:
1. **Select Crossover Type** - Bullish or Bearish
- Bullish = EMA20 crosses above EMA50
- Bearish = EMA20 crosses below EMA50

#### For MACD Signal Alerts:
1. **Select Signal Type** - Bullish or Bearish
- Bullish = MACD crosses above signal line
- Bearish = MACD crosses below signal line

### Step 4: Enable Notifications
- ✅ Check **"📧 Email Notification"** to receive emails
- (Optional) Check **"📱 SMS Notification"** if configured

### Step 5: Preview and Create
- Review the alert trigger description
- Click **"Create Alert"**
- Alert is now active and will be checked every 2 hours

---

## 📧 Email Notifications

When an alert triggers, you'll receive an email with:
- **Subject:** 🚨 SwingFinder Alert: [TICKER]
- **Body:** Details about what triggered
- **Current Values:** Indicator values at trigger time

**Example Email:**
```
Subject: 🚨 SwingFinder Alert: AAPL

AAPL RSI14 alert triggered!

RSI14 crosses below 30
Current RSI14: 28.45

This is an oversold signal - potential bounce opportunity.
```

---

## 💡 Alert Strategy Examples

### Strategy 1: Catch Oversold Bounces
**Goal:** Buy stocks when they become oversold

**Alerts to Create:**
1. RSI14 crosses below 30 (oversold)
2. BandPos20 crosses below 0.2 (near lower band)

**How to Use:**
- When alert triggers, check analyzer for confirmation
- Look for bullish divergence or support levels
- Enter if setup looks good

---

### Strategy 2: Avoid Overbought Entries
**Goal:** Don't buy stocks that are extended

**Alerts to Create:**
1. RSI14 crosses above 70 (overbought)

**How to Use:**
- When alert triggers, avoid new entries
- Consider taking profits on existing positions
- Wait for pullback before entering

---

### Strategy 3: Trend Change Detection
**Goal:** Catch major trend changes early

**Alerts to Create:**
1. EMA Crossover - Bullish (golden cross)
2. MACD Signal - Bullish

**How to Use:**
- When both alerts trigger, strong bullish signal
- Enter on pullback to EMA20
- Use EMA50 as stop loss

---

### Strategy 4: Exit Signal Detection
**Goal:** Get out before major downtrends

**Alerts to Create:**
1. EMA Crossover - Bearish (death cross)
2. MACD Signal - Bearish

**How to Use:**
- When alert triggers, review position
- Consider exiting or tightening stops
- Avoid new entries until trend reverses

---

## ⚙️ How Alerts Are Checked

Alerts are checked automatically every **2 hours** using GitHub Actions:

1. **GitHub Action runs** (scheduled workflow)
2. **Fetches active alerts** from your alerts.json file
3. **Gets latest data** from Tiingo API
4. **Calculates indicators** (RSI, EMA, MACD, etc.)
5. **Checks conditions** for each alert
6. **Sends emails** for triggered alerts
7. **Logs results** in GitHub Actions logs

**You don't need to do anything** - alerts run automatically in the background!

---

## 📋 Managing Alerts

### View Active Alerts
- Go to **"📋 Active Alerts"** tab
- See all your active alerts
- View trigger conditions and notification settings

### Pause an Alert
- Click **"⏸️"** button on any alert
- Alert stops checking but isn't deleted
- Can reactivate later

### Delete an Alert
- Click **"🗑️"** button on any alert
- Alert is permanently removed

### View Alert History
- Go to **"📊 Alert History"** tab
- See past triggered alerts
- Review what conditions were met

---

## 💰 Cost

**FREE!** Indicator-Based Alerts use:
- Your existing Tiingo API subscription ($30/month)
- GitHub Actions (free tier: 2,000 minutes/month)
- Gmail SMTP (free)

**No additional costs!**

---

## ⚠️ Important Notes

### Limitations
- Alerts check every **2 hours** (not real-time)
- Requires GitHub Actions to be enabled
- Email must be configured in repository secrets
- Limited to stocks in your watchlist

### Best Practices
- ✅ Don't create too many alerts (max 10-20)
- ✅ Use "crosses" conditions for better signals
- ✅ Combine multiple indicators for confirmation
- ✅ Test alerts with small positions first
- ✅ Review alert history to see what works

### Tips
- **RSI Alerts:** Use 30/70 thresholds for oversold/overbought
- **EMA Cross:** Best for swing trading (multi-day holds)
- **MACD:** Good for momentum confirmation
- **Volume:** Combine with price alerts for breakouts

---

## 🚀 Next Steps

1. **Create your first alert** - Start with a simple RSI alert
2. **Test it** - Wait for it to trigger and review the email
3. **Add more alerts** - Build a complete alert system
4. **Refine** - Adjust thresholds based on results
5. **Combine with backtesting** - See which alerts work best

**Remember:** Alerts are tools to help you spot opportunities - always do your own analysis before trading!

