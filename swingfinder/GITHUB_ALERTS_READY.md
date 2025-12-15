# ✅ GitHub Actions Alerts - READY TO ACTIVATE

## 🎉 What's Already Set Up

I just created the missing GitHub Actions workflow file! Here's what you now have:

### ✅ Files Created:
1. **`.github/workflows/check_alerts.yml`** - GitHub Actions workflow (NEW!)
2. **`check_alerts.py`** - Alert checking script (already existed)
3. **`data/alerts.json`** - Your alerts storage (already existed)

---

## 📅 Alert Schedule

Your alerts will run **automatically** at these times (Monday-Friday):

| Time (ET) | Time (UTC) | Purpose |
|-----------|------------|---------|
| 10:00 AM  | 3:00 PM    | Mid-morning check |
| 12:00 PM  | 5:00 PM    | Noon check |
| 2:00 PM   | 7:00 PM    | Afternoon check |
| 4:15 PM   | 9:15 PM    | After market close |

**Total: 4 checks per day during market hours**

---

## 🚀 How to Activate (3 Steps)

### Step 1: Push to GitHub

First, commit and push the new workflow file:

```bash
git add .github/workflows/check_alerts.yml
git commit -m "Add GitHub Actions alert workflow"
git push
```

### Step 2: Add GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 4 secrets:

| Secret Name | Value | Where to Find |
|-------------|-------|---------------|
| `TIINGO_API_KEY` | `68a2812b8c6fcb25ddb8f374acba6f8624e6dca0` | Already in your `.streamlit/secrets.toml` |
| `ALERT_EMAIL` | `ksherrill3012@gmail.com` | Already in your `.streamlit/secrets.toml` |
| `ALERT_EMAIL_PASSWORD` | `pjhr bunx ieuj uwln` | Already in your `.streamlit/secrets.toml` |
| `USER_EMAIL` | `ksherrill3012@gmail.com` | Already in your `.streamlit/secrets.toml` |

**Note:** `GITHUB_TOKEN` is automatically provided by GitHub Actions - you don't need to add it!

### Step 3: Enable GitHub Actions

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. If prompted, click **"I understand my workflows, go ahead and enable them"**
4. You should see the "Check Alerts" workflow listed

---

## 🧪 Test It Now

### Option 1: Manual Test (Recommended)
1. Go to **Actions** tab in GitHub
2. Click **Check Alerts** workflow
3. Click **Run workflow** → **Run workflow**
4. Wait ~30 seconds and check the results

### Option 2: Create a Test Alert
1. Open your SwingFinder app
2. Go to **Alerts** tab
3. Create a price alert for a stock you're watching
4. Set the target price slightly above/below current price
5. Wait for the next scheduled check (or run manually)

---

## 📊 What Happens When Alert Triggers

1. **GitHub Actions runs** `check_alerts.py` at scheduled times
2. **Fetches current price** from Tiingo API
3. **Checks your alert condition** (e.g., is price > $180?)
4. **If triggered**, sends you an email with:
   - Stock symbol
   - Alert condition that was met
   - Current price
   - Timestamp

**Example Email:**
```
Subject: 🔔 Alert Triggered: AAPL

Your alert for AAPL has been triggered!

Alert Type: Price Alert
Condition: Price above $180.00
Current Price: $182.50
Triggered at: 2025-12-15 14:00:00 ET

---
SwingFinder Alert System
```

---

## 🔍 Monitoring Your Alerts

### View Alert Check Logs:
1. Go to **Actions** tab in GitHub
2. Click on any **Check Alerts** workflow run
3. Click **check-alerts** job
4. Expand **Check alerts** step to see detailed logs

### What You'll See:
```
🔔 Starting alert check at 2025-12-15 14:00:00
📋 Found 3 active alerts

🔍 Checking AAPL (price alert)...
💰 Current price: $185.50
✅ No trigger for AAPL

🔍 Checking TSLA (indicator alert)...
📊 RSI: 72.5
🚨 ALERT TRIGGERED! RSI above 70
📧 Sending email notification...
✅ Email sent successfully

Alert check complete!
```

---

## 💡 Pro Tips

1. **Test with a guaranteed trigger** - Set a price alert for a stock that's already above/below your target to test email delivery

2. **Check spam folder** - First alert email might go to spam, mark it as "Not Spam"

3. **Monitor GitHub Actions usage** - Free tier gives 2,000 minutes/month (plenty for this)

4. **API rate limits** - Tiingo free tier allows 500 requests/hour (you'll use ~4-20 per day)

---

## 🛠️ Troubleshooting

### Alerts Not Running?
- Check if GitHub Actions is enabled in your repo settings
- Verify the workflow file is in `.github/workflows/` folder
- Check Actions tab for any error messages

### No Email Received?
- Verify all 4 secrets are set correctly in GitHub
- Check spam/junk folder
- Look at GitHub Actions logs to see if email was sent

### Price Not Fetching?
- Verify `TIINGO_API_KEY` secret is set correctly
- Check Tiingo API rate limits (500 requests/hour on free tier)

---

## ✅ Summary

**What You Have:**
- ✅ GitHub Actions workflow file created
- ✅ Alert checking script ready
- ✅ Email credentials in secrets.toml

**What You Need to Do:**
1. Push the workflow file to GitHub
2. Add 4 secrets to GitHub repository
3. Enable GitHub Actions
4. Test with a manual run

**Result:** Automated alerts running 4 times per day during market hours! 🚀

---

## 📝 Next Steps

After activating:
1. Create your first alert in the SwingFinder app
2. Run a manual test from GitHub Actions
3. Wait for the next scheduled check
4. Check your email for notifications

**Your alerts will now run automatically every 2 hours during market hours!** 🎉

