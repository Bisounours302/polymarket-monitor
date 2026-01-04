from database import init_db, get_session, Alert

# Initialize DB connection
init_db()
session = get_session()

print("Removing dummy alert...")

# Delete Dummy Alert by Wallet Address used in add_dummy_alert.py
dummy_wallet = "0x1234567890abcdef1234567890abcdef12345678"

try:
    deleted_count = session.query(Alert).filter(Alert.wallet_address == dummy_wallet).delete()
    session.commit()
    print(f"Successfully removed {deleted_count} dummy alert(s).")
except Exception as e:
    print(f"Error removing alert: {e}")
finally:
    session.close()
