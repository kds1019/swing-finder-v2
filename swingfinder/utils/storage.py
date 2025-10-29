import json
import os
from pathlib import Path
import streamlit as st
import requests

# ---------------- Default Local Paths ----------------
CACHE_DIR = Path(".cache")
DEFAULT_PATH = CACHE_DIR / "active_trades.json"
WATCHLIST_PATH = CACHE_DIR / "watchlist.json"

# ---------------- Local JSON Utilities ----------------
def load_json(path: Path = DEFAULT_PATH) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️ load_json: {e}")
    return {}

def save_json(data: dict, path: Path = DEFAULT_PATH) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"⚠️ save_json: {e}")

# ---------------- Gist Sync (for Streamlit Cloud) ----------------
def _gist_headers():
    token = st.secrets.get("GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("❌ Missing GITHUB_TOKEN in secrets.toml or environment")
    return {"Authorization": f"token {token}"}

def load_gist_json(gist_id: str, filename: str) -> dict:
    """Fetch a specific JSON file from a GitHub Gist."""
    try:
        r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=_gist_headers(), timeout=10)
        if not r.ok:
            print(f"⚠️ Gist fetch failed: {r.status_code}")
            return {}
        data = r.json()
        files = data.get("files", {})
        if filename in files:
            return json.loads(files[filename]["content"])
    except Exception as e:
        print(f"⚠️ load_gist_json: {e}")
    return {}

def save_gist_json(gist_id: str, filename: str, content: dict) -> None:
    """Save JSON data back to a Gist file."""
    try:
        payload = {"files": {filename: {"content": json.dumps(content, indent=2)}}}
        r = requests.patch(f"https://api.github.com/gists/{gist_id}", headers=_gist_headers(), json=payload, timeout=10)
        if not r.ok:
            print(f"⚠️ Gist save failed: {r.status_code}")
    except Exception as e:
        print(f"⚠️ save_gist_json: {e}")

# ---------------- High-Level Watchlist Helpers ----------------
def load_watchlist() -> list:
    """Load watchlist from cloud (Gist) if available, else local cache."""
    gist_id = st.secrets.get("GIST_WATCHLIST_ID") or os.getenv("GIST_WATCHLIST_ID")
    if gist_id:
        data = load_gist_json(gist_id, "watchlist.json")
        if data:
            return data
    # fallback to local file
    return load_json(WATCHLIST_PATH).get("tickers", [])

def save_watchlist(tickers: list) -> None:
    """Save watchlist both locally and to cloud if configured."""
    # Local save
    save_json({"tickers": tickers}, WATCHLIST_PATH)

    # Cloud sync if Gist configured
    gist_id = st.secrets.get("GIST_WATCHLIST_ID") or os.getenv("GIST_WATCHLIST_ID")
    if gist_id:
        save_gist_json(gist_id, "watchlist.json", {"tickers": tickers})

