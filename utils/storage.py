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

# ---------------- App-Wide Watchlist Gist Functions ----------------
def _get_gist_creds():
    """Return (github_token, gist_id) tuple from secrets/env. Both may be None."""
    github_token = (
        st.secrets.get("GITHUB_GIST_TOKEN")
        or st.secrets.get("GITHUB_TOKEN")
        or os.getenv("GITHUB_GIST_TOKEN")
        or os.getenv("GITHUB_TOKEN")
    )
    gist_id = (
        st.secrets.get("GIST_ID")
        or st.secrets.get("GIST_WATCHLIST_ID")
        or os.getenv("GIST_ID")
        or os.getenv("GIST_WATCHLIST_ID")
    )
    return github_token, gist_id


def load_watchlists_from_gist() -> dict:
    """
    Load all named watchlists from GitHub Gist.
    Returns dict of {name: [ticker_list]}.
    Falls back to {"Unnamed": []} if Gist is unavailable.
    """
    try:
        github_token, gist_id = _get_gist_creds()
        if not github_token or not gist_id:
            return {"Unnamed": []}

        url = f"https://api.github.com/gists/{gist_id}"
        headers = {"Authorization": f"token {github_token}"}
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
        logger.warning(f"load_watchlists_from_gist error: {e}")
        return {"Unnamed": []}


def save_watchlists_to_gist(watchlists_dict: dict) -> None:
    """
    Save all named watchlists to GitHub Gist.
    watchlists_dict format: {name: [ticker_list]}
    """
    try:
        github_token, gist_id = _get_gist_creds()
        if not github_token or not gist_id:
            logger.warning("save_watchlists_to_gist: missing Gist credentials")
            return

        url = f"https://api.github.com/gists/{gist_id}"
        headers = {"Authorization": f"token {github_token}"}
        payload = {
            "files": {
                "watchlist.json": {
                    "content": json.dumps(watchlists_dict, indent=2)
                }
            }
        }
        r = requests.patch(url, headers=headers, json=payload, timeout=10)
        if not r.ok:
            logger.warning(f"save_watchlists_to_gist failed: {r.status_code}")
    except Exception as e:
        logger.error(f"save_watchlists_to_gist error: {e}")


def load_base_scan_metadata() -> dict:
    """
    Load Base Formation Scanner metadata from Gist.
    Returns dict of {ticker: {resistance, base_score, tier, date_added}}
    """
    try:
        github_token, gist_id = _get_gist_creds()
        if not github_token or not gist_id:
            return {}
        data = load_gist_json(gist_id, "base_scan_metadata.json")
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"load_base_scan_metadata error: {e}")
        return {}


def save_base_scan_metadata(metadata: dict) -> None:
    """Save Base Formation Scanner metadata to Gist."""
    try:
        github_token, gist_id = _get_gist_creds()
        if not github_token or not gist_id:
            return
        save_gist_json(gist_id, "base_scan_metadata.json", metadata)
    except Exception as e:
        logger.error(f"save_base_scan_metadata error: {e}")


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





