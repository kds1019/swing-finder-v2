
# SwingFinder (Modular Scaffold)

This folder preserves your current app behavior **exactly** while preparing a clean modular structure.

## How it works
- `app.py` is the **new entry**. For now it defers to `app_legacy.py` so nothing changes.
- `app_legacy.py` is your original uploaded app (verbatim).
- `utils/` contains shared helpers (Step 1 extraction: Tiingo fetchers, indicators, storage skeleton).
- `active_trades.py` is a **placeholder** for the new Morning/EOD/Quick Coaching system.

## Run it
```bash
streamlit run app.py
```

## What’s next (Step 2 → Step 4)
1. Replace selected calls in `app_legacy.py` with imports from `utils/tiingo_api.py` and `utils/indicators.py` (one call site at a time).
2. Extract your Analyzer section into `analyzer.py` with a function `render_analyzer()` and call it from `app.py`.
3. Extract your Scanner into `scanner.py` with `render_scanner()`.
4. Wire `active_trades.py` into the sidebar and main page and begin implementing Morning/EOD reports.

## Notes
- Caching: keep using `@st.cache_data` exactly as you do now. The helper functions in `utils/` already include it.
- Secrets: reuse your existing `.streamlit/secrets.toml` (copy it into this folder unchanged).
- Requirements: copy your existing `requirements.txt` into this folder unchanged.

Generated: 2025-10-25T23:59:34
