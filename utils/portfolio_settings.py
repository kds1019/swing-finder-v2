"""
Portfolio settings — account value, risk %, max positions.
Stored in data/portfolio_settings.json.
Loaded once; shared across all pages via st.session_state['portfolio'].
"""
from pathlib import Path
from datetime import datetime
from utils.storage import load_json, save_json

SETTINGS_PATH = Path("data/portfolio_settings.json")

_DEFAULTS: dict = {
    "account_value": 10000.0,
    "risk_pct": 1.0,       # % of account risked per trade
    "max_positions": 5,     # capital allocation ceiling
    "last_updated": None,
}


def load_portfolio_settings() -> dict:
    """Load settings from disk, filling missing keys with defaults."""
    data = load_json(SETTINGS_PATH, default={})
    return {**_DEFAULTS, **data}


def save_portfolio_settings(settings: dict) -> None:
    """Stamp last_updated and persist to disk."""
    settings["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_json(settings, SETTINGS_PATH)


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
