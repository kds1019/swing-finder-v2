"""
Trade Journal Page - Track, analyze, and get coaching on your trades
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
from active_trades import (
    load_trade_journal,
    save_trade_journal,
    calculate_performance_stats,
    calculate_mistake_stats
)
# Removed: gpt_export import (replaced with built-in Claude AI)


def build_journal_coaching_prompt(trades: List[Dict[str, Any]], focus: str = "general") -> str:
    """Build a coaching prompt based on journal entries."""
    
    if not trades:
        return "No trades to analyze yet. Start trading and journal your results!"
    
    # Calculate stats
    wins = [t for t in trades if t.get("pnl_dollar", 0) > 0]
    losses = [t for t in trades if t.get("pnl_dollar", 0) <= 0]
    
    total_pnl = sum(t.get("pnl_dollar", 0) for t in trades)
    win_rate = (len(wins) / len(trades) * 100) if trades else 0
    avg_win = sum(t.get("pnl_dollar", 0) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.get("pnl_dollar", 0) for t in losses) / len(losses) if losses else 0

    # Calculate profit factor safely
    if avg_loss != 0:
        profit_factor = abs(avg_win / avg_loss)
        profit_factor_str = f"{profit_factor:.2f}"
    else:
        profit_factor_str = "N/A"

    prompt = f"""I need coaching on my swing trading performance. Here's my recent trading data:

📊 PERFORMANCE SUMMARY ({len(trades)} trades):
- Total P&L: ${total_pnl:,.2f}
- Win Rate: {win_rate:.1f}% ({len(wins)} wins, {len(losses)} losses)
- Average Win: ${avg_win:,.2f}
- Average Loss: ${avg_loss:,.2f}
- Profit Factor: {profit_factor_str}

📝 RECENT TRADES:
"""
    
    # Add last 10 trades
    for trade in trades[-10:]:
        symbol = trade.get("symbol", "")
        entry = trade.get("entry_price", 0)
        exit_p = trade.get("exit_price", 0)
        pnl = trade.get("pnl_dollar", 0)
        pnl_pct = trade.get("pnl_percent", 0)
        reason = trade.get("exit_reason", "")
        setup = trade.get("setup_type", "")
        notes = trade.get("notes", "")
        
        prompt += f"""
{symbol}: Entry ${entry:.2f} → Exit ${exit_p:.2f} | P&L: ${pnl:,.2f} ({pnl_pct:+.1f}%)
  Setup: {setup}
  Exit Reason: {reason}
  Notes: {notes}
"""
    
    # Add focus-specific questions
    if focus == "general":
        prompt += """

🎯 COACHING REQUEST:
Please analyze my trading performance and provide:
1. What patterns do you see in my wins vs losses?
2. Am I following my rules consistently?
3. What's my biggest weakness based on this data?
4. What should I focus on improving next?
5. Any specific advice for my trading style?
"""
    elif focus == "psychology":
        prompt += """

🧠 PSYCHOLOGY COACHING:
Based on my trades, help me with:
1. Do I cut winners short or let losers run?
2. Am I revenge trading after losses?
3. Do I follow my stop losses?
4. What emotional patterns do you see?
5. How can I improve my trading discipline?
"""
    elif focus == "strategy":
        prompt += """

📈 STRATEGY COACHING:
Analyze my strategy execution:
1. Which setups work best for me?
2. Am I entering at good prices?
3. Are my exits optimal?
4. Should I adjust my risk/reward targets?
5. What strategy improvements would help most?
"""
    elif focus == "risk":
        prompt += """

⚠️ RISK MANAGEMENT COACHING:
Review my risk management:
1. Am I sizing positions correctly?
2. Do I respect my stop losses?
3. Is my risk/reward ratio optimal?
4. Am I over-trading or under-trading?
5. How can I improve my risk management?
"""
    
    return prompt


def show_journal_page():
    """Main trade journal page."""
    st.title("📔 Trade Journal & Coaching")
    st.markdown("Track your trades, analyze performance, and get AI coaching")
    
    # Load journal
    journal = load_trade_journal()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Performance Stats",
        "📝 Journal Entries", 
        "🤖 AI Coaching",
        "➕ Manual Entry"
    ])
    
    # Tab 1: Performance Stats
    with tab1:
        if not journal:
            st.info("No trades in journal yet. Close some trades to see stats!")
        else:
            stats = calculate_performance_stats()
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Trades", stats.get("total_trades", 0))
            with col2:
                pnl = stats.get("total_pnl", 0)
                st.metric("Total P&L", f"${pnl:,.2f}", 
                         delta=f"{'+' if pnl > 0 else ''}{pnl:,.2f}")
            with col3:
                wr = stats.get("win_rate", 0)
                st.metric("Win Rate", f"{wr:.1f}%")
            with col4:
                st.metric("Profit Factor", f"{stats.get('profit_factor', 0):.2f}")
            
            st.markdown("---")
            
            # Detailed stats
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📈 Wins")
                st.metric("Win Count", stats.get("wins", 0))
                st.metric("Average Win", f"${stats.get('avg_win', 0):,.2f}")
                st.metric("Largest Win", f"${stats.get('largest_win', 0):,.2f}")

            with col2:
                st.subheader("📉 Losses")
                st.metric("Loss Count", stats.get("losses", 0))
                st.metric("Average Loss", f"${stats.get('avg_loss', 0):,.2f}")
                st.metric("Largest Loss", f"${stats.get('largest_loss', 0):,.2f}")

            st.markdown("---")
            st.subheader("📊 R-Multiple Performance")
            st.metric("Average R-Multiple", f"{stats.get('avg_r_multiple', 0):.2f}R")
            st.caption("R-Multiple measures profit/loss relative to initial risk")

            # Mistake Tracker Stats
            mistake_stats = calculate_mistake_stats()
            if mistake_stats.get("total_mistakes", 0) > 0:
                st.markdown("---")
                st.subheader("🚨 Mistake Tracker")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Mistakes Tracked", mistake_stats.get("total_mistakes", 0))
                    st.metric("Cost of Mistakes", f"${mistake_stats.get('total_cost', 0):,.2f}")

                with col2:
                    top_mistake = mistake_stats.get("top_mistake", "None")
                    top_count = mistake_stats.get("top_mistake_count", 0)
                    st.metric("Most Common Mistake", f"{top_mistake} ({top_count}x)")

                # Show breakdown
                with st.expander("📊 Mistake Breakdown"):
                    breakdown = mistake_stats.get("mistake_breakdown", {})
                    costs = mistake_stats.get("mistake_costs", {})

                    for mistake, count in breakdown.items():
                        cost = costs.get(mistake, 0)
                        st.markdown(f"**{mistake}**: {count} times → Cost: ${cost:,.2f}")

    # Tab 2: Journal Entries
    with tab2:
        st.subheader("📝 All Journal Entries")

        if not journal:
            st.info("No journal entries yet. Trades are automatically added when you close them in Active Trades.")
        else:
            # Filter options
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_type = st.selectbox("Filter", ["All", "Wins Only", "Losses Only"])
            with col2:
                days_back = st.selectbox("Time Period", [7, 14, 30, 60, 90, 365, "All Time"])
            with col3:
                sort_by = st.selectbox("Sort By", ["Date (Newest)", "Date (Oldest)", "P&L (High to Low)", "P&L (Low to High)"])

            # Filter trades
            filtered = journal.copy()

            if filter_type == "Wins Only":
                filtered = [t for t in filtered if t.get("pnl_dollar", 0) > 0]
            elif filter_type == "Losses Only":
                filtered = [t for t in filtered if t.get("pnl_dollar", 0) <= 0]

            if days_back != "All Time":
                cutoff = datetime.now() - timedelta(days=days_back)
                filtered = [t for t in filtered if datetime.fromisoformat(t.get("exit_date", "")) > cutoff]

            # Sort trades
            if sort_by == "Date (Newest)":
                filtered.sort(key=lambda x: x.get("exit_date", ""), reverse=True)
            elif sort_by == "Date (Oldest)":
                filtered.sort(key=lambda x: x.get("exit_date", ""))
            elif sort_by == "P&L (High to Low)":
                filtered.sort(key=lambda x: x.get("pnl_dollar", 0), reverse=True)
            elif sort_by == "P&L (Low to High)":
                filtered.sort(key=lambda x: x.get("pnl_dollar", 0))

            st.markdown(f"**Showing {len(filtered)} of {len(journal)} trades**")
            st.markdown("---")

            # Display each trade with edit capability
            for idx, trade in enumerate(filtered):
                symbol = trade.get("symbol", "")
                entry_date = trade.get("entry_date", "")
                exit_date = trade.get("exit_date", "")
                entry_price = trade.get("entry_price", 0)
                exit_price = trade.get("exit_price", 0)
                pnl = trade.get("pnl_dollar", 0)
                pnl_pct = trade.get("pnl_percent", 0)
                r_mult = trade.get("r_multiple", 0)
                exit_reason = trade.get("exit_reason", "")
                setup = trade.get("setup_type", "")
                notes = trade.get("notes", "")

                # Color based on win/loss
                color = "🟢" if pnl > 0 else "🔴"

                with st.expander(f"{color} **{symbol}** | ${pnl:+,.2f} ({pnl_pct:+.1f}%) | {exit_date[:10]}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Entry:** ${entry_price:.2f} on {entry_date[:10]}")
                        st.markdown(f"**Exit:** ${exit_price:.2f} on {exit_date[:10]}")
                        st.markdown(f"**P&L:** ${pnl:+,.2f} ({pnl_pct:+.1f}%)")
                        st.markdown(f"**R-Multiple:** {r_mult:.2f}R")

                    with col2:
                        st.markdown(f"**Setup Type:** {setup}")
                        st.markdown(f"**Exit Reason:** {exit_reason}")
                        st.markdown(f"**Shares:** {trade.get('shares', 0)}")

                        # Show mistake if tracked
                        mistake = trade.get("mistake")
                        if mistake:
                            st.markdown(f"**🚨 Mistake:** {mistake}")

                    st.markdown("---")
                    st.markdown("**📝 Notes:**")

                    # Editable notes
                    new_notes = st.text_area(
                        "Edit notes",
                        value=notes,
                        height=100,
                        key=f"notes_{idx}_{symbol}_{exit_date}",
                        placeholder="Add your thoughts, lessons learned, what went well, what to improve..."
                    )

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("💾 Save Notes", key=f"save_{idx}_{symbol}_{exit_date}", use_container_width=True):
                            # Update the trade in journal
                            for j_trade in journal:
                                if (j_trade.get("symbol") == symbol and
                                    j_trade.get("exit_date") == exit_date):
                                    j_trade["notes"] = new_notes
                                    break

                            save_trade_journal(journal)
                            st.success("✅ Notes saved!")
                            st.rerun()

                    with col2:
                        # GPT Review button
                        if st.button("💬 Get GPT Review", key=f"gpt_{idx}_{symbol}_{exit_date}", use_container_width=True):
                            st.session_state[f"show_gpt_review_{idx}"] = True

                    with col3:
                        # Delete button
                        if st.button("🗑️ Delete", key=f"delete_{idx}_{symbol}_{exit_date}", use_container_width=True, type="secondary"):
                            st.session_state[f"confirm_delete_{idx}"] = True

                    # Confirmation dialog for delete
                    if st.session_state.get(f"confirm_delete_{idx}", False):
                        st.warning(f"⚠️ Are you sure you want to delete this trade: **{symbol}** (${pnl:+,.2f})?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("❌ Cancel", key=f"cancel_delete_{idx}", use_container_width=True):
                                st.session_state[f"confirm_delete_{idx}"] = False
                                st.rerun()
                        with col2:
                            if st.button("✅ Yes, Delete", key=f"confirm_delete_yes_{idx}", use_container_width=True, type="primary"):
                                # Remove the trade from journal
                                journal = [t for t in journal if not (
                                    t.get("symbol") == symbol and
                                    t.get("exit_date") == exit_date
                                )]
                                save_trade_journal(journal)
                                st.session_state[f"confirm_delete_{idx}"] = False
                                st.success(f"✅ Deleted {symbol} from journal!")
                                st.rerun()

                    # Show GPT review in expander if button clicked
                    if st.session_state.get(f"show_gpt_review_{idx}", False):
                        with st.expander("💬 GPT Trade Review - Copy to ChatGPT", expanded=True):
                            # Build trade dict for GPT export
                            trade_for_gpt = {
                                "symbol": symbol,
                                "entry": entry_price,
                                "exit_price": exit_price,
                                "shares": trade.get("shares", 0),
                                "opened": entry_date,
                                "exit_date": exit_date,
                                "setup_type": setup,
                                "exit_reason": exit_reason,
                                "notes": new_notes,  # Use current notes
                                "pnl_dollar": pnl,
                                "pnl_percent": pnl_pct,
                                "r_multiple": r_mult,
                            }

                            review_prompt = build_trade_review_for_gpt(trade_for_gpt)

                            st.text_area(
                                "Copy this to ChatGPT for detailed trade review:",
                                value=review_prompt,
                                height=400,
                                key=f"gpt_area_{idx}_{symbol}_{exit_date}",
                                help="Select all (Ctrl+A) and copy (Ctrl+C) to paste into ChatGPT"
                            )

                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("📋 Copy", key=f"copy_gpt_{idx}", use_container_width=True):
                                    st.toast("✅ Select all (Ctrl+A) and copy (Ctrl+C)!")
                            with col2:
                                if st.button("✅ Close", key=f"close_gpt_{idx}", use_container_width=True):
                                    st.session_state[f"show_gpt_review_{idx}"] = False
                                    st.rerun()

    # Tab 3: AI Coaching
    with tab3:
        st.subheader("🤖 AI Trade Coaching")
        st.markdown("Get personalized coaching based on your journal entries")

        if not journal:
            st.info("No trades to analyze yet. Close some trades first!")
        else:
            # Coaching focus
            col1, col2 = st.columns([2, 1])
            with col1:
                focus = st.selectbox(
                    "Coaching Focus",
                    ["general", "psychology", "strategy", "risk"],
                    format_func=lambda x: {
                        "general": "📊 General Performance Review",
                        "psychology": "🧠 Trading Psychology",
                        "strategy": "📈 Strategy & Execution",
                        "risk": "⚠️ Risk Management"
                    }[x]
                )

            with col2:
                # Set min/max/default based on journal size
                min_trades = min(1, len(journal))
                max_trades = len(journal)
                default_trades = min(20, len(journal))

                num_trades = st.number_input(
                    "Trades to analyze",
                    min_value=min_trades,
                    max_value=max_trades,
                    value=default_trades,
                    step=1
                )

            st.markdown("---")

            # Generate coaching prompt
            recent_trades = journal[-num_trades:]
            prompt = build_journal_coaching_prompt(recent_trades, focus)

            st.markdown("### 💬 Copy this to ChatGPT for coaching:")
            st.text_area(
                "Coaching Prompt (Select all and copy)",
                value=prompt,
                height=400,
                help="Copy this entire prompt and paste it into ChatGPT for personalized coaching"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 Copy to Clipboard", use_container_width=True):
                    st.toast("✅ Copied! Paste into ChatGPT")
            with col2:
                if st.button("🔄 Regenerate Prompt", use_container_width=True):
                    st.rerun()

    # Tab 4: Manual Entry
    with tab4:
        st.subheader("➕ Add Manual Journal Entry")
        st.markdown("Add a trade that wasn't tracked in Active Trades")

        col1, col2 = st.columns(2)

        with col1:
            symbol = st.text_input("Symbol", placeholder="AAPL")
            entry_price = st.number_input("Entry Price", min_value=0.01, value=100.0, step=0.01)
            exit_price = st.number_input("Exit Price", min_value=0.01, value=105.0, step=0.01)
            shares = st.number_input("Shares", min_value=1, value=100, step=1)

        with col2:
            entry_date = st.date_input("Entry Date", value=datetime.now() - timedelta(days=7))
            exit_date = st.date_input("Exit Date", value=datetime.now())
            setup_type = st.selectbox("Setup Type", [
                "Momentum", "Reversal", "Breakout", "Pullback",
                "Volume Surge", "Other"
            ])
            exit_reason = st.selectbox("Exit Reason", [
                "Hit Target", "Hit Stop", "Trailing Stop",
                "Time Stop", "Manual Exit", "Other"
            ])

        notes = st.text_area(
            "Trade Notes",
            placeholder="What was your thesis? What went well? What could improve?",
            height=150
        )

        if st.button("➕ Add to Journal", type="primary", use_container_width=True):
            if not symbol:
                st.error("Please enter a symbol")
            else:
                # Calculate P&L
                pnl = (exit_price - entry_price) * shares
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100

                # Create journal entry
                new_entry = {
                    "symbol": symbol.upper(),
                    "entry_date": entry_date.isoformat(),
                    "exit_date": exit_date.isoformat(),
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "shares": shares,
                    "pnl_dollar": round(pnl, 2),
                    "pnl_percent": round(pnl_pct, 2),
                    "r_multiple": 0,  # Can't calculate without stop
                    "exit_reason": exit_reason,
                    "setup_type": setup_type,
                    "notes": notes,
                }

                # Add to journal
                journal.append(new_entry)
                save_trade_journal(journal)

                st.success(f"✅ Added {symbol} to journal: ${pnl:+,.2f} ({pnl_pct:+.1f}%)")
                st.balloons()
                st.rerun()

