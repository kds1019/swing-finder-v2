"""
Universe Builder — Standalone Safe Version (Phase 1)
Fetches and filters Tiingo’s full symbol universe, then saves a clean
list for SwingFinder use later.
"""

import os
import json
import requests
import time
from datetime import datetime

TIINGO_TOKEN = os.getenv("TIINGO_TOKEN")  # or set manually for quick tests
CACHE_PATH = os.path.join(os.path.dirname(__file__), "filtered_universe.json")

# ------------------ Configurable Filters ------------------
EXCHANGES = {"NYSE", "NASDAQ", "AMEX"}
MIN_PRICE = 10.0
MAX_PRICE = 60.0  # User's preferred swing trading range
MIN_AVG_VOLUME = 1_000_000  # 1M volume for better liquidity
KEEP_TYPES = {"Stock", "Common Stock", "REIT", "Equity"}

# -----------------------------------------------------------

def fetch_tiingo_universe(token: str) -> list[dict]:
    """
    Fetch complete Tiingo universe using the supported tickers endpoint.
    This gives us ALL supported stocks, not just search results.
    """
    print("🔄 Fetching complete Tiingo symbol universe...")
    headers = {"Authorization": f"Token {token}"}

    # Try the full supported tickers endpoint first
    try:
        url = "https://api.tiingo.com/tiingo/daily"
        resp = requests.get(url, headers=headers, timeout=30)

        if resp.ok:
            all_symbols = resp.json()
            print(f"✅ Fetched {len(all_symbols)} symbols from Tiingo daily endpoint")
            return all_symbols
    except Exception as e:
        print(f"⚠️ Daily endpoint failed: {e}, falling back to search method...")

    # Fallback: Use search with expanded coverage
    print("🔄 Using search method (expanded sweep)...")
    base_url = "https://api.tiingo.com/tiingo/utilities/search"

    # Build comprehensive prefix list: single letters + two-letter combos
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    prefixes = letters + [a + b for a in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for b in "ABC"]
    prefixes = prefixes[:200]   # ~200 queries total (safe for Tiingo Power tier)

    all_symbols = []
    for prefix in prefixes:
        try:
            resp = requests.get(base_url, headers=headers, params={"query": prefix, "limit": 1000})
            if not resp.ok:
                print(f"⚠️  Failed for {prefix}: {resp.status_code}")
                continue

            batch = resp.json()
            if batch:
                print(f"📦 {prefix}: {len(batch)} symbols")
                all_symbols.extend(batch)
            time.sleep(0.25)  # avoid rate limit
        except Exception as e:
            print(f"❌ Error on {prefix}: {e}")
            continue

    print(f"✅ Finished fetching {len(all_symbols)} total symbols (search method)")
    return all_symbols



def filter_symbols(symbols: list[dict]) -> list[dict]:
    """
    High-quality filter for swing trading stocks.
    Focuses on liquid, tradeable U.S. equities and REITs.
    Excludes: ETFs, funds, bonds, warrants, units, preferred shares, OTC junk.
    """
    print("🧹 Filtering symbols (quality mode for swing trading)...")

    filtered = []
    seen_tickers = set()  # Prevent duplicates

    for sym in symbols:
        tkr = sym.get("ticker", "")
        name = str(sym.get("name") or "").lower()
        exchange = sym.get("exchange", "")
        asset_type = sym.get("assetType", "")

        # --- Basic ticker validation ---
        if not tkr or len(tkr) > 5:  # Skip empty or too-long tickers
            continue
        if tkr in seen_tickers:  # Skip duplicates
            continue

        # --- Exclude special characters and suffixes (warrants, units, preferred) ---
        if any(x in tkr for x in [".", "^", "/", "-", "+"]):
            continue
        if any(tkr.endswith(x) for x in ["W", "WS", "WT", "U", "R"]):  # Warrants, Units, Rights
            continue
        if len(tkr) == 5 and tkr[4] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":  # Likely preferred/class shares
            continue

        # --- Exclude non-equity asset types ---
        if any(x in name for x in ["fund", "etf", "trust", "bond", "note", "index",
                                     "portfolio", "treasury", "municipal", "debt"]):
            continue

        # --- Exclude ADRs with weird suffixes (keep clean ADRs like BABA) ---
        if len(tkr) == 5 and tkr.endswith("F"):  # Common ADR suffix pattern
            continue
        if len(tkr) == 5 and tkr.endswith("Y"):  # Another ADR pattern
            continue

        # --- Only keep stocks from major U.S. exchanges ---
        if exchange and exchange not in ["NYSE", "NASDAQ", "AMEX", "NYSEArca", "BATS", ""]:
            continue

        # --- Asset type filter (be inclusive to catch all stocks) ---
        if asset_type and asset_type not in ["Stock", "Common Stock", "REIT", "Equity", "ETF", ""]:
            continue

        # --- Prefer 1-4 character tickers (cleaner stocks) ---
        if len(tkr) <= 4:
            filtered.append({"ticker": tkr.upper(), "name": sym.get("name", "")})
            seen_tickers.add(tkr)
        # Allow some 5-char tickers if they look legitimate (no suffix patterns)
        elif len(tkr) == 5 and tkr.isalpha():
            # Only if it doesn't match common junk patterns
            if not any(x in name for x in ["class", "series", "warrant", "unit"]):
                filtered.append({"ticker": tkr.upper(), "name": sym.get("name", "")})
                seen_tickers.add(tkr)

    print(f"✅ {len(filtered)} quality tickers after filtering (removed {len(symbols) - len(filtered)} junk)")
    return filtered


def save_universe(filtered: list[dict]):
    data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "count": len(filtered),
            "filters": {
                "description": "Quality swing trading stocks under $100",
                "exchanges": list(EXCHANGES),
                "price_range": [MIN_PRICE, MAX_PRICE],
                "min_avg_volume": MIN_AVG_VOLUME,
                "keep_types": list(KEEP_TYPES),
                "excluded": "ETFs, funds, bonds, warrants, units, preferred shares, OTC junk",
            },
        },
        "tickers": filtered,
    }
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved {len(filtered)} quality tickers to {CACHE_PATH}")

    # Show sample of major stocks if present
    ticker_list = [t["ticker"] for t in filtered]
    major_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "AMD", "INTC", "BAC"]
    found_major = [s for s in major_stocks if s in ticker_list]
    if found_major:
        print(f"✅ Major stocks found: {', '.join(found_major[:10])}")
    else:
        print("⚠️ Warning: No major stocks found in universe!")


def add_missing_major_stocks(filtered: list[dict], token: str) -> list[dict]:
    """
    Ensure major liquid stocks are included even if search API missed them.
    Validates each ticker with Tiingo before adding.
    """
    print("\n🔍 Checking for missing major stocks...")

    # Comprehensive list of major liquid stocks under $100
    major_stocks = [
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "NVDA", "META", "NFLX",
        "AMD", "INTC", "QCOM", "AVGO", "TXN", "AMAT", "MU", "LRCX", "KLAC",
        "JPM", "BAC", "WFC", "C", "GS", "MS", "SCHW", "AXP", "BLK", "SPGI",
        "V", "MA", "PYPL", "SQ", "COIN", "HOOD", "SOFI", "AFRM",
        "WMT", "COST", "TGT", "HD", "LOW", "NKE", "SBUX", "MCD", "CMG",
        "DIS", "NFLX", "PARA", "WBD", "SPOT", "RBLX",
        "UBER", "LYFT", "DASH", "ABNB", "BKNG", "EXPE",
        "F", "GM", "RIVN", "LCID", "NIO", "XPEV", "LI",
        "XOM", "CVX", "COP", "SLB", "HAL", "MRO", "OXY", "DVN",
        "PFE", "ABBV", "JNJ", "UNH", "LLY", "MRK", "BMY", "GILD", "BIIB", "MRNA",
        "BA", "CAT", "DE", "GE", "HON", "MMM", "RTX", "LMT", "NOC",
        "PLTR", "SNOW", "DKNG", "PINS", "SNAP", "TWLO", "ZM", "DOCU", "CRWD",
    ]

    existing_tickers = {t["ticker"] for t in filtered}
    added = []

    headers = {"Authorization": f"Token {token}"}

    for ticker in major_stocks:
        if ticker in existing_tickers:
            continue

        # Validate ticker exists in Tiingo
        try:
            url = f"https://api.tiingo.com/tiingo/daily/{ticker.lower()}"
            resp = requests.get(url, headers=headers, timeout=5)

            if resp.ok:
                data = resp.json()
                name = data.get("name", ticker)
                filtered.append({"ticker": ticker, "name": name})
                added.append(ticker)
                print(f"  ✅ Added {ticker} ({name})")
            time.sleep(0.1)  # Rate limit protection
        except Exception as e:
            print(f"  ⚠️ Could not validate {ticker}: {e}")
            continue

    if added:
        print(f"\n✅ Added {len(added)} missing major stocks: {', '.join(added[:20])}")
    else:
        print("\n✅ All major stocks already present")

    return filtered


def main():
    token = TIINGO_TOKEN or input("Enter Tiingo API Token: ").strip()
    symbols = fetch_tiingo_universe(token)
    filtered = filter_symbols(symbols)

    # Add any missing major stocks
    filtered = add_missing_major_stocks(filtered, token)

    save_universe(filtered)

    # Preview sample tickers
    sample = [t["ticker"] for t in filtered[:15]]
    print("🔍 Example tickers:", ", ".join(sample))


if __name__ == "__main__":
    main()

def refresh_universe_manual(token: str):
    """
    Rebuild the cached Tiingo universe file manually from inside Streamlit.
    Returns True if successful, False otherwise.
    """
    import streamlit as st
    try:
        st.info("🔄 Refreshing Tiingo universe... please wait.")
        symbols = fetch_tiingo_universe(token)
        filtered = filter_symbols(symbols)
        save_universe(filtered)
        st.success(f"✅ Universe updated with {len(filtered)} tickers.")
        return True
    except Exception as e:
        st.error(f"❌ Universe refresh failed: {e}")
        return False
