import json
import os
from pathlib import Path
from typing import Union, Any
import streamlit as st
import requests

from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# ---------------- Default Local Paths ----------------
CACHE_DIR = Path(".cache")
DEFAULT_PATH = CACHE_DIR / "active_trades.json"
WATCHLIST_PATH = CACHE_DIR / "watchlist.json"

# ---------------- Local JSON Utilities ----------------
def load_json(path = DEFAULT_PATH, default: Any = None) -> Union[dict, list, Any]:
    """
    Load JSON from file. Accepts Path object or string.
    Returns the loaded data (dict, list, or other JSON type).
    If file doesn't exist or error occurs, returns `default` (None by default).
    """
    try:
        # Convert string to Path if needed
        if isinstance(path, str):
            path = Path(path)

        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"load_json error for {path}: {e}")

    # Return default value (could be {}, [], None, etc.)
    return default if default is not None else {}

def save_json(data: Union[dict, list, Any], path = DEFAULT_PATH) -> None:
    """
    Save JSON to file. Accepts Path object or string.
    Data can be dict, list, or any JSON-serializable type.
    """
    try:
        # Convert string to Path if needed
        if isinstance(path, str):
            path = Path(path)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"save_json error for {path}: {e}")

# ---------------- Gist Sync (for Streamlit Cloud) ----------------
def _gist_headers():
    token = (
        st.secrets.get("GITHUB_TOKEN")
        or st.secrets.get("GITHUB_GIST_TOKEN")  # Use existing token name
        or os.getenv("GITHUB_TOKEN")
        or os.getenv("GITHUB_GIST_TOKEN")
    )
    if not token:
        raise RuntimeError("❌ Missing GITHUB_TOKEN or GITHUB_GIST_TOKEN in secrets.toml or environment")
    return {"Authorization": f"token {token}"}

def load_gist_json(gist_id: str, filename: str) -> dict:
    """Fetch a specific JSON file from a GitHub Gist."""
    try:
        r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=_gist_headers(), timeout=10)
        if not r.ok:
            logger.warning(f"Gist fetch failed: {r.status_code}")
            return {}
        data = r.json()
        files = data.get("files", {})
        if filename in files:
            return json.loads(files[filename]["content"])
    except Exception as e:
        logger.error(f"load_gist_json error: {e}")
    return {}

def save_gist_json(gist_id: str, filename: str, content: dict) -> None:
    """Save JSON data back to a Gist file."""
    try:
        payload = {"files": {filename: {"content": json.dumps(content, indent=2)}}}
        r = requests.patch(f"https://api.github.com/gists/{gist_id}", headers=_gist_headers(), json=payload, timeout=10)
        if not r.ok:
            logger.warning(f"Gist save failed: {r.status_code}")
    except Exception as e:
        logger.error(f"save_gist_json error: {e}")

# ---------------- High-Level Watchlist Helpers ----------------
def load_watchlist() -> list:
    """
    Load watchlist from Scanner's session state or Gist.
    Returns a flat list of tickers, compatible with Scanner's multi-watchlist format.
    """
    # First, check if Scanner has loaded watchlists in session state
    if hasattr(st, 'session_state'):
        # Check for active watchlist
        if 'watchlist' in st.session_state and st.session_state.watchlist:
            return st.session_state.watchlist

        # Check for all watchlists
        if 'watchlists' in st.session_state and st.session_state.watchlists:
            all_tickers = []
            for watchlist_name, tickers in st.session_state.watchlists.items():
                if isinstance(tickers, list):
                    all_tickers.extend(tickers)
            # Remove duplicates while preserving order
            seen = set()
            unique_tickers = []
            for ticker in all_tickers:
                if ticker not in seen:
                    seen.add(ticker)
                    unique_tickers.append(ticker)
            if unique_tickers:
                return unique_tickers

    # Try loading from Gist
    gist_id = st.secrets.get("GIST_WATCHLIST_ID") or os.getenv("GIST_WATCHLIST_ID")

    if gist_id:
        data = load_gist_json(gist_id, "watchlist.json")
        if data:
            # Handle Scanner's multi-watchlist format: {"Unnamed": ["AAPL", "MSFT"], ...}
            if isinstance(data, dict):
                # Flatten all watchlists into one list
                all_tickers = []
                for watchlist_name, tickers in data.items():
                    if isinstance(tickers, list):
                        all_tickers.extend(tickers)
                # Remove duplicates while preserving order
                seen = set()
                unique_tickers = []
                for ticker in all_tickers:
                    if ticker not in seen:
                        seen.add(ticker)
                        unique_tickers.append(ticker)
                return unique_tickers
            elif isinstance(data, list):
                # Simple list format
                return data

    # Fallback to local file
    local_data = load_json(WATCHLIST_PATH)
    if isinstance(local_data, dict):
        # Handle both formats
        if "tickers" in local_data:
            return local_data["tickers"]
        else:
            # Multi-watchlist format
            all_tickers = []
            for watchlist_name, tickers in local_data.items():
                if isinstance(tickers, list):
                    all_tickers.extend(tickers)
            return list(set(all_tickers))  # Remove duplicates

    return []

def save_watchlist(tickers: list) -> None:
    """Save watchlist both locally and to cloud if configured."""
    # Local save
    save_json({"tickers": tickers}, WATCHLIST_PATH)

    # Cloud sync if Gist configured
    gist_id = st.secrets.get("GIST_WATCHLIST_ID") or os.getenv("GIST_WATCHLIST_ID")
    if gist_id:
        save_gist_json(gist_id, "watchlist.json", {"tickers": tickers})




def add_stock_to_enhanced_watchlist(symbol: str, entry: float = None, stop: float = None,
                                   target: float = None, setup_type: str = None, notes: str = None):
    """
    Add a stock to the enhanced watchlist with entry/stop/target data.
    Auto-syncs to both local file and GitHub Gist.

    Args:
        symbol: Stock ticker
        entry: Entry price
        stop: Stop loss price
        target: Target price
        setup_type: Type of setup (e.g., "Breakout", "Pullback")
        notes: Optional notes

    Returns:
        bool: True if added successfully, False if already exists
    """
    # Load current watchlist
    gist_id = st.secrets.get("GIST_ID") or os.getenv("GIST_ID")
    watchlist = []

    if gist_id:
        try:
            watchlist = load_gist_json(gist_id, "watchlist_enhanced.json") or []
        except:
            pass

    if not watchlist:
        watchlist = load_json("data/watchlist_enhanced.json", default=[])

    # Check if stock already exists
    existing_symbols = [item.get('symbol') for item in watchlist if isinstance(item, dict)]
    if symbol in existing_symbols:
        return False  # Already exists

    # Create new stock entry
    new_stock = {
        'symbol': symbol,
        'setup_type': setup_type,
        'entry': entry,
        'stop': stop,
        'target': target,
        'notes': notes
    }

    # Add to watchlist
    watchlist.append(new_stock)

    # Save locally
    save_json(watchlist, "data/watchlist_enhanced.json")

    # Save to Gist
    if gist_id:
        github_token = st.secrets.get("GITHUB_GIST_TOKEN") or os.getenv("GITHUB_GIST_TOKEN")
        if github_token:
            try:
                save_gist_json(gist_id, "watchlist_enhanced.json", watchlist)

                # Also update Scanner format for compatibility
                scanner_data = load_gist_json(gist_id, "watchlist.json") or {}
                if isinstance(scanner_data, dict):
                    active_name = st.session_state.get("active_watchlist", "Unnamed")
                    if active_name not in scanner_data:
                        scanner_data[active_name] = []
                    if symbol not in scanner_data[active_name]:
                        scanner_data[active_name].append(symbol)
                    save_gist_json(gist_id, "watchlist.json", scanner_data)
            except:
                pass

    return True
