import datetime as dt
import requests
import pandas as pd
import streamlit as st

from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

TIINGO_BASE = "https://api.tiingo.com"


# ---------------- Tiingo API ----------------
@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def tiingo_all_us_tickers(token: str) -> list[str]:
    """
    Build a broad Tiingo ticker universe via utilities/search (A–Z) and allow REITs/Equities.
    """
    import string
    url = "https://api.tiingo.com/tiingo/utilities/search"
    headers = {"Content-Type": "application/json"}
    tickers = []

    logger.info("Running Tiingo A–Z fetch (enhanced REIT/Equity version)...")

    try:
        for ch in string.ascii_uppercase:
            params = {"token": token, "query": ch, "limit": 1000}
            r = requests.get(url, headers=headers, params=params, timeout=20)
            if not r.ok:
                logger.warning(f"Search chunk {ch} failed ({r.status_code})")
                continue

            data = r.json()
            for d in data:
                sym = (d.get("ticker") or "").upper()
                exch = d.get("exchange", "")
                asset_type = d.get("assetType", "")
                if (
                    sym.isalpha()
                    and exch not in ("CRYPTO", "FX")
                    and asset_type in ("Stock", "REIT", "Equity", "ETF", "")
                ):
                    tickers.append(sym)

        tickers = sorted(set(tickers))
        logger.info(f"Tiingo ticker universe fetch complete ({len(tickers)} symbols)")

        if "EFC" in tickers:
            logger.debug("EFC included successfully.")
        else:
            logger.warning("EFC still missing.")

    except Exception as e:
        logger.error(f"Tiingo tickers fetch error: {e}")
        return []

    logger.debug("tiingo_all_us_tickers() CALLED from enhanced A–Z fallback")
    return tickers








@st.cache_data(show_spinner=False, ttl=60 * 30)
def tiingo_history(ticker: str, token: str, days: int) -> pd.DataFrame | None:
    """Fetch daily historical data for a US stock from Tiingo."""
    import datetime as dt
    import pandas as pd
    import requests

    start = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    url = f"https://api.tiingo.com/tiingo/daily/{ticker.lower()}/prices"

    params = {
        "token": token,
        "startDate": start,
        "resampleFreq": "daily",
        "format": "json",
    }

    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            logger.warning(f"Tiingo fetch failed for {ticker}: {r.status_code}")
            return None

        data = r.json()
        if not data or not isinstance(data, list):
            logger.warning(f"No data in Tiingo response for {ticker}")
            return None

        df = pd.DataFrame(data)
        if df.empty:
            return None

        df["date"] = pd.to_datetime(df["date"])
        df.rename(
            columns={
                "date": "Date",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            },
            inplace=True,
        )
        return df[["Date", "Open", "High", "Low", "Close", "Volume"]].sort_values(
            "Date"
        ).reset_index(drop=True)

    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return None
    
    # ---------------- Tiingo Sector Metadata ----------------
@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def get_tiingo_sector(ticker: str, token: str) -> str:
    """Fetch sector classification for a ticker from Tiingo metadata."""
    import requests
    url = f"https://api.tiingo.com/tiingo/daily/{ticker.lower()}"
    headers = {"Authorization": f"Token {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if not r.ok:
            logger.warning(f"Sector fetch failed for {ticker}: {r.status_code}")
            return "Unknown"
        data = r.json()
        sector = data.get("sector", "Unknown")
        if not sector:
            sector = "Unknown"
        return sector
    except Exception as e:
        logger.error(f"Error getting sector for {ticker}: {e}")
        return "Unknown"

# ---------------- Sector Snapshot (EMA20 vs EMA50) ----------------
@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def get_sector_snapshot(token: str):
    """Return quick EMA-based trend snapshot for key sector ETFs."""
    import pandas as pd
    import requests

    sectors = {
        "XLK": "Technology",
        "XLF": "Financials",
        "XLE": "Energy",
        "XLV": "Healthcare",
        "XLI": "Industrials",
        "XLY": "Consumer Discretionary",
        "XLP": "Consumer Staples",
        "XLB": "Materials",
        "XLRE": "Real Estate",
        "XLU": "Utilities",
        "XLC": "Communication Services",
    }

    start = (pd.Timestamp.utcnow().date() - pd.Timedelta(days=60)).isoformat()
    rows = []
    for sym, name in sectors.items():
        try:
            url = f"https://api.tiingo.com/tiingo/daily/{sym.lower()}/prices"
            headers = {"Authorization": f"Token {token}"}
            params = {"resampleFreq": "daily", "startDate": start}
            r = requests.get(url, headers=headers, params=params, timeout=10)
            if r.status_code != 200:
                continue
            df = pd.DataFrame(r.json())
            if df.empty:
                continue
            close = df["close"].astype(float)
            ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
            ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
            bias = "Uptrend" if ema20 > ema50 else "Downtrend"
            # Calculate momentum (5-day and 20-day returns)
            current_price = float(close.iloc[-1])
            price_5d_ago = float(close.iloc[-5]) if len(close) >= 5 else current_price
            price_20d_ago = float(close.iloc[-20]) if len(close) >= 20 else current_price

            momentum_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100
            momentum_20d = ((current_price - price_20d_ago) / price_20d_ago) * 100

            # Relative strength (vs SPY if available)
            rows.append({
                "ETF": sym,
                "Sector": name,
                "Bias": bias,
                "Momentum_5D": round(momentum_5d, 2),
                "Momentum_20D": round(momentum_20d, 2),
                "Price": round(current_price, 2)
            })
        except Exception:
            continue

    return pd.DataFrame(rows)


# ---------------- Sector Rotation Analysis ----------------
@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def analyze_sector_rotation(token: str) -> dict:
    """
    Analyze sector rotation to identify hot and cold sectors.
    Returns sectors to focus on and avoid.
    """
    sector_df = get_sector_snapshot(token)

    if sector_df.empty:
        return {
            "hot_sectors": [],
            "cold_sectors": [],
            "rotation_signal": "Unknown",
            "market_breadth": 0
        }

    # Classify sectors by momentum
    hot_sectors = []
    cold_sectors = []

    for _, row in sector_df.iterrows():
        sector_name = row["Sector"]
        momentum_5d = row.get("Momentum_5D", 0)
        momentum_20d = row.get("Momentum_20D", 0)
        bias = row.get("Bias", "Neutral")

        # Hot sector: uptrend + positive momentum
        if bias == "Uptrend" and momentum_5d > 0 and momentum_20d > 0:
            hot_sectors.append({
                "sector": sector_name,
                "etf": row["ETF"],
                "momentum_5d": momentum_5d,
                "momentum_20d": momentum_20d
            })
        # Cold sector: downtrend or negative momentum
        elif bias == "Downtrend" or (momentum_5d < 0 and momentum_20d < 0):
            cold_sectors.append({
                "sector": sector_name,
                "etf": row["ETF"],
                "momentum_5d": momentum_5d,
                "momentum_20d": momentum_20d
            })

    # Sort by momentum
    hot_sectors.sort(key=lambda x: x["momentum_5d"], reverse=True)
    cold_sectors.sort(key=lambda x: x["momentum_5d"])

    # Market breadth (% of sectors in uptrend)
    uptrend_count = len(sector_df[sector_df["Bias"] == "Uptrend"])
    market_breadth = (uptrend_count / len(sector_df)) * 100 if len(sector_df) > 0 else 0

    # Rotation signal
    if market_breadth > 70:
        rotation_signal = "Risk On - Most sectors strong"
    elif market_breadth > 50:
        rotation_signal = "Mixed - Selective rotation"
    elif market_breadth > 30:
        rotation_signal = "Defensive - Weak breadth"
    else:
        rotation_signal = "Risk Off - Most sectors weak"

    return {
        "hot_sectors": hot_sectors[:5],  # Top 5
        "cold_sectors": cold_sectors[:5],  # Bottom 5
        "rotation_signal": rotation_signal,
        "market_breadth": round(market_breadth, 1),
        "sector_data": sector_df
    }

# ---------------- Market Snapshot (SPY + VIX) ----------------
import datetime as dt
import pandas as pd
import requests

@st.cache_data(ttl=60 * 60 * 6)  # refresh every 6 hours
def get_market_snapshot(token: str):
    """Fetch SPY trend and volatility context for Smart Mode."""
    try:
        start = (dt.date.today() - dt.timedelta(days=60)).isoformat()
        url = f"https://api.tiingo.com/tiingo/daily/spy/prices"
        params = {"token": token, "startDate": start, "resampleFreq": "daily"}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return None
        df = pd.DataFrame(r.json())
        df["date"] = pd.to_datetime(df["date"])
        df["EMA20"] = df["close"].ewm(span=20).mean()
        df["EMA50"] = df["close"].ewm(span=50).mean()
        df["TR"] = df["close"].diff().abs()
        df["ATR20"] = df["TR"].rolling(20).mean()
        atrp = (df["ATR20"].iloc[-1] / df["close"].iloc[-1]) * 100

        bias = "Uptrend" if df["EMA20"].iloc[-1] > df["EMA50"].iloc[-1] else "Downtrend"
        vol_regime = "High Volatility" if atrp > 2.5 else "Low Volatility"

        return {
            "bias": bias,
            "vol_regime": vol_regime,
            "spy_price": round(df["close"].iloc[-1], 2),
            "atrp": round(atrp, 2)
        }
    except Exception as e:
        print(f"⚠️ Market snapshot error: {e}")
        return None
    
    # ---------------- Intraday (custom timeframe) Data Fetch ----------------
@st.cache_data(ttl=600, show_spinner=False)
def fetch_tiingo_intraday(symbol: str, token: str,
                          timeframe: str = "1hour",
                          lookback_days: int = 5):
    """
    Fetch recent intraday prices for a symbol.
    timeframe: one of {"5min","15min","30min","1hour","2hour","4hour"}
    lookback_days: how many days of data to pull back.
    """
    import pandas as pd, requests, datetime as dt

    start = (dt.datetime.utcnow() - dt.timedelta(days=lookback_days)).isoformat()
    url = f"https://api.tiingo.com/iex/{symbol.lower()}/prices"
    params = {"resampleFreq": timeframe, "startDate": start}
    headers = {"Authorization": f"Token {token}"}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if not r.ok:
            return pd.DataFrame()
        df = pd.DataFrame(r.json())
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"])
        df["close"] = df["close"].astype(float)
        return df[["date", "close"]]
    except Exception:
        return pd.DataFrame()

import requests
import streamlit as st

@st.cache_data(ttl=86400)
def get_next_earnings_date(symbol: str, token: str) -> str:
    """
    Fetch next earnings date from Tiingo metadata.
    Returns 'YYYY-MM-DD' or 'N/A' if unavailable.
    """
    url = f"https://api.tiingo.com/tiingo/daily/{symbol.lower()}"
    headers = {"Authorization": f"Token {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if not r.ok:
            print(f"⚠️ Earnings fetch failed for {symbol}: {r.status_code}")
            return "N/A"
        data = r.json()
        return data.get("nextEarningsDate", "N/A")
    except Exception as e:
        print(f"⚠️ Earnings error for {symbol}: {e}")
        return "N/A"
    
    # ---------------------------------------------------------------------------
# 🔹 Tiingo Real-Time Quote (IEX) — supports pre/post market for Power plan
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_tiingo_realtime_quote(symbol: str, token: str) -> dict:
    """Return real-time quote (includes pre- and post-market) from Tiingo IEX."""
    import requests
    url = f"https://api.tiingo.com/iex/{symbol.lower()}"
    headers = {"Authorization": f"Token {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if not r.ok:
            print(f"⚠️ Tiingo real-time fetch failed {symbol}: {r.status_code}")
            return {}
        data = r.json()[0] if isinstance(r.json(), list) else r.json()

        # Normalize fields so .get("last") always works
        if data.get("last") is None and data.get("tngoLast") is not None:
            data["last"] = data["tngoLast"]

        return data

    except Exception as e:
        print(f"❌ Tiingo real-time fetch error for {symbol}: {e}")
        return {}

# ---------------------------------------------------------------------------
# 🔹 Yahoo Finance fallback — for pre-market quotes when Tiingo IEX is quiet
# ---------------------------------------------------------------------------
def fetch_yf_premarket(symbol: str):
    """Fetch pre-market price from Yahoo Finance if Tiingo has no new trades yet."""
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        info = t.info
        pm_price = info.get("preMarketPrice")
        return pm_price
    except Exception as e:
        print(f"⚠️ YF premarket fetch failed for {symbol}: {e}")
        return None
