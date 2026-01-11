"""
Live monitoring and override controls for agent execution
Real-time progress tracking with manual intervention capabilities
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional
import time


class LiveMonitor:
    """Real-time monitoring and control for agent execution"""

    def __init__(self):
        if 'monitor_state' not in st.session_state:
            st.session_state.monitor_state = {
                'current_agent': None,
                'progress': 0,
                'status': 'idle',
                'logs': [],
                'override_requested': False,
                'pause_requested': False,
                'abort_requested': False,
                'paper_trades': [],
                'decisions': {}
            }

    def start_analysis(self, ticker: str):
        """Start monitoring a new analysis"""
        st.session_state.monitor_state = {
            'ticker': ticker,
            'started_at': datetime.now().isoformat(),
            'current_agent': 'Initialization',
            'progress': 0,
            'status': 'running',
            'logs': [f"[{datetime.now().strftime('%H:%M:%S')}] Starting analysis for {ticker}"],
            'override_requested': False,
            'pause_requested': False,
            'abort_requested': False,
            'paper_trades': [],
            'decisions': {},
            'tool_calls': [],
            'agent_timeline': []
        }

    def log(self, message: str, level: str = "info"):
        """Add log message"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        icon = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(level, "ℹ️")
        log_entry = f"[{timestamp}] {icon} {message}"
        st.session_state.monitor_state['logs'].append(log_entry)

    def update_agent(self, agent_name: str):
        """Update current agent"""
        st.session_state.monitor_state['current_agent'] = agent_name
        st.session_state.monitor_state['agent_timeline'].append({
            'agent': agent_name,
            'timestamp': datetime.now().isoformat(),
            'status': 'active'
        })
        self.log(f"Agent activated: {agent_name}", "info")

    def update_progress(self, progress: int):
        """Update progress (0-100)"""
        st.session_state.monitor_state['progress'] = progress

    def add_tool_call(self, tool_name: str, args: Dict):
        """Log tool call"""
        st.session_state.monitor_state['tool_calls'].append({
            'timestamp': datetime.now().isoformat(),
            'tool': tool_name,
            'args': args
        })
        self.log(f"Tool called: {tool_name}", "info")

    def add_paper_trade(self, trade: Dict):
        """Add paper trade to monitor"""
        trade['timestamp'] = datetime.now().isoformat()
        st.session_state.monitor_state['paper_trades'].append(trade)
        self.log(f"Paper trade: {trade['action']} {trade['quantity']} {trade['ticker']} @ ${trade['price']:.2f}", "success")

    def save_decision(self, agent: str, decision: str):
        """Save agent decision"""
        st.session_state.monitor_state['decisions'][agent] = {
            'decision': decision,
            'timestamp': datetime.now().isoformat()
        }

    def is_override_requested(self) -> bool:
        """Check if override was requested"""
        return st.session_state.monitor_state.get('override_requested', False)

    def is_pause_requested(self) -> bool:
        """Check if pause was requested"""
        return st.session_state.monitor_state.get('pause_requested', False)

    def is_abort_requested(self) -> bool:
        """Check if abort was requested"""
        return st.session_state.monitor_state.get('abort_requested', False)

    def clear_override(self):
        """Clear override flag"""
        st.session_state.monitor_state['override_requested'] = False

    def render_live_console(self):
        """Render the live monitoring console"""
        state = st.session_state.monitor_state

        st.markdown("## 📊 Live Execution Monitor")

        # Control buttons
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("⏸️ Pause", key="btn_pause", disabled=state['status'] != 'running'):
                st.session_state.monitor_state['pause_requested'] = True
                self.log("Pause requested by user", "warning")
                st.rerun()

        with col2:
            if st.button("▶️ Resume", key="btn_resume", disabled=state['status'] == 'running'):
                st.session_state.monitor_state['pause_requested'] = False
                st.session_state.monitor_state['status'] = 'running'
                self.log("Resumed by user", "success")
                st.rerun()

        with col3:
            if st.button("🔧 Override", key="btn_override", type="secondary"):
                st.session_state.monitor_state['override_requested'] = True
                self.log("Override requested - waiting for confirmation", "warning")
                st.rerun()

        with col4:
            if st.button("⛔ Abort", key="btn_abort", type="secondary"):
                st.session_state.monitor_state['abort_requested'] = True
                st.session_state.monitor_state['status'] = 'aborted'
                self.log("Analysis aborted by user", "error")
                st.rerun()

        st.markdown("---")

        # Current status
        col1, col2, col3 = st.columns(3)

        with col1:
            status_color = {
                'running': '🟢',
                'paused': '🟡',
                'completed': '🔵',
                'aborted': '🔴',
                'idle': '⚪'
            }.get(state['status'], '⚪')
            st.metric("Status", f"{status_color} {state['status'].title()}")

        with col2:
            st.metric("Current Agent", state.get('current_agent', 'N/A'))

        with col3:
            st.metric("Progress", f"{state.get('progress', 0)}%")

        # Progress bar
        st.progress(state.get('progress', 0) / 100)

        st.markdown("---")

        # Tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📜 Live Logs",
            "🤖 Agent Timeline",
            "🔧 Tool Calls",
            "💰 Paper Trades",
            "📊 Decisions"
        ])

        with tab1:
            self._render_logs()

        with tab2:
            self._render_timeline()

        with tab3:
            self._render_tool_calls()

        with tab4:
            self._render_paper_trades()

        with tab5:
            self._render_decisions()

        # Override modal
        if state.get('override_requested'):
            self._render_override_modal()

    def _render_logs(self):
        """Render live logs"""
        st.markdown("### 📜 Execution Logs (Real-time)")

        logs = st.session_state.monitor_state.get('logs', [])

        # Create scrollable log container
        log_container = st.container()

        with log_container:
            # Show last 50 logs
            for log in logs[-50:]:
                st.text(log)

        # Auto-scroll indicator
        if len(logs) > 50:
            st.caption(f"Showing last 50 of {len(logs)} logs")

    def _render_timeline(self):
        """Render agent timeline"""
        st.markdown("### 🤖 Agent Execution Timeline")

        timeline = st.session_state.monitor_state.get('agent_timeline', [])

        if timeline:
            import pandas as pd

            df = pd.DataFrame(timeline)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['time'] = df['timestamp'].dt.strftime('%H:%M:%S')

            st.dataframe(
                df[['time', 'agent', 'status']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No agents executed yet")

    def _render_tool_calls(self):
        """Render tool calls"""
        st.markdown("### 🔧 Tool Calls")

        tool_calls = st.session_state.monitor_state.get('tool_calls', [])

        if tool_calls:
            for i, call in enumerate(tool_calls[-20:]):  # Last 20
                with st.expander(f"🔧 {call['tool']} - {call['timestamp'][:19]}"):
                    st.json(call['args'])
        else:
            st.info("No tool calls yet")

    def _render_paper_trades(self):
        """Render paper trades"""
        st.markdown("### 💰 Paper Trades (Simulated)")

        trades = st.session_state.monitor_state.get('paper_trades', [])

        if trades:
            import pandas as pd

            df = pd.DataFrame(trades)

            # Calculate P/L if possible
            if 'current_price' in df.columns:
                df['pnl'] = (df['current_price'] - df['price']) * df['quantity']
                df['pnl%'] = ((df['current_price'] / df['price']) - 1) * 100

            st.dataframe(df, use_container_width=True, hide_index=True)

            # Summary
            total_value = (df['quantity'] * df['price']).sum()
            st.metric("Total Trade Value", f"${total_value:,.2f}")
        else:
            st.info("No paper trades yet")

    def _render_decisions(self):
        """Render agent decisions"""
        st.markdown("### 📊 Agent Decisions")

        decisions = st.session_state.monitor_state.get('decisions', {})

        if decisions:
            for agent, decision_data in decisions.items():
                with st.expander(f"🤖 {agent}"):
                    st.markdown(f"**Decision Time:** {decision_data['timestamp'][:19]}")
                    st.markdown("**Decision:**")
                    st.markdown(decision_data['decision'])
        else:
            st.info("No decisions made yet")

    def _render_override_modal(self):
        """Render override decision modal"""
        st.markdown("---")
        st.markdown("## 🔧 Manual Override")

        st.warning("⚠️ You have requested to override the agent's decision. Choose your action:")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("✅ Force BUY", type="primary", use_container_width=True):
                st.session_state.monitor_state['manual_decision'] = 'BUY'
                st.session_state.monitor_state['override_requested'] = False
                self.log("Manual override: FORCE BUY", "warning")
                st.success("Override applied: BUY")
                st.rerun()

        with col2:
            if st.button("❌ Force SELL", type="primary", use_container_width=True):
                st.session_state.monitor_state['manual_decision'] = 'SELL'
                st.session_state.monitor_state['override_requested'] = False
                self.log("Manual override: FORCE SELL", "warning")
                st.success("Override applied: SELL")
                st.rerun()

        with col3:
            if st.button("⏸️ Force HOLD", use_container_width=True):
                st.session_state.monitor_state['manual_decision'] = 'HOLD'
                st.session_state.monitor_state['override_requested'] = False
                self.log("Manual override: FORCE HOLD", "warning")
                st.success("Override applied: HOLD")
                st.rerun()

        st.markdown("---")

        # Custom decision
        with st.expander("📝 Custom Instructions"):
            custom_instruction = st.text_area(
                "Enter custom instructions for the agent",
                placeholder="e.g., 'Only buy if P/E ratio is below 20'"
            )

            if st.button("Apply Custom Instructions", use_container_width=True):
                st.session_state.monitor_state['custom_instruction'] = custom_instruction
                st.session_state.monitor_state['override_requested'] = False
                self.log(f"Custom instruction applied: {custom_instruction}", "warning")
                st.success("Custom instructions applied")
                st.rerun()

        # Cancel override
        if st.button("↩️ Cancel Override", use_container_width=True):
            st.session_state.monitor_state['override_requested'] = False
            self.log("Override cancelled", "info")
            st.rerun()


# Singleton instance
_monitor = None

def get_monitor() -> LiveMonitor:
    """Get or create monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = LiveMonitor()
    return _monitor
