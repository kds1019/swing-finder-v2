"""
Portfolio settings — account value, risk %, max positions.

Persistence strategy (most-reliable first):
  1. GitHub Gist  — survives Streamlit Cloud reboots (uses GIST_WATCHLIST_ID secret,
                     saves a separate 'portfolio_settings.json' file inside the same gist)
  2. Local file   — data/portfolio_settings.json  (works on local dev)
  3. Hardcoded defaults — fallback when neither is available
"""
from pathlib import Path
from datetime import datetime
from utils.storage import load_json, save_json, load_gist_json, save_gist_json

import streamlit as st
import os

SETTINGS_PATH = Path("data/portfolio_settings.json")
GIST_FILENAME = "portfolio_settings.json"

_DEFAULTS: dict = {
    "account_value": 10000.0,
    "risk_pct": 1.0,       # % of account risked per trade
    "max_positions": 5,     # capital allocation ceiling
    "last_updated": None,
}


def _gist_id() -> str | None:
    """Return the Gist ID to use for portfolio persistence, or None."""
    try:
        return (
            st.secrets.get("GIST_WATCHLIST_ID")
            or os.getenv("GIST_WATCHLIST_ID")
        )
    except Exception:
        return None


def load_portfolio_settings() -> dict:
    """Load settings — Gist first, then local file, then defaults."""
    # 1. Try Gist (persists across Streamlit Cloud reboots)
    gid = _gist_id()
    if gid:
        try:
            data = load_gist_json(gid, GIST_FILENAME)
            if data:
                return {**_DEFAULTS, **data}
        except Exception:
            pass

    # 2. Try local file (works on local dev / Docker)
    data = load_json(SETTINGS_PATH, default={})
    return {**_DEFAULTS, **data}


def save_portfolio_settings(settings: dict) -> None:
    """Stamp last_updated, then persist to Gist AND local file."""
    settings["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Always write local file
    save_json(settings, SETTINGS_PATH)

    # Also write Gist if available
    gid = _gist_id()
    if gid:
        try:
            save_gist_json(gid, GIST_FILENAME, settings)
        except Exception:
            pass  # Gist failure is non-fatal; local file is the backup


def calc_position_size(account_value: float, risk_pct: float,
                       entry: float, stop: float) -> dict:
    """
    Calculate share count from a fixed-dollar-risk rule.

    Returns:
        shares            — number of whole shares to buy
        dollar_risk       — $ risked (account_value × risk_pct%)
        risk_per_share    — |entry − stop|
        position_value    — shares × entry
        pct_of_account    — position_value / account_value × 100
    """
    if entry <= 0 or stop <= 0 or entry == stop or account_value <= 0:
        return {}
    dollar_risk    = account_value * (risk_pct / 100.0)
    risk_per_share = abs(entry - stop)
    shares         = max(int(dollar_risk / risk_per_share), 0)
    position_value = shares * entry
    pct_of_account = (position_value / account_value * 100) if account_value > 0 else 0
    return {
        "shares":         shares,
        "dollar_risk":    round(dollar_risk, 2),
        "risk_per_share": round(risk_per_share, 2),
        "position_value": round(position_value, 2),
        "pct_of_account": round(pct_of_account, 1),
    }


def format_portfolio_context_for_claude(settings: dict,
                                        entry: float = 0,
                                        stop: float = 0) -> str:
    """
    Return a text block that can be injected into any Claude prompt.
    Optionally includes a computed position size when entry/stop are provided.
    """
    acct       = settings.get("account_value", _DEFAULTS["account_value"])
    risk_pct   = settings.get("risk_pct",      _DEFAULTS["risk_pct"])
    max_pos    = settings.get("max_positions",  _DEFAULTS["max_positions"])
    updated    = settings.get("last_updated") or "not yet set"
    dollar_risk = acct * (risk_pct / 100.0)

    lines = [
        "=== TRADER'S ACCOUNT CONTEXT ===",
        f"Account Value      : ${acct:,.0f}",
        f"Risk per Trade     : {risk_pct}% = ${dollar_risk:,.0f} max loss per trade",
        f"Max Open Positions : {max_pos}",
        f"Settings Updated   : {updated}",
    ]

    if entry > 0 and stop > 0:
        sz = calc_position_size(acct, risk_pct, entry, stop)
        if sz:
            lines += [
                "",
                "POSITION SIZE FOR THIS TRADE:",
                f"  Stop distance  : ${sz['risk_per_share']:.2f} per share",
                f"  Shares to buy  : {sz['shares']} shares @ ${entry:.2f}",
                f"  Position value : ${sz['position_value']:,.0f}"
                f"  ({sz['pct_of_account']:.1f}% of account)",
                f"  Dollar at risk : ${sz['dollar_risk']:,.0f}"
                f"  ({risk_pct}% rule)",
            ]

    lines.append("")
    return "\n".join(lines)
