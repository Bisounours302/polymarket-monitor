import streamlit as st
import pandas as pd
import time
from sqlalchemy.orm import sessionmaker
from database import get_engine, Alert, GlobalSettings

st.set_page_config(
    page_title="Polymarket Monitor",
    layout="wide"
)

# Database Connection
engine = get_engine()
Session = sessionmaker(bind=engine)

def get_session():
    return Session()

def load_data():
    session = get_session()
    try:
        query = session.query(Alert).statement
        df = pd.read_sql(query, session.bind)
        return df
    finally:
        session.close()

def load_settings():
    session = get_session()
    try:
        whales = session.query(GlobalSettings).filter_by(key="notify_whales").first()
        suspicious = session.query(GlobalSettings).filter_by(key="notify_suspicious").first()
        return {
            "notify_whales": whales.value == "true" if whales else True,
            "notify_suspicious": suspicious.value == "true" if suspicious else True
        }
    except Exception:
        return {"notify_whales": True, "notify_suspicious": True}
    finally:
        session.close()

def save_setting(key, value):
    session = get_session()
    try:
        setting = session.query(GlobalSettings).filter_by(key=key).first()
        if not setting:
            setting = GlobalSettings(key=key)
            session.add(setting)
        setting.value = "true" if value else "false"
        session.commit()
    except Exception as e:
        st.error(f"Error saving setting: {e}")
    finally:
        session.close()

# Sidebar: Settings & Tools
st.sidebar.title("Configuration")

st.sidebar.subheader("Notifications")
current_settings = load_settings()

notify_whales = st.sidebar.checkbox(
    "Notify on WHALES (> $5k)", 
    value=current_settings["notify_whales"]
)
if notify_whales != current_settings["notify_whales"]:
    save_setting("notify_whales", notify_whales)
    st.sidebar.success("Updated!")
    time.sleep(1)
    st.rerun()

notify_suspicious = st.sidebar.checkbox(
    "Notify on INSIDERS (Fresh Wallet)", 
    value=current_settings["notify_suspicious"]
)
if notify_suspicious != current_settings["notify_suspicious"]:
    save_setting("notify_suspicious", notify_suspicious)
    st.sidebar.success("Updated!")
    time.sleep(1)
    st.rerun()

st.sidebar.markdown("---")
# Auto refresh default TRUE as requested
auto_refresh = st.sidebar.checkbox("Auto Refresh (30s)", value=True)

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
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    today_df = df[df['timestamp'].dt.date == pd.Timestamp.now().date()]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Alerts", len(df))
    col2.metric("Volume Today", f"${today_df['amount_usd'].sum():,.2f}")
    col3.metric("Max Trade", f"${df['amount_usd'].max():,.2f}")

    st.markdown("---")

    # Filters
    col_filter1, col_filter2 = st.columns([1, 4])
    with col_filter1:
        view_mode = st.radio("View Mode", ["All Trades", "Suspicious Only (Nonce < 10)"])
    
    # Data View
    column_config = {
        "polymarket_url": st.column_config.LinkColumn("Market Link"),
        "amount_usd": st.column_config.NumberColumn("Amount (USD)", format="$%.2f"),
        "timestamp": st.column_config.DatetimeColumn("Time", format="D MMM YYYY, h:mm a"),
        "nonce": st.column_config.NumberColumn("Nonce", help="Transaction count using Polygon RPC")
    }

    if view_mode == "Suspicious Only (Nonce < 10)":
        display_df = df[df['nonce'] < 10]
        st.subheader("Potential Insider Activity")
    else:
        display_df = df
        st.subheader("All High Volume Trades")

    st.dataframe(
        display_df.sort_values(by="timestamp", ascending=False),
        column_config=column_config,
        use_container_width=True,
        hide_index=True
    )
    
else:
    st.info("No data detected yet. Worker is scanning...")

# API Inspector Section
st.markdown("---")
with st.expander("🛠️ API Debug Inspector (Raw Data)"):
    st.write("Check what the bot sees directly from the APIs.")
    
    if st.button("Fetch Active Markets (Gamma API)"):
        with st.spinner("Fetching markets..."):
            try:
                # Import here to avoid circular or startup issues
                from monitor import fetch_markets, fetch_trades_graphql
                
                markets = fetch_markets()
                st.write(f"Found {len(markets)} active markets.")
                st.dataframe(pd.DataFrame(markets)[['slug', 'question', 'volume', 'clobTokenIds']])
                
                if markets:
                    sample_market = markets[0]
                    clob_id = sample_market.get("clobTokenIds", [None])[0]
                    st.write(f"Testing Trades for Top Market: **{sample_market['question']}**")
                    trades = fetch_trades_graphql(clob_id)
                    st.write(f"Found {len(trades)} recent trades (The Graph).")
                    st.json(trades)
                    
            except Exception as e:
                st.error(f"Error fetching API: {e}")
