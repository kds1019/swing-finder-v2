import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.tiingo_api import tiingo_history
from utils.indicators import (
    compute_indicators, find_support_resistance, analyze_volume,
    detect_patterns, detect_gaps, calculate_beta_and_correlation,
    calculate_fibonacci_levels, get_fibonacci_zone_label
)
from utils.storage import load_json, save_json
from utils.tiingo_api import get_next_earnings_date
from utils.ml_models import ensemble_ml_forecast
from news_feed import show_news_widget
from utils.fundamentals import (
    get_fundamentals, calculate_fundamental_score,
    extract_key_metrics, format_large_number
)
from utils.earnings_analysis import (
    get_earnings_history, analyze_earnings_performance,
    calculate_earnings_quality_score, format_earnings_table,
    get_earnings_risk_level
)
from utils.relative_strength import (
    get_multi_timeframe_strength, analyze_strength_trend,
    calculate_relative_strength_rank
)

def _render_entry_coaching(symbol: str, setup_type: str, indicators: dict, notes: str = ""):
    """Show the entry coaching prompt with one-click copy (matches Active Trades style)."""
    # Build the prompt
    prompt_text = (
        f"You are a swing-trading coach. Provide educational coaching only; no financial advice.\n\n"
        f"Symbol: {symbol}\n"
        f"Setup type: {setup_type}\n"
        f"Indicators: {indicators}\n"
        f"Notes: {notes or '-'}\n\n"
        "Use fresh, live market data from Yahoo Finance to evaluate entry conditions. "
        "Coach me on timing, confirmation, and risk management."
    )

    # Display copy button and code block
    copy_col, _ = st.columns([1, 8])
    if copy_col.button("📋 Copy Prompt", key=f"copy_prompt_{symbol}"):
        st.session_state["copied_prompt"] = prompt_text
        st.toast("✅ Prompt copied! Paste it directly into ChatGPT.")

    # Display the prompt text for manual viewing/copying
    st.code(prompt_text, language="markdown")


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

        # --- Fibonacci Retracement Levels ---
        try:
            fib_data = calculate_fibonacci_levels(df, lookback=20)
            if fib_data:
                fib_levels = fib_data["fib_levels"]
                fib_zone = fib_data["zone"]
                fib_position = fib_data["current_fib_position"]

                # Define colors for each Fibonacci level
                fib_colors = {
                    "0%": "#ef4444",      # Red (swing high)
                    "23.6%": "#f97316",   # Orange
                    "38.2%": "#eab308",   # Yellow
                    "50%": "#3b82f6",     # Blue (equilibrium)
                    "61.8%": "#10b981",   # Green (golden ratio)
                    "78.6%": "#059669",   # Dark green
                    "100%": "#22c55e",    # Bright green (swing low)
                }

                # Add horizontal lines for each Fibonacci level
                for level_name, level_price in fib_levels.items():
                    # Determine if this level is in discount or premium zone
                    level_pct = float(level_name.replace("%", ""))
                    is_discount = level_pct <= 50

                    fig.add_hline(
                        y=level_price,
                        line_dash="dash",
                        line_color=fib_colors.get(level_name, "#9ca3af"),
                        line_width=1,
                        opacity=0.6,
                        annotation_text=f"Fib {level_name}",
                        annotation_position="right",
                        row=1, col=1
                    )

                # Add shaded zones for discount/premium areas
                # Discount zone (0-50%): Light green background
                fig.add_hrect(
                    y0=fib_levels["100%"], y1=fib_levels["50%"],
                    fillcolor="green", opacity=0.05,
                    layer="below", line_width=0,
                    annotation_text="💎 Discount Zone",
                    annotation_position="top left",
                    row=1, col=1
                )

                # Premium zone (50-100%): Light red background
                fig.add_hrect(
                    y0=fib_levels["50%"], y1=fib_levels["0%"],
                    fillcolor="red", opacity=0.05,
                    layer="below", line_width=0,
                    annotation_text="⚠️ Premium Zone",
                    annotation_position="bottom left",
                    row=1, col=1
                )

        except Exception as e:
            st.warning(f"Could not calculate Fibonacci levels: {e}")

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
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Last Close", f"${df.iloc[-1]['Close']:.2f}")
        with col2:
            st.metric("ATR(14)", f"{df.iloc[-1]['ATR14']:.2f}")
        with col3:
            st.metric("RSI(14)", f"{df.iloc[-1]['RSI14']:.1f}")
        with col4:
            st.metric("MACD", f"{df.iloc[-1]['MACD']:.2f}")
        with col5:
            # --- Next Earnings Date ---
            earnings_date = get_next_earnings_date(symbol, TIINGO_TOKEN)
            if earnings_date and earnings_date != "N/A":
                earnings_date = earnings_date.split("T")[0]
                st.metric("Next Earnings", earnings_date)
            else:
                st.metric("Next Earnings", "Not Scheduled")

        # --- Fibonacci Metrics ---
        st.divider()
        st.subheader("📊 Fibonacci Retracement Analysis")

        try:
            fib_data = calculate_fibonacci_levels(df, lookback=20)
            if fib_data:
                fib_position = fib_data["current_fib_position"]
                fib_zone = fib_data["zone"]
                fib_zone_label = get_fibonacci_zone_label(fib_position)
                optimal_entry = fib_data["optimal_entry"]
                current_price = float(df["Close"].iloc[-1])

                # Display Fibonacci info
                fib_col1, fib_col2, fib_col3, fib_col4 = st.columns(4)

                with fib_col1:
                    zone_color = "🟢" if fib_zone == "discount" else "🔴"
                    st.metric("Fibonacci Position", f"{fib_position:.1f}%")
                    st.caption(f"{zone_color} {fib_zone_label}")

                with fib_col2:
                    st.metric("Current Zone", fib_zone.title())
                    if fib_zone == "discount":
                        st.success("💎 Better Risk/Reward")
                    else:
                        st.warning("⚠️ Higher Risk Entry")

                with fib_col3:
                    st.metric("Optimal Entry", f"${optimal_entry:.2f}")
                    entry_diff = ((current_price - optimal_entry) / optimal_entry) * 100
                    if abs(entry_diff) < 2:
                        st.success("✅ Near optimal entry")
                    else:
                        st.caption(f"{entry_diff:+.1f}% from optimal")

                with fib_col4:
                    swing_range = fib_data["swing_high"] - fib_data["swing_low"]
                    st.metric("Swing Range", f"${swing_range:.2f}")
                    st.caption(f"High: ${fib_data['swing_high']:.2f}")
                    st.caption(f"Low: ${fib_data['swing_low']:.2f}")

                # Show key Fibonacci levels
                st.caption("**Key Fibonacci Levels:**")
                fib_levels_display = " | ".join([f"{k}: ${v:.2f}" for k, v in fib_data["fib_levels"].items()])
                st.caption(fib_levels_display)

        except Exception as e:
            st.warning(f"Could not display Fibonacci analysis: {e}")

        # ===================== Entry Checklist =====================
        st.divider()
        st.subheader("✅ Entry Checklist")

        # Get support/resistance levels
        sr_levels = find_support_resistance(df, window=10, num_levels=2)
        vol_analysis = analyze_volume(df, lookback=20)

        last_row = df.iloc[-1]
        current_price = float(last_row["Close"])
        rsi = float(last_row["RSI14"])
        ema20 = float(last_row["EMA20"])
        ema50 = float(last_row["EMA50"])

        # Checklist items
        trend_ok = ema20 > ema50
        rsi_ok = 45 <= rsi <= 65
        volume_ok = vol_analysis.get("relative_volume", 1.0) > 1.0
        earnings_safe = earnings_date == "Not Scheduled" or (earnings_date and earnings_date != "N/A" and pd.to_datetime(earnings_date) > pd.Timestamp.now() + pd.Timedelta(days=5))
        vol_signal_ok = vol_analysis.get("volume_signal") in ["Accumulation", "Neutral"]

        # Display checklist
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(f"{'✅' if trend_ok else '❌'} **Trend**: EMA20 {'>' if trend_ok else '<'} EMA50")
            st.markdown(f"{'✅' if rsi_ok else '⚠️'} **RSI**: {rsi:.1f} (ideal: 45-65)")
            st.markdown(f"{'✅' if volume_ok else '⚠️'} **Volume**: {vol_analysis.get('relative_volume', 1.0):.2f}x avg")

        with col_b:
            st.markdown(f"{'✅' if earnings_safe else '⚠️'} **Earnings**: {earnings_date if earnings_date != 'Not Scheduled' else 'None soon'}")
            st.markdown(f"{'✅' if vol_signal_ok else '⚠️'} **Volume Signal**: {vol_analysis.get('volume_signal', 'Unknown')}")

            # Show support/resistance
            if sr_levels["support"]:
                st.markdown(f"📍 **Support**: ${', $'.join(map(str, sr_levels['support']))}")
            if sr_levels["resistance"]:
                st.markdown(f"📍 **Resistance**: ${', $'.join(map(str, sr_levels['resistance']))}")

        # Entry trigger suggestion
        st.markdown("---")
        if trend_ok and rsi_ok and volume_ok:
            if sr_levels["resistance"]:
                entry_trigger = sr_levels["resistance"][0]
                st.success(f"🎯 **Entry Trigger**: Break above ${entry_trigger:.2f} with volume > 1.5x average")
            else:
                st.success(f"🎯 **Entry Trigger**: Break above yesterday's high (${df.iloc[-2]['High']:.2f}) with volume")
        else:
            st.warning("⏸️ **Wait**: Not all conditions met. Be patient for better setup.")

        # ===================== Fundamental Analysis =====================
        st.divider()
        st.subheader("📊 Fundamental Analysis")

        try:
            fundamentals = get_fundamentals(symbol, TIINGO_TOKEN)

            if fundamentals and fundamentals.get("quarterly"):
                # Calculate score
                score_data = calculate_fundamental_score(fundamentals)
                metrics = extract_key_metrics(fundamentals)

                # Display score
                score = score_data["score"]
                grade = score_data["grade"]
                score_color = "green" if score >= 70 else "orange" if score >= 50 else "red"

                col_fund1, col_fund2, col_fund3 = st.columns([1, 2, 2])

                with col_fund1:
                    st.markdown(
                        f"<div style='background-color:{score_color};padding:20px;border-radius:10px;color:white;text-align:center;'>"
                        f"<h2 style='margin:0;'>{score}/100</h2>"
                        f"<p style='margin:0;'>Grade: {grade}</p></div>",
                        unsafe_allow_html=True
                    )

                with col_fund2:
                    st.markdown("**Profitability**")
                    st.markdown(f"- Profit Margin: **{metrics.get('profit_margin', 0):.1f}%**")
                    st.markdown(f"- ROE: **{metrics.get('roe', 0):.1f}%**")
                    st.markdown(f"- ROA: **{metrics.get('roa', 0):.1f}%**")

                with col_fund3:
                    st.markdown("**Financial Health**")
                    st.markdown(f"- Debt/Equity: **{metrics.get('debt_to_equity', 0):.2f}**")
                    st.markdown(f"- Current Ratio: **{metrics.get('current_ratio', 0):.2f}**")
                    st.markdown(f"- Cash: **{format_large_number(metrics.get('cash', 0))}**")

                # Detailed breakdown in expander
                with st.expander("📋 Detailed Fundamental Breakdown"):
                    col_detail1, col_detail2 = st.columns(2)

                    with col_detail1:
                        st.markdown("### Income Statement")
                        st.markdown(f"- Revenue: {format_large_number(metrics.get('revenue', 0))}")
                        st.markdown(f"- Gross Profit: {format_large_number(metrics.get('gross_profit', 0))}")
                        st.markdown(f"- Operating Income: {format_large_number(metrics.get('operating_income', 0))}")
                        st.markdown(f"- Net Income: {format_large_number(metrics.get('net_income', 0))}")
                        st.markdown(f"- Gross Margin: {metrics.get('gross_margin', 0):.1f}%")

                    with col_detail2:
                        st.markdown("### Balance Sheet")
                        st.markdown(f"- Total Assets: {format_large_number(metrics.get('total_assets', 0))}")
                        st.markdown(f"- Total Liabilities: {format_large_number(metrics.get('total_liabilities', 0))}")
                        st.markdown(f"- Total Equity: {format_large_number(metrics.get('total_equity', 0))}")
                        st.markdown(f"- Total Debt: {format_large_number(metrics.get('total_debt', 0))}")
                        st.markdown(f"- Current Assets: {format_large_number(metrics.get('current_assets', 0))}")

                    st.markdown("### Quality Score Breakdown")
                    for detail in score_data["details"]:
                        st.markdown(f"- {detail}")
            else:
                st.info("Fundamental data not available for this ticker")

        except Exception as e:
            st.warning(f"Could not load fundamental data: {e}")

        # ===================== Earnings Analysis =====================
        st.divider()
        st.subheader("📅 Earnings Analysis")

        try:
            earnings_history = get_earnings_history(symbol, TIINGO_TOKEN)

            if earnings_history and len(earnings_history) > 0:
                # Calculate metrics
                performance = analyze_earnings_performance(earnings_history)
                quality = calculate_earnings_quality_score(earnings_history)

                # Display quality score
                col_earn1, col_earn2, col_earn3 = st.columns([1, 2, 2])

                with col_earn1:
                    score_color = "green" if quality["score"] >= 70 else "orange" if quality["score"] >= 50 else "red"
                    st.markdown(
                        f"<div style='background-color:{score_color};padding:20px;border-radius:10px;color:white;text-align:center;'>"
                        f"<h2 style='margin:0;'>{quality['score']}/100</h2>"
                        f"<p style='margin:0;'>Grade: {quality['grade']}</p>"
                        f"<small>Earnings Quality</small></div>",
                        unsafe_allow_html=True
                    )

                with col_earn2:
                    st.markdown("**Growth Metrics**")
                    st.markdown(f"- Revenue Growth (YoY): **{performance['revenue_growth']:.1f}%**")
                    st.markdown(f"- Earnings Growth (YoY): **{performance['earnings_growth']:.1f}%**")
                    st.markdown(f"- Total Reports: **{performance['total_reports']}**")

                with col_earn3:
                    st.markdown("**Latest Quarter**")
                    latest_rev = performance['latest_revenue']
                    latest_earn = performance['latest_earnings']
                    st.markdown(f"- Revenue: **${latest_rev/1e9:.2f}B**" if latest_rev > 1e9 else f"- Revenue: **${latest_rev/1e6:.2f}M**")
                    st.markdown(f"- Net Income: **${latest_earn/1e9:.2f}B**" if abs(latest_earn) > 1e9 else f"- Net Income: **${latest_earn/1e6:.2f}M**")

                # Earnings risk check
                next_earnings = get_next_earnings_date(symbol, TIINGO_TOKEN)

                if next_earnings and next_earnings != "N/A":
                    try:
                        from datetime import datetime
                        earnings_date = datetime.strptime(next_earnings, "%Y-%m-%d")
                        days_until = (earnings_date - datetime.now()).days
                        risk_level = get_earnings_risk_level(days_until)

                        st.info(f"**Next Earnings**: {next_earnings} ({days_until} days) - {risk_level}")
                    except:
                        st.info(f"**Next Earnings**: {next_earnings}")

                # Detailed history in expander
                with st.expander("📊 Earnings History (Last 8 Quarters)"):
                    earnings_df = format_earnings_table(earnings_history)
                    if not earnings_df.empty:
                        st.dataframe(earnings_df, use_container_width=True)

                    st.markdown("### Quality Score Breakdown")
                    for detail in quality["details"]:
                        st.markdown(f"- {detail}")
            else:
                st.info("Earnings history not available for this ticker")

        except Exception as e:
            st.warning(f"Could not load earnings data: {e}")

        # ===================== Pattern Recognition =====================
        st.divider()
        st.subheader("📐 Chart Patterns")

        patterns = detect_patterns(df)

        if patterns:
            for pattern in patterns:
                confidence_color = "green" if pattern["confidence"] >= 75 else "orange" if pattern["confidence"] >= 60 else "gray"
                st.markdown(
                    f"<div style='background-color:{confidence_color};padding:10px;border-radius:10px;color:white;margin-bottom:10px;'>"
                    f"<b>{pattern['type']}</b> - {pattern['bias']} (Confidence: {pattern['confidence']}%)<br>"
                    f"<small>{pattern['description']}</small><br>"
                    f"<b>Action:</b> {pattern['action']}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("No clear chart patterns detected. Look for cleaner setups.")

        # ===================== Gap Analysis =====================
        st.divider()
        st.subheader("📊 Gap Analysis")

        gaps = detect_gaps(df, min_gap_pct=2.0, lookback=60)

        col_gap1, col_gap2 = st.columns(2)

        with col_gap1:
            st.markdown("**Unfilled Gap Ups** (Support)")
            if gaps["gap_ups"]:
                for gap in gaps["gap_ups"][:3]:  # Show top 3
                    st.markdown(f"- ${gap['gap_low']:.2f} - ${gap['gap_high']:.2f} ({gap['size_pct']}%)")
            else:
                st.info("No unfilled gap ups")

        with col_gap2:
            st.markdown("**Unfilled Gap Downs** (Resistance)")
            if gaps["gap_downs"]:
                for gap in gaps["gap_downs"][:3]:  # Show top 3
                    st.markdown(f"- ${gap['gap_low']:.2f} - ${gap['gap_high']:.2f} ({gap['size_pct']}%)")
            else:
                st.info("No unfilled gap downs")

        if gaps["nearest_gap"]:
            nearest = gaps["nearest_gap"]
            st.info(f"🎯 **Nearest Gap**: {nearest['type'].replace('_', ' ').title()} at ${nearest['gap_low']:.2f}-${nearest['gap_high']:.2f}")

        # ===================== Multi-Timeframe Relative Strength =====================
        st.divider()
        st.subheader("🏆 Multi-Timeframe Relative Strength")

        try:
            mtf_strength = get_multi_timeframe_strength(symbol, TIINGO_TOKEN)

            if mtf_strength:
                # Display strength across timeframes
                col_tf1, col_tf2, col_tf3, col_tf4, col_tf5 = st.columns(5)

                timeframes = [
                    ("1 Week", "1_week", col_tf1),
                    ("1 Month", "1_month", col_tf2),
                    ("3 Months", "3_months", col_tf3),
                    ("6 Months", "6_months", col_tf4),
                    ("1 Year", "1_year", col_tf5)
                ]

                for label, key, col in timeframes:
                    if key in mtf_strength:
                        data = mtf_strength[key]
                        with col:
                            st.markdown(
                                f"<div style='text-align:center;padding:10px;border-radius:8px;background:#f8f9fa;'>"
                                f"<div style='font-size:12px;color:#666;'>{label}</div>"
                                f"<div style='font-size:24px;'>{data['emoji']}</div>"
                                f"<div style='font-size:14px;font-weight:600;'>{data['rs_ratio']:+.1f}%</div>"
                                f"<div style='font-size:11px;color:#666;'>{data['strength']}</div></div>",
                                unsafe_allow_html=True
                            )

                # Trend analysis
                trend = analyze_strength_trend(mtf_strength)

                if "Accelerating" in trend or "Improving" in trend:
                    st.success(f"**Trend**: {trend}")
                elif "Decelerating" in trend or "Weakening" in trend:
                    st.warning(f"**Trend**: {trend}")
                else:
                    st.info(f"**Trend**: {trend}")
            else:
                st.info("Multi-timeframe strength data not available")

        except Exception as e:
            st.warning(f"Could not calculate multi-timeframe strength: {e}")

        # ===================== Market Correlation =====================
        st.divider()
        st.subheader("📈 Market Correlation (vs SPY)")

        try:
            spy_df = tiingo_history("SPY", TIINGO_TOKEN, 120)
            if spy_df is not None and len(spy_df) > 0:
                correlation_data = calculate_beta_and_correlation(df, spy_df, period=60)

                col_corr1, col_corr2, col_corr3 = st.columns(3)

                with col_corr1:
                    beta = correlation_data.get("beta")
                    if beta:
                        beta_color = "red" if beta > 1.5 else "orange" if beta > 1.0 else "green"
                        st.markdown(
                            f"<div style='background-color:{beta_color};padding:10px;border-radius:10px;color:white;text-align:center;'>"
                            f"<b>Beta</b><br>{beta:.2f}<br>"
                            f"<small>{correlation_data.get('beta_interpretation', '')}</small></div>",
                            unsafe_allow_html=True
                        )

                with col_corr2:
                    corr = correlation_data.get("correlation")
                    if corr:
                        corr_color = "blue" if abs(corr) > 0.7 else "gray"
                        st.markdown(
                            f"<div style='background-color:{corr_color};padding:10px;border-radius:10px;color:white;text-align:center;'>"
                            f"<b>Correlation</b><br>{corr:.2f}<br>"
                            f"<small>{correlation_data.get('correlation_interpretation', '')}</small></div>",
                            unsafe_allow_html=True
                        )

                with col_corr3:
                    st.info(f"**Interpretation**: {correlation_data.get('interpretation', 'N/A')}")
            else:
                st.warning("Could not fetch SPY data for correlation analysis")
        except Exception as e:
            st.warning(f"Correlation analysis unavailable: {e}")

        # ===================== Advanced ML Forecast =====================
        st.divider()
        st.subheader("🤖 Advanced ML Forecast")

        try:
            ml_forecast = ensemble_ml_forecast(df, days_ahead=5)

            if ml_forecast["success"]:
                col_ml1, col_ml2, col_ml3 = st.columns(3)

                with col_ml1:
                    ensemble_price = ml_forecast["ensemble_price"]
                    current_price = df["Close"].iloc[-1]
                    ml_change = ((ensemble_price - current_price) / current_price) * 100
                    ml_color = "green" if ml_change > 0 else "red"

                    st.markdown(
                        f"<div style='background-color:{ml_color};padding:10px;border-radius:10px;color:white;text-align:center;'>"
                        f"<b>Ensemble Prediction</b><br>${ensemble_price:.2f}<br>"
                        f"{ml_change:+.2f}% (5d)<br>"
                        f"<small>Confidence: {ml_forecast['confidence']:.0f}%</small></div>",
                        unsafe_allow_html=True
                    )

                with col_ml2:
                    st.markdown(
                        f"<div style='background-color:blue;padding:10px;border-radius:10px;color:white;text-align:center;'>"
                        f"<b>Prediction Range</b><br>"
                        f"${ml_forecast['forecast_low']:.2f} - ${ml_forecast['forecast_high']:.2f}<br>"
                        f"<small>Agreement: {100 - ml_forecast['agreement']:.0f}%</small></div>",
                        unsafe_allow_html=True
                    )

                with col_ml3:
                    st.markdown(
                        f"<div style='background-color:purple;padding:10px;border-radius:10px;color:white;text-align:center;'>"
                        f"<b>Model Details</b><br>"
                        f"RF: ${ml_forecast['rf_prediction']:.2f} ({ml_forecast['rf_confidence']:.0f}%)<br>"
                        f"GB: ${ml_forecast['gb_prediction']:.2f} ({ml_forecast['gb_confidence']:.0f}%)</div>",
                        unsafe_allow_html=True
                    )

                # Interpretation
                if ml_forecast['agreement'] < 5:
                    st.success("✅ **Strong Agreement**: Both models predict similar prices - high confidence")
                elif ml_forecast['agreement'] < 10:
                    st.info("ℹ️ **Moderate Agreement**: Models mostly agree - reasonable confidence")
                else:
                    st.warning("⚠️ **Low Agreement**: Models diverge - use caution")
            else:
                st.warning(f"ML forecast unavailable: {ml_forecast.get('error', 'Unknown error')}")

        except Exception as e:
            st.warning(f"Advanced ML forecast unavailable: {e}")


        # --- Forecast, ML Edge, Seasonality, and Sentiment ---
        st.divider()
        st.subheader("🧠 Statistical Forecasts & Sentiment")

        try:
            # ===================== 1️⃣ Multi-Model Forecast (Improved) =====================
            from sklearn.linear_model import LinearRegression

            lookback = 30
            days_ahead = 5
            df_recent = df.tail(lookback).reset_index(drop=True)
            df_recent["Index"] = np.arange(len(df_recent))
            last_price = float(df_recent["Close"].iloc[-1])

            # Model 1: Linear Regression
            lr_model = LinearRegression().fit(df_recent[["Index"]], df_recent["Close"])
            lr_pred = float(lr_model.predict([[len(df_recent) + days_ahead]])[0])

            # Model 2: EMA Projection
            ema_20 = df_recent["Close"].ewm(span=20).mean().iloc[-1]
            ema_trend = (last_price - ema_20) / ema_20
            ema_pred = last_price * (1 + ema_trend * (days_ahead / 20))

            # Model 3: Moving Average Projection
            ma_20 = df_recent["Close"].tail(20).mean()
            ma_trend = (last_price - ma_20) / ma_20
            ma_pred = last_price * (1 + ma_trend * (days_ahead / 20))

            # Consensus Forecast
            predictions = [lr_pred, ema_pred, ma_pred]
            predicted_price = sum(predictions) / len(predictions)

            # Confidence based on agreement between models
            std_dev = np.std(predictions)
            confidence = max(0, 100 - (std_dev / predicted_price * 100 * 10))

            forecast_change = predicted_price - last_price
            forecast_pct = (forecast_change / last_price) * 100
            direction = "⬆️ Up" if forecast_change > 0 else "⬇️ Down"

            # Forecast range
            forecast_low = min(predictions)
            forecast_high = max(predictions)

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

            # --- Sentiment Section ---
            # --- Sentiment Data Fetch ---
            import requests
            from textblob import TextBlob

            articles = []
            sentiment_score = 0.0
            sentiment_label = "😐 Neutral"

            try:
                news_url = f"https://api.tiingo.com/tiingo/news?tickers={symbol}&token={TIINGO_TOKEN}"
                r = requests.get(news_url, timeout=5)
                if r.ok:
                    articles = r.json()[:5]  # Limit to 5 most recent
                    scores = [TextBlob(a.get("title", "")).sentiment.polarity for a in articles if a.get("title")]
                    if scores:
                        sentiment_score = sum(scores) / len(scores)
                        if sentiment_score > 0.05:
                            sentiment_label = "😊 Positive"
                        elif sentiment_score < -0.05:
                            sentiment_label = "😟 Negative"
            except Exception as e:
                st.warning(f"⚠️ News sentiment fetch failed: {e}")

            # ===================== Real-Time News Feed =====================
            st.divider()
            try:
                show_news_widget(symbol, TIINGO_TOKEN, limit=5)
            except Exception as e:
                st.warning(f"Could not load news feed: {e}")

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
                    f"<b>Multi-Model Forecast</b><br>{forecast_arrow} ${predicted_price:.2f}<br>"
                    f"{forecast_pct:+.2f}% ({days_ahead}d)<br>"
                    f"<small>Confidence: {confidence:.0f}%</small><br>"
                    f"<small>Range: ${forecast_low:.2f}-${forecast_high:.2f}</small></div>",
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
            
        # ---- SAFETY PREAMBLE: compute indicators for the coaching helper ----
        # Assumes you have `df` (your analyzer dataframe) and `symbol`, `setup_type` already.
        # If you use different names for your dataframe or setup, tweak accordingly.

        def _last_or_none(s):
            try:
                return float(s.iloc[-1])
            except Exception:
                return None

        # If your analyzer already added columns like EMA20/EMA50/RSI/ATR, use them.
        # Otherwise compute lightweight versions here.
        if "EMA20" in df.columns and "EMA50" in df.columns:
            ema20_val = _last_or_none(df["EMA20"])
            ema50_val = _last_or_none(df["EMA50"])
        else:
            # quick EMAs from close
            ema20_val = _last_or_none(df["close"].ewm(span=20).mean()) if "close" in df.columns else None
            ema50_val = _last_or_none(df["close"].ewm(span=50).mean()) if "close" in df.columns else None

        if "RSI" in df.columns:
            rsi_val = _last_or_none(df["RSI"])
        else:
            # simple RSI(14)
            if "close" in df.columns and len(df) >= 15:
                delta = df["close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss.replace(0, float("nan"))
                rsi_series = 100 - (100 / (1 + rs))
                rsi_val = _last_or_none(rsi_series)
            else:
                rsi_val = None

        # ATR if available; otherwise None (keep it optional)
        atr_val = _last_or_none(df["ATR"]) if "ATR" in df.columns else None

        # Volume info
        if "volume" in df.columns:
            avg_volume = _last_or_none(df["volume"].rolling(20).mean()) or _last_or_none(df["volume"])
        else:
            avg_volume = None

        # Trend label (simple inference if not already defined)
        try:
            trend_label = "Uptrend" if (ema20_val is not None and ema50_val is not None and ema20_val > ema50_val) else "Downtrend"
        except Exception:
            trend_label = "-"

        # Pattern / setup type: use your analyzer’s variables if you have them; else default
        setup_pattern = locals().get("setup_pattern", "-")
        setup_type = locals().get("setup_type", setup_pattern if setup_pattern != "-" else "Unknown")

        # ---- NOW call the helper safely ----
        indicators = {
            "ema20": ema20_val,
            "ema50": ema50_val,
            "rsi": rsi_val,
            "atr": atr_val,
            "volume": avg_volume,
            "trend": trend_label,
            "pattern": setup_pattern,
        }
       
        # === ENTRY COACHING SECTION ===
        st.divider()
        st.markdown("### 🧠 Entry Coaching Helper")

        # use a persistent key so Streamlit keeps state between reruns
        if "show_entry_prompt" not in st.session_state:
            st.session_state["show_entry_prompt"] = False

        # simple toggle button
        if st.button("📋 Copy Entry Coaching Prompt"):
            st.session_state["show_entry_prompt"] = not st.session_state["show_entry_prompt"]

        # when toggled on, show expander + text
        if st.session_state["show_entry_prompt"]:
           with st.expander("📋 Copy Entry Coaching Prompt", expanded=False):
                prompt_text = (
                    f"You are a swing-trading coach. Provide educational coaching only; no financial advice.\n\n"
                    f"Symbol: {symbol}\n"
                    f"Setup type: {setup_type}\n"
                    f"Indicators: {indicators}\n"
                    f"Notes: {st.session_state.get('planner_notes', '-')}\n\n"
                    "Use fresh intraday and premarket data from Yahoo Finance when analyzing entry setups. "
                    "Coach me on timing, confirmation, and risk management."
                )
                st.code(prompt_text, language="markdown")




            
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
        
        
       
        # ENTRY COACHING PROMPT BUILDER
# ---------------------------------------------------------------------------
def _render_entry_coaching(symbol: str, setup_type: str, indicators: dict, notes: str = ""):
    """Automatically render AI coaching guidance at the bottom of the Analyzer."""
    ema20 = indicators.get("ema20")
    ema50 = indicators.get("ema50")
    rsi = indicators.get("rsi")
    atr = indicators.get("atr")
    volume = indicators.get("volume")
    trend = indicators.get("trend")
    pattern = indicators.get("pattern")

    st.divider()
    st.markdown("### 🧠 Entry Coaching Helper")

    st.info(f"""
**Symbol:** {symbol}  
**Setup Type:** {setup_type}  
**Trend:** {trend}  
**Pattern:** {pattern}  
**EMA20:** {ema20}  **EMA50:** {ema50}  **RSI:** {rsi}  **ATR:** {atr}  **Volume:** {volume}

Use this as your entry-planning helper in ChatGPT:

> You are a swing-trading coach. Provide educational coaching only — no financial advice.  
> Symbol: {symbol}  
> Setup type: {setup_type}  
> Indicators — EMA20: {ema20}, EMA50: {ema50}, RSI: {rsi}, ATR: {atr}, Volume: {volume}, Trend: {trend}, Pattern: {pattern}.  
> Before analyzing, fetch **fresh real-time price data** for this symbol from Yahoo Finance or another reliable market data source.  
> Coach me on:
> - whether this setup shows strong technical confirmation for entry,  
> - where ideal entries may form (breakout or pullback zones),  
> - early invalidation signs to avoid false breakouts,  
> - and how to plan risk/reward positioning before entering.
""")

