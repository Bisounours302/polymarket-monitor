import os
import time
import requests
import logging
import json
from datetime import datetime
from web3 import Web3
from web3.middleware import geth_poa_middleware
from dotenv import load_dotenv
from database import init_db, get_session, Alert, GlobalSettings

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POLYGON_RPC_URL = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
MIN_USD_THRESHOLD = float(os.getenv("MIN_USD_THRESHOLD", 5000))
MAX_NONCE_THRESHOLD = int(os.getenv("MAX_NONCE_THRESHOLD", 10))

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Web3
try:
    w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    if w3.is_connected():
        logger.info(f"Connected to Polygon RPC: {POLYGON_RPC_URL}")
    else:
        logger.error(f"Failed to connect to Polygon RPC: {POLYGON_RPC_URL}")
except Exception as e:
    logger.error(f"Error initializing Web3: {e}")

# Database Initialization
init_db()

def get_nonce(wallet_address):
    """Fetch transaction count (nonce) for a wallet."""
    try:
        checksum_address = Web3.to_checksum_address(wallet_address)
        nonce = w3.eth.get_transaction_count(checksum_address)
        return nonce
    except Exception as e:
        logger.error(f"Error fetching nonce for {wallet_address}: {e}")
        return None

from notifications import send_telegram_alert

def fetch_markets():
    """Fetch top active markets by volume from Gamma API."""
    try:
        url = "https://gamma-api.polymarket.com/markets?limit=20&active=true&closed=false&order=volume:desc"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        return []

def fetch_trades(clob_id):
    """Fetch recent trades for a specific market from CLOB API."""
    try:
        # CLOB API Public Endpoint for Trades
        url = f"https://clob.polymarket.com/trades?market={clob_id}&limit=10"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"Error fetching trades for {clob_id}: {e}")
        return []

def main():
    logger.info("Starting Polymarket Insider Monitor...")
    
    # Cache processed trades to verify deduplication
    # In production, you might want to load recent tx_hashes from DB on startup
    processed_hashes = set()
    
    while True:
        try:
            session = get_session()
            markets = fetch_markets()
            
            # DEBUG LOGGING
            logger.info(f"Fetched {len(markets)} markets from Gamma.")
            
            for market in markets:
                clob_id = market.get("clobTokenIds", [None])[0]
                market_slug = market.get("slug", "unknown")
                market_name = market.get("question", "Unknown Market")
                
                if not clob_id:
                    continue
                
                trades = fetch_trades(clob_id)
                # DEBUG LOGGING
                if trades:
                    logger.info(f"Market {market_name[:20]}...: {len(trades)} trades fetched.")
                
                for trade in trades:
                    # Trade structure validation
                    # CLOB trade object: {'price': '0.55', 'size': '100', 'side': 'BUY', ... 'transaction_hash': '...'}
                    # Note: 'transaction_hash' might be inside a 'match' object or top level depending on endpoint version.
                    # We assume standard fields.
                    
                    # Important: Check keys carefully based on response.
                    # Standard CLOB response list of dicts.
                    
                    price = float(trade.get('price', 0))
                    size = float(trade.get('size', 0))
                    amount_usd = price * size
                    
                    # Filter Level 1: Volume
                    if amount_usd < MIN_USD_THRESHOLD:
                        # logger.debug(f"Skipping small trade: ${amount_usd}")
                        continue
                        
                    logger.info(f"Candidate Trade Found: ${amount_usd} on {market_name}")
                        
                    tx_hash = trade.get('transactionHash') or trade.get('hash') or f"{trade.get('timestamp')}-{size}"
                    
                    if tx_hash in processed_hashes:
                        continue
                        
                    processed_hashes.add(tx_hash)
                    
                    # Filter Level 2: Analysis
                    # Taker address is usually what we care about for "who initiated"
                    wallet_address = trade.get('taker') or trade.get('maker_address') # Simplified
                    
                    if not wallet_address:
                        continue
                    
                    # Check Nonce
                    nonce = get_nonce(wallet_address)
                    
                    if nonce is not None:
                        is_suspicious = nonce < MAX_NONCE_THRESHOLD
                        alert_type = "SUSPICIOUS" if is_suspicious else "WHALE"
                        
                        # Log detection
                        logger.info(f"[{alert_type}] {amount_usd} USD by {wallet_address} (Nonce: {nonce})")
                        
                        polymarket_url = f"https://polymarket.com/event/{market_slug}"
                        
                        # Save to DB (We save ALL large trades now)
                        new_alert = Alert(
                            market_name=market_name,
                            amount_usd=amount_usd,
                            wallet_address=wallet_address,
                            nonce=nonce,
                            polymarket_url=polymarket_url,
                            tx_hash=str(tx_hash)
                        )
                        session.add(new_alert)
                        session.commit()
                        
                        # Send Telegram (filtering handled here or in notifications, but better to pass config)
                        # Fetch latest settings
                        try:
                            whales_setting = session.query(GlobalSettings).filter_by(key="notify_whales").first()
                            suspicious_setting = session.query(GlobalSettings).filter_by(key="notify_suspicious").first()
                            
                            notify_whales = whales_setting.value.lower() == "true" if whales_setting else True
                            notify_suspicious = suspicious_setting.value.lower() == "true" if suspicious_setting else True
                        except:
                            notify_whales = True
                            notify_suspicious = True

                        alert_data = {
                            "amount_usd": amount_usd,
                            "market_name": market_name,
                            "wallet_address": wallet_address,
                            "nonce": nonce,
                            "polymarket_url": polymarket_url,
                            "timestamp": datetime.now(),
                            "alert_type": alert_type,
                            "config": {
                                "notify_whales": notify_whales,
                                "notify_suspicious": notify_suspicious
                            }
                        }
                        send_telegram_alert(alert_data)
            
            session.close()
            # Wait before next cycle
            logger.info("Cycle complete. Sleeping for 30s...")
            time.sleep(30)

        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
