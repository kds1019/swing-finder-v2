"""Verify the quality of the ticker universe."""
import json

# Load the new universe
with open('utils/filtered_universe.json', 'r') as f:
    data = json.load(f)

tickers = [t['ticker'] for t in data['tickers']]

print("=" * 70)
print("TICKER UNIVERSE VERIFICATION")
print("=" * 70)

print(f"\nTotal tickers: {len(tickers)}")
print(f"Last updated: {data['meta']['last_updated']}")

# Check for major stocks
major_stocks = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX",
    "AMD", "INTC", "JPM", "BAC", "WFC", "V", "MA", "PYPL", 
    "UBER", "PLTR", "COIN", "HOOD", "SOFI", "F", "GM", "NKE", "SBUX", "MCD"
]

found = [s for s in major_stocks if s in tickers]
missing = [s for s in major_stocks if s not in tickers]

print(f"\nMAJOR STOCKS CHECK:")
print(f"  Found: {len(found)}/{len(major_stocks)}")
print(f"  Present: {', '.join(found[:15])}")
if len(found) > 15:
    print(f"           {', '.join(found[15:])}")
if missing:
    print(f"  Missing: {', '.join(missing)}")

# Show sample tickers
print(f"\nSAMPLE TICKERS (first 30):")
print(f"  {', '.join(sorted(tickers)[:30])}")

# Check for junk patterns
junk_patterns = [t for t in tickers if len(t) > 4 or any(x in t for x in [".", "^", "-"])]
print(f"\nQUALITY CHECK:")
print(f"  Tickers with junk patterns: {len(junk_patterns)}")
print(f"  Clean tickers (1-4 chars): {len([t for t in tickers if len(t) <= 4])}")

print("\n" + "=" * 70)
if len(found) >= 20 and len(junk_patterns) < 10:
    print("STATUS: EXCELLENT - Scanner ready for quality scans!")
elif len(found) >= 10:
    print("STATUS: GOOD - Most major stocks present")
else:
    print("STATUS: NEEDS IMPROVEMENT - Run build_quality_universe.py")
print("=" * 70)

