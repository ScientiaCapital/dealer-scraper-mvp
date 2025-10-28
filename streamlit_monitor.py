#!/usr/bin/env python3
"""
Real-time Scraping Monitor Dashboard
Launch with: streamlit run streamlit_monitor.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import glob
import json
import time
from datetime import datetime
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Coperniq Dealer Scraper Monitor",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .success { border-left-color: #2ca02c; }
    .warning { border-left-color: #ff7f0e; }
    .danger { border-left-color: #d62728; }
</style>
""", unsafe_allow_html=True)

def load_log_file(filepath):
    """Load and parse log file"""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except:
        return ""

def parse_progress(log_content):
    """Extract progress from log"""
    lines = log_content.split('\n')

    # Find current ZIP being scraped
    current_zip = None
    total_zips = 137
    completed = 0
    dealers_collected = 0

    for line in lines:
        if '[' in line and '/' in line and 'Scraping ZIP' in line:
            try:
                # Extract "[X/137]"
                bracket_content = line.split('[')[1].split(']')[0]
                completed = int(bracket_content.split('/')[0])
            except:
                pass

        if 'Found' in line and 'dealers' in line and 'Total:' in line:
            try:
                # Extract "Total: X"
                total_str = line.split('Total:')[1].strip().rstrip(')')
                dealers_collected = int(total_str)
            except:
                pass

    return {
        'completed_zips': completed,
        'total_zips': total_zips,
        'progress_pct': (completed / total_zips * 100) if total_zips > 0 else 0,
        'dealers_collected': dealers_collected
    }

def load_checkpoint_data(pattern):
    """Load latest checkpoint file"""
    files = glob.glob(f"output/{pattern}")
    if not files:
        return None

    latest = max(files)
    try:
        with open(latest, 'r') as f:
            return json.load(f)
    except:
        return None

def main():
    # Header
    st.title("🏗️ Coperniq Dealer Scraper - Live Monitor")
    st.markdown("---")

    # Sidebar
    st.sidebar.header("⚙️ Controls")
    auto_refresh = st.sidebar.checkbox("Auto-refresh (5s)", value=True)

    if auto_refresh:
        time.sleep(5)
        st.rerun()

    # Manual refresh
    if st.sidebar.button("🔄 Refresh Now"):
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 📊 Dashboard Info
    - **Auto-refresh**: Updates every 5 seconds
    - **Data source**: Log files & checkpoints
    - **Geographic coverage**: All 50 US states
    """)

    # Main dashboard
    col1, col2, col3 = st.columns(3)

    # Cummins Status
    with col1:
        st.subheader("🔧 Cummins RS")
        cummins_log = load_log_file("output/cummins_national.log")
        if cummins_log:
            cummins_stats = parse_progress(cummins_log)
            st.metric("Progress", f"{cummins_stats['progress_pct']:.1f}%")
            st.metric("ZIPs Completed", f"{cummins_stats['completed_zips']}/137")
            st.metric("Dealers Collected", f"{cummins_stats['dealers_collected']:,}")

            # Progress bar
            progress = cummins_stats['completed_zips'] / 137
            st.progress(progress)

            if cummins_stats['completed_zips'] >= 137:
                st.success("✅ COMPLETE")
            else:
                st.info(f"🔄 Running...")
        else:
            st.warning("⏳ Not started")

    # Briggs Status
    with col2:
        st.subheader("🔩 Briggs & Stratton")
        briggs_log = load_log_file("output/briggs_national.log")
        if briggs_log:
            briggs_stats = parse_progress(briggs_log)
            st.metric("Progress", f"{briggs_stats['progress_pct']:.1f}%")
            st.metric("ZIPs Completed", f"{briggs_stats['completed_zips']}/137")
            st.metric("Dealers Collected", f"{briggs_stats['dealers_collected']:,}")

            # Progress bar
            progress = briggs_stats['completed_zips'] / 137
            st.progress(progress)

            if briggs_stats['completed_zips'] >= 137:
                st.success("✅ COMPLETE")
            else:
                st.info(f"🔄 Running...")
        else:
            st.warning("⏳ Not started")

    # Generac Status
    with col3:
        st.subheader("⚡ Generac")
        generac_log = load_log_file("output/generac_national.log")
        if generac_log:
            generac_stats = parse_progress(generac_log)
            st.metric("Progress", f"{generac_stats['progress_pct']:.1f}%")
            st.metric("ZIPs Completed", f"{generac_stats['completed_zips']}/137")
            st.metric("Dealers Collected", f"{generac_stats['dealers_collected']:,}")

            # Progress bar
            progress = generac_stats['completed_zips'] / 137
            st.progress(progress)

            if generac_stats['completed_zips'] >= 137:
                st.success("✅ COMPLETE")
            else:
                st.info(f"🔄 Running...")
        else:
            st.warning("⏳ Not started")

    st.markdown("---")

    # Performance charts
    st.header("📈 Performance Analytics")

    col1, col2 = st.columns(2)

    with col1:
        # Dealers per OEM (from checkpoints)
        st.subheader("Dealers Collected by OEM")

        oem_data = {
            'OEM': [],
            'Dealers': []
        }

        # Check Cummins
        if cummins_log:
            cummins_stats = parse_progress(cummins_log)
            oem_data['OEM'].append('Cummins')
            oem_data['Dealers'].append(cummins_stats['dealers_collected'])

        # Check Briggs
        if briggs_log:
            briggs_stats = parse_progress(briggs_log)
            oem_data['OEM'].append('Briggs')
            oem_data['Dealers'].append(briggs_stats['dealers_collected'])

        # Check Generac
        if generac_log:
            generac_stats = parse_progress(generac_log)
            oem_data['OEM'].append('Generac')
            oem_data['Dealers'].append(generac_stats['dealers_collected'])

        if oem_data['OEM']:
            df = pd.DataFrame(oem_data)
            fig = px.bar(df, x='OEM', y='Dealers', color='OEM',
                        title="Dealer Collection by OEM")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available yet")

    with col2:
        # Progress comparison
        st.subheader("Scraping Progress Comparison")

        progress_data = {
            'OEM': [],
            'Progress %': []
        }

        if cummins_log:
            cummins_stats = parse_progress(cummins_log)
            progress_data['OEM'].append('Cummins')
            progress_data['Progress %'].append(cummins_stats['progress_pct'])

        if briggs_log:
            briggs_stats = parse_progress(briggs_log)
            progress_data['OEM'].append('Briggs')
            progress_data['Progress %'].append(briggs_stats['progress_pct'])

        if generac_log:
            generac_stats = parse_progress(generac_log)
            progress_data['OEM'].append('Generac')
            progress_data['Progress %'].append(generac_stats['progress_pct'])

        if progress_data['OEM']:
            df = pd.DataFrame(progress_data)
            fig = px.bar(df, x='OEM', y='Progress %', color='OEM',
                        title="Progress by OEM (%)",
                        range_y=[0, 100])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available yet")

    # Recent logs
    st.markdown("---")
    st.header("📜 Recent Activity")

    tab1, tab2, tab3 = st.tabs(["Cummins", "Briggs", "Generac"])

    with tab1:
        if cummins_log:
            recent_lines = cummins_log.split('\n')[-30:]
            st.code('\n'.join(recent_lines), language='bash')
        else:
            st.info("No log data available")

    with tab2:
        if briggs_log:
            recent_lines = briggs_log.split('\n')[-30:]
            st.code('\n'.join(recent_lines), language='bash')
        else:
            st.info("No log data available")

    with tab3:
        if generac_log:
            recent_lines = generac_log.split('\n')[-30:]
            st.code('\n'.join(recent_lines), language='bash')
        else:
            st.info("No log data available")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>🏗️ Coperniq Partner Prospecting System • Real-time Scraping Monitor</p>
        <p>Built with Streamlit • Auto-refreshing every 5 seconds</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
