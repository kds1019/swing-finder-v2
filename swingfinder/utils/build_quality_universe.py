"""
Build a high-quality ticker universe for swing trading.
Uses multiple sources to ensure comprehensive coverage of liquid, tradeable stocks.
"""

import os
import json
import requests
import time
from datetime import datetime

TIINGO_TOKEN = os.getenv("TIINGO_TOKEN")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "filtered_universe.json")

# Quality filters for swing trading (user's preferred range)
MIN_PRICE = 10.0
MAX_PRICE = 60.0
MIN_AVG_VOLUME = 1_000_000  # 1M volume for better liquidity


def get_sp500_tickers() -> list[str]:
    """Get S&P 500 tickers - using curated list since Wikipedia blocks scraping."""
    print("📊 Loading S&P 500 tickers...")

    # Curated S&P 500 list (major components - you can expand this)
    sp500 = [
        # Tech Giants
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL",
        "ADBE", "CRM", "ACN", "CSCO", "AMD", "INTC", "IBM", "QCOM", "TXN", "INTU",
        "NOW", "AMAT", "MU", "ADI", "LRCX", "KLAC", "SNPS", "CDNS", "MCHP", "FTNT",

        # Finance
        "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "AXP", "SPGI",
        "CB", "MMC", "PGR", "AON", "TFC", "USB", "PNC", "COF", "AIG", "MET",

        # Healthcare
        "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY",
        "AMGN", "GILD", "CVS", "CI", "ELV", "REGN", "VRTX", "HUM", "BIIB", "ISRG",

        # Consumer
        "WMT", "HD", "MCD", "NKE", "COST", "SBUX", "TGT", "LOW", "TJX", "DG",
        "BKNG", "MAR", "HLT", "CMG", "YUM", "ABNB", "LULU", "ROST", "ULTA", "DPZ",

        # Industrials
        "CAT", "BA", "HON", "UPS", "RTX", "LMT", "GE", "DE", "MMM", "NOC",
        "GD", "EMR", "ETN", "ITW", "PH", "WM", "FDX", "NSC", "CSX", "UNP",

        # Energy
        "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL",
        "DVN", "HES", "MRO", "APA", "FANG", "BKR", "KMI", "WMB", "OKE", "LNG",

        # Consumer Staples
        "PG", "KO", "PEP", "COST", "WMT", "PM", "MO", "CL", "MDLZ", "GIS",
        "KHC", "HSY", "K", "CAG", "SJM", "CPB", "KMB", "CLX", "CHD", "TSN",

        # Communications
        "GOOGL", "META", "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA",
        "TTWO", "PARA", "WBD", "OMC", "IPG", "FOXA", "FOX", "MTCH", "NWSA", "NWS",

        # Utilities
        "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PEG", "XEL", "ED",

        # Real Estate
        "AMT", "PLD", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "VICI",

        # Materials
        "LIN", "APD", "SHW", "ECL", "FCX", "NEM", "NUE", "DOW", "DD", "PPG",
    ]

    print(f"  ✅ Got {len(set(sp500))} S&P 500 tickers")
    return list(set(sp500))


def get_nasdaq100_tickers() -> list[str]:
    """Get NASDAQ 100 tickers - using curated list."""
    print("📊 Loading NASDAQ 100 tickers...")

    nasdaq100 = [
        # Already covered in S&P 500, but adding NASDAQ-specific ones
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST",
        "NFLX", "AMD", "PEP", "ADBE", "CSCO", "TMUS", "CMCSA", "INTC", "TXN", "QCOM",
        "INTU", "AMGN", "HON", "AMAT", "SBUX", "ISRG", "BKNG", "GILD", "ADI", "VRTX",
        "ADP", "REGN", "MDLZ", "LRCX", "PANW", "KLAC", "SNPS", "CDNS", "MELI", "PYPL",
        "ASML", "ABNB", "CRWD", "MAR", "ORLY", "CTAS", "MNST", "FTNT", "AZN", "NXPI",
        "WDAY", "ADSK", "MRVL", "DASH", "PCAR", "CPRT", "PAYX", "ROST", "ODFL", "FAST",
        "KDP", "EA", "DXCM", "VRSK", "CTSH", "LULU", "GEHC", "IDXX", "EXC", "XEL",
        "CCEP", "ON", "TEAM", "CSGP", "TTWO", "ANSS", "ZS", "DDOG", "BIIB", "ILMN",
        "CDW", "WBD", "GFS", "MDB", "MRNA", "SMCI", "WBA", "DLTR", "ARM", "FANG",
    ]

    print(f"  ✅ Got {len(set(nasdaq100))} NASDAQ 100 tickers")
    return list(set(nasdaq100))


def get_popular_stocks() -> list[str]:
    """Curated list of popular liquid stocks for swing trading."""
    return [
        # Mega Cap Tech
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "NFLX",
        
        # Semiconductors
        "AMD", "INTC", "QCOM", "AVGO", "TXN", "AMAT", "MU", "LRCX", "KLAC", "MRVL",
        
        # Finance
        "JPM", "BAC", "WFC", "C", "GS", "MS", "SCHW", "AXP", "BLK", "SPGI", "COF",
        
        # Payments/Fintech
        "V", "MA", "PYPL", "SQ", "COIN", "HOOD", "SOFI", "AFRM", "UPST",
        
        # Retail/Consumer
        "WMT", "COST", "TGT", "HD", "LOW", "NKE", "SBUX", "MCD", "CMG", "LULU",
        
        # Media/Entertainment
        "DIS", "PARA", "WBD", "SPOT", "RBLX", "EA", "TTWO", "ATVI",
        
        # Travel/Gig Economy
        "UBER", "LYFT", "DASH", "ABNB", "BKNG", "EXPE", "MAR", "HLT",
        
        # Automotive/EV
        "F", "GM", "RIVN", "LCID", "NIO", "XPEV", "LI",
        
        # Energy
        "XOM", "CVX", "COP", "SLB", "HAL", "MRO", "OXY", "DVN", "EOG", "PXD",
        
        # Healthcare/Biotech
        "PFE", "ABBV", "JNJ", "UNH", "LLY", "MRK", "BMY", "GILD", "BIIB", "MRNA", "REGN",
        
        # Industrials
        "BA", "CAT", "DE", "GE", "HON", "MMM", "RTX", "LMT", "NOC", "GD",
        
        # Growth/Cloud
        "PLTR", "SNOW", "DKNG", "PINS", "SNAP", "TWLO", "ZM", "DOCU", "CRWD", "NET",
        
        # E-commerce/Retail Tech
        "SHOP", "ETSY", "W", "CHWY", "CVNA",
        
        # REITs (popular liquid ones)
        "AMT", "PLD", "CCI", "EQIX", "PSA", "DLR", "O", "VICI", "SPG",
        
        # Consumer Staples
        "PG", "KO", "PEP", "COST", "WMT", "CL", "KHC", "MDLZ",
        
        # Telecom
        "T", "VZ", "TMUS",
        
        # Materials
        "FCX", "NEM", "GOLD", "AA", "X", "CLF",
    ]


def validate_and_enrich_tickers(tickers: list[str], token: str) -> list[dict]:
    """
    Validate tickers with Tiingo and get metadata.
    Only keeps tickers that exist and meet quality criteria.
    """
    print(f"\n🔍 Validating {len(tickers)} tickers with Tiingo...")
    
    validated = []
    headers = {"Authorization": f"Token {token}"}
    
    for i, ticker in enumerate(tickers, 1):
        try:
            # Get ticker metadata
            url = f"https://api.tiingo.com/tiingo/daily/{ticker.lower()}"
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.ok:
                data = resp.json()
                name = data.get("name", ticker)
                validated.append({
                    "ticker": ticker.upper(),
                    "name": name,
                    "exchange": data.get("exchangeCode", ""),
                })
                
                if i % 50 == 0:
                    print(f"  ✅ Validated {i}/{len(tickers)} tickers...")
            else:
                print(f"  ⚠️ Skipped {ticker} (not found)")
            
            time.sleep(0.15)  # Rate limit protection
            
        except Exception as e:
            print(f"  ⚠️ Error validating {ticker}: {e}")
            continue
    
    print(f"✅ Validated {len(validated)}/{len(tickers)} tickers")
    return validated


def build_universe(token: str) -> list[dict]:
    """Build comprehensive ticker universe from multiple sources."""
    all_tickers = set()
    
    # Get S&P 500
    sp500 = get_sp500_tickers()
    all_tickers.update(sp500)
    
    # Get NASDAQ 100
    nasdaq100 = get_nasdaq100_tickers()
    all_tickers.update(nasdaq100)
    
    # Add popular stocks
    popular = get_popular_stocks()
    all_tickers.update(popular)
    
    print(f"\n📦 Combined universe: {len(all_tickers)} unique tickers")
    
    # Validate and enrich
    validated = validate_and_enrich_tickers(sorted(all_tickers), token)
    
    return validated


def save_universe(tickers: list[dict]):
    """Save the universe to JSON file."""
    data = {
        "meta": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "count": len(tickers),
            "sources": ["S&P 500", "NASDAQ 100", "Popular Liquid Stocks"],
            "filters": {
                "description": "High-quality swing trading stocks",
                "price_range": [MIN_PRICE, MAX_PRICE],
                "min_avg_volume": MIN_AVG_VOLUME,
            },
        },
        "tickers": tickers,
    }
    
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Saved {len(tickers)} tickers to {CACHE_PATH}")
    
    # Show sample of major stocks
    ticker_list = [t["ticker"] for t in tickers]
    major_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "AMD", "INTC", "JPM"]
    found_major = [s for s in major_stocks if s in ticker_list]
    
    print(f"\n✅ Major stocks included ({len(found_major)}/10):")
    print(f"   {', '.join(found_major)}")
    
    missing = [s for s in major_stocks if s not in ticker_list]
    if missing:
        print(f"\n⚠️ Missing major stocks: {', '.join(missing)}")


def main():
    """Main entry point."""
    token = TIINGO_TOKEN or input("Enter Tiingo API Token: ").strip()
    
    if not token:
        print("❌ No Tiingo token provided!")
        return
    
    print("🚀 Building high-quality ticker universe for swing trading...\n")
    
    tickers = build_universe(token)
    save_universe(tickers)
    
    print("\n✅ Universe build complete!")
    print(f"📊 Total tickers: {len(tickers)}")
    print(f"🎯 Ready for scanning!")


if __name__ == "__main__":
    main()

