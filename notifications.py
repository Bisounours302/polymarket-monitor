import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(alert_data):
    """
    Send formatted alert to Telegram.
    
    alert_data can be a dict with:
    - amount_usd
    - market_name
    - wallet_address
    - nonce
    - polymarket_url
    - timestamp (datetime obj)
    
    OR for testing, specific fields can be mocked.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not set. Skipping notification.")
        return False

    # Check if this is a test or real alert
    if alert_data.get("is_test"):
        message = (
            f"🧪 **TEST NOTIFICATION** 🧪\n\n"
            f"If you receive this, your Telegram Bot configuration is CORRECT! ✅\n"
            f"Current settings:\n"
            f"- Chat ID: `{TELEGRAM_CHAT_ID}`"
        )
    else:
        timestamp_str = alert_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(alert_data['timestamp'], 'strftime') else str(alert_data['timestamp'])
        
        message = (
            f"🚨 **INSIDER / WHALE ALERT** 🚨\n\n"
            f"💰 **Amount:** ${alert_data.get('amount_usd', 0):,.2f}\n"
            f"📉 **Market:** {alert_data.get('market_name', 'Unknown')}\n"
            f"👤 **Wallet:** `{alert_data.get('wallet_address', 'N/A')}`\n"
            f"🆕 **Nonce:** {alert_data.get('nonce', 0)} (New Account!)\n"
            f"🔗 [View on Polymarket]({alert_data.get('polymarket_url', '#')})\n"
            f"🕒 {timestamp_str}"
        )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Telegram API Error: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False
