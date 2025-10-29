
import datetime as dt
import requests
import pandas as pd
import streamlit as st

TIINGO_BASE = "https://api.tiingo.com"

# ---------------- Tiingo API ----------------
@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)  # refresh every 24 hours
def tiingo_all_us_tickers(token: str) -> list[str]:
    """
    Fetch all active US tickers from Tiingo via the /utilities/search endpoint.
    Refreshes once per day (24h TTL). Randomized order for varied scan results.
    """
    import string, time, requests, random

    url = "https://api.tiingo.com/tiingo/utilities/search"
    headers = {"Content-Type": "application/json"}
    all_tickers = []

    # Loop over A–Z to get full alphabet coverage
    for ch in string.ascii_uppercase:
        params = {"token": token, "query": ch, "limit": 1000}
        r = requests.get(url, headers=headers, params=params, timeout=20)
        if not r.ok:
            continue
        data = r.json()
        for d in data:
            sym = d.get("ticker", "").upper()
            exch = d.get("exchange", "")
            if (
                sym.isalpha()
                and d.get("assetType") == "Stock"
                and exch not in ("CRYPTO", "FX")
            ):
                all_tickers.append(sym)
        time.sleep(0.2)  # polite pacing to avoid 429s

    # ✅ dedupe and randomize order
    clean = list(set(all_tickers))
    random.shuffle(clean)

    st.write(f"📈 Tiingo universe fetched: {len(clean):,} tickers (refreshed once per day)")
    return clean



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
            print(f"⚠️ Tiingo fetch failed for {ticker}: {r.status_code}")
            return None  # ✅ must be indented inside the if

        data = r.json()
        if not data or not isinstance(data, list):
            print(f"⚠️ No data in Tiingo response for {ticker}")
            return None  # ✅ indented here, not global

        df = pd.DataFrame(data)
        if df.empty:
            return None  # ✅ indented inside the if

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
        print(f"❌ Error fetching {ticker}: {e}")
        return None  # ✅ inside except, properly indented
    
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
            print(f"⚠️ Sector fetch failed for {ticker}: {r.status_code}")
            return "Unknown"
        data = r.json()
        sector = data.get("sector", "Unknown")
        if not sector:
            sector = "Unknown"
        return sector
    except Exception as e:
        print(f"❌ Error getting sector for {ticker}: {e}")
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
            rows.append({"ETF": sym, "Sector": name, "Bias": bias})
        except Exception:
            continue

    return pd.DataFrame(rows)

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

