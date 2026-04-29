import streamlit as st
import sqlite3
import pandas as pd
import json
import plotly.express as px
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Negotiation Research Command",
    page_icon="",
    layout="wide"
)

st.title("Autonomous Negotiation Agent (Live View)")

# --- DATABASE CONNECTION ---
def get_data(query):
    conn = sqlite3.connect("research_study.db")
    try:
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        # If table doesn't exist yet, return empty
        return pd.DataFrame()
    finally:
        conn.close()

# --- 1. MISSION CONTROL METRICS ---
st.markdown("### Mission Control Metrics")

# Create 5 distinct columns
col1, col2, col3, col4, col5 = st.columns(5)

# Fetch Data
# 1. Total Volume
total_leads = get_data("SELECT COUNT(*) as c FROM leads").iloc[0]['c']

# 2. Active Interactions
active_chats = get_data("SELECT COUNT(*) as c FROM leads WHERE status NOT IN ('INIT', 'CLOSED')").iloc[0]['c']

# 3. Potential Savings
savings_df = get_data("""
    SELECT SUM(scraped_price - json_extract(state_json, '$.car.target_price')) as saved
    FROM leads WHERE status = 'NEGOTIATING'
""")
savings = savings_df.iloc[0]['saved'] if not savings_df.empty and savings_df.iloc[0]['saved'] else 0

# 4. Market Velocity (Avg Response Time)
# We calculate hours elapsed between creation and last update for active deals
time_df = get_data("""
    SELECT AVG((julianday(updated_at) - julianday(created_at)) * 24) as avg_hours
    FROM leads WHERE status != 'INIT'
""")
avg_time = time_df.iloc[0]['avg_hours'] if not time_df.empty and time_df.iloc[0]['avg_hours'] else 0.0

# Render Metrics
col1.metric("Total Cars", total_leads)
col2.metric("Active Negotiations", active_chats)
col3.metric("Potential Savings", f"{int(savings):,} DH")
col4.metric("Avg Response Time", f"{avg_time:.2f} Hours") # <--- This is the missing one
col5.metric("System Status", "ONLINE", delta_color="normal")

st.markdown("---")

# --- 2. RESEARCH DATA (A/B TESTING) ---
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Strategy Performance")
    ab_query = """
        SELECT 
            strategy_group, 
            COUNT(*) as total,
            SUM(CASE WHEN status='NEGOTIATING' THEN 1 ELSE 0 END) as success
        FROM leads 
        GROUP BY strategy_group
    """
    ab_df = get_data(ab_query)
    
    if not ab_df.empty:
        ab_df['Conversion Rate (%)'] = (ab_df['success'] / ab_df['total']) * 100
        fig = px.bar(ab_df, x='strategy_group', y='Conversion Rate (%)', 
                     color='strategy_group', title="Response Rate by Strategy (Casual vs Formal)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Awaiting Research Data...")

with col_right:
    st.subheader("Market Prices")
    price_df = get_data("SELECT scraped_price FROM leads WHERE scraped_price > 1000")
    if not price_df.empty:
        fig2 = px.histogram(price_df, x="scraped_price", nbins=15, title="Listing Price Distribution")
        st.plotly_chart(fig2, use_container_width=True)

# --- 3. LIVE TERMINAL ---
st.subheader("Live Neural Feed (Last 5)")
feed_df = get_data("SELECT * FROM leads ORDER BY updated_at DESC LIMIT 5")

if not feed_df.empty:
    for index, row in feed_df.iterrows():
        try:
            state = json.loads(row['state_json'])
            msgs = state.get('messages', [])
            
            with st.expander(f"{row['model_name']} ({row['phone']}) - {row['status']}"):
                for m in msgs[-3:]: 
                    if m.startswith("AI:"):
                        st.caption(f"{m}")
                    else:
                        st.markdown(f"**{m}**")
        except:
            pass
else:
    st.write("No live data yet.")

# --- 4. AUTO-REFRESH LOGIC (MOVED TO BOTTOM) ---
# This is the fix. We render everything FIRST, then wait.
st.markdown("---")
if st.checkbox("Enable Live Auto-Refresh (5s)", value=False):
    time.sleep(5) # Wait 5 seconds
    st.rerun()    # Then restart the script
