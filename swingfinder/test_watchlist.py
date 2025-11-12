"""
Quick test to verify watchlist loading
"""

from utils.storage import load_watchlist, load_json

print("Testing watchlist loading...")
print()

# Test load_watchlist function
watchlist = load_watchlist()
print(f"load_watchlist() returned: {watchlist}")
print(f"Type: {type(watchlist)}")
print(f"Length: {len(watchlist)}")
print()

# Test raw file
raw_data = load_json("data/watchlist.json")
print(f"Raw watchlist.json data: {raw_data}")
print(f"Type: {type(raw_data)}")
print()

if isinstance(raw_data, dict):
    print("Watchlist is in multi-watchlist format (Scanner format)")
    for name, tickers in raw_data.items():
        print(f"  {name}: {tickers}")
elif isinstance(raw_data, list):
    print("Watchlist is in simple list format")
    print(f"  Tickers: {raw_data}")
else:
    print("Unknown format!")

print()
print("✅ Test complete!")

