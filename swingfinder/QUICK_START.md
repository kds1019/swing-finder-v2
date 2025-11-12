# SwingFinder - Quick Start Guide

## 🎉 What Just Got Fixed

Your SwingFinder app has been cleaned up and improved! Here's what changed:

### ✅ Critical Fixes
1. **API Token Loading** - Fixed the mismatch between your secrets file and app code
2. **App Won't Run Without Token** - Added safety check to prevent errors
3. **Removed Duplicate Code** - Cleaned up duplicate imports
4. **Archived Old Code** - Moved `app_legacy.py` to `archive/` folder

### ✅ New Features
1. **Centralized Config** - All settings now in `config.py`
2. **Professional Logging** - Replaced print statements with proper logging
3. **Pinned Dependencies** - Version-locked all packages for stability
4. **Better .gitignore** - Refined to protect secrets while keeping needed files

---

## 🚀 How to Run Your App

### Option 1: Using the Batch File
```bash
run-swing-finder.bat
```

### Option 2: Manual Start
```bash
# Activate virtual environment (if not already active)
.venv\Scripts\activate

# Run the app
streamlit run app.py
```

---

## 📁 New File Structure

```
swingfinder/
├── app.py                    # ✅ Main entry (cleaned up)
├── scanner.py                # ✅ Scanner module (cleaned up)
├── analyzer.py               # Analyzer module
├── active_trades.py          # Active trades module
├── config.py                 # ✨ NEW: All configuration settings
├── requirements.txt          # ✅ Updated with pinned versions
├── .gitignore               # ✅ Updated ignore rules
├── IMPROVEMENTS.md          # ✨ NEW: Detailed change log
├── QUICK_START.md           # ✨ NEW: This file
│
├── utils/
│   ├── logger.py            # ✨ NEW: Logging infrastructure
│   ├── tiingo_api.py        # ✅ Updated with logging
│   ├── storage.py           # ✅ Updated with logging
│   ├── indicators.py        # Technical indicators
│   └── universe_builder.py  # Universe builder
│
├── archive/
│   └── app_legacy.py        # ✨ Moved here (old code)
│
├── .streamlit/
│   └── secrets.toml         # Your API keys (not in git)
│
└── .env                     # Your environment variables (not in git)
```

---

## 🔧 Using the New Config File

Instead of hardcoding values, you can now import from `config.py`:

```python
from config import (
    SCAN_LOOKBACK_DAYS,
    MAX_WORKERS,
    DEFAULT_RR_RATIO,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT
)

# Use the constants
df = tiingo_history(ticker, token, SCAN_LOOKBACK_DAYS)
```

**Benefits:**
- Change settings in one place
- No more magic numbers
- Easy to understand what values mean

---

## 📝 Using the New Logger

Instead of `print()`, use the logger:

```python
from utils.logger import get_logger

logger = get_logger(__name__)

# Different log levels
logger.debug("Detailed debugging info")
logger.info("General information")
logger.warning("Something to watch out for")
logger.error("An error occurred")
logger.critical("Critical failure!")
```

**Benefits:**
- Timestamps on all messages
- Log levels for filtering
- Can save to files
- Professional debugging

---

## 🔐 Your Secrets Are Safe

✅ Verified that `.streamlit/secrets.toml` is NOT in git
✅ `.gitignore` properly configured
✅ API keys remain private

Your secrets file structure is correct:
```toml
TIINGO_API_KEY = "your_key_here"
TIINGO_TOKEN = "your_key_here"
GITHUB_GIST_TOKEN = "your_token_here"
# ... etc
```

---

## 📦 Dependencies

All packages now have version constraints to prevent breaking changes:

```
streamlit>=1.28.0,<2.0.0
pandas>=2.0.0,<3.0.0
numpy>=1.24.0,<2.0.0
plotly>=5.17.0,<6.0.0
requests>=2.31.0,<3.0.0
python-dotenv>=1.0.0,<2.0.0
scikit-learn>=1.3.0,<2.0.0
textblob>=0.17.0,<1.0.0
tiingo>=0.14.0,<1.0.0
```

To update dependencies:
```bash
pip install -r requirements.txt --upgrade
```

---

## 🧪 Testing Your App

1. **Start the app:**
   ```bash
   streamlit run app.py
   ```

2. **Check that:**
   - ✅ App loads without errors
   - ✅ Scanner page works
   - ✅ Analyzer page works
   - ✅ Active Trades page works
   - ✅ API calls succeed

3. **If you see errors:**
   - Check that your `.env` or `.streamlit/secrets.toml` has `TIINGO_TOKEN`
   - Check the console for log messages (now properly formatted!)
   - Look for error messages in the Streamlit UI

---

## 📚 What's in Each File

### Core App Files
- **app.py** - Main entry point, navigation, page routing
- **scanner.py** - Stock scanner with filters and watchlists
- **analyzer.py** - Individual stock analysis with charts
- **active_trades.py** - Trade tracking and management

### Configuration & Utils
- **config.py** - All constants and settings
- **utils/logger.py** - Logging setup
- **utils/tiingo_api.py** - Tiingo API wrapper functions
- **utils/storage.py** - JSON and Gist storage helpers
- **utils/indicators.py** - Technical indicator calculations
- **utils/universe_builder.py** - Stock universe filtering

### Documentation
- **README.md** - Original project description
- **IMPROVEMENTS.md** - Detailed list of all changes made
- **QUICK_START.md** - This file

---

## 🎯 Next Steps (Optional)

Want to improve further? Consider:

1. **Add Type Hints** - Make code more maintainable
2. **Write Tests** - Ensure code works as expected
3. **Add Input Validation** - Prevent user errors
4. **Optimize Performance** - Speed up scans
5. **Add More Documentation** - Help future you understand the code

---

## ❓ Common Questions

**Q: Where did app_legacy.py go?**
A: It's in the `archive/` folder. You can delete it if you don't need it.

**Q: Do I need to change my secrets file?**
A: No! Your secrets file is already correct. The app was updated to match it.

**Q: Will my old watchlists still work?**
A: Yes! All your data files are preserved.

**Q: Can I still use print() statements?**
A: Yes, but using the logger is better for debugging and production.

**Q: What if something breaks?**
A: All changes are in git. You can revert if needed. But everything should work!

---

## 🆘 Troubleshooting

### App won't start
```bash
# Make sure virtual environment is active
.venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt

# Try running again
streamlit run app.py
```

### "TIINGO_TOKEN not found" error
Check that you have the token in either:
- `.streamlit/secrets.toml` with key `TIINGO_TOKEN` or `TIINGO_API_KEY`
- `.env` file with key `TIINGO_TOKEN` or `TIINGO_API_KEY`

### Import errors
```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall
```

---

## 📞 Support

If you need help:
1. Check the console logs (now nicely formatted!)
2. Review `IMPROVEMENTS.md` for what changed
3. Check the Streamlit error messages
4. Look at the logger output for debugging info

---

**Last Updated**: 2025-11-08
**Status**: ✅ Ready to use!

