# SwingFinder Alert Setup Guide 🔔

## 📧 **EMAIL ALERTS SETUP** (FREE!)

Email alerts are **completely FREE** and easy to set up!

### **Step 1: Create Gmail App Password**

1. Go to your Google Account: https://myaccount.google.com/
2. Click "Security" in the left sidebar
3. Enable "2-Step Verification" (if not already enabled)
4. Scroll down to "App passwords"
5. Click "App passwords"
6. Select "Mail" and "Other (Custom name)"
7. Enter "SwingFinder" as the name
8. Click "Generate"
9. **Copy the 16-character password** (you'll need this!)

### **Step 2: Add to Streamlit Secrets**

1. Open `.streamlit/secrets.toml` file
2. Add these lines:

```toml
ALERT_EMAIL = "your.email@gmail.com"
ALERT_EMAIL_PASSWORD = "your-16-char-app-password"
USER_EMAIL = "your.email@gmail.com"  # Where to send alerts
```

3. Save the file

### **Step 3: Test Email Alerts**

1. Go to "Alerts" page in SwingFinder
2. Create a test alert
3. Check "📧 Email Notification"
4. You should receive a test email!

---

## 📱 **SMS ALERTS SETUP** (Optional - Paid)

SMS alerts use Twilio (pay per message, ~$0.01 each)

### **Step 1: Create Twilio Account**

1. Go to https://www.twilio.com/try-twilio
2. Sign up for free trial ($15 credit)
3. Verify your phone number
4. Get a Twilio phone number

### **Step 2: Get Credentials**

1. Go to Twilio Console: https://console.twilio.com/
2. Copy your **Account SID**
3. Copy your **Auth Token**
4. Copy your **Twilio Phone Number**

### **Step 3: Add to Streamlit Secrets**

1. Open `.streamlit/secrets.toml` file
2. Add these lines:

```toml
TWILIO_ACCOUNT_SID = "your-account-sid"
TWILIO_AUTH_TOKEN = "your-auth-token"
TWILIO_PHONE_NUMBER = "+1234567890"  # Your Twilio number
USER_PHONE = "+1234567890"  # Your personal number
```

3. Save the file

### **Step 4: Install Twilio**

```bash
pip install twilio
```

### **Step 5: Test SMS Alerts**

1. Go to "Alerts" page in SwingFinder
2. Create a test alert
3. Check "📱 SMS Notification"
4. You should receive a text message!

---

## 🎯 **RECOMMENDED SETUP**

### **For Most Users** (FREE):
- ✅ Use **Email Alerts** only
- ✅ Check email on phone
- ✅ No cost!

### **For Active Traders** (Paid):
- ✅ Use **Email + SMS**
- ✅ Get instant text notifications
- ✅ ~$5-10/month for SMS

---

## 🔔 **ALERT TYPES**

### **1. Price Alerts**
- Trigger when price crosses a level
- Example: "Alert me when AAPL > $180"

### **2. Volume Alerts**
- Trigger on volume surges
- Example: "Alert me when volume > 2x average"

### **3. Pattern Alerts**
- Trigger when chart pattern detected
- Example: "Alert me when Bull Flag forms"

### **4. News Alerts**
- Trigger on news sentiment
- Example: "Alert me on bullish news"

---

## 💡 **ALERT BEST PRACTICES**

### **Don't Over-Alert**:
- ❌ Don't create 50 alerts
- ✅ Create 5-10 high-quality alerts
- ✅ Focus on your best setups

### **Use Price Alerts for Entry**:
- ✅ Set alert at breakout level
- ✅ Get notified when setup triggers
- ✅ Analyze before entering

### **Use Volume Alerts for Confirmation**:
- ✅ Combine with price alerts
- ✅ Volume surge = strong move
- ✅ Avoid low-volume breakouts

### **Use Pattern Alerts for Scanning**:
- ✅ Auto-detect patterns
- ✅ Review in analyzer
- ✅ Confirm before entering

---

## 📊 **EXAMPLE ALERT STRATEGY**

### **For Swing Trading**:

```
1. Price Alert: AAPL crosses above $180
   → Entry trigger

2. Volume Alert: AAPL volume > 2x average
   → Confirmation

3. Pattern Alert: Bull Flag detected
   → Setup formation

4. News Alert: Bullish news
   → Catalyst
```

### **Workflow**:
1. Get price alert → Check chart
2. Get volume alert → Confirm strength
3. Get pattern alert → Analyze setup
4. Get news alert → Check catalyst
5. All align? → Enter trade!

---

## ⚙️ **ALERT SETTINGS**

### **Email Settings**:
- **From**: Your Gmail account
- **To**: Your email (can be same or different)
- **Format**: HTML email with charts/links

### **SMS Settings**:
- **From**: Twilio number
- **To**: Your phone number
- **Format**: Plain text (160 chars max)

---

## 🔧 **TROUBLESHOOTING**

### **Email Not Working?**
1. Check Gmail app password is correct
2. Make sure 2-Step Verification is enabled
3. Check spam folder
4. Try different email address

### **SMS Not Working?**
1. Check Twilio credentials
2. Verify phone number format (+1234567890)
3. Check Twilio account balance
4. Make sure phone is verified in Twilio

### **Alerts Not Triggering?**
1. Make sure app is running
2. Alerts check every 5 minutes
3. Check alert is active (not paused)
4. Verify alert conditions are correct

---

## 💰 **COST BREAKDOWN**

### **Email Alerts**:
- **Cost**: FREE
- **Limit**: Unlimited
- **Speed**: ~1-2 seconds

### **SMS Alerts**:
- **Cost**: ~$0.01 per message
- **Limit**: Based on Twilio balance
- **Speed**: Instant

### **Example Monthly Cost**:
```
Email only: $0
Email + 100 SMS: ~$1
Email + 500 SMS: ~$5
Email + 1000 SMS: ~$10
```

---

## 🎯 **QUICK START (EMAIL ONLY)**

### **5-Minute Setup**:

1. **Get Gmail App Password** (2 min)
   - Google Account → Security → App passwords
   - Generate password for "SwingFinder"

2. **Add to Secrets** (1 min)
   - Edit `.streamlit/secrets.toml`
   - Add ALERT_EMAIL and ALERT_EMAIL_PASSWORD

3. **Create Alert** (2 min)
   - Go to Alerts page
   - Create price alert
   - Check email notification
   - Done!

---

## ✅ **VERIFICATION CHECKLIST**

Before going live:

- [ ] Gmail app password created
- [ ] Secrets file updated
- [ ] Test email sent successfully
- [ ] Alert created
- [ ] Alert triggered (test)
- [ ] Email received

Optional (SMS):
- [ ] Twilio account created
- [ ] Twilio credentials added
- [ ] Test SMS sent successfully

---

## 📱 **MOBILE NOTIFICATIONS**

### **Email on Phone**:
- ✅ Gmail app notifications
- ✅ iPhone Mail notifications
- ✅ Android Email notifications

### **SMS on Phone**:
- ✅ Native text message
- ✅ Instant notification
- ✅ Works even without internet

---

## 🚀 **READY TO GO!**

**Recommended First Alert**:
```
Type: Price Alert
Ticker: Your favorite stock
Condition: Crosses above
Target: Key resistance level
Notification: Email
```

**This will**:
- Alert you when breakout happens
- Let you analyze before entering
- Keep you informed without spam

---

## 💡 **PRO TIPS**

1. **Start with Email Only** - It's free and works great
2. **Add SMS for Critical Alerts** - Only your best setups
3. **Don't Over-Alert** - Quality over quantity
4. **Test First** - Create test alert before going live
5. **Check Regularly** - Review alert history to optimize

---

**Need Help?** Check the troubleshooting section or create a test alert to verify setup!

**Happy Trading! 🚀**

