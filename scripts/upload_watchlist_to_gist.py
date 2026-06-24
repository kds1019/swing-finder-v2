"""
One-time script to upload local watchlist to GitHub Gist
Run this to sync your local watchlist data to Streamlit Cloud
"""

import json
import os
import requests

# Load your Gist credentials
GIST_ID = input("Enter your GIST_ID: ").strip()
GITHUB_TOKEN = input("Enter your GITHUB_GIST_TOKEN: ").strip()

if not GIST_ID or not GITHUB_TOKEN:
    print("❌ Error: GIST_ID and GITHUB_GIST_TOKEN are required")
    exit(1)

# Load local watchlist data
print("\n📂 Loading local watchlist data...")

try:
    with open("data/watchlist_enhanced.json", "r") as f:
        enhanced_data = json.load(f)
    print(f"✅ Loaded {len(enhanced_data)} stocks from enhanced watchlist")
except Exception as e:
    print(f"❌ Error loading enhanced watchlist: {e}")
    enhanced_data = []

try:
    with open("data/watchlist.json", "r") as f:
        scanner_data = json.load(f)
    print(f"✅ Loaded scanner watchlist")
except Exception as e:
    print(f"❌ Error loading scanner watchlist: {e}")
    scanner_data = {}

# Upload to Gist
print("\n☁️ Uploading to GitHub Gist...")

url = f"https://api.github.com/gists/{GIST_ID}"
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Prepare files to update
files = {}

if enhanced_data:
    files["watchlist_enhanced.json"] = {
        "content": json.dumps(enhanced_data, indent=2)
    }

if scanner_data:
    files["watchlist.json"] = {
        "content": json.dumps(scanner_data, indent=2)
    }

# Update Gist
try:
    response = requests.patch(url, headers=headers, json={"files": files})
    
    if response.status_code == 200:
        print("✅ Successfully uploaded watchlist to Gist!")
        print(f"\n📊 Uploaded:")
        if enhanced_data:
            print(f"   - watchlist_enhanced.json ({len(enhanced_data)} stocks)")
        if scanner_data:
            print(f"   - watchlist.json (scanner format)")
        print(f"\n🎉 Your watchlist is now synced to Streamlit Cloud!")
        print(f"   Go to Pre-Market Dashboard and refresh - it should show your stocks now.")
    else:
        print(f"❌ Error uploading to Gist: {response.status_code}")
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")

