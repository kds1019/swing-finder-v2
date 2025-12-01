"""
Backtesting Page for SwingFinder
Test scanner strategies on historical data
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from utils.backtesting import backtest_strategy
from utils.storage import load_watchlist
from scanner import load_verified_universe


def show_backtest_page(token: str):
    """Main backtesting page UI."""
    
    st.title("📊 Strategy Backtester")
    st.markdown("**Test your scanner settings on historical data to validate performance**")
    
    st.info("💡 **How it works:** The backtester simulates running your scanner on past data, "
            "then tracks what would have happened if you traded every setup. "
            "This helps you optimize your settings and build confidence in your strategy!")
    
    # Sidebar settings
    with st.sidebar:
        st.subheader("🔧 Backtest Settings")
        
        # Ticker selection
        ticker_source = st.radio(
            "Test on:",
            ["Watchlist", "Full Universe", "Custom List"],
            help="Choose which stocks to backtest"
        )
        
        if ticker_source == "Watchlist":
            tickers = load_watchlist()
            if not tickers:
                st.warning("⚠️ No watchlist found! Add stocks to your watchlist first.")
                st.stop()
        elif ticker_source == "Full Universe":
            tickers = load_verified_universe(token)[:100]  # Limit to 100 for speed
            st.caption(f"Testing on {len(tickers)} stocks (limited for performance)")
        else:
            custom_input = st.text_area(
                "Enter tickers (comma-separated)",
                "AAPL, TSLA, NVDA, MSFT, GOOGL",
                help="Enter stock symbols separated by commas"
            )
            tickers = [t.strip().upper() for t in custom_input.split(",") if t.strip()]
        
        st.divider()
        
        # Time period
        lookback_days = st.selectbox(
            "Test Period",
            [("3 Months", 90), ("6 Months", 180), ("1 Year", 365), ("2 Years", 730)],
            index=2,
            format_func=lambda x: x[0]
        )[1]
        
        # Scanner settings (match scanner.py)
        st.subheader("Scanner Settings")
        
        setup_mode = st.selectbox(
            "Setup Mode",
            ["Pullback", "Breakout", "Both"],
            index=2
        )
        
        sensitivity = st.slider(
            "Sensitivity",
            1, 5, 3,
            help="1 = Very Strict, 5 = Very Relaxed"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            price_min = st.number_input("Min Price", value=10.0, min_value=0.0, step=5.0)
        with col2:
            price_max = st.number_input("Max Price", value=60.0, min_value=0.0, step=10.0)
        
        min_volume = st.number_input(
            "Min Volume",
            value=500000,
            min_value=0,
            step=100000,
            format="%d"
        )
        
        st.divider()
        
        # Trade management settings
        st.subheader("Trade Management")
        
        hold_days = st.slider(
            "Max Hold Days",
            1, 20, 5,
            help="Maximum days to hold each trade"
        )
        
        stop_loss_mult = st.number_input(
            "Stop Loss (ATR multiplier)",
            value=1.5,
            min_value=0.5,
            max_value=3.0,
            step=0.1,
            help="Stop = Entry - (X × ATR)"
        )
        
        take_profit_mult = st.number_input(
            "Take Profit (R multiplier)",
            value=2.0,
            min_value=1.0,
            max_value=5.0,
            step=0.5,
            help="Target = Entry + (X × Risk)"
        )
        
        st.divider()
        
        run_backtest = st.button("🚀 Run Backtest", type="primary", use_container_width=True)
    
    # Run backtest
    if run_backtest:
        st.session_state["backtest_running"] = True
        
        with st.spinner(f"🔄 Backtesting {len(tickers)} stocks over {lookback_days} days... This may take 1-2 minutes"):
            results = backtest_strategy(
                tickers=tickers,
                token=token,
                lookback_days=lookback_days,
                setup_mode=setup_mode,
                sensitivity=sensitivity,
                price_min=price_min,
                price_max=price_max,
                min_volume=min_volume,
                hold_days=hold_days,
                stop_loss_atr_mult=stop_loss_mult,
                take_profit_r_mult=take_profit_mult
            )
            
            st.session_state["backtest_results"] = results
        
        st.session_state["backtest_running"] = False
        st.success("✅ Backtest complete!")
    
    # Display results
    results = st.session_state.get("backtest_results")
    
    if not results:
        st.info("👈 Configure settings in the sidebar and click 'Run Backtest' to see results")
        st.stop()
    
    if "error" in results:
        st.error(f"❌ {results['error']}")
        st.stop()
    
    # Display results in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Performance", "📋 All Trades", "⚙️ Settings"])

    with tab1:
        show_overview_tab(results)

    with tab2:
        show_performance_tab(results)

    with tab3:
        show_trades_tab(results)

    with tab4:
        show_settings_tab(results, setup_mode, sensitivity, lookback_days)


def show_overview_tab(results: dict):
    """Display overview metrics."""

    st.subheader("📊 Backtest Summary")

    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Trades",
            results["total_trades"],
            help="Number of setups that would have been flagged by scanner"
        )

    with col2:
        win_rate = results["win_rate"]
        st.metric(
            "Win Rate",
            f"{win_rate:.1f}%",
            delta=f"{win_rate - 50:.1f}% vs 50%",
            delta_color="normal" if win_rate >= 50 else "inverse",
            help="Percentage of winning trades"
        )

    with col3:
        avg_return = results["avg_return"]
        st.metric(
            "Avg Return",
            f"{avg_return:+.2f}%",
            delta=f"{avg_return:.2f}%",
            delta_color="normal" if avg_return > 0 else "inverse",
            help="Average return per trade"
        )

    with col4:
        profit_factor = results["profit_factor"]
        pf_display = f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞"
        st.metric(
            "Profit Factor",
            pf_display,
            delta="Good" if profit_factor > 1.5 else "Needs Work",
            delta_color="normal" if profit_factor > 1.5 else "inverse",
            help="Gross Profit / Gross Loss (>1.5 is good)"
        )

    st.divider()

    # Second row of metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Avg Win",
            f"+{results['avg_win']:.2f}%",
            help="Average return on winning trades"
        )

    with col2:
        st.metric(
            "Avg Loss",
            f"{results['avg_loss']:.2f}%",
            help="Average return on losing trades"
        )

    with col3:
        st.metric(
            "Avg R-Multiple",
            f"{results['avg_r_multiple']:.2f}R",
            delta="Good" if results['avg_r_multiple'] > 0.5 else "Needs Work",
            delta_color="normal" if results['avg_r_multiple'] > 0.5 else "inverse",
            help="Average risk/reward multiple (>0.5R is good)"
        )

    with col4:
        st.metric(
            "Expectancy",
            f"${results['expectancy']:.2f}",
            delta="Positive" if results['expectancy'] > 0 else "Negative",
            delta_color="normal" if results['expectancy'] > 0 else "inverse",
            help="Average $ per trade (theoretical)"
        )

    st.divider()

    # Win/Loss breakdown
    st.subheader("🎯 Win/Loss Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        # Pie chart
        fig = go.Figure(data=[go.Pie(
            labels=["Wins", "Losses"],
            values=[results["total_wins"], results["total_losses"]],
            marker=dict(colors=["#00D084", "#F26868"]),
            hole=0.4
        )])
        fig.update_layout(
            title="Win/Loss Distribution",
            height=300,
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Exit reasons
        exit_reasons = results["exit_reasons"]
        fig = go.Figure(data=[go.Bar(
            x=list(exit_reasons.keys()),
            y=list(exit_reasons.values()),
            marker=dict(color=["#5DD39E", "#F26868", "#FFDD4A"])
        )])
        fig.update_layout(
            title="Exit Reasons",
            xaxis_title="Reason",
            yaxis_title="Count",
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Best/Worst trades
    st.subheader("🏆 Best & Worst Trades")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🟢 Best Trade")
        best = results["best_trade"]
        if best:
            entry_date = pd.to_datetime(best['entry_date']).strftime('%Y-%m-%d')
            exit_date = pd.to_datetime(best['exit_date']).strftime('%Y-%m-%d')
            st.markdown(f"""
            - **Ticker:** {best['ticker']}
            - **Setup:** {best['setup_type']}
            - **Entry:** {entry_date} @ ${best['entry_price']:.2f}
            - **Exit:** {exit_date} @ ${best['exit_price']:.2f}
            - **Return:** +{best['pnl_pct']:.2f}% ({best['r_multiple']:.2f}R)
            - **Reason:** {best['exit_reason']}
            """)

    with col2:
        st.markdown("### 🔴 Worst Trade")
        worst = results["worst_trade"]
        if worst:
            entry_date = pd.to_datetime(worst['entry_date']).strftime('%Y-%m-%d')
            exit_date = pd.to_datetime(worst['exit_date']).strftime('%Y-%m-%d')
            st.markdown(f"""
            - **Ticker:** {worst['ticker']}
            - **Setup:** {worst['setup_type']}
            - **Entry:** {entry_date} @ ${worst['entry_price']:.2f}
            - **Exit:** {exit_date} @ ${worst['exit_price']:.2f}
            - **Return:** {worst['pnl_pct']:.2f}% ({worst['r_multiple']:.2f}R)
            - **Reason:** {worst['exit_reason']}
            """)


def show_performance_tab(results: dict):
    """Display performance charts."""

    st.subheader("📈 Performance Over Time")

    # Monthly performance
    monthly_stats = pd.DataFrame(results["monthly_stats"])

    if len(monthly_stats) > 0:
        # Cumulative returns chart
        all_trades = pd.DataFrame(results["all_trades"])
        all_trades["entry_date"] = pd.to_datetime(all_trades["entry_date"])
        all_trades = all_trades.sort_values("entry_date")
        all_trades["cumulative_return"] = all_trades["pnl_pct"].cumsum()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=all_trades["entry_date"],
            y=all_trades["cumulative_return"],
            mode="lines",
            name="Cumulative Return",
            line=dict(color="#5DD39E", width=2),
            fill="tozeroy",
            fillcolor="rgba(93, 211, 158, 0.1)"
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.update_layout(
            title="Cumulative Return Over Time",
            xaxis_title="Date",
            yaxis_title="Cumulative Return (%)",
            height=400,
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Monthly breakdown
        st.subheader("📅 Monthly Breakdown")

        monthly_display = monthly_stats.copy()
        monthly_display.columns = ["Month", "Trades", "Avg Return", "Total Return", "Total P&L"]
        monthly_display["Avg Return"] = monthly_display["Avg Return"].apply(lambda x: f"{x:.2f}%")
        monthly_display["Total Return"] = monthly_display["Total Return"].apply(lambda x: f"{x:.2f}%")
        monthly_display["Total P&L"] = monthly_display["Total P&L"].apply(lambda x: f"${x:.2f}")

        st.dataframe(monthly_display, use_container_width=True, hide_index=True)

        st.divider()

        # Setup type performance
        st.subheader("🎯 Performance by Setup Type")

        setup_stats = all_trades.groupby("setup_type").agg({
            "pnl_pct": ["count", "mean", lambda x: (x > 0).sum() / len(x) * 100],
            "r_multiple": "mean"
        }).reset_index()

        setup_stats.columns = ["Setup Type", "Trades", "Avg Return (%)", "Win Rate (%)", "Avg R-Multiple"]

        st.dataframe(setup_stats, use_container_width=True, hide_index=True)


def show_trades_tab(results: dict):
    """Display all trades table."""

    st.subheader("📋 All Trades")

    all_trades = pd.DataFrame(results["all_trades"])

    if len(all_trades) == 0:
        st.warning("No trades found")
        return

    # Format for display
    display_df = all_trades[[
        "ticker", "setup_type", "entry_date", "entry_price",
        "exit_date", "exit_price", "pnl_pct", "r_multiple",
        "exit_reason", "hold_days"
    ]].copy()

    display_df["entry_date"] = pd.to_datetime(display_df["entry_date"]).dt.strftime("%Y-%m-%d")
    display_df["exit_date"] = pd.to_datetime(display_df["exit_date"]).dt.strftime("%Y-%m-%d")
    display_df["entry_price"] = display_df["entry_price"].apply(lambda x: f"${x:.2f}")
    display_df["exit_price"] = display_df["exit_price"].apply(lambda x: f"${x:.2f}")
    display_df["pnl_pct"] = display_df["pnl_pct"].apply(lambda x: f"{x:+.2f}%")
    display_df["r_multiple"] = display_df["r_multiple"].apply(lambda x: f"{x:.2f}R")

    display_df.columns = [
        "Ticker", "Setup", "Entry Date", "Entry Price",
        "Exit Date", "Exit Price", "Return", "R-Multiple",
        "Exit Reason", "Hold Days"
    ]

    # Add filters
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_setup = st.multiselect(
            "Filter by Setup",
            options=all_trades["setup_type"].unique(),
            default=all_trades["setup_type"].unique()
        )

    with col2:
        filter_exit = st.multiselect(
            "Filter by Exit Reason",
            options=all_trades["exit_reason"].unique(),
            default=all_trades["exit_reason"].unique()
        )

    with col3:
        filter_result = st.selectbox(
            "Filter by Result",
            ["All", "Wins Only", "Losses Only"]
        )

    # Apply filters
    filtered_trades = all_trades.copy()
    filtered_trades = filtered_trades[filtered_trades["setup_type"].isin(filter_setup)]
    filtered_trades = filtered_trades[filtered_trades["exit_reason"].isin(filter_exit)]

    if filter_result == "Wins Only":
        filtered_trades = filtered_trades[filtered_trades["pnl_pct"] > 0]
    elif filter_result == "Losses Only":
        filtered_trades = filtered_trades[filtered_trades["pnl_pct"] <= 0]

    st.caption(f"Showing {len(filtered_trades)} of {len(all_trades)} trades")

    # Display filtered table
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=600)

    # Download button
    csv = all_trades.to_csv(index=False)
    st.download_button(
        label="📥 Download All Trades (CSV)",
        data=csv,
        file_name="backtest_trades.csv",
        mime="text/csv"
    )


def show_settings_tab(results: dict, setup_mode: str, sensitivity: int, lookback_days: int):
    """Display backtest settings and recommendations."""

    st.subheader("⚙️ Backtest Configuration")

    st.markdown(f"""
    ### Settings Used:
    - **Setup Mode:** {setup_mode}
    - **Sensitivity:** {sensitivity} (1=Strict, 5=Relaxed)
    - **Test Period:** {lookback_days} days
    - **Stocks Tested:** {results['tested_tickers']}
    - **Failed Tickers:** {len(results['failed_tickers'])}

    ### Results Summary:
    - **Total Setups Found:** {results['total_trades']}
    - **Win Rate:** {results['win_rate']:.1f}%
    - **Avg Return:** {results['avg_return']:+.2f}%
    - **Profit Factor:** {results['profit_factor']:.2f}
    """)

    st.divider()

    # Recommendations
    st.subheader("💡 Recommendations")

    win_rate = results["win_rate"]
    avg_return = results["avg_return"]
    profit_factor = results["profit_factor"]

    if win_rate >= 60 and avg_return > 2 and profit_factor > 2:
        st.success("🎉 **Excellent Strategy!** Your settings show strong historical performance. "
                   "Consider using these settings for live trading.")
    elif win_rate >= 50 and avg_return > 1:
        st.info("👍 **Good Strategy.** Your settings show positive expectancy. "
                "Consider testing with different sensitivity levels to optimize further.")
    elif win_rate >= 40:
        st.warning("⚠️ **Needs Improvement.** Win rate is below 50%. "
                   "Try adjusting sensitivity or focusing on one setup type (Pullback or Breakout).")
    else:
        st.error("❌ **Poor Performance.** These settings don't show positive expectancy. "
                 "Consider changing setup mode, sensitivity, or price range filters.")

    st.divider()

    # Optimization suggestions
    st.subheader("🔧 Optimization Tips")

    st.markdown("""
    **To improve your strategy:**

    1. **Adjust Sensitivity:**
       - Lower sensitivity (1-2) = Fewer but higher quality setups
       - Higher sensitivity (4-5) = More setups but lower quality

    2. **Focus on Best Setup Type:**
       - Check "Performance by Setup Type" in Performance tab
       - Focus on the setup type with highest win rate

    3. **Optimize Price Range:**
       - Higher priced stocks ($30-60) often have better trends
       - Lower priced stocks ($10-20) can be more volatile

    4. **Test Different Hold Periods:**
       - Shorter holds (3-5 days) = Quick profits but more trades
       - Longer holds (7-10 days) = Bigger moves but fewer trades

    5. **Adjust Risk Management:**
       - Tighter stops (1-1.5 ATR) = Less risk but more stop-outs
       - Wider stops (2-2.5 ATR) = More risk but fewer stop-outs
    """)



