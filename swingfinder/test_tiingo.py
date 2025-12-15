"""Test script to verify Tiingo API is working"""
import requests
import pandas as pd
from datetime import datetime, timedelta

# Load token from secrets
try:
    with open('.streamlit/secrets.toml', 'r') as f:
        for line in f:
            if 'TIINGO_TOKEN' in line or 'TIINGO_API_KEY' in line:
                token = line.split('=')[1].strip().strip('"')
                break
except:
    print("❌ Could not load token from secrets.toml")
    exit(1)

print(f"✅ Token loaded: {token[:10]}...")

# Test 1: Fetch AAPL data
print("\n📊 Testing AAPL data fetch...")
start = (datetime.now().date() - timedelta(days=30)).isoformat()
url = f"https://api.tiingo.com/tiingo/daily/aapl/prices"
params = {
    "token": token,
    "startDate": start,
    "resampleFreq": "daily",
    "format": "json",
}

try:
    r = requests.get(url, params=params, timeout=15)
    print(f"Status Code: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"✅ Received {len(data)} data points")
        if data:
            latest = data[-1]
            print(f"Latest data: {latest['date']}")
            print(f"Close: ${latest['close']:.2f}")
            print(f"Volume: {latest['volume']:,}")
    else:
        print(f"❌ API Error: {r.status_code}")
        print(f"Response: {r.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Check API rate limits
print("\n🔍 Checking API account info...")
url2 = "https://api.tiingo.com/api/test"
params2 = {"token": token}

try:
    r2 = requests.get(url2, params=params2, timeout=10)
    if r2.status_code == 200:
        info = r2.json()
        print(f"✅ API Status: {info}")
    else:
        print(f"❌ Could not fetch API info: {r2.status_code}")
except Exception as e:
    print(f"❌ Error checking API: {e}")

print("\n✅ Test complete!")

