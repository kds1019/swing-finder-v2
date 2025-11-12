import streamlit as st
import pandas as pd
import numpy as np
import math
import random
import concurrent.futures as futures
import time
import requests
import json
import os

# ✅ Helpers
from utils.tiingo_api import (
    tiingo_all_us_tickers,
    tiingo_history,
    get_tiingo_sector,
    get_sector_snapshot,
    get_market_snapshot,
    analyze_sector_rotation,
)

from utils.indicators import (
    rsi, atr, compute_indicators,
    find_support_resistance, analyze_volume, calculate_relative_strength
)
from utils.storage import load_json, save_json
from utils.fundamentals import get_fundamentals, calculate_fundamental_score

# ---------------- Universe Loader ----------------
from utils.universe_builder import CACHE_PATH

@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)  # Cache for 24 hours
def load_verified_universe(token: str) -> list[str]:
    """
    Safely load the locally cached Tiingo universe file.
    Removes duplicate tickers and falls back to Tiingo API if needed.

    PRIORITY: Always tries to load from cache file FIRST (275 quality tickers).
    Only falls back to Tiingo API if cache is missing/corrupted.
    """
    try:
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, "r") as f:
                data = json.load(f)
            tickers = [t["ticker"].upper() for t in data.get("tickers", [])]
            # 🔹 remove duplicates while preserving order
            seen = set()
            unique_tickers = [t for t in tickers if not (t in seen or seen.add(t))]
            if unique_tickers:
                print(f"✅ Loaded {len(unique_tickers)} unique tickers from HIGH-QUALITY CACHE "
                      f"(deduped from {len(tickers)})")
                print(f"📊 Using curated S&P 500 + NASDAQ 100 + popular stocks universe")
                return unique_tickers
        print("⚠️ Cache missing or empty, falling back to Tiingo API universe (1000+ tickers)")
        print("💡 TIP: Run 'python utils/build_quality_universe.py' to build quality cache")
        return tiingo_all_us_tickers(token)
    except Exception as e:
        print(f"❌ Error loading verified universe: {e}")
        print("⚠️ Falling back to Tiingo API universe")
        return tiingo_all_us_tickers(token)



# ---------------- Scanner Configuration Constants ----------------
SCAN_LOOKBACK_DAYS = 120      # how many days of Tiingo history to load
MAX_WORKERS = 8               # number of threads for concurrent scanning
REQUEST_PAUSE_S = 0.25        # delay between batches
BATCH_TICKER_COUNT = 50       # tickers per batch


def scanner_ui(TIINGO_TOKEN):
    # --- Initialize session state defaults ---
    defaults = {
        "risk_stop_atr_mult": 2.0,
        "risk_target_r_mult": 2.0,
        "risk_rr": 2.0,
        "smart_mode": False,
        "watchlist_results": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ---------- Gist Functions (defined early so they can be used anywhere) ----------
    import requests, json, os

    def load_watchlists_from_gist():
        """Load all saved watchlists (dict of {name: [tickers]}) from GitHub Gist."""
        try:
            token = (
                st.secrets.get("GITHUB_GIST_TOKEN")
                or os.getenv("GITHUB_GIST_TOKEN")
                or st.secrets.get("GITHUB_TOKEN")
            )
            gist_id = (
                st.secrets.get("GIST_ID")
                or os.getenv("GIST_ID")
                or st.secrets.get("GIST_WATCHLIST_ID")
            )

            if not token or not gist_id:
                return {"Unnamed": []}

            url = f"https://api.github.com/gists/{gist_id}"
            headers = {"Authorization": f"token {token}"}
            r = requests.get(url, headers=headers, timeout=10)
            if not r.ok:
                return {"Unnamed": []}

            files = r.json().get("files", {})
            if not files:
                return {"Unnamed": []}

            content = (
                files.get("watchlist.json", next(iter(files.values()), {}))
                .get("content", "{}")
            )

            data = json.loads(content)
            if isinstance(data, list):
                return {"Unnamed": data}
            if not isinstance(data, dict):
                return {"Unnamed": []}
            return data

        except Exception as e:
            return {"Unnamed": []}

    def save_watchlists_to_gist(watchlists_dict: dict):
        """Save all watchlists (dict of {name: [tickers]}) to GitHub Gist."""
        try:
            token = (
                st.secrets.get("GITHUB_GIST_TOKEN")
                or os.getenv("GITHUB_GIST_TOKEN")
                or st.secrets.get("GITHUB_TOKEN")
            )
            gist_id = (
                st.secrets.get("GIST_ID")
                or os.getenv("GIST_ID")
                or st.secrets.get("GIST_WATCHLIST_ID")
            )

            if not token or not gist_id:
                st.warning("⚠️ Missing Gist credentials in secrets.")
                return

            url = f"https://api.github.com/gists/{gist_id}"
            headers = {"Authorization": f"token {token}"}
            payload = {
                "files": {
                    "watchlist.json": {
                        "content": json.dumps(watchlists_dict, indent=2)
                    }
                }
            }
            r = requests.patch(url, headers=headers, json=payload, timeout=10)
            if not r.ok:
                st.warning(f"⚠️ Failed to save watchlists: {r.status_code}")

        except Exception as e:
            st.warning(f"⚠️ Could not save to Gist: {e}")

    st.title("📊 Scanner")

    # ---------------- Sensitivity Slider ----------------
    st.sidebar.markdown("### 🎚️ Filter Sensitivity")
    sensitivity = st.sidebar.select_slider(
        "Adjust filter strictness",
        options=[1, 2, 3, 4, 5],
        value=3,
        help="1=Very Strict (fewer, higher quality) | 3=Balanced | 5=Relaxed (more results)"
    )

    # Map sensitivity to thresholds
    sensitivity_map = {
        1: {"breakout_rsi": 65, "breakout_band": 0.70, "pullback_rsi_max": 40, "pullback_band": 0.30},
        2: {"breakout_rsi": 60, "breakout_band": 0.65, "pullback_rsi_max": 45, "pullback_band": 0.35},
        3: {"breakout_rsi": 55, "breakout_band": 0.55, "pullback_rsi_max": 50, "pullback_band": 0.45},
        4: {"breakout_rsi": 52, "breakout_band": 0.50, "pullback_rsi_max": 52, "pullback_band": 0.50},
        5: {"breakout_rsi": 50, "breakout_band": 0.45, "pullback_rsi_max": 55, "pullback_band": 0.55},
    }
    thresholds = sensitivity_map[sensitivity]

    # ---------------- Trade Plan math (Target & Stop) ----------------
    def trade_plan_levels(last_close: float, atr_val: float, mode: str,
                        stop_atr_mult: float, rr_mult: float) -> tuple[float, float]:
        """
        Returns (stop, target). For Pullback, assume bounce; for Breakout, assume expansion.
        """
        atr_val = float(atr_val) if pd.notna(atr_val) else 0.0
        stop = last_close - stop_atr_mult * atr_val
        if mode == "Pullback":
            target = last_close + rr_mult * (last_close - stop)        # bounce back
        elif mode == "Breakout":
            target = last_close + rr_mult * (stop_atr_mult * atr_val)  # push higher
        else:
            target = last_close + rr_mult * (stop_atr_mult * atr_val)
        return (round(max(stop, 0.01), 4), round(max(target, 0.01), 4))

    # --------------------------------------------------------------
    # Classify setup (Pullback / Breakout / Neutral)
    # --------------------------------------------------------------
    def classify_setup(last: pd.Series) -> str:
        try:
            ema20 = float(last["EMA20"])
            ema50 = float(last["EMA50"])
            rsi = float(last["RSI14"])
        except Exception:
            return "Neutral"

        ema_up = ema20 > ema50

        # Loosened rules for visibility
        if ema_up and rsi >= 50:
            return "Breakout"
        elif ema_up and rsi < 50:
            return "Pullback"
        elif not ema_up and rsi < 60:
            return "Pullback"
        else:
            return "Neutral"



    # --------------------------------------------------------------
    def passes_filters(last, price_min, price_max, min_volume, mode="Both") -> bool:
        """Apply meaningful filters to cut down noise, Webull-style."""
        try:
            px = float(last["Close"])
            vol = float(last["Volume"])
            rsi = float(last.get("RSI14", 50))
            ema20 = float(last.get("EMA20", np.nan))
            ema50 = float(last.get("EMA50", np.nan))
            band = float(last.get("BandPos20", 0.5))

            # --- Basic sanity filters ---
            if pd.isna(px) or pd.isna(vol):
                return False
            if px < price_min or px > price_max:
                return False
            if vol < min_volume:
                return False

            # --- Mode-based logic ---
            if mode == "Breakout":
                # Strong uptrend + momentum
                return ema20 > ema50 and rsi > 55 and band > 0.55

            elif mode == "Pullback":
                # Uptrend but short-term dip near support
                return ema20 > ema50 and rsi < 60 and band <= 0.45 and px <= ema20

            else:  # Both — include anything trending up
                return ema20 > ema50

        except Exception as e:
            print(f"⚠️ passes_filters error: {e}")
            return False


    # ---------------- Setup Guidance Helper (with key level) ----------------
    from typing import Optional

    def setup_guidance_text(setup_type: str, key_level: Optional[float] = None) -> str:
        """
        Returns entry guidance text based on setup type.
        If key_level is provided, it appends a support (pullback) or resistance (breakout) hint.
        """
        if setup_type == "Breakout":
            msg = (
                "💥 **Breakout Setup** — Wait for price to **break and hold above resistance** "
                "on strong volume. Enter after a confirmed push/close above that zone; "
                "stop just below the breakout base or last consolidation low."
            )
            if key_level is not None:
                msg += f"\n\n🚀 **Resistance Level:** around **${key_level:.2f}** (recent swing high / breakout zone)"
            return msg

        elif setup_type == "Pullback":
            msg = (
                "📉 **Pullback Setup** — Let the dip **stabilize near support/VWAP**, then "
                "look for a **green reversal candle** on rising volume. Enter **above the reversal high**; "
                "stop below the swing low."
            )
            if key_level is not None:
                msg += f"\n\n🧭 **Support Zone:** around **${key_level:.2f}** (recent swing low / EMA20 area)"
            return msg

        elif setup_type == "Recent Close":
            msg = (
                "⏸ **Recent Close Setup** — Neutral today. Look for **next-session confirmation** "
                "above yesterday’s high with volume before entering."
            )
            if key_level is not None:
                msg += f"\n\n🔎 **Confirmation Trigger:** watch **${key_level:.2f}** (yesterday’s high) for strength."
            return msg

        return "🧭 Setup guidance unavailable."
    

    # ---------------- Single ticker evaluation ----------------
    def evaluate_ticker(ticker: str, mode: str, price_min: float, price_max: float, min_volume: float) -> dict | None:
        """Evaluate a single ticker and return a metrics card with trend context + near-miss detection."""
        try:
                    # --- Load Smart Context if active ---
            market_bias = None
            vol_regime = None
            if st.session_state.get("smart_mode", False):
                market = get_market_snapshot(TIINGO_TOKEN)
                if market:
                    market_bias = market["bias"]          # "Uptrend" or "Downtrend"
                    vol_regime = market["vol_regime"]    # "High Volatility" / "Low Volatility"
                    
            if market_bias:
                st.write(f"🧠 Smart bias active → {market_bias}, Volatility: {vol_regime}")


            # --- Fetch & compute indicators ---
            df = tiingo_history(ticker, TIINGO_TOKEN, SCAN_LOOKBACK_DAYS)
            if df is None or df.empty:
                st.write(f"⚠️ No Tiingo data for {ticker}")
                return None

            if df is None or len(df) < 60:
                return None

            df = compute_indicators(df)
            if ticker in ["AAPL", "MSFT", "TSLA"]:
                st.write(df.tail(1)[["Close","EMA20","EMA50","RSI14","BandPos20"]])

            last = df.iloc[-1]

            px = float(last["Close"])
            vol = float(last["Volume"])
            if pd.isna(px) or pd.isna(vol) or px < price_min or px > price_max or vol < min_volume:
                return None

            ema20 = float(last["EMA20"])
            ema50 = float(last["EMA50"])
            rsi = float(last["RSI14"])
            band = float(last["BandPos20"])
            atr = float(last.get("ATR14", np.nan))
            atr = px * 0.01 if pd.isna(atr) or atr <= 0 else atr
            support = float(last.get("LL20", np.nan))
            resistance = float(last.get("HH20", np.nan))
            
                    # --- Dynamic filter tuning based on market bias (FIXED LOGIC) ---
            rsi_buffer = 0
            band_buffer = 0

            if market_bias == "Uptrend":
                # In strong markets, be MORE lenient to catch more opportunities
                rsi_buffer = -3      # LOOSER RSI requirement (was +3, which was backwards!)
                band_buffer = -0.05  # LOOSER band requirement
            elif market_bias == "Downtrend":
                # In weak markets, be MORE selective to avoid traps
                rsi_buffer = +3      # STRICTER RSI requirement
                band_buffer = +0.05  # STRICTER band requirement

            # Example: In uptrend, Breakout needs RSI > 52 instead of 55 (more opportunities)


            # --- Setup & Near Miss detection (using sensitivity thresholds) ---
            setup, near_miss, near_type = None, False, None

            if ema20 > ema50:
                # Confirmed setups (apply sensitivity + market bias adjustments)
                breakout_rsi_threshold = thresholds["breakout_rsi"] + rsi_buffer
                breakout_band_threshold = thresholds["breakout_band"] + band_buffer
                pullback_rsi_threshold = thresholds["pullback_rsi_max"] + rsi_buffer
                pullback_band_threshold = thresholds["pullback_band"] + band_buffer

                if mode in ["Breakout", "Both"] and rsi > breakout_rsi_threshold and band > breakout_band_threshold:
                    setup = "Breakout"
                elif mode in ["Pullback", "Both"] and rsi < pullback_rsi_threshold and band <= pullback_band_threshold and px <= ema20:
                    setup = "Pullback"


                # Near misses (broader tolerance window)
                if not setup:
                    near_pct = 15.0       # within 15% of resistance
                    near_atr_mult = 4.0   # within 4×ATR of support

                    if mode in ["Breakout", "Both"] and 40 <= rsi <= 67 and 0.35 <= band <= 0.70:
                        near_miss, near_type = True, "RSI/Band breakout proximity"
                    elif mode in ["Pullback", "Both"] and 40 <= rsi <= 70 and 0.20 <= band <= 0.60:
                        near_miss, near_type = True, "RSI/Band pullback proximity"

                    # Check proximity to recent high/low
                    if pd.notna(resistance) and resistance > 0 and (resistance - px) / resistance <= near_pct / 100:
                        near_miss, near_type = True, f"≤{near_pct:.0f}% below 20-day high"
                    elif pd.notna(support) and (px - support) <= near_atr_mult * atr:
                        near_miss, near_type = True, f"≤{near_atr_mult:.1f}×ATR above 20-day low"

            # --- Skip if no signal ---
            if not setup and not near_miss:
                return None

            # --- Determine trend context ---
            if ema20 > ema50 * 1.02:
                trend_context = "Uptrend"
            elif ema20 < ema50 * 0.98:
                trend_context = "Downtrend"
            else:
                trend_context = "Sideways"

            # --- Combine setup + trend for readable context ---
            if setup:
                setup_context = f"{setup} in {trend_context}"
            elif near_miss:
                setup_context = f"Potential {near_type or 'setup'} in {trend_context}"
            else:
                setup_context = trend_context

            # --- Target / Stop (ATR-based) ---
            stop = px - atr * 1.5
            target = px + (px - stop) * 2.0
            
                    # --- Smart Score calculation ---
            smart_score = 50  # neutral baseline

            # Setup strength: RSI/Band alignment
            if setup == "Breakout":
                smart_score += min((rsi - 50) * 1.2, 25)   # reward strong RSI
                smart_score += min((band - 0.5) * 50, 15)  # reward high band
            elif setup == "Pullback":
                smart_score += min((60 - rsi) * 1.2, 25)   # reward deeper dips
                smart_score += min((0.5 - band) * 50, 15)  # reward lower band

            # Trend context (Uptrend gets a bonus)
            if ema20 > ema50:
                smart_score += 10
            else:
                smart_score -= 10

            # If Smart Mode is active and favored sectors exist
            if st.session_state.get("smart_mode", False):
                favored = st.session_state.get("favored_sectors", [])
                ticker_sector = get_tiingo_sector(ticker, TIINGO_TOKEN)
                if any(s.lower() in ticker_sector.lower() for s in favored):
                    smart_score += 10  # aligned with favored sector
                else:
                    smart_score -= 5   # not in favored trend

            smart_score = int(np.clip(smart_score, 0, 100))
            
                    # --- SmartScore Calculation (sector + market bias aware) ---
            smart_score = 50  # start neutral

            # Base on setup type
            if setup == "Breakout":
                smart_score += (rsi - 50) * 0.8 + (band - 0.5) * 40
            elif setup == "Pullback":
                smart_score += (60 - rsi) * 0.8 + (0.5 - band) * 40
            elif near_miss:
                smart_score += 5  # slight bump if it's a near setup

            # Sector alignment bonus (Smart Mode only)
            if st.session_state.get("smart_mode", False) and "smart_context" in st.session_state:
                try:
                    smart_df = st.session_state["smart_context"]["sectors_df"]
                    sector = get_tiingo_sector(ticker, TIINGO_TOKEN)
                    bias = smart_df.loc[smart_df["Sector"] == sector, "Bias"].values[0] if sector in smart_df["Sector"].values else "Neutral"

                    if bias == "Uptrend" and setup == "Breakout":
                        smart_score += 15
                    elif bias == "Downtrend" and setup == "Pullback":
                        smart_score += 15
                    elif bias == "Sideways":
                        smart_score -= 5
                except Exception as e:
                    st.write(f"⚠️ SmartScore sector bias error: {e}")

            # Clamp SmartScore to 0–100 range
            smart_score = max(0, min(100, round(smart_score, 1)))

            # --- Volume Analysis ---
            vol_analysis = analyze_volume(df, lookback=20)

            # --- Support/Resistance Detection ---
            sr_levels = find_support_resistance(df, window=10, num_levels=2)

            # Adjust stop to nearest support if available
            actual_stop = stop
            if sr_levels["support"]:
                nearest_support = sr_levels["support"][-1]  # closest support below price
                # Use support if it's within reasonable range (not too far)
                if px - nearest_support < atr * 3:
                    actual_stop = nearest_support * 0.995  # just below support

            # Adjust target to nearest resistance if available
            actual_target = target
            if sr_levels["resistance"]:
                nearest_resistance = sr_levels["resistance"][0]  # closest resistance above price
                # Use resistance if it's closer than calculated target
                if nearest_resistance < target:
                    actual_target = nearest_resistance * 0.99  # just below resistance

            # --- Build result card ---
            # Note: Fundamental scores are fetched on-demand after scan to keep scans fast
            card = {
                "Symbol": ticker,
                "Price": round(px, 2),
                "Volume": int(vol),
                "RSI14": round(rsi, 1),
                "EMA20>EMA50": ema20 > ema50,
                "BandPos20": round(band, 2),
                "ATR14": round(atr, 2),
                "Setup": setup or "NearMiss",
                "Stop": round(actual_stop, 2),
                "Target": round(actual_target, 2),
                "SmartScore": smart_score,
                "NearMiss": near_miss,
                "NearType": near_type,
                "SetupContext": setup_context,
                "RelVolume": vol_analysis.get("relative_volume", 1.0),
                "VolSignal": vol_analysis.get("volume_signal", "Neutral"),
                "Support": sr_levels["support"],
                "Resistance": sr_levels["resistance"],
            }

            # --- Debug (optional, visible in console/UI logs) ---
            if setup:
                st.write(f"✅ {ticker}: Confirmed {setup} | Trend={trend_context}")
            elif near_miss:
                st.write(f"🟡 {ticker}: Near Miss → {near_type} | Trend={trend_context}")
            else:
                st.write(f"⚙️ {ticker}: No match | Trend={trend_context}")

            return card

        except Exception as e:
            st.write(f"⚠️ {ticker} failed with error: {e}")
            return None


    # ---------------- Scanner (full universe, concurrent) ----------------
    def run_full_scan(mode: str, price_min: float, price_max: float, min_volume: float,
                    max_cards: int) -> list[dict]:
        tickers = load_verified_universe(TIINGO_TOKEN)

        # Shuffle to diversify early results & keep UI feeling live
        random.seed()
        random.shuffle(tickers)

        results: list[dict] = []
        progress = st.progress(0, text="🔎 Scanning U.S. market…")
        total = len(tickers)
        scanned = 0

        for i in range(0, total, BATCH_TICKER_COUNT):
            if len(results) >= max_cards:
                break
            batch = tickers[i:i + BATCH_TICKER_COUNT]
            with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                futs = [ex.submit(evaluate_ticker, t, mode, price_min, price_max, min_volume) for t in batch]
                for f in futures.as_completed(futs):
                    rec = f.result()
                    if rec is not None:
                        results.append(rec)

            scanned = min(i + len(batch), total)
            progress.progress(scanned / total, text=f"🔎 Scanning… {scanned}/{total} tickers | Hits: {len(results)}")
            time.sleep(REQUEST_PAUSE_S)

        progress.empty()

        # --- Smart sorting: favor strong setups and favored sectors ---
        def sort_key(r):
            base_score = 0
            if r.get("Setup") == "Breakout":
                base_score = 100 - r.get("RSI14", 0)  # lower RSI = more potential
            elif r.get("Setup") == "Pullback":
                base_score = r.get("BandPos20", 0) * 100

            # Boost for favored sectors (Smart Mode)
            bonus = 0
            if st.session_state.get("smart_mode", False):
                smart_context = st.session_state.get("smart_context", {})
                favored = [s.lower() for s in smart_context.get("favored_sectors", [])]
                sector = str(r.get("Sector", "Unknown")).lower()
                if any(s in sector for s in favored):
                    bonus += 15

            return -(base_score + bonus)

        results.sort(key=sort_key)

        # --- Separate confirmed vs near misses ---
        confirmed = [r for r in results if r.get("Setup") in ["Breakout", "Pullback"]]
        near_misses = [r for r in results if r.get("NearMiss")]

        st.session_state["scanner_results_confirmed"] = confirmed
        st.session_state["scanner_results_near"] = near_misses
        st.session_state["scanner_results"] = confirmed + near_misses   # ✅ add this line!

        st.write(f"🧪 Debug: {len(confirmed)} confirmed | {len(near_misses)} near misses collected")

        # --- remove duplicate symbols ---
        unique_results = []
        seen = set()
        for r in results:
            sym = r.get("Symbol")
            if sym not in seen:
                unique_results.append(r)
                seen.add(sym)
        return unique_results

        return confirmed + near_misses




    # ---------------- Helper for Watchlist Screener only ----------------
    def check_ticker_failure_reason(ticker, price_min, price_max, min_volume):
        """Identify why a watchlist ticker failed the filters."""
        try:
            df = fetch_tiingo(ticker, 10)
            if df.empty:
                return "no data returned from Tiingo"

            last_close = float(df["Close"].iloc[-1])
            last_volume = float(df["Volume"].iloc[-1])

            if last_close < price_min:
                return f"failed price filter (Close ${last_close:.2f} < Min ${price_min})"
            if last_close > price_max:
                return f"failed price filter (Close ${last_close:.2f} > Max ${price_max})"
            if last_volume < min_volume:
                return f"failed volume filter (Vol {last_volume:,.0f} < {min_volume:,.0f})"

            return "did not qualify based on technical setup"
        except Exception as e:
            return f"error checking failure reason: {e}"


    # ---------------- Watchlist Screener (detailed reasons for failed tickers) ----------------
    def run_watchlist_scan_only(watchlist, mode, price_min, price_max, min_volume):
        """Run the screener only for tickers in the user's watchlist, returning results and detailed debug info."""
        if not watchlist:
            return [], [("⚠️", "No tickers found in watchlist.")]

        results = []
        debug_log = []
        total = len(watchlist)
        progress = st.progress(0, text=f"🎯 Scanning {total} watchlist symbols...")

        for i, ticker in enumerate(watchlist, start=1):
            try:
                rec = evaluate_ticker(ticker, mode, price_min, price_max, min_volume)
                if rec:
                    results.append(rec)
                    debug_log.append(("✅", f"{ticker}: passed all filters"))
                else:
                    reason = check_ticker_failure_reason(ticker, price_min, price_max, min_volume)
                    debug_log.append(("🚫", f"{ticker}: {reason}"))
            except Exception as e:
                debug_log.append(("⚠️", f"{ticker}: error — {e}"))
            progress.progress(i / total, text=f"🎯 {i}/{total} scanned | Hits: {len(results)}")

        progress.empty()

        # --- Add fundamental scores for watchlist stocks ---
        if results:
            st.info("📊 Fetching fundamental scores for watchlist stocks...")
            fund_progress = st.progress(0, text="Fetching fundamentals...")

            for i, rec in enumerate(results):
                ticker = rec["Symbol"]
                try:
                    fundamentals = get_fundamentals(ticker, TIINGO_TOKEN)
                    if fundamentals:
                        score_data = calculate_fundamental_score(fundamentals)
                        if score_data:
                            rec["FundScore"] = score_data.get("total_score", 0)
                            rec["FundGrade"] = score_data.get("grade", "N/A")
                except:
                    pass  # Skip if fundamentals unavailable

                fund_progress.progress((i + 1) / len(results),
                                      text=f"Fetching fundamentals... {i+1}/{len(results)}")

            fund_progress.empty()

        if not results:
            debug_log.append(("❌", "No tickers met your criteria."))
        return results, debug_log


    # ---------------- UI: Controls ----------------
    with st.sidebar:
        st.subheader("🔧 Market Scanner (Tiingo, U.S.)")
    # --- Setup Mode Dropdown (persistent in session_state) ---
        st.session_state["setup_mode"] = st.selectbox(
            "Setup Mode",
            ["Pullback", "Breakout", "Both"],
            index=["Pullback", "Breakout", "Both"].index(st.session_state.get("setup_mode", "Breakout"))
        )
        mode = st.session_state["setup_mode"]  # keep local reference for clarity

        c1, c2 = st.columns(2)
        with c1:
            price_min = st.number_input("Min Price ($)", value=10.0, min_value=0.0, step=0.5)
        with c2:
            price_max = st.number_input("Max Price ($)", value=60.0, min_value=0.0, step=1.0)

        min_volume = st.number_input("Min Volume (shares, latest bar)", value=1_000_000, step=50_000, min_value=0)
        max_cards  = st.slider("Max Cards to Show", min_value=24, max_value=500, value=120, step=12)
        # ---------------- Smart Mode toggle ----------------
        smart_mode = st.toggle("🧠 Enable Smart Mode", value=st.session_state.get("smart_mode", False))
        st.session_state["smart_mode"] = smart_mode

        # Make sure smart_context exists
        if "smart_context" not in st.session_state:
            st.session_state["smart_context"] = {}

        # ---------------- Compute favored sectors when Smart Mode is enabled ----------------
        if st.session_state["smart_mode"]:
            try:
                sector_df = get_sector_snapshot(TIINGO_TOKEN)
                favored = sector_df.loc[sector_df["Bias"] == "Uptrend", "Sector"].tolist()

                # ✅ Store both DataFrame and list in smart_context
                st.session_state["smart_context"]["sectors_df"] = sector_df
                st.session_state["smart_context"]["favored_sectors"] = favored

                # ✅ Display current favored sectors
                if favored:
                    st.success("🌟 Favored sectors: " + ", ".join(favored))
                else:
                    st.info("🌥️ No favored sectors right now")

            except Exception as e:
                st.warning(f"⚠️ Smart Mode failed to load sectors: {e}")
                st.session_state["smart_context"]["sectors_df"] = None
                st.session_state["smart_context"]["favored_sectors"] = []
        else:
            # ✅ Always keep keys initialized even if Smart Mode is off
            st.session_state["smart_context"]["sectors_df"] = None
            st.session_state["smart_context"]["favored_sectors"] = []


        st.markdown("---")
        st.caption("**Trade Plan Defaults** (used for Target/Stop on each card)")
        c3, c4 = st.columns(2)
        with c3:
            st.session_state["risk_stop_atr_mult"] = st.number_input("Stop = ATR ×", value=float(st.session_state["risk_stop_atr_mult"]), min_value=0.5, step=0.5)
        with c4:
            st.session_state["risk_rr"] = st.number_input("Reward Ratio (R)", value=float(st.session_state["risk_rr"]), min_value=0.5, step=0.5)

        run_scan = st.button("🚀 Run Full U.S. Scan", use_container_width=True)

    # ---------------- UI: Results Grid ----------------
    if st.session_state.get("smart_mode", False):
        market = get_market_snapshot(TIINGO_TOKEN)
        if market:
            st.markdown(f"""
            ### 🧭 Market Snapshot
            **SPY:** ${market['spy_price']} — *{market['bias']}*
            Volatility: *{market['vol_regime']}* ({market['atrp']}% ATR)
            """)
        else:
            st.warning("⚠️ Could not load SPY snapshot for market bias.")

        # ===================== Sector Rotation Analysis =====================
        st.divider()
        st.subheader("🔄 Sector Rotation")

        try:
            rotation = analyze_sector_rotation(TIINGO_TOKEN)

            # Market breadth indicator
            breadth = rotation.get("market_breadth", 0)
            breadth_color = "green" if breadth > 60 else "orange" if breadth > 40 else "red"

            col_rot1, col_rot2 = st.columns([1, 2])

            with col_rot1:
                st.markdown(
                    f"<div style='background-color:{breadth_color};padding:15px;border-radius:10px;color:white;text-align:center;'>"
                    f"<b>Market Breadth</b><br>{breadth:.1f}%<br>"
                    f"<small>{rotation.get('rotation_signal', '')}</small></div>",
                    unsafe_allow_html=True
                )

            with col_rot2:
                st.markdown("**🔥 Hot Sectors (Focus Here)**")
                hot = rotation.get("hot_sectors", [])
                if hot:
                    for sector in hot[:3]:
                        st.markdown(f"- **{sector['sector']}** ({sector['etf']}): +{sector['momentum_5d']:.1f}% (5d)")
                else:
                    st.info("No hot sectors detected")

            # Cold sectors in expander
            with st.expander("❄️ Cold Sectors (Avoid)"):
                cold = rotation.get("cold_sectors", [])
                if cold:
                    for sector in cold[:3]:
                        st.markdown(f"- **{sector['sector']}** ({sector['etf']}): {sector['momentum_5d']:.1f}% (5d)")
                else:
                    st.info("No cold sectors detected")

        except Exception as e:
            st.warning(f"⚠️ Sector rotation analysis unavailable: {e}")

    st.header("📊 Webull-Style Market Scanner — U.S. (Tiingo)")
    st.caption("All active U.S. equities. Filters: price, volume, and setup mode (Pullback/Breakout/Both). Cards show your Trade Plan target & stop.")

    if run_scan:
        st.session_state["scanner_running"] = True
        with st.spinner("Scanning the U.S. market... this may take 1–2 minutes"):
            current_mode = st.session_state.get("setup_mode", "Breakout")
            st.write(f"🧭 Running full scan mode: {current_mode}")
            st.session_state["scanner_results"] = run_full_scan(
                mode=current_mode,
                price_min=price_min,
                price_max=price_max,
                min_volume=min_volume,
                max_cards=max_cards
            )
        st.session_state["scanner_running"] = False

        # ---------------- Smart Mode Context (Sector Trend Awareness) ----------------
        if st.session_state.get("smart_mode", False):
            try:
                smart_context = {}
                smart_context["sectors_df"] = get_sector_snapshot(TIINGO_TOKEN)
                st.session_state["smart_context"] = smart_context
                st.caption("🧠 Smart Mode active — sector trends updated.")
            except Exception as e:
                st.warning(f"Smart Mode failed: {e}")

    # safely retrieve results (don’t reset them on rerun)
    results = st.session_state.get("scanner_results", [])

    if not results:
        st.info("Run the full scan to see cards. Use the sidebar to set filters.")
    else:
        # ✅ Separate Confirmed vs Near Miss tabs
        confirmed = st.session_state.get("scanner_results_confirmed", [])
        near_misses = st.session_state.get("scanner_results_near", [])

        tab_confirmed, tab_near = st.tabs([
            f"✅ Confirmed Setups ({len(confirmed)})",
            f"🟡 Near Misses ({len(near_misses)})"
        ])

        # --- Confirmed setups tab ---
        with tab_confirmed:
            if confirmed:
                per_row = 4
                rows = math.ceil(len(confirmed) / per_row)
                for r in range(rows):
                    cols = st.columns(per_row)
                    for j, col in enumerate(cols):
                        idx = r * per_row + j
                        if idx >= len(confirmed): break
                        rec = confirmed[idx]

                        # --- Smart Badge for Sector Alignment ---
                        favored_badge = ""
                        if st.session_state.get("smart_mode", False) and "smart_context" in st.session_state:
                            df = st.session_state["smart_context"]["sectors_df"]
                            sector = get_tiingo_sector(rec["Symbol"], TIINGO_TOKEN)
                            bias = df.loc[df["Sector"] == sector, "Bias"].values[0] if sector in df["Sector"].values else "Unknown"
                            if bias == "Uptrend" and rec["Setup"] == "Breakout":
                                favored_badge = "🟢 Sector Uptrend"
                            elif bias == "Downtrend" and rec["Setup"] == "Pullback":
                                favored_badge = "🔵 Sector Downtrend"

                        with col:
                            st.markdown(
                                f"""
                                <div style="
                                    border:2px solid {'#22c55e' if rec['Setup']=='Breakout' else '#3b82f6'};
                                    border-radius:14px;padding:10px;">
                                    <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                        <div style="font-weight:700;font-size:1.15rem">{rec['Symbol']}</div>
                                        <div style="font-weight:600">${rec['Price']:.2f}</div>
                                    </div>
                                    <div style="margin-top:4px;">
                                        <span style="font-size:0.85rem;color:#facc15;">⭐ Smart: {rec.get('SmartScore', '—')}</span>
                                        {f"<span style='font-size:0.85rem;color:#10b981;margin-left:8px;'>💎 Fund: {rec.get('FundScore', '—')} ({rec.get('FundGrade', 'N/A')})</span>" if rec.get('FundScore') else ""}
                                    </div>
                                    <div style="font-size:0.9rem;opacity:0.9;margin-top:4px;">
                                        Setup: <b>{rec['Setup']}</b> &nbsp;|&nbsp; RSI14: <b>{rec['RSI14']}</b> &nbsp;|&nbsp; Vol: <b>{rec['Volume']:,}</b><br/>
                                        EMA20&gt;EMA50: <b>{'✅' if rec['EMA20>EMA50'] else '❌'}</b> &nbsp;|&nbsp; BandPos20: <b>{rec['BandPos20']}</b> &nbsp;|&nbsp; ATR14: <b>{rec['ATR14']}</b>
                                    </div>
                                    <div style="margin-top:6px;font-size:0.95rem;line-height:1.4;">
                                        🛡️ Stop: <b>${rec['Stop']:.2f}</b><br/>
                                        🎯 <b style="color:#16a34a;">Target: ${rec['Target']:.2f}</b>
                                    </div>
                                    {f"<div style='margin-top:4px;font-size:0.85rem;opacity:0.85;color:#22c55e;'>{favored_badge}</div>" if favored_badge else ""}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                            st.markdown(
                                f"🧭 Context: <b>{rec.get('SetupContext', 'N/A')}</b>",
                                unsafe_allow_html=True
                            )

                            cA, cB = st.columns(2)
                            with cA:
                                if st.button("➕ Watchlist", key=f"wl_confirmed_{rec['Symbol']}_{r}_{j}"):
                                    if rec["Symbol"] not in st.session_state.watchlist:
                                        st.session_state.watchlist.append(rec["Symbol"])
                                        # Save to watchlists dict and sync to Gist
                                        if st.session_state.get("active_watchlist"):
                                            st.session_state.watchlists[st.session_state.active_watchlist] = st.session_state.watchlist
                                            save_watchlists_to_gist(st.session_state.watchlists)
                                        st.success(f"✅ Added {rec['Symbol']} to watchlist & synced!")
                                    else:
                                        st.info(f"{rec['Symbol']} already on watchlist.")
                            with cB:
                                if st.button("🔍 Send to Analyzer", key=f"an_confirmed_{rec['Symbol']}_{r}_{j}"):
                                    st.session_state["analyze_symbol"] = rec["Symbol"]
                                    st.session_state["active_page"] = "Analyzer"   # ✅ trigger page switch
                                    st.rerun()

            else:
                st.info("No confirmed setups found in this scan.")

        # --- Near Misses tab ---
        with tab_near:
            if near_misses:
                per_row = 4
                rows = math.ceil(len(near_misses) / per_row)
                for r in range(rows):
                    cols = st.columns(per_row)
                    for j, col in enumerate(cols):
                        idx = r * per_row + j
                        if idx >= len(near_misses): break
                        rec = near_misses[idx]
                        with col:
                            st.markdown(
                                f"""
                                <div style="
                                    border:2px dashed #facc15;
                                    border-radius:14px;padding:10px;">
                                    <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                        <div style="font-weight:700;font-size:1.15rem">{rec['Symbol']}</div>
                                        <div style="font-weight:600">${rec['Price']:.2f}</div>
                                    </div>
                                    <div style="margin-top:4px;">
                                        <span style="font-size:0.85rem;color:#facc15;">⭐ Smart: {rec.get('SmartScore', '—')}</span>
                                        {f"<span style='font-size:0.85rem;color:#10b981;margin-left:8px;'>💎 Fund: {rec.get('FundScore', '—')} ({rec.get('FundGrade', 'N/A')})</span>" if rec.get('FundScore') else ""}
                                    </div>
                                    <div style="font-size:0.9rem;opacity:0.9;margin-top:4px;">
                                        🟡 Potential <b>{rec['NearMiss']}</b> setup forming<br/>
                                        RSI14: <b>{rec['RSI14']}</b> | BandPos20: <b>{rec['BandPos20']}</b>
                                    </div>
                                    <div style="margin-top:6px;font-size:0.95rem;line-height:1.4;">
                                        🛡️ Stop: <b>${rec['Stop']:.2f}</b><br/>
                                        🎯 <b style="color:#16a34a;">Target: ${rec['Target']:.2f}</b>
                                    </div>
                                    {f"<div style='margin-top:4px;font-size:0.85rem;opacity:0.85;color:#22c55e;'>{favored_badge}</div>" if favored_badge else ""}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                            st.markdown(
                                f"<div style='font-size:0.85rem;opacity:0.75;margin-top:-4px;'>🧭 Context: <b>{rec.get('SetupContext', 'N/A')}</b></div>",
                                unsafe_allow_html=True
                            )


                            cA, cB = st.columns(2)
                            with cA:
                                if st.button("➕ Watchlist", key=f"wl_nearmiss_{rec['Symbol']}_{r}_{j}"):
                                    if rec["Symbol"] not in st.session_state.watchlist:
                                        st.session_state.watchlist.append(rec["Symbol"])
                                        # Save to watchlists dict and sync to Gist
                                        if st.session_state.get("active_watchlist"):
                                            st.session_state.watchlists[st.session_state.active_watchlist] = st.session_state.watchlist
                                            save_watchlists_to_gist(st.session_state.watchlists)
                                        st.success(f"✅ Added {rec['Symbol']} to watchlist & synced!")
                                    else:
                                        st.info(f"{rec['Symbol']} already on watchlist.")
                            with cB:
                                if st.button("🔍 Send to Analyzer", key=f"an_nearmiss_{rec['Symbol']}_{r}_{j}"):
                                    st.session_state["analyze_symbol"] = rec["Symbol"]
                                    st.session_state["active_page"] = "Analyzer"   # ✅ trigger page switch
                                    st.rerun()

            else:
                st.info("No near misses detected in this scan.")




    # ---------------- Watchlist Screener Results (Main Page) ----------------
    if "watchlist_results" in st.session_state and st.session_state["watchlist_results"]:
        st.markdown("---")
        with st.expander("🎯 Watchlist Screener Results", expanded=True):
            st.caption(f"{len(st.session_state['watchlist_results'])} symbols met your criteria.")

            per_row = 4
            results = st.session_state["watchlist_results"]
            rows = math.ceil(len(results) / per_row)
            for r in range(rows):
                cols = st.columns(per_row)
                for j, col in enumerate(cols):
                    idx = r * per_row + j
                    if idx >= len(results):
                        break
                    rec = results[idx]

                    with col:
                        st.markdown(
                            f"""
                            <div style="
                                border:2px solid {'#22c55e' if rec['Setup']=='Breakout' else ('#3b82f6' if rec['Setup']=='Pullback' else '#9ca3af')};
                                border-radius:14px;padding:10px;">
                                <div style="display:flex;justify-content:space-between;align-items:baseline;">
                                    <div style="font-weight:700;font-size:1.15rem">{rec['Symbol']}</div>
                                    <div style="font-weight:600">${rec['Price']:.2f}</div>
                                </div>
                                <div style="margin-top:4px;">
                                    {f"<span style='font-size:0.85rem;color:#10b981;'>💎 Fund: {rec.get('FundScore', '—')} ({rec.get('FundGrade', 'N/A')})</span>" if rec.get('FundScore') else ""}
                                </div>
                                <div style="font-size:0.9rem;opacity:0.9;margin-top:4px;">
                                    Setup: <b>{rec['Setup']}</b> &nbsp;|&nbsp; RSI14: <b>{rec['RSI14']}</b> &nbsp;|&nbsp; Vol: <b>{rec['Volume']:,}</b><br/>
                                    EMA20&gt;EMA50: <b>{'✅' if rec['EMA20>EMA50'] else '❌'}</b> &nbsp;|&nbsp; BandPos20: <b>{rec['BandPos20']}</b> &nbsp;|&nbsp; ATR14: <b>{rec['ATR14']}</b>
                                </div>
                                <div style="margin-top:6px;font-size:0.95rem;line-height:1.4;">
                                    🛡️ Stop: <b>${rec['Stop']:.2f}</b><br/>
                                    🎯 <b style="color:#16a34a;">Target: ${rec['Target']:.2f}</b>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        cA, cB = st.columns(2)
                        with cA:
                            if st.button("➕ Watchlist", key=f"wl_watchlist_{rec['Symbol']}"):
                                if rec["Symbol"] not in st.session_state.watchlist:
                                    st.session_state.watchlist.append(rec["Symbol"])
                                    # Save to watchlists dict and sync to Gist
                                    if st.session_state.get("active_watchlist"):
                                        st.session_state.watchlists[st.session_state.active_watchlist] = st.session_state.watchlist
                                        save_watchlists_to_gist(st.session_state.watchlists)
                                    st.success(f"✅ Added {rec['Symbol']} to watchlist & synced!")
                                else:
                                    st.info(f"{rec['Symbol']} already on watchlist.")
                        with cB:
                            if st.button("🔍 Analyzer", key=f"wl_an_{rec['Symbol']}"):
                                st.session_state["analyze_symbol"] = rec["Symbol"]
                                st.session_state["active_page"] = "Analyzer"
                                st.rerun()


            # ✅ Move this outside the card loop (but still inside the expander)
            debug_log = st.session_state.get("watchlist_debug", [])
            if debug_log:
                st.markdown("---")
                st.markdown("### 📋 Debug Log (Watchlist Screener)")
                for icon, msg in debug_log:
                    st.write(f"{icon} {msg}")



    # =========================================================================================================

    # ----------------- Session Initialization -----------------
    if "watchlists" not in st.session_state:
        st.session_state.watchlists = load_watchlists_from_gist()

    if "active_watchlist" not in st.session_state:
        keys = list(st.session_state.watchlists.keys())
        st.session_state.active_watchlist = keys[0] if keys else None

    if "watchlist" not in st.session_state:
        if st.session_state.active_watchlist:
            st.session_state.watchlist = st.session_state.watchlists.get(
                st.session_state.active_watchlist, []
            )
        else:
            st.session_state.watchlist = []


    # ----------------- Sidebar Watchlist Manager -----------------
    with st.sidebar.expander("📂 Watchlist"):
        st.markdown("### Watchlist Manager")

        all_names = list(st.session_state.watchlists.keys())
        if not all_names:
            st.info("No watchlists yet — create one below 👇")
            selected_name = "➕ Create New"
        else:
            selected_name = st.selectbox(
                "Active Watchlist",
                options=all_names + ["➕ Create New"],
                index=all_names.index(st.session_state.active_watchlist)
                if st.session_state.active_watchlist in all_names
                else len(all_names),
            )

        # 🗑️ Delete current watchlist
        if selected_name not in ["➕ Create New"] and all_names:
            with st.expander("⚠️ Delete This Watchlist"):
                st.warning(f"Deleting '{selected_name}' will permanently remove it from cloud storage.")
                if st.button(f"🗑️ Confirm Delete '{selected_name}'", key=f"confirm_delete_{selected_name}"):
                    try:
                        del st.session_state.watchlists[selected_name]
                        save_watchlists_to_gist(st.session_state.watchlists)
                        st.session_state.active_watchlist = None
                        st.session_state.watchlist = []
                        # Force reload from Gist on next run by clearing session state
                        if "watchlists" in st.session_state:
                            del st.session_state["watchlists"]
                        st.success(f"✅ Watchlist '{selected_name}' deleted & synced!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete '{selected_name}': {e}")

        # --- Create New Watchlist ---
        if selected_name == "➕ Create New":
            new_name = st.text_input("New watchlist name:")
            if st.button("Create Watchlist"):
                if new_name.strip():
                    new_name = new_name.strip()
                    st.session_state.watchlists[new_name] = []
                    save_watchlists_to_gist(st.session_state.watchlists)
                    st.session_state.active_watchlist = new_name
                    st.session_state.watchlist = []
                    # Force reload from Gist on next run by clearing session state
                    if "watchlists" in st.session_state:
                        del st.session_state["watchlists"]
                    st.success(f"✅ Created watchlist '{new_name}' & synced!")
                    st.rerun()

        else:
            # Load selected watchlist
            st.session_state.active_watchlist = selected_name
            st.session_state.watchlist = st.session_state.watchlists.get(selected_name, [])

            # --- Add Symbols ---
            add_manual = st.text_input(
                "Add Symbol(s)",
                placeholder="e.g. AAPL or AAPL, MSFT, TSLA",
                key="wl_add_symbol",
            )
            if st.button("Add to Watchlist"):
                if add_manual:
                    symbols = [
                        s.strip().upper()
                        for s in add_manual.replace(",", " ").split()
                        if s.strip()
                    ]
                    new_syms = [s for s in symbols if s not in st.session_state.watchlist]
                    if new_syms:
                        st.session_state.watchlist.extend(new_syms)
                        st.session_state.watchlists[
                            st.session_state.active_watchlist
                        ] = st.session_state.watchlist
                        save_watchlists_to_gist(st.session_state.watchlists)
                        st.success(f"Added: {', '.join(new_syms)}")
                        st.rerun()
                    else:
                        st.info("All entered symbols already exist.")

            # --- Display Watchlist ---
            if st.session_state.watchlist:
                st.markdown("---")
                st.markdown(f"**Current Watchlist ({len(st.session_state.watchlist)})**")

                selected = st.selectbox(
                    "Pick a ticker",
                    options=st.session_state.watchlist,
                    key="wl_pick_for_actions",
                )

                c1, c2, c3 = st.columns([2, 2, 3])
                if c1.button("🔍 Analyze", key="wl_analyze_selected"):
                    st.session_state["analyze_symbol"] = selected
                    st.session_state["active_page"] = "Analyzer"
                    st.toast(f"Sent {selected} to Analyzer", icon="🔍")
                    st.rerun()

                if c2.button("❌ Remove", key="wl_remove_selected"):
                    st.session_state.watchlist.remove(selected)
                    st.session_state.watchlists[
                        st.session_state.active_watchlist
                    ] = st.session_state.watchlist
                    save_watchlists_to_gist(st.session_state.watchlists)
                    st.toast(f"Removed {selected}", icon="❌")
                    st.rerun()

                if st.button("🗑️ Clear Watchlist"):
                    st.session_state.watchlist = []
                    st.session_state.watchlists[
                        st.session_state.active_watchlist
                    ] = []
                    save_watchlists_to_gist(st.session_state.watchlists)
                    st.warning("Cleared and synced watchlist.")

            # --- Watchlist Screener trigger ---
            if st.button("🎯 Run Watchlist Screener", use_container_width=True):
                if not st.session_state.watchlist:
                    st.warning("⚠️ Your watchlist is empty.")
                else:
                    with st.spinner(f"Scanning {len(st.session_state.watchlist)} symbols..."):
                        results, debug_log = run_watchlist_scan_only(
                            st.session_state.watchlist,
                            mode,
                            price_min,
                            price_max,
                            min_volume,
                        )
                    st.session_state["watchlist_results"] = results
                    st.session_state["watchlist_debug"] = debug_log
                    st.session_state["show_watchlist_results"] = True
                    st.rerun()


