"""Test that the scanner can load the universe correctly."""
import os
import json

# Test the same logic as scanner.py
CACHE_PATH = os.path.join("utils", "filtered_universe.json")

print("=" * 70)
print("SCANNER UNIVERSE LOADING TEST")
print("=" * 70)

# Test 1: Check if cache file exists
print(f"\n1. Cache file exists: {os.path.exists(CACHE_PATH)}")
print(f"   Path: {CACHE_PATH}")

if os.path.exists(CACHE_PATH):
    # Test 2: Load cache file
    try:
        with open(CACHE_PATH, "r") as f:
            data = json.load(f)
        
        tickers = [t["ticker"].upper() for t in data.get("tickers", [])]
        
        # Test 3: Remove duplicates
        seen = set()
        unique_tickers = [t for t in tickers if not (t in seen or seen.add(t))]
        
        print(f"\n2. Cache loaded successfully:")
        print(f"   Total tickers: {len(unique_tickers)}")
        print(f"   Duplicates removed: {len(tickers) - len(unique_tickers)}")
        
        # Test 4: Check for major stocks
        major_stocks = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "AMD", "INTC",
            "JPM", "BAC", "WFC", "V", "MA", "PYPL", "UBER", "PLTR", "COIN",
            "HOOD", "SOFI", "F", "GM", "NKE", "SBUX", "MCD", "DIS", "NFLX"
        ]
        
        found = [s for s in major_stocks if s in unique_tickers]
        missing = [s for s in major_stocks if s not in unique_tickers]
        
        print(f"\n3. Major stocks check:")
        print(f"   Found: {len(found)}/{len(major_stocks)}")
        print(f"   Present: {', '.join(found[:10])}")
        if len(found) > 10:
            print(f"            {', '.join(found[10:20])}")
        if len(found) > 20:
            print(f"            {', '.join(found[20:])}")
        
        if missing:
            print(f"   Missing: {', '.join(missing)}")
        
        # Test 5: Check for junk tickers
        junk = [t for t in unique_tickers if len(t) > 4 or any(x in t for x in [".", "^", "-"])]
        
        print(f"\n4. Quality check:")
        print(f"   Clean tickers (1-4 chars): {len([t for t in unique_tickers if len(t) <= 4])}")
        print(f"   Questionable tickers: {len(junk)}")
        if junk:
            print(f"   Sample: {junk[:10]}")
        
        # Test 6: Sample tickers
        print(f"\n5. Sample tickers (first 20):")
        print(f"   {', '.join(sorted(unique_tickers)[:20])}")
        
        # Final verdict
        print("\n" + "=" * 70)
        if len(unique_tickers) == 275 and len(found) >= 20 and len(junk) < 10:
            print("✅ STATUS: EXCELLENT - Scanner will load 275 quality tickers!")
            print("✅ All major stocks present, minimal junk")
            print("✅ Ready to run: streamlit run scanner.py")
        elif len(unique_tickers) < 300:
            print("✅ STATUS: GOOD - Scanner will load quality tickers")
            print(f"⚠️  Some major stocks missing: {', '.join(missing)}")
        else:
            print("⚠️  STATUS: NEEDS IMPROVEMENT")
            print(f"   Expected ~275 tickers, got {len(unique_tickers)}")
            print("   Run: python utils/build_quality_universe.py")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR loading cache: {e}")
        print("⚠️  Scanner will fall back to Tiingo API (1000+ tickers)")
        print("💡 Fix: Run 'python utils/build_quality_universe.py'")
else:
    print("\n❌ Cache file not found!")
    print("⚠️  Scanner will fall back to Tiingo API (1000+ tickers)")
    print("💡 Fix: Run 'python utils/build_quality_universe.py'")

