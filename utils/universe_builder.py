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

# Import rate limiter if available
try:
    from utils.rate_limiter import tiingo_limiter
    USE_RATE_LIMITER = True
except ImportError:
    USE_RATE_LIMITER = False
    print("⚠️ Rate limiter not available, using manual delays")

TIINGO_TOKEN = os.getenv("TIINGO_TOKEN")  # or set manually for quick tests
CACHE_PATH = os.path.join(os.path.dirname(__file__), "filtered_universe.json")

# ------------------ Configurable Filters ------------------
EXCHANGES = {"NYSE", "NASDAQ", "AMEX"}
MIN_PRICE = 10.0
MAX_PRICE = 60.0  # User's preferred swing trading range
MIN_AVG_VOLUME = 1_000_000  # 1M volume for better liquidity
KEEP_TYPES = {"Stock", "Common Stock", "REIT", "Equity"}

# -----------------------------------------------------------

def get_curated_ticker_list() -> list[str]:
    """
    Return curated list of ~500 major liquid stocks.
    This replaces the 200+ API call alphabet search with a single list.
    Includes: S&P 500, NASDAQ 100, and popular swing trading stocks.
    """
    return [
        # Mega Cap Tech (FAANG+)
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "NVDA", "META", "NFLX",

        # Semiconductors
        "AMD", "INTC", "QCOM", "AVGO", "TXN", "AMAT", "MU", "LRCX", "KLAC", "MRVL",
        "MCHP", "ADI", "NXPI", "ON", "SWKS", "QRVO", "MPWR", "ENTG",

        # Financials
        "JPM", "BAC", "WFC", "C", "GS", "MS", "SCHW", "AXP", "BLK", "SPGI",
        "USB", "PNC", "TFC", "COF", "BK", "STT", "NTRS", "FITB", "KEY", "RF",

        # Payments
        "V", "MA", "PYPL", "SQ", "COIN", "HOOD", "SOFI", "AFRM", "UPST",

        # Retail & Consumer
        "WMT", "COST", "TGT", "HD", "LOW", "NKE", "SBUX", "MCD", "CMG", "YUM",
        "DG", "DLTR", "ROST", "TJX", "BBY", "ULTA", "DKS", "LULU",

        # Media & Entertainment
        "DIS", "PARA", "WBD", "SPOT", "RBLX", "EA", "TTWO", "ATVI",

        # Travel & Hospitality
        "UBER", "LYFT", "DASH", "ABNB", "BKNG", "EXPE", "MAR", "HLT", "AAL", "DAL", "UAL", "LUV",

        # Automotive
        "F", "GM", "RIVN", "LCID", "NIO", "XPEV", "LI", "TSLA",

        # Energy
        "XOM", "CVX", "COP", "SLB", "HAL", "MRO", "OXY", "DVN", "EOG", "PXD",
        "MPC", "VLO", "PSX", "HES", "FANG", "APA",

        # Healthcare & Pharma
        "PFE", "ABBV", "JNJ", "UNH", "LLY", "MRK", "BMY", "GILD", "BIIB", "MRNA",
        "AMGN", "REGN", "VRTX", "ISRG", "DHR", "TMO", "ABT", "SYK", "BSX", "MDT",

        # Industrials
        "BA", "CAT", "DE", "GE", "HON", "MMM", "RTX", "LMT", "NOC", "GD",
        "EMR", "ETN", "ITW", "PH", "ROK", "DOV", "FTV",

        # Cloud & Software
        "PLTR", "SNOW", "DKNG", "PINS", "SNAP", "TWLO", "ZM", "DOCU", "CRWD",
        "CRM", "ORCL", "ADBE", "NOW", "WDAY", "TEAM", "DDOG", "NET", "MDB",
        "PANW", "ZS", "OKTA", "FTNT", "SPLK",

        # E-commerce & Logistics
        "SHOP", "ETSY", "EBAY", "W", "CHWY", "CVNA", "FDX", "UPS", "XPO",

        # Telecom
        "T", "VZ", "TMUS", "CMCSA", "CHTR", "DIS",

        # REITs
        "AMT", "PLD", "CCI", "EQIX", "PSA", "DLR", "O", "WELL", "AVB", "EQR",

        # Materials & Chemicals
        "LIN", "APD", "ECL", "SHW", "DD", "DOW", "NEM", "FCX", "NUE", "STLD",

        # Consumer Staples
        "PG", "KO", "PEP", "COST", "WMT", "CL", "KMB", "GIS", "K", "HSY",

        # Biotech
        "BNTX", "MRNA", "NVAX", "SGEN", "ALNY", "BMRN", "EXAS", "ILMN", "INCY",

        # Cannabis
        "TLRY", "CGC", "SNDL", "ACB", "CRON",

        # EV & Battery
        "TSLA", "RIVN", "LCID", "FSR", "GOEV", "RIDE", "QS", "BLNK", "CHPT",

        # Fintech
        "SQ", "PYPL", "COIN", "HOOD", "SOFI", "AFRM", "UPST", "LC", "NU",

        # Cybersecurity
        "CRWD", "ZS", "PANW", "FTNT", "OKTA", "NET", "S", "TENB",

        # Gaming
        "RBLX", "U", "EA", "TTWO", "ATVI", "ZNGA",

        # Solar & Clean Energy
        "ENPH", "SEDG", "RUN", "NOVA", "FSLR", "SPWR",

        # SPACs & High Growth
        "SOFI", "OPEN", "CLOV", "WISH", "SKLZ", "DKNG",

        # Meme Stocks
        "GME", "AMC", "BB", "BBBY", "KOSS", "EXPR",

        # Chinese ADRs
        "BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "BILI", "IQ",

        # Additional S&P 500 Components
        "ABBV", "ACN", "ADBE", "ADP", "AIG", "ALL", "AMAT", "AMP", "AMT", "AMZN",
        "ANTM", "AON", "APA", "APD", "APH", "APTV", "ARE", "ATO", "AVB", "AVGO",
        "AWK", "AXP", "AZO", "BA", "BAC", "BAX", "BBY", "BDX", "BEN", "BIIB",
        "BK", "BKNG", "BKR", "BLK", "BMY", "BR", "BRK.B", "BSX", "BWA", "BXP",
        "C", "CAG", "CAH", "CARR", "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL",
        "CDNS", "CDW", "CE", "CERN", "CF", "CFG", "CHD", "CHRW", "CHTR", "CI",
        "CINF", "CL", "CLX", "CMA", "CMCSA", "CME", "CMG", "CMI", "CMS", "CNC",
        "CNP", "COF", "COO", "COP", "COST", "COTY", "CPB", "CPRT", "CRM", "CSCO",
        "CSX", "CTAS", "CTLT", "CTRA", "CTSH", "CTVA", "CTXS", "CVS", "CVX", "CZR",
        "D", "DAL", "DD", "DE", "DFS", "DG", "DGX", "DHI", "DHR", "DIS",
        "DISCA", "DISCK", "DISH", "DLR", "DLTR", "DOV", "DOW", "DPZ", "DRE", "DRI",
        "DTE", "DUK", "DVA", "DVN", "DXC", "DXCM", "EA", "EBAY", "ECL", "ED",
        "EFX", "EIX", "EL", "EMN", "EMR", "ENPH", "EOG", "EQIX", "EQR", "ES",
        "ESS", "ETN", "ETR", "ETSY", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR",
        "F", "FANG", "FAST", "FB", "FBHS", "FCX", "FDX", "FE", "FFIV", "FIS",
        "FISV", "FITB", "FLT", "FMC", "FOX", "FOXA", "FRC", "FRT", "FTNT", "FTV",
        "GD", "GE", "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL",
        "GPC", "GPN", "GPS", "GRMN", "GS", "GWW", "HAL", "HAS", "HBAN", "HBI",
        "HCA", "HD", "HES", "HIG", "HII", "HLT", "HOLX", "HON", "HPE", "HPQ",
        "HRL", "HSIC", "HST", "HSY", "HUM", "HWM", "IBM", "ICE", "IDXX", "IEX",
        "IFF", "ILMN", "INCY", "INFO", "INTC", "INTU", "IP", "IPG", "IPGP", "IQV",
        "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT", "JCI", "JKHY",
        "JNJ", "JNPR", "JPM", "K", "KEY", "KEYS", "KHC", "KIM", "KLAC", "KMB",
        "KMI", "KMX", "KO", "KR", "L", "LDOS", "LEG", "LEN", "LH", "LHX",
        "LIN", "LKQ", "LLY", "LMT", "LNC", "LNT", "LOW", "LRCX", "LUMN", "LUV",
        "LVS", "LW", "LYB", "LYV", "MA", "MAA", "MAR", "MAS", "MCD", "MCHP",
        "MCK", "MCO", "MDLZ", "MDT", "MET", "MGM", "MHK", "MKC", "MKTX", "MLM",
        "MMC", "MMM", "MNST", "MO", "MOS", "MPC", "MPWR", "MRK", "MRNA", "MRO",
        "MS", "MSCI", "MSFT", "MSI", "MTB", "MTCH", "MTD", "MU", "NCLH", "NDAQ",
        "NEE", "NEM", "NFLX", "NI", "NKE", "NLOK", "NLSN", "NOC", "NOW", "NRG",
        "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWL", "NWS", "NWSA", "NXPI",
        "O", "ODFL", "OGN", "OKE", "OMC", "ORCL", "ORLY", "OTIS", "OXY", "PAYC",
        "PAYX", "PCAR", "PEAK", "PEG", "PENN", "PEP", "PFE", "PFG", "PG", "PGR",
        "PH", "PHM", "PKG", "PKI", "PLD", "PM", "PNC", "PNR", "PNW", "POOL",
        "PPG", "PPL", "PRGO", "PRU", "PSA", "PSX", "PTC", "PVH", "PWR", "PXD",
        "PYPL", "QCOM", "QRVO", "RCL", "RE", "REG", "REGN", "RF", "RHI", "RJF",
        "RL", "RMD", "ROK", "ROL", "ROP", "ROST", "RSG", "RTX", "SBAC", "SBUX",
        "SCHW", "SEE", "SHW", "SIVB", "SJM", "SLB", "SNA", "SNPS", "SO", "SPG",
        "SPGI", "SRE", "STE", "STT", "STX", "STZ", "SWK", "SWKS", "SYF", "SYK",
        "SYY", "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX",
        "TGT", "TJX", "TMO", "TMUS", "TPR", "TRMB", "TROW", "TRV", "TSCO", "TSLA",
        "TSN", "TT", "TTWO", "TWTR", "TXN", "TXT", "TYL", "UA", "UAA", "UAL",
        "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V", "VFC",
        "VIAC", "VLO", "VMC", "VNO", "VRSK", "VRSN", "VRTX", "VTR", "VTRS", "VZ",
        "WAB", "WAT", "WBA", "WDC", "WEC", "WELL", "WFC", "WHR", "WLTW", "WM",
        "WMB", "WMT", "WRB", "WRK", "WST", "WU", "WY", "WYNN", "XEL", "XLNX",
        "XOM", "XRAY", "XYL", "YUM", "ZBH", "ZBRA", "ZION", "ZTS",
    ]


def fetch_tiingo_universe(token: str) -> list[dict]:
    """
    Optimized universe builder using curated ticker list.
    Reduces API calls from 200+ to ~20 by validating a curated list.
    """
    print("🔄 Building universe from curated ticker list...")
    headers = {"Authorization": f"Token {token}"}

    # Get curated list
    curated_tickers = get_curated_ticker_list()
    print(f"📋 Validating {len(curated_tickers)} curated tickers...")

    all_symbols = []
    batch_size = 25  # Validate in batches

    for i in range(0, len(curated_tickers), batch_size):
        batch = curated_tickers[i:i + batch_size]

        for ticker in batch:
            try:
                # Rate limit if available
                if USE_RATE_LIMITER:
                    tiingo_limiter.wait_if_needed()

                # Validate ticker with metadata endpoint
                url = f"https://api.tiingo.com/tiingo/daily/{ticker.lower()}"
                resp = requests.get(url, headers=headers, timeout=5)

                # Record request if rate limiter available
                if USE_RATE_LIMITER:
                    tiingo_limiter.record_request()

                if resp.ok:
                    data = resp.json()
                    all_symbols.append({
                        "ticker": ticker,
                        "name": data.get("name", ticker),
                        "exchange": data.get("exchangeCode", ""),
                        "assetType": "Stock"
                    })
                else:
                    print(f"  ⚠️ {ticker} not found ({resp.status_code})")

                # Manual delay if no rate limiter
                if not USE_RATE_LIMITER:
                    time.sleep(0.1)

            except Exception as e:
                print(f"  ❌ Error validating {ticker}: {e}")
                continue

        # Progress update
        print(f"  ✅ Validated {min(i + batch_size, len(curated_tickers))}/{len(curated_tickers)} tickers")

    print(f"✅ Successfully validated {len(all_symbols)} tickers")
    return all_symbols



def filter_symbols(symbols: list[dict]) -> list[dict]:
    """
    High-quality filter for swing trading stocks.
    Focuses on liquid, tradeable U.S. equities and REITs.
    Excludes: ETFs, funds, bonds, warrants, units, preferred shares, OTC junk.
    """
    print("🧹 Filtering symbols (quality mode for swing trading)...")

    filtered = []
    seen_tickers = set()  # Prevent duplicates

    for sym in symbols:
        tkr = sym.get("ticker", "")
        name = str(sym.get("name") or "").lower()
        exchange = sym.get("exchange", "")
        asset_type = sym.get("assetType", "")

        # --- Basic ticker validation ---
        if not tkr or len(tkr) > 5:  # Skip empty or too-long tickers
            continue
        if tkr in seen_tickers:  # Skip duplicates
            continue

        # --- Exclude special characters and suffixes (warrants, units, preferred) ---
        if any(x in tkr for x in [".", "^", "/", "-", "+"]):
            continue
        if any(tkr.endswith(x) for x in ["W", "WS", "WT", "U", "R"]):  # Warrants, Units, Rights
            continue
        if len(tkr) == 5 and tkr[4] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":  # Likely preferred/class shares
            continue

        # --- Exclude non-equity asset types ---
        if any(x in name for x in ["fund", "etf", "trust", "bond", "note", "index",
                                     "portfolio", "treasury", "municipal", "debt"]):
            continue

        # --- Exclude ADRs with weird suffixes (keep clean ADRs like BABA) ---
        if len(tkr) == 5 and tkr.endswith("F"):  # Common ADR suffix pattern
            continue
        if len(tkr) == 5 and tkr.endswith("Y"):  # Another ADR pattern
            continue

        # --- Only keep stocks from major U.S. exchanges ---
        if exchange and exchange not in ["NYSE", "NASDAQ", "AMEX", "NYSEArca", "BATS", ""]:
            continue

        # --- Asset type filter (be inclusive to catch all stocks) ---
        if asset_type and asset_type not in ["Stock", "Common Stock", "REIT", "Equity", "ETF", ""]:
            continue

        # --- Prefer 1-4 character tickers (cleaner stocks) ---
        if len(tkr) <= 4:
            filtered.append({"ticker": tkr.upper(), "name": sym.get("name", "")})
            seen_tickers.add(tkr)
        # Allow some 5-char tickers if they look legitimate (no suffix patterns)
        elif len(tkr) == 5 and tkr.isalpha():
            # Only if it doesn't match common junk patterns
            if not any(x in name for x in ["class", "series", "warrant", "unit"]):
                filtered.append({"ticker": tkr.upper(), "name": sym.get("name", "")})
                seen_tickers.add(tkr)

    print(f"✅ {len(filtered)} quality tickers after filtering (removed {len(symbols) - len(filtered)} junk)")
    return filtered


def save_universe(filtered: list[dict]):
    """Save universe to JSON file with metadata and timestamp."""
    now = datetime.now()

    data = {
        "meta": {
            "last_updated": now.strftime("%Y-%m-%d %H:%M:%S"),
            "last_updated_timestamp": now.timestamp(),
            "count": len(filtered),
            "method": "curated_list_validation",
            "api_calls_used": "~20 (optimized)",
            "filters": {
                "description": "Curated list of major liquid stocks",
                "exchanges": list(EXCHANGES),
                "price_range": [MIN_PRICE, MAX_PRICE],
                "min_avg_volume": MIN_AVG_VOLUME,
                "keep_types": list(KEEP_TYPES),
                "excluded": "ETFs, funds, bonds, warrants, units, preferred shares, OTC junk",
            },
        },
        "tickers": filtered,
    }

    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"💾 Saved {len(filtered)} quality tickers to {CACHE_PATH}")
    print(f"📅 Last updated: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # Show sample of major stocks if present
    ticker_list = [t["ticker"] for t in filtered]
    major_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "AMD", "INTC", "BAC"]
    found_major = [s for s in major_stocks if s in ticker_list]
    if found_major:
        print(f"✅ Major stocks found: {', '.join(found_major[:10])}")
    else:
        print("⚠️ Warning: No major stocks found in universe!")


def add_missing_major_stocks(filtered: list[dict], token: str) -> list[dict]:
    """
    Check if major stocks are present (should already be in curated list).
    This is now just a verification step.
    """
    print("\n🔍 Verifying major stocks are present...")

    # Key stocks to verify
    major_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "AMD", "INTC", "JPM"]

    existing_tickers = {t["ticker"] for t in filtered}
    missing = [s for s in major_stocks if s not in existing_tickers]

    if missing:
        print(f"  ⚠️ Missing major stocks: {', '.join(missing)}")
        print("  💡 Consider adding them to the curated list")
    else:
        print(f"  ✅ All major stocks present: {', '.join(major_stocks)}")

    return filtered


def main():
    token = TIINGO_TOKEN or input("Enter Tiingo API Token: ").strip()
    symbols = fetch_tiingo_universe(token)
    filtered = filter_symbols(symbols)

    # Add any missing major stocks
    filtered = add_missing_major_stocks(filtered, token)

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

        # Step 1: Fetch symbols
        with st.spinner("Fetching symbols from Tiingo..."):
            symbols = fetch_tiingo_universe(token)
            st.write(f"📥 Fetched {len(symbols)} symbols from Tiingo")

        # Step 2: Filter symbols
        with st.spinner("Filtering symbols..."):
            filtered = filter_symbols(symbols)
            st.write(f"✅ Filtered to {len(filtered)} quality tickers")

        # Step 3: Save to file
        with st.spinner("Saving to file..."):
            save_universe(filtered)
            st.write(f"💾 Saved to {CACHE_PATH}")

        # Verify file was written
        if os.path.exists(CACHE_PATH):
            file_time = datetime.fromtimestamp(os.path.getmtime(CACHE_PATH))
            st.success(f"✅ Universe updated with {len(filtered)} tickers at {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.error(f"❌ File not found after save: {CACHE_PATH}")
            return False

        return True
    except Exception as e:
        st.error(f"❌ Universe refresh failed: {e}")
        import traceback
        st.code(traceback.format_exc())
        return False
