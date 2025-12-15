# 🔔 Automated Alert System Setup

Your alert system is now configured to run **every 2 hours** during market hours automatically via GitHub Actions!

## 📅 Alert Check Schedule

The system checks your alerts at:
- **10:00 AM ET** - Mid-morning check
- **12:00 PM ET** - Noon check
- **2:00 PM ET** - Afternoon check
- **4:15 PM ET** - After market close

**Total: 4 checks per day, Monday-Friday**

---

## ⚙️ Setup Instructions

### 1. Add GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

#### Required:
- `TIINGO_API_KEY` - Your Tiingo API token (you already have this)

#### For Email Alerts:
- `ALERT_EMAIL` - Your Gmail address (e.g., `yourname@gmail.com`)
- `ALERT_EMAIL_PASSWORD` - Gmail App Password (see instructions below)

#### For SMS Alerts (Optional):
- `TWILIO_ACCOUNT_SID` - Your Twilio Account SID
- `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token
- `TWILIO_PHONE_NUMBER` - Your Twilio phone number (e.g., `+15551234567`)

---

### 2. Get Gmail App Password

1. Go to your Google Account: https://myaccount.google.com/
2. Click **Security** in the left sidebar
3. Enable **2-Step Verification** (if not already enabled)
4. Search for "App passwords" or go to: https://myaccount.google.com/apppasswords
5. Select **Mail** and **Other (Custom name)**
6. Name it "SwingFinder Alerts"
7. Click **Generate**
8. Copy the 16-character password (it will look like: `abcd efgh ijkl mnop`)
9. Add this as `ALERT_EMAIL_PASSWORD` secret in GitHub

**Important:** Use the App Password, NOT your regular Gmail password!

---

### 3. Enable GitHub Actions

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. If prompted, click **"I understand my workflows, go ahead and enable them"**
4. You should see the "Check Alerts" workflow listed

---

### 4. Test the Alert System

#### Option A: Manual Test (Recommended)
1. Go to **Actions** tab in GitHub
2. Click **Check Alerts** workflow
3. Click **Run workflow** → **Run workflow**
4. Wait ~30 seconds and check the results

#### Option B: Create a Test Alert
1. Open your SwingFinder app
2. Go to **Alerts** tab
3. Create a price alert for a stock you're watching
4. Set the target price slightly above/below current price
5. Wait for the next scheduled check (or run manually)

---

## 📊 How It Works

1. **GitHub Actions runs** `check_alerts.py` every 2 hours
2. **Script loads** active alerts from `data/alerts.json`
3. **Fetches current prices** from Tiingo API
4. **Checks each alert** to see if conditions are met
5. **Sends email/SMS** if alert is triggered
6. **Logs results** in GitHub Actions logs

---

## 🔍 Monitoring

### View Alert Check Logs:
1. Go to **Actions** tab in GitHub
2. Click on any **Check Alerts** workflow run
3. Click **check-alerts** job
4. Expand **Check alerts** step to see detailed logs

### What You'll See:
```
🔔 Starting alert check at 2024-01-15 14:00:00
📋 Found 3 active alerts

🔍 Checking AAPL (price alert)...
💰 Current price: $185.50
✅ No trigger for AAPL

🔍 Checking TSLA (price alert)...
💰 Current price: $242.75
🚨 ALERT TRIGGERED for TSLA!
✅ Email sent to yourname@gmail.com

============================================================
✅ Alert check complete: 1 alerts triggered
============================================================
```

---

## 🛠️ Troubleshooting

### Alerts Not Running?
- Check **Actions** tab → Make sure workflows are enabled
- Check **Settings** → **Actions** → **General** → Allow all actions

### Email Not Sending?
- Verify `ALERT_EMAIL` and `ALERT_EMAIL_PASSWORD` secrets are set correctly
- Make sure you're using Gmail App Password, not regular password
- Check Gmail security settings allow less secure apps

### Price Not Fetching?
- Verify `TIINGO_API_KEY` secret is set correctly
- Check Tiingo API rate limits (500 requests/hour on free tier)

### Wrong Timezone?
- GitHub Actions uses UTC time
- The cron schedule is already adjusted for ET timezone
- During daylight saving time changes, times may shift by 1 hour

---

## 📝 Notes

- **Free tier limits:** GitHub Actions gives 2,000 free minutes/month (plenty for this)
- **API usage:** ~4-20 API calls per day (well within Tiingo limits)
- **Alert storage:** Alerts are stored in `data/alerts.json` in your repo
- **Manual trigger:** You can always run alerts manually from Actions tab

---

## 🚀 Next Steps

1. ✅ Add GitHub secrets (especially email credentials)
2. ✅ Enable GitHub Actions
3. ✅ Run a manual test
4. ✅ Create your first alert in the app
5. ✅ Wait for the next scheduled check or trigger manually

**Your alerts will now run automatically every 2 hours during market hours!** 🎉

