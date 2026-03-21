"""
Quick script to check why RNG and AAL aren't in the universe
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
TIINGO_TOKEN = os.getenv("TIINGO_TOKEN")

def check_ticker(ticker):
    """Check if ticker meets universe criteria"""
    print(f"\n{'='*60}")
    print(f"Checking {ticker}")
    print(f"{'='*60}")
    
    # Get ticker metadata
    url = f"https://api.tiingo.com/tiingo/daily/{ticker}"
    headers = {"Content-Type": "application/json"}
    params = {"token": TIINGO_TOKEN}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return
        
        meta = response.json()
        
        print(f"\n📊 Metadata:")
        print(f"  Name: {meta.get('name', 'N/A')}")
        print(f"  Exchange: {meta.get('exchangeCode', 'N/A')}")
        print(f"  Asset Type: {meta.get('assetType', 'N/A')}")
        print(f"  Start Date: {meta.get('startDate', 'N/A')}")
        print(f"  End Date: {meta.get('endDate', 'N/A')}")
        
        # Get recent price data
        price_url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
        price_params = {"token": TIINGO_TOKEN, "startDate": "2025-01-01"}
        
        price_response = requests.get(price_url, headers=headers, params=price_params)
        if price_response.status_code == 200:
            prices = price_response.json()
            if prices:
                latest = prices[-1]
                print(f"\n💰 Latest Price Data:")
                print(f"  Date: {latest.get('date', 'N/A')}")
                print(f"  Close: ${latest.get('close', 0):.2f}")
                print(f"  Volume: {latest.get('volume', 0):,}")
                
                # Calculate average volume (last 20 days)
                if len(prices) >= 20:
                    avg_vol = sum(p.get('volume', 0) for p in prices[-20:]) / 20
                    print(f"  Avg Volume (20d): {avg_vol:,.0f}")
                else:
                    avg_vol = latest.get('volume', 0)
                    print(f"  Avg Volume: {avg_vol:,.0f} (less than 20 days data)")
                
                # Check filters
                print(f"\n✅ Filter Check:")
                
                exchange = meta.get('exchangeCode', '')
                asset_type = meta.get('assetType', '')
                price = latest.get('close', 0)
                volume = avg_vol
                
                # Exchange
                if exchange in ["NYSE", "NASDAQ", "AMEX"]:
                    print(f"  ✅ Exchange: {exchange} (PASS)")
                else:
                    print(f"  ❌ Exchange: {exchange} (FAIL - need NYSE/NASDAQ/AMEX)")
                
                # Asset Type
                if asset_type in ["Stock", "Common Stock", "REIT", "Equity"]:
                    print(f"  ✅ Asset Type: {asset_type} (PASS)")
                else:
                    print(f"  ❌ Asset Type: {asset_type} (FAIL - need Stock/Common Stock/REIT/Equity)")
                
                # Price
                if 10.0 <= price <= 60.0:
                    print(f"  ✅ Price: ${price:.2f} (PASS - within $10-$60)")
                else:
                    print(f"  ❌ Price: ${price:.2f} (FAIL - need $10-$60)")
                
                # Volume
                if volume >= 1_000_000:
                    print(f"  ✅ Volume: {volume:,.0f} (PASS - above 1M)")
                else:
                    print(f"  ❌ Volume: {volume:,.0f} (FAIL - need >1M)")
                
                # Final verdict
                print(f"\n🎯 Final Verdict:")
                if (exchange in ["NYSE", "NASDAQ", "AMEX"] and 
                    asset_type in ["Stock", "Common Stock", "REIT", "Equity"] and
                    10.0 <= price <= 60.0 and 
                    volume >= 1_000_000):
                    print(f"  ✅ {ticker} SHOULD be in universe")
                else:
                    print(f"  ❌ {ticker} should NOT be in universe")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_ticker("RNG")
    check_ticker("AAL")

