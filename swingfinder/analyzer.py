import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.tiingo_api import tiingo_history
from utils.indicators import compute_indicators
from utils.storage import load_json, save_json


# ---------------- Analyzer UI ----------------
def analyzer_ui(TIINGO_TOKEN):
    """
    Wraps the legacy analyzer code so it runs as its own modular file.
    """
    # 🔹 Paste your full legacy Analyzer code below this comment
    # Make sure to replace any references to 'TIINGO_TOKEN' with the parameter (same name)
    # and to remove Streamlit page titles already handled in app.py.

    if st.button("⬅️ Back to Scanner"):
        st.session_state["active_page"] = "Scanner"
        st.rerun()

    # ---------------- Analyzer ----------------
    st.subheader("🔍 Analyzer — with RSI, MACD, ATR")

    # Use symbol from session if sent, otherwise default to AAPL
    default_symbol = st.session_state.get("analyze_symbol", "AAPL")
    symbol = st.text_input("Symbol", default_symbol or "AAPL").upper()

    # If a new symbol is entered manually, update the session state
    if symbol != st.session_state.get("analyze_symbol"):
        st.session_state["analyze_symbol"] = symbol

    # Auto-run analyzer when ticker was sent from Watchlist or Scanner
    auto_trigger = st.session_state.get("analyze_symbol") == symbol
    run_analysis = st.button("Analyze") or auto_trigger

    if run_analysis:
        df = tiingo_history(symbol, TIINGO_TOKEN, 200)

        if df is None or df.empty:
            st.warning("⚠️ No historical data returned for this ticker.")
            st.stop()  # 🧠 pauses execution safely, doesn’t kill entire page

        # --- Indicators ---
        df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
        df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

        # RSI (14)
        delta = df["Close"].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        roll_up = pd.Series(gain).rolling(14).mean()
        roll_down = pd.Series(loss).rolling(14).mean()
        rs = roll_up / (roll_down + 1e-9)
        df["RSI14"] = 100.0 - (100.0 / (1.0 + rs))

        # MACD (12,26,9)
        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = ema12 - ema26
        df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]

        # ATR (14)
        high_low = df["High"] - df["Low"]
        high_close = np.abs(df["High"] - df["Close"].shift(1))
        low_close = np.abs(df["Low"] - df["Close"].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["ATR14"] = tr.rolling(14).mean()

        # --- Plot main chart + subplots ---
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(f"{symbol} Price & EMAs", "MACD", "RSI(14)")
        )

        # Candlestick + EMAs
        fig.add_trace(go.Candlestick(
            x=df["Date"], open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA20"], mode="lines", name="EMA20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["Date"], y=df["EMA50"], mode="lines", name="EMA50"), row=1, col=1)

        # MACD
        fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], mode="lines", name="MACD"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD_SIGNAL"], mode="lines", name="Signal"), row=2, col=1)
        fig.add_trace(go.Bar(x=df["Date"], y=df["MACD_HIST"], name="Hist"), row=2, col=1)

        # RSI
        fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI14"], mode="lines", name="RSI(14)"), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)

        fig.update_layout(height=800, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- Metrics ---
        st.metric("Last Close", f"${df.iloc[-1]['Close']:.2f}")
        st.metric("ATR(14)", f"{df.iloc[-1]['ATR14']:.2f}")
        st.metric("RSI(14)", f"{df.iloc[-1]['RSI14']:.1f}")
        st.metric("MACD", f"{df.iloc[-1]['MACD']:.2f}")

        # --- Forecast, ML Edge, Seasonality, and Sentiment ---
        st.divider()
        st.subheader("🧠 Forecasts, ML Edge, Seasonality & Sentiment")

        try:
            # ===================== 1️⃣ TinyToy Forecast =====================
            from sklearn.linear_model import LinearRegression

            lookback = 20
            df_recent = df.tail(lookback).reset_index(drop=True)
            df_recent["Index"] = np.arange(len(df_recent))

            model = LinearRegression().fit(df_recent[["Index"]], df_recent["Close"])
            predicted_price = float(model.predict([[len(df_recent)]])[0])
            last_price = float(df_recent["Close"].iloc[-1])
            forecast_change = predicted_price - last_price
            forecast_pct = (forecast_change / last_price) * 100
            direction = "⬆️ Up" if forecast_change > 0 else "⬇️ Down"

            # ===================== 2️⃣ ML Edge =====================
            ema_trend = (df_recent["EMA20"].iloc[-1] - df_recent["EMA50"].iloc[-1]) / df_recent["Close"].iloc[-1]
            rsi_val = df_recent["RSI14"].iloc[-1]
            rsi_edge = (50 - abs(50 - rsi_val)) / 50
            atr_vol = df_recent["ATR14"].iloc[-1] / df_recent["Close"].iloc[-1]
            ml_edge_score = max(0.0, min(1.0, (ema_trend * 5 + rsi_edge - atr_vol * 2)))

            # ===================== 3️⃣ Seasonality =====================
            df["Month"] = pd.to_datetime(df["Date"]).dt.month
            monthly_returns = df.groupby("Month")["Close"].apply(lambda x: x.pct_change().mean() * 100)
            this_month = pd.Timestamp.now().month
            seasonality_avg = float(monthly_returns.get(this_month, 0.0))

            # ===================== 4️⃣ Sentiment =====================
            import os
            import requests
            from textblob import TextBlob

            sentiment_score = 0.0
            try:
                api_key = os.getenv("TIINGO_API_KEY")
                news_url = f"https://api.tiingo.com/tiingo/news?tickers={symbol}&token={api_key}"
                r = requests.get(news_url, timeout=5)
                if r.ok:
                    articles = r.json()[:5]
                    sentiments = []
                    for art in articles:
                        title = art.get("title", "")
                        polarity = TextBlob(title).sentiment.polarity
                        sentiments.append(polarity)
                    if sentiments:
                        sentiment_score = np.mean(sentiments)
            except Exception:
                pass

            sentiment_label = (
                "😊 Positive" if sentiment_score > 0.05 else
                "😐 Neutral" if sentiment_score >= -0.05 else
                "😟 Negative"
            )

            # ===================== 5️⃣ Visual Dashboard =====================
            c1, c2, c3, c4 = st.columns(4)

            # 🧭 Forecast Color
            forecast_color = "green" if forecast_change > 0 else "red"
            forecast_arrow = "⬆️" if forecast_change > 0 else "⬇️"

            # 🧠 ML Edge Color
            if ml_edge_score >= 0.7:
                edge_color = "green"
                edge_label = "Strong Edge"
            elif ml_edge_score >= 0.4:
                edge_color = "orange"
                edge_label = "Moderate Edge"
            else:
                edge_color = "red"
                edge_label = "Weak Edge"

            # 🌤️ Seasonality Color
            season_color = "green" if seasonality_avg > 0 else "red"

            # 📰 Sentiment Color
            if sentiment_score > 0.05:
                senti_color = "green"
            elif sentiment_score < -0.05:
                senti_color = "red"
            else:
                senti_color = "gray"

            with c1:
                st.markdown(
                    f"<div style='background-color:{forecast_color};padding:10px;border-radius:10px;color:white;text-align:center;'>"
                    f"<b>TinyToy Forecast</b><br>{forecast_arrow} ${predicted_price:.2f}<br>"
                    f"{forecast_pct:+.2f}%</div>",
                    unsafe_allow_html=True
                )

            with c2:
                st.markdown(
                    f"<div style='background-color:{edge_color};padding:10px;border-radius:10px;color:white;text-align:center;'>"
                    f"<b>ML Edge</b><br>{ml_edge_score*100:.1f}%<br>{edge_label}</div>",
                    unsafe_allow_html=True
                )

            with c3:
                st.markdown(
                    f"<div style='background-color:{season_color};padding:10px;border-radius:10px;color:white;text-align:center;'>"
                    f"<b>Seasonality</b><br>{seasonality_avg:+.2f}%</div>",
                    unsafe_allow_html=True
                )

            with c4:
                st.markdown(
                    f"<div style='background-color:{senti_color};padding:10px;border-radius:10px;color:white;text-align:center;'>"
                    f"<b>Sentiment</b><br>{sentiment_label}</div>",
                    unsafe_allow_html=True
                )

        except Exception as e:
            st.warning(f"⚠️ Forecast/Edge/Seasonality/Sentiment failed: {e}")


            
                           # --- Trade Planning (context-aware setups, manual override, improved coaching) ---
    st.divider()
    st.subheader("🧾 Trade Plan")

    # --- Risk settings ---
    account = float(st.session_state.get("account_size", 10_000.0))
    risk_pct = float(st.session_state.get("risk_per_trade", 1.0))
    rr_ratio = float(st.session_state.get("rr_ratio", 2.0))

    # --- Manual override control (persists in session) ---
    override_default = st.session_state.get("plan_mode", "Auto")
    mode = st.radio(
        "Setup type (override optional):",
        ["Auto", "Pullback", "Breakout", "Wait (Consolidation)"],
        horizontal=True,
        index=["Auto", "Pullback", "Breakout", "Wait (Consolidation)"].index(override_default)
    )
    st.session_state["plan_mode"] = mode

    # --- Prep commonly used series/values ---
    df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df.get("Volume", pd.Series(index=df.index, dtype=float)).fillna(0)

    # --- Ensure EMA10/20/50 columns exist ---
    if "EMA10" not in df.columns:
        df["EMA10"] = df["Close"].ewm(span=10, adjust=False).mean()
    if "EMA20" not in df.columns:
        df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    if "EMA50" not in df.columns:
        df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    # now safely unpack
    ema10, ema20, ema50 = df["EMA10"], df["EMA20"], df["EMA50"]


   # --- Ensure required indicators exist before using them ---
    if "RSI14" not in df.columns:
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss
        df["RSI14"] = 100 - (100 / (1 + rs))

    if "MACD" not in df.columns or "MACD_SIGNAL" not in df.columns:
        short_ema = df["Close"].ewm(span=12, adjust=False).mean()
        long_ema = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = short_ema - long_ema
        df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()

    if "ATR14" not in df.columns:
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift()).abs()
        low_close = (df["Low"] - df["Close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["ATR14"] = tr.rolling(window=14, min_periods=1).mean()

    # --- Indicators now guaranteed to exist ---
    rsi = df["RSI14"]
    macd = df["MACD"]
    macd_sig = df["MACD_SIGNAL"]
    atr14 = df["ATR14"]
    last_close = float(df["Close"].iloc[-1])


    # --- Context windows ---
    RANGE_LOOKBACK = 20
    recent_high = float(high.tail(RANGE_LOOKBACK).max())
    recent_low = float(low.tail(RANGE_LOOKBACK).min())
    range_pct = (recent_high - recent_low) / max(1e-6, recent_high) * 100.0
    avg_vol = float(vol.tail(20).mean())
    curr_vol = float(vol.iloc[-1])

    # --- Trend detection ---
    trend_up = (ema10.iloc[-1] > ema20.iloc[-1] > ema50.iloc[-1])
    trend_down = (ema10.iloc[-1] < ema20.iloc[-1] < ema50.iloc[-1])

    # --- Consolidation detection (tight range + flat momentum) ---
    is_consolidation = (
        range_pct < 3.0 and
        abs(float(macd.iloc[-1] - macd_sig.iloc[-1])) < 0.1 and
        45 < float(rsi.iloc[-1]) < 55
    )

   # --- Smarter Auto-Detection Rules (v3: realistic trading behavior) ---
    detected = "Neutral"

    # ✅ Trend alignment with slight tolerance
    trend_up = ema10.iloc[-1] > ema20.iloc[-1] * 0.99 and ema20.iloc[-1] > ema50.iloc[-1] * 0.98
    trend_down = ema10.iloc[-1] < ema20.iloc[-1] * 1.01 and ema20.iloc[-1] < ema50.iloc[-1] * 1.02

    # --- Consolidation ---
    if range_pct < 3.5 and 40 < rsi.iloc[-1] < 60 and abs(macd.iloc[-1] - macd_sig.iloc[-1]) < 0.2:
        detected = "Wait (Consolidation)"

    # --- Breakout ---
    elif trend_up and (last_close >= recent_high * 0.97 or rsi.iloc[-1] > 65 or curr_vol >= avg_vol * 1.2):
        detected = "Breakout"

    # --- Pullback ---
    elif trend_up and rsi.iloc[-1] < 55 and last_close <= ema20.iloc[-1] * 1.05:
        detected = "Pullback"

    # --- Breakdown ---
    elif trend_down and last_close <= recent_low * 1.03:
        detected = "Breakdown"

    # --- Fallback ---
    else:
        detected = "Neutral"

    
    # --- Optional debug printout ---
    # st.write({
    #     "trend_up": trend_up,
    #     "trend_down": trend_down,
    #     "last_close": last_close,
    #     "recent_high": recent_high,
    #     "recent_low": recent_low,
    #     "ema10": ema10.iloc[-1],
    #     "ema20": ema20.iloc[-1],
    #     "ema50": ema50.iloc[-1],
    #     "rsi": rsi.iloc[-1],
    #     "curr_vol": curr_vol,
    #     "avg_vol": avg_vol
    # })


    # Apply manual override if not Auto
    setup_choice = detected if mode == "Auto" else mode

    # --- Entry/Key levels based on setup_choice ---
    entry_signal = setup_choice
    key_level = None

    if setup_choice == "Breakout":
        key_level = recent_high  # resistance
        # Suggest entering on close above resistance or next-day retest; here we use last_close as planner price
        entry_price = max(last_close, recent_high)  # conservative: not below resistance
    elif setup_choice == "Pullback":
        key_level = recent_low  # support
        # Enter near reclaim of EMA20; keep your prior “smart-aggressive” concept but anchored to support
        entry_price = last_close
    elif setup_choice == "Wait (Consolidation)":
        key_level = (recent_low + recent_high) / 2.0
        entry_price = last_close  # no action yet; coaching will say "wait for levels"
    else:  # Neutral fallback
        # Neutral: wait for yesterday's high as confirmation
        if len(df) >= 2:
            key_level = float(high.iloc[-2])
        else:
            key_level = recent_high
        entry_price = last_close

    # --- Sanity guard: if entry is >15% away from market, use current ---
    if abs(entry_price - last_close) / max(1e-6, last_close) > 0.15:
        entry_price = last_close
        entry_signal = f"{entry_signal} (sanity fallback)"

    # --- Stop placement: swing-low vs ATR-based, whichever is tighter but sane ---
    ema20_now = float(ema20.iloc[-1])
    atr = float(atr14.iloc[-1]) if pd.notna(atr14.iloc[-1]) else np.nan
    swing_low = float(low.tail(10).min())
    if not np.isnan(atr) and atr > 0:
        atr_stop = ema20_now - 1.3 * atr
        proposed_stop = min(swing_low, atr_stop)
        if proposed_stop >= entry_price:
            proposed_stop = entry_price - 1.2 * atr
    else:
        proposed_stop = entry_price * 0.97
    stop = max(0.01, proposed_stop)

    # --- Target: R-multiple vs recent swing-high (take farther if above entry) ---
    risk_per_share = max(1e-6, entry_price - stop)
    rr_target = entry_price + rr_ratio * risk_per_share
    prior_high = float(high.tail(10).max())
    target = max(rr_target, prior_high) if prior_high > entry_price else rr_target

    # --- Sizing & reward ---
    risk_amt = account * (risk_pct / 100.0)
    shares = int(risk_amt // risk_per_share) if risk_per_share > 0 else 0
    reward = (target - entry_price) * shares

    # --- ETA: pace from max(20-bar avg abs move, 0.7×ATR) ---
    avg_abs_diff = close.diff().abs().tail(20).mean()
    if atr and atr > 0:
        pace = float(max(avg_abs_diff if pd.notna(avg_abs_diff) else 0.0, 0.7 * atr))
    else:
        pace = float(avg_abs_diff) if pd.notna(avg_abs_diff) else np.nan
    eta_days = (target - entry_price) / pace if (pace and pace > 0) else np.nan

    # --- Display (same layout you had) ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Setup Type", entry_signal)
        st.metric("Entry Price", f"${entry_price:.2f}")
    with c2:
        st.metric("Stop Loss", f"${stop:.2f}")
        st.metric("Target Price", f"${target:.2f}")
    with c3:
        st.metric("R:R Ratio", f"{rr_ratio:.2f}")
        st.metric("Shares to Buy", f"{shares}")
    with c4:
        st.metric("ETA to Target", f"{eta_days:.1f} days" if not np.isnan(eta_days) else "—")
        st.metric("Potential Reward ($)", f"{reward:,.2f}")

    st.caption(
        "Context-aware setups: trend (EMA10/20/50), consolidation filter (tight range + flat MACD/RSI), "
        "volume confirmation for breakouts, and pullback requires a recent dip + EMA20 reclaim. "
        "Manual override lets you lock what you see on the chart."
    )

    # --- Send to Active Trades (unchanged) ---
    st.markdown("---")
    st.subheader("💼 Trade Management")

    if st.button("💼 Send to Active Trades", use_container_width=True):
        st.session_state["planner_symbol"] = symbol
        st.session_state["planner_entry"] = float(entry_price)
        st.session_state["planner_stop"] = float(stop)
        st.session_state["planner_target"] = float(target)
        st.session_state["planner_shares"] = float(shares)
        st.session_state["planner_notes"] = f"Auto-imported from Analyzer ({entry_signal})"
        st.session_state["active_page"] = "Active Trades"
        st.rerun()

    # 💡 Setup guidance expander
    with st.expander("💡 How to Trade This Setup", expanded=True):
        st.markdown(setup_guidance_text(entry_signal, key_level, recent_low, recent_high))


    # Use session state only — no duplicate defaults
    st.sidebar.number_input("Account Size ($)", min_value=0.0, key="account_size")
    st.sidebar.number_input("Risk per Trade (%)", min_value=0.1, max_value=10.0, key="risk_per_trade")
    st.sidebar.number_input("Target R:R Ratio", min_value=0.5, max_value=10.0, step=0.1, key="rr_ratio")
    
# ---------------- Guidance Text Helper ----------------
def setup_guidance_text(entry_signal: str, key_level: float,
                        support_level: float | None = None,
                        resistance_level: float | None = None) -> str:
    """
    Returns guidance text for the analyzer depending on setup type, with clearer levels.
    """
    def fmt(x):
        return f"${x:.2f}" if x is not None and np.isfinite(x) else "—"

    if entry_signal.startswith("Breakout"):
        return (
            f"💥 **Breakout Setup**\n\n"
            f"- Resistance to beat: **{fmt(resistance_level or key_level)}**.\n"
            f"- Prefer a strong close above resistance with **volume > 20-bar avg**.\n"
            f"- Conservative entry: post-breakout **retest** that holds above {fmt(resistance_level or key_level)}.\n"
            f"- Stop idea: below the breakout base or recent swing low.\n"
        )
    elif entry_signal.startswith("Pullback"):
        return (
            f"📉 **Pullback Setup**\n\n"
            f"- Support area: **{fmt(support_level or key_level)}**. Look for a green reversal / reclaim of EMA20.\n"
            f"- Entry once reversal is confirmed; avoid catching a falling knife.\n"
            f"- Stop idea: below swing low or ~1.3×ATR under EMA20.\n"
        )
    elif "Consolidation" in entry_signal:
        return (
            f"⏸ **Consolidation (Wait)**\n\n"
            f"- Range: **{fmt(support_level)} – {fmt(resistance_level)}**. Momentum is flat; patience preferred.\n"
            f"- Breakout trigger: close **above {fmt(resistance_level)}** with volume pickup.\n"
            f"- Breakdown risk: close **below {fmt(support_level)}**.\n"
        )
    else:
        return (
            "🟨 **Neutral / No clear edge**\n\n"
            "- Consider waiting for confirmation: yesterday’s high for bullish bias, "
            "or a clear reclaim/failure of EMA20.\n"
        )
