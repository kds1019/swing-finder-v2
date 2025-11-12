"""
Direct test of Tiingo Fundamentals API
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Get token from .env or secrets
TIINGO_TOKEN = os.getenv("TIINGO_TOKEN", "")

if not TIINGO_TOKEN:
    print("❌ No TIINGO_TOKEN found!")
    print("Check your .env file or .streamlit/secrets.toml")
    exit()

print(f"✅ Token found: {TIINGO_TOKEN[:10]}...")
print()

# Test with AAPL
ticker = "AAPL"
print(f"Testing Fundamentals API with {ticker}...")
print()

# Try the statements endpoint
url = f"https://api.tiingo.com/tiingo/fundamentals/{ticker.lower()}/statements"
headers = {"Authorization": f"Token {TIINGO_TOKEN}"}

print(f"URL: {url}")
print(f"Headers: {headers}")
print()

try:
    response = requests.get(url, headers=headers, timeout=10)
    
    print(f"Status Code: {response.status_code}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS! Got data!")
        print(f"Type: {type(data)}")
        print(f"Length: {len(data) if isinstance(data, list) else 'N/A'}")
        print()
        
        if isinstance(data, list) and len(data) > 0:
            print("First item keys:")
            print(json.dumps(list(data[0].keys()), indent=2))
            print()
            print("First item sample:")
            print(json.dumps(data[0], indent=2)[:500])
        else:
            print("Data content:")
            print(json.dumps(data, indent=2)[:500])
    
    elif response.status_code == 401:
        print("❌ AUTHENTICATION FAILED!")
        print("Your API token is invalid or expired")
        print()
        print("Solutions:")
        print("1. Check your Tiingo account is active")
        print("2. Verify you have Tiingo Power subscription")
        print("3. Generate a new API token")
    
    elif response.status_code == 403:
        print("❌ FORBIDDEN!")
        print("Your subscription doesn't include Fundamentals API")
        print()
        print("Tiingo Fundamentals requires:")
        print("- Tiingo Power ($30/month) OR")
        print("- Tiingo Fundamentals add-on")
        print()
        print("Check: https://www.tiingo.com/account/api")
    
    elif response.status_code == 404:
        print("❌ NOT FOUND!")
        print(f"Ticker {ticker} not found in Tiingo database")
    
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(f"Response: {response.text[:200]}")

except Exception as e:
    print(f"❌ EXCEPTION: {e}")

print()
print("=" * 50)
print()

# Also test the daily metrics endpoint
print(f"Testing Daily Metrics API with {ticker}...")
print()

url2 = f"https://api.tiingo.com/tiingo/fundamentals/{ticker.lower()}/daily"
params = {"token": TIINGO_TOKEN}

print(f"URL: {url2}")
print()

try:
    response2 = requests.get(url2, params=params, timeout=10)
    
    print(f"Status Code: {response2.status_code}")
    print()
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"✅ SUCCESS! Got daily metrics!")
        print(f"Type: {type(data2)}")
        print(f"Length: {len(data2) if isinstance(data2, list) else 'N/A'}")
        print()
        
        if isinstance(data2, list) and len(data2) > 0:
            print("First item:")
            print(json.dumps(data2[0], indent=2)[:500])
    else:
        print(f"❌ ERROR: {response2.status_code}")
        print(f"Response: {response2.text[:200]}")

except Exception as e:
    print(f"❌ EXCEPTION: {e}")

print()
print("=" * 50)
print("TEST COMPLETE!")
print()
print("If you see 403 FORBIDDEN, you need to:")
print("1. Upgrade to Tiingo Power, OR")
print("2. Add Fundamentals API to your subscription")
print()
print("Check your subscription at: https://www.tiingo.com/account/api")

