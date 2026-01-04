import streamlit as st
import pandas as pd
import time
from sqlalchemy.orm import sessionmaker
from database import get_engine, Alert

st.set_page_config(
    page_title="Polymarket Insider Monitor",
    page_icon="🕵️",
    layout="wide"
)

# Database Connection
engine = get_engine()
Session = sessionmaker(bind=engine)

def load_data():
    session = Session()
    try:
        query = session.query(Alert).statement
        df = pd.read_sql(query, session.bind)
        return df
    finally:
        session.close()

# Sidebar
st.sidebar.title("Configuration")
auto_refresh = st.sidebar.checkbox("Auto Refresh (30s)", value=False)

if auto_refresh:
    time.sleep(30)
    st.rerun()

if st.sidebar.button("Refresh Now"):
    st.rerun()

# Main Content
st.title("🕵️ Polymarket Insider Trading Monitor")
st.markdown("Dashboard for tracking suspicious high-value trades from new wallets.")

# Metrics
df = load_data()

if not df.empty:
    col1, col2, col3 = st.columns(3)
    
    # Metric 1: Total Alerts
    col1.metric("Total Alerts", len(df))
    
    # Metric 2: Today's Volume Detected
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    today_df = df[df['timestamp'].dt.date == pd.Timestamp.now().date()]
    today_vol = today_df['amount_usd'].sum()
    col2.metric("Suspicious Volume (Today)", f"${today_vol:,.2f}")
    
    # Metric 3: Max Single Trade
    max_trade = df['amount_usd'].max()
    col3.metric("Max Single Trade", f"${max_trade:,.2f}")

    # Data Table
    st.subheader("Recent Alerts")
    
    # Sort Options
    sort_col = st.selectbox("Sort by", ["timestamp", "amount_usd", "nonce"], index=0)
    sort_asc = st.checkbox("Ascending", value=False)
    
    df_sorted = df.sort_values(by=sort_col, ascending=sort_asc)
    
    # Display formatted table
    st.dataframe(
        df_sorted[[
            "timestamp", "market_name", "amount_usd", 
            "wallet_address", "nonce", "polymarket_url"
        ]],
        column_config={
            "polymarket_url": st.column_config.LinkColumn("Market Link"),
            "amount_usd": st.column_config.NumberColumn("Amount (USD)", format="$%.2f"),
            "timestamp": st.column_config.DatetimeColumn("Detected At", format="D MMM YYYY, h:mm a")
        },
        use_container_width=True,
        hide_index=True
    )
    
else:
    st.info("No alerts detected yet. Waiting for worker to find suspicious trades...")

# Footer
st.markdown("---")
st.caption("Powered by Gamma API & Web3.py")
