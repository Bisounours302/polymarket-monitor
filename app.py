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
st.title("Polymarket Monitor")
st.markdown("Real-time tracking of high-value trades and potential insider activity.")

# Metrics
df = load_data()

if not df.empty:
    # Pre-process
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    max_nonce_threshold = 10 # Should match env but hardcoded for UI logic convenience or loaded from somewhere
    
    today_df = df[df['timestamp'].dt.date == pd.Timestamp.now().date()]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Alerts", len(df))
    col2.metric("Volume Today", f"${today_df['amount_usd'].sum():,.2f}")
    col3.metric("Max Trade", f"${df['amount_usd'].max():,.2f}")

    st.markdown("---")

    # Tabs
    tab_all, tab_suspicious = st.tabs(["All Large Trades", "Suspicious (New Wallets)"])

    column_config = {
        "polymarket_url": st.column_config.LinkColumn("Market Link"),
        "amount_usd": st.column_config.NumberColumn("Amount (USD)", format="$%.2f"),
        "timestamp": st.column_config.DatetimeColumn("Time", format="D MMM YYYY, h:mm a"),
        "nonce": st.column_config.NumberColumn("Nonce", help="Transaction count. <10 implies new wallet.")
    }

    with tab_all:
        st.subheader("High Volume Trades")
        st.dataframe(
            df.sort_values(by="timestamp", ascending=False),
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )

    with tab_suspicious:
        st.subheader("Potential Insider Activity (Nonce < 10)")
        suspicious_df = df[df['nonce'] < 10].sort_values(by="timestamp", ascending=False)
        st.dataframe(
            suspicious_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )
    
else:
    st.info("No data detected yet. Waiting for worker...")

# Footer
st.markdown("---")
st.caption("Powered by Gamma API & Web3.py")
