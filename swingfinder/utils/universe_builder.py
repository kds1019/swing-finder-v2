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
MIN_PRICE = 5.0
MAX_PRICE = 150.0
MIN_AVG_VOLUME = 500_000
KEEP_TYPES = {"Common Stock", "REIT"}

# -----------------------------------------------------------

def fetch_tiingo_universe(token: str) -> list[dict]:
    """
    Expanded universe fetch using /utilities/search.
    Iterates through A–Z, 0–9, and limited 2-letter prefixes (AA–AZ, BA–BZ, … AZ–CZ)
    to enlarge coverage while staying rate-safe.
    """
    print("🔄 Fetching Tiingo symbol universe (expanded sweep)…")
    headers = {"Authorization": f"Token {token}"}
    base_url = "https://api.tiingo.com/tiingo/utilities/search"

    # build short prefix list: single letters + first 3 two-letter combos for each
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

    print(f"✅ Finished fetching {len(all_symbols)} total symbols (expanded)")
    return all_symbols



def filter_symbols(symbols: list[dict]) -> list[dict]:
    """
    Refined light filter for /utilities/search results.
    Keeps only common U.S. equities and REITs.
    """
    print("🧹 Filtering symbols (refined mode)...")

    filtered = []
    for sym in symbols:
        tkr = sym.get("ticker", "")
        name = str(sym.get("name") or "").lower()

        if not tkr or len(tkr) > 5:
            continue
        if any(x in tkr for x in [".", "^", "/", "WS"]):
            continue
        if any(x in name for x in ["fund", "etf", "trust", "bond", "note", "index", "growth", "class", "portfolio"]):
            continue
        # include REITs and normal companies
        if not any(x in name for x in ["reit", "inc", "corp", "co", "group", "ltd", "plc"]):
            continue

        filtered.append({"ticker": tkr.upper(), "name": sym.get("name", "")})

    print(f"✅ {len(filtered)} tickers after refined filter")
    return filtered


def save_universe(filtered: list[dict]):
    data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "count": len(filtered),
            "filters": {
                "exchanges": list(EXCHANGES),
                "price_range": [MIN_PRICE, MAX_PRICE],
                "min_avg_volume": MIN_AVG_VOLUME,
                "keep_types": list(KEEP_TYPES),
            },
        },
        "tickers": filtered,
    }
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved {len(filtered)} tickers to {CACHE_PATH}")


def main():
    token = TIINGO_TOKEN or input("Enter Tiingo API Token: ").strip()
    symbols = fetch_tiingo_universe(token)
    filtered = filter_symbols(symbols)
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
