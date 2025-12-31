# ⚙️ SwingFinder Setup Guide

Complete setup instructions for SwingFinder - get up and running in 10 minutes.

---

## 🚀 Quick Start (Local)

### **1. Clone the Repository**
```bash
git clone https://github.com/yourusername/swingfinder.git
cd swingfinder
```

### **2. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **3. Create Secrets File**
Create `.streamlit/secrets.toml`:
```toml
# Required: Tiingo API (free tier available)
TIINGO_API_KEY = "your_tiingo_api_key_here"

# Optional: Email Alerts
ALERT_EMAIL = "your_gmail@gmail.com"
ALERT_EMAIL_PASSWORD = "your_app_password"
USER_EMAIL = "recipient@gmail.com"

# Optional: Cloud Persistence
GITHUB_GIST_TOKEN = "ghp_your_token_here"
GIST_ID = "your_gist_id_here"
```

### **4. Run the App**
```bash
streamlit run app.py
```

App opens at `http://localhost:8501`

---

## ☁️ Streamlit Cloud Deployment

### **1. Push to GitHub**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### **2. Deploy on Streamlit Cloud**
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select your repository
4. Main file: `app.py`
5. Click "Deploy"

### **3. Add Secrets**
1. In Streamlit Cloud dashboard, click your app
2. Click "Settings" → "Secrets"
3. Paste your secrets.toml content
4. Click "Save"

---

## 🔑 API Keys & Secrets

### **Tiingo API (Required for Premium Features)**

**Get Free API Key:**
1. Go to [tiingo.com](https://www.tiingo.com)
2. Sign up (free tier: 500 requests/hour)
3. Go to Account → API
4. Copy your API token

**Add to secrets.toml:**
```toml
TIINGO_API_KEY = "your_token_here"
```

**What You Get:**
- Real-time stock data
- Historical price data
- Sector analysis
- News feed
- Earnings data

---

### **Email Alerts (Optional)**

**Setup Gmail App Password:**
1. Go to Google Account settings
2. Security → 2-Step Verification (enable if not already)
3. Search "App passwords"
4. Generate password for "Mail"
5. Copy the 16-character password

**Add to secrets.toml:**
```toml
ALERT_EMAIL = "your_gmail@gmail.com"
ALERT_EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"  # App password
USER_EMAIL = "where_to_send_alerts@gmail.com"
```

**What You Get:**
- Price alert emails
- Indicator alert emails
- Volume spike notifications
- Custom alert messages

---

### **Cloud Persistence (Optional but Recommended)**

**Why You Need This:**
- Streamlit Cloud has ephemeral storage
- Local files get deleted on app restart
- Cloud persistence saves to GitHub Gist (permanent)

**Setup GitHub Gist:**

1. **Create Personal Access Token:**
   - Go to GitHub → Settings → Developer settings
   - Personal access tokens → Tokens (classic)
   - Generate new token
   - Check "gist" scope
   - Copy token (starts with `ghp_`)

2. **Create a Gist:**
   - Go to [gist.github.com](https://gist.github.com)
   - Create new secret gist
   - Name: "swingfinder-data"
   - Add file: `active_trades.json` with content: `{"trades": []}`
   - Create secret gist
   - Copy Gist ID from URL (long alphanumeric string)

3. **Add to secrets.toml:**
```toml
GITHUB_GIST_TOKEN = "ghp_your_token_here"
GIST_ID = "your_gist_id_here"
```

**What Gets Saved to Cloud:**
- ✅ Active trades
- ✅ Trade journal
- ✅ Watchlists
- ✅ Alerts
- ✅ All persist across app restarts

---

## 📁 File Structure

```
swingfinder/
├── app.py                  # Main Streamlit app
├── scanner.py              # Scanner logic
├── active_trades.py        # Trade management
├── alerts_page.py          # Alert system
├── backtest_page.py        # Backtesting
├── analyzer.py             # Chart analysis
├── config.py               # Configuration
├── requirements.txt        # Dependencies
├── .streamlit/
│   └── secrets.toml        # API keys (DO NOT COMMIT)
├── data/
│   ├── active_trades.json  # Local trades (ephemeral)
│   ├── alerts.json         # Local alerts (ephemeral)
│   └── tiingo_us_equities.csv  # Stock universe
└── utils/
    ├── alerts.py           # Alert functions
    ├── storage.py          # Cloud persistence
    ├── indicators.py       # Technical indicators
    ├── tiingo_api.py       # API wrapper
    └── ...
```

---

## 🧪 Verify Setup

### **Test Tiingo API:**
```python
import requests
token = "your_token_here"
r = requests.get("https://api.tiingo.com/api/test", headers={"Authorization": f"Token {token}"})
print(r.json())  # Should show: {"message": "You successfully sent a request"}
```

### **Test Email Alerts:**
1. Go to Alerts page
2. Create test alert
3. Set condition that will trigger immediately
4. Check your email

### **Test Cloud Persistence:**
1. Create an active trade
2. Close the app completely
3. Reopen the app
4. Trade should still be there ✅

---

## 🔒 Security Best Practices

### **Never Commit Secrets:**
```bash
# .gitignore should include:
.streamlit/secrets.toml
*.env
.env
```

### **Use Environment Variables (Alternative):**
```bash
export TIINGO_API_KEY="your_key"
export ALERT_EMAIL="your_email"
```

### **Rotate Tokens Regularly:**
- Regenerate GitHub tokens every 90 days
- Update Gmail app passwords if compromised
- Never share tokens publicly

---

## 🆘 Troubleshooting

### **"Module not found" errors:**
```bash
pip install -r requirements.txt --upgrade
```

### **Streamlit Cloud deployment fails:**
- Check requirements.txt has all dependencies
- Verify Python version (3.9+)
- Check app.py is in root directory

### **API rate limits:**
- Tiingo free tier: 500 requests/hour
- Reduce scanner frequency
- Cache results locally

### **Email alerts not sending:**
- Verify Gmail app password (not regular password)
- Check 2-step verification is enabled
- Try different email provider

### **Cloud persistence not working:**
- Verify Gist ID is correct
- Check token has "gist" scope
- Ensure Gist is secret (not public)
- Check Streamlit Cloud logs for errors

---

## 📚 Additional Resources

- **Tiingo API Docs:** https://api.tiingo.com/documentation
- **Streamlit Docs:** https://docs.streamlit.io
- **GitHub Gist API:** https://docs.github.com/en/rest/gists

---

**Setup Complete!** 🎉 You're ready to start swing trading with SwingFinder.

Next: Check out [FEATURES.md](FEATURES.md) to learn about all available features.

