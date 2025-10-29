
import json
from pathlib import Path
import streamlit as st

DEFAULT_PATH = Path(".cache/active_trades.json")

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
