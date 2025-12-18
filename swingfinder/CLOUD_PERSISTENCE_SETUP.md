# ☁️ Cloud Persistence Setup for Active Trades

## Problem
Your active trades disappear after a few days because **Streamlit Community Cloud has ephemeral storage** - files get deleted when the app restarts or redeploys.

---

## ✅ Solution: GitHub Gist Storage

I've updated your app to use **GitHub Gist** for cloud persistence. This stores your trades in a private GitHub Gist that persists forever!

---

## 🔧 Setup Instructions (5 minutes)

### **Step 1: Create a GitHub Personal Access Token**

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Give it a name: `SwingFinder Trades Storage`
4. Set expiration: **No expiration** (or 1 year)
5. Check these permissions:
   - ✅ **gist** (Create gists)
6. Click **"Generate token"**
7. **Copy the token** (you won't see it again!)

---

### **Step 2: Create a GitHub Gist for Storage**

1. Go to: https://gist.github.com
2. Click **"New gist"**
3. Set filename: `active_trades.json`
4. Paste this content:
   ```json
   {
     "trades": []
   }
   ```
5. Select **"Create secret gist"** (keeps it private)
6. Click **"Create secret gist"**
7. **Copy the Gist ID** from the URL:
   - URL: `https://gist.github.com/your-username/abc123def456`
   - Gist ID: `abc123def456` ← Copy this part!

---

### **Step 3: Add Secrets to Streamlit Cloud**

1. Go to: https://share.streamlit.io
2. Find your **SwingFinder** app
3. Click **Settings** (gear icon)
4. Click **"Secrets"** tab
5. Add these two lines to your secrets:

```toml
GITHUB_TOKEN = "ghp_your_token_here"
GIST_TRADES_ID = "your_gist_id_here"
```

**Example:**
```toml
GITHUB_TOKEN = "ghp_abc123def456xyz789"
GIST_TRADES_ID = "1a2b3c4d5e6f7g8h9i0j"
```

6. Click **"Save"**
7. App will automatically redeploy

---

### **Step 4: Test It Works**

1. Open your SwingFinder app
2. Go to **Active Trades** page
3. Add a test trade
4. **Restart the app** (Settings → Reboot)
5. Check if the trade is still there ✅

**If it's still there, you're all set!** 🎉

---

## 🔐 Security Notes

**Your data is safe:**
- ✅ Gist is **secret** (not public)
- ✅ Only you can access it with your token
- ✅ Token is stored in Streamlit secrets (encrypted)
- ✅ Never committed to GitHub repo

---

## 📊 What Gets Saved to Cloud

**Automatically saved to Gist:**
1. **Active Trades** (`active_trades.json`)
   - All open positions
   - Entry, stop, target prices
   - Position sizes
   - Notes and setup types

2. **Trade Journal** (`trade_journal.json`)
   - All closed trades
   - P&L history
   - Win rate stats
   - Exit reasons

**Saved both locally AND to cloud:**
- Local file: `data/active_trades.json` (temporary)
- Cloud: GitHub Gist (permanent)

---

## 🧪 How It Works

### **Before (Local Storage Only):**
```
App saves → data/active_trades.json → ❌ Deleted on restart
```

### **After (Cloud + Local):**
```
App saves → data/active_trades.json (local)
         → GitHub Gist (cloud) ✅ Persists forever

App loads → Try Gist first ✅
         → Fallback to local if Gist fails
```

---

## 🔄 Migration of Existing Trades

**If you have trades in local storage right now:**

1. **Before setup:** Export your trades (copy them somewhere)
2. **After setup:** Re-add them manually
3. They'll now save to cloud automatically

**Or:** I can create a migration script to copy local → Gist. Let me know!

---

## ❓ Troubleshooting

### **Issue: Trades still disappearing**

**Check:**
1. Did you add both secrets? (`GITHUB_TOKEN` and `GIST_TRADES_ID`)
2. Is the token valid? (Check https://github.com/settings/tokens)
3. Is the Gist ID correct? (Check https://gist.github.com)
4. Did the app redeploy after adding secrets?

**Test:**
- Look for warning messages in the app (yellow boxes)
- If you see "⚠️ Could not save to cloud storage", check your secrets

---

### **Issue: "Missing GITHUB_TOKEN" error**

**Fix:**
1. Make sure you added `GITHUB_TOKEN` to Streamlit secrets
2. Make sure there are no extra spaces or quotes
3. Format: `GITHUB_TOKEN = "ghp_..."`

---

### **Issue: Gist not updating**

**Check:**
1. Go to your Gist: https://gist.github.com/your-username/your-gist-id
2. Click "Revisions" to see if it's updating
3. If not, check token permissions (needs `gist` scope)

---

## 🚀 Benefits of Cloud Storage

✅ **Persistent** - Trades never disappear  
✅ **Automatic** - Saves on every change  
✅ **Backup** - Data stored in GitHub  
✅ **Accessible** - View/edit Gist directly if needed  
✅ **Free** - No cost for GitHub Gists  
✅ **Secure** - Private Gist, encrypted token  

---

## 📱 Works on Mobile Too!

Once set up, your trades will persist across:
- ✅ Desktop browser
- ✅ Mobile browser
- ✅ App restarts
- ✅ Redeployments
- ✅ Different devices

**Same data everywhere!**

---

## 🔧 Advanced: Local Development

**If running locally** (not on Streamlit Cloud):

1. Create `.streamlit/secrets.toml` (if it doesn't exist)
2. Add the same secrets:
   ```toml
   GITHUB_TOKEN = "ghp_your_token_here"
   GIST_TRADES_ID = "your_gist_id_here"
   ```
3. Restart local app
4. Trades will sync to same Gist!

**Result:** Same trades on local AND cloud! 🎉

---

## 📄 What I Changed

**Updated files:**
- ✅ `active_trades.py` - Added Gist storage functions
  - `_load_trades()` - Now tries Gist first, then local
  - `_save_trades()` - Saves to both Gist and local
  - `load_trade_journal()` - Cloud-enabled
  - `save_trade_journal()` - Cloud-enabled

**How it works:**
1. When you save a trade, it saves to:
   - Local file (for speed)
   - GitHub Gist (for persistence)
2. When you load trades, it tries:
   - GitHub Gist first (cloud data)
   - Local file if Gist fails (fallback)

---

## 🎯 Quick Setup Checklist

- [ ] Create GitHub Personal Access Token (with `gist` permission)
- [ ] Create secret Gist with `active_trades.json`
- [ ] Copy Gist ID from URL
- [ ] Add `GITHUB_TOKEN` to Streamlit secrets
- [ ] Add `GIST_TRADES_ID` to Streamlit secrets
- [ ] Save secrets (app will redeploy)
- [ ] Test by adding a trade and restarting app
- [ ] ✅ Trades persist!

---

## 💡 Next Steps

1. **Set up cloud storage** (follow steps above)
2. **Test it works** (add trade, restart, check if it's still there)
3. **Enjoy persistent trades!** 🎉

**Your trades will never disappear again!**

---

## 🆘 Need Help?

If you run into issues:

1. **Check the app for warning messages** (yellow boxes)
2. **Verify your secrets** are correct (no typos, no extra spaces)
3. **Check your Gist** is updating (view revisions)
4. **Let me know** and I'll help troubleshoot!

---

## 📊 Summary

**Problem:** Trades disappear after a few days  
**Cause:** Streamlit Cloud has ephemeral storage  
**Solution:** GitHub Gist cloud storage  
**Setup Time:** 5 minutes  
**Cost:** FREE  
**Result:** Trades persist forever! ✅  

**Let's get this set up!** 🚀

