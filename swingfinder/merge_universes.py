"""
Merge the current 1,350-ticker universe with the curated quality stocks.
This ensures we have BOTH broad coverage AND the high-quality S&P 500 + NASDAQ 100 stocks.
"""

import os
import json
from datetime import datetime

CACHE_PATH = "utils/filtered_universe.json"

# Import the curated lists from build_quality_universe.py
def get_sp500_tickers() -> list[str]:
    """S&P 500 tickers from build_quality_universe.py"""
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
    return list(set(sp500))

def get_nasdaq100_tickers() -> list[str]:
    """NASDAQ 100 tickers from build_quality_universe.py"""
    nasdaq100 = [
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST",
        "NFLX", "AMD", "ADBE", "CSCO", "PEP", "INTC", "CMCSA", "TMUS", "QCOM", "TXN",
        "INTU", "AMGN", "HON", "AMAT", "SBUX", "GILD", "ADI", "VRTX", "REGN", "LRCX",
        "PYPL", "KLAC", "SNPS", "CDNS", "MELI", "ASML", "ABNB", "ORLY", "CTAS", "CRWD",
        "PANW", "ADP", "MDLZ", "MAR", "MRVL", "FTNT", "DASH", "WDAY", "ADSK", "MNST",
        "TEAM", "DXCM", "CHTR", "PCAR", "NXPI", "MCHP", "PAYX", "ROST", "ODFL", "FAST",
        "CPRT", "EA", "CTSH", "LULU", "VRSK", "CSGP", "GEHC", "IDXX", "TTWO", "ANSS",
        "ZS", "DDOG", "BIIB", "ON", "ILMN", "MDB", "WBD", "MRNA", "DLTR", "XEL",
        # Popular growth/tech stocks
        "UBER", "LYFT", "SNOW", "PLTR", "COIN", "HOOD", "SOFI", "RBLX", "RIVN", "LCID",
        "NIO", "XPEV", "LI", "SPOT", "PINS", "SNAP", "TWLO", "ZM", "DOCU", "SQ",
    ]
    return list(set(nasdaq100))

def get_popular_stocks() -> list[str]:
    """Additional popular swing trading stocks"""
    popular = [
        "UBER", "LYFT", "DASH", "ABNB", "BKNG", "EXPE",
        "F", "GM", "RIVN", "LCID", "NIO", "XPEV", "LI",
        "COIN", "HOOD", "SOFI", "AFRM", "SQ", "PYPL",
        "SNOW", "PLTR", "DKNG", "PINS", "SNAP", "TWLO", "ZM", "DOCU", "CRWD",
        "RBLX", "SPOT", "PARA", "WBD",
    ]
    return list(set(popular))

def merge_universes():
    """Merge current universe with curated quality stocks"""
    print("🔄 Merging universes...")
    
    # Load current universe
    with open(CACHE_PATH, "r") as f:
        data = json.load(f)
    
    current_tickers = {t["ticker"].upper() for t in data["tickers"]}
    print(f"📊 Current universe: {len(current_tickers)} tickers")
    
    # Get curated lists
    sp500 = get_sp500_tickers()
    nasdaq100 = get_nasdaq100_tickers()
    popular = get_popular_stocks()
    
    # Combine all curated tickers
    curated = set(sp500 + nasdaq100 + popular)
    print(f"📊 Curated quality stocks: {len(curated)} tickers")
    
    # Find missing tickers
    missing = curated - current_tickers
    print(f"🔍 Missing from current universe: {len(missing)} tickers")
    
    if missing:
        print(f"   Missing tickers: {', '.join(sorted(missing)[:20])}" + 
              (f" ... and {len(missing) - 20} more" if len(missing) > 20 else ""))
        
        # Add missing tickers
        for ticker in sorted(missing):
            data["tickers"].append({"ticker": ticker, "name": f"{ticker} (curated)"})
        
        # Update metadata
        data["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        data["meta"]["count"] = len(data["tickers"])
        data["meta"]["description"] = "Merged: Full Tiingo universe + S&P 500 + NASDAQ 100 + Popular stocks"
        
        # Save merged universe
        with open(CACHE_PATH, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✅ Merged universe saved: {len(data['tickers'])} total tickers")
        print(f"   Added {len(missing)} curated stocks to existing {len(current_tickers)} tickers")
        
        # Verify key stocks are present
        final_tickers = {t["ticker"] for t in data["tickers"]}
        test_stocks = ["LYFT", "CSX", "BKR", "AAPL", "MSFT", "TSLA"]
        for stock in test_stocks:
            status = "✅" if stock in final_tickers else "❌"
            print(f"   {status} {stock}")
    else:
        print("✅ All curated stocks already present!")

if __name__ == "__main__":
    merge_universes()

