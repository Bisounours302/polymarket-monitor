from database import init_db, get_session, Alert
from datetime import datetime
import uuid

# Initialize DB connection
init_db()
session = get_session()

print("Seeding dummy alert...")

# Create Dummy Alert
dummy_alert = Alert(
    market_name="Test Market - Will BTC hit 100k?",
    amount_usd=1337.00,
    wallet_address="0x1234567890abcdef1234567890abcdef12345678",
    nonce=5,
    polymarket_url="https://polymarket.com",
    tx_hash=str(uuid.uuid4()),
    timestamp=datetime.utcnow()
)

session.add(dummy_alert)
session.commit()
session.close()

print("Dummy alert inserted successfully! Check the dashboard.")
