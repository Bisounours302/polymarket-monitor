import os
import time
import logging
from datetime import datetime
from web3 import Web3
from web3.middleware import geth_poa_middleware
from dotenv import load_dotenv
from database import init_db, get_session, Alert, GlobalSettings
from notifications import send_telegram_alert
from polymarket import fetch_markets, fetch_trades_graphql

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POLYGON_RPC_URL = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
# LOWER THRESHOLD FOR DEBUGGING
MIN_USD_THRESHOLD = float(os.getenv("MIN_USD_THRESHOLD", 10)) 
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
        if not wallet_address:
            return None
        checksum_address = Web3.to_checksum_address(wallet_address)
        nonce = w3.eth.get_transaction_count(checksum_address)
        return nonce
    except Exception as e:
        logger.error(f"Error fetching nonce for {wallet_address}: {e}")
        return None

def main():
    logger.info("Starting Polymarket Public Monitor (Read-Only)...")
    
    processed_hashes = set()
    
    while True:
        try:
            session = get_session()
            # Check System Status
            system_setting = session.query(GlobalSettings).filter_by(key="system_active").first()
            if system_setting and system_setting.value.lower() == "false":
                logger.info("System paused. Sleeping...")
                session.close()
                time.sleep(10)
                continue

            markets = fetch_markets()
            
            # Save latest state for Debug Inspector (Atomic Write)
            try:
                debug_path = "/app/data/debug_markets.json"
                # If running locally (not in docker), adjust path
                if not os.path.exists("/app/data"):
                    debug_path = "data/debug_markets.json"
                    os.makedirs(os.path.dirname(debug_path), exist_ok=True)
                
                # Write to temp file first to prevent partial reads
                temp_path = debug_path + ".tmp"
                with open(temp_path, "w") as f:
                    json.dump(markets, f, indent=2)
                    
                # Atomic swap
                os.replace(temp_path, debug_path)
            except Exception as e:
                logger.error(f"Failed to save debug cache: {e}")
            
            logger.info(f"Scanning {len(markets)} active markets...")
            
            for market in markets:
                # STRATEGY CHANGE: Use Hex(ClobTokenID) 
                # Condition ID proved unreliable for Graph queries on this subgraph.
                # We prioritize the first Token ID converted to Hex.
                
                market_id = None
                clob_ids = market.get("clobTokenIds", [])
                
                if clob_ids and len(clob_ids) > 0:
                    try:
                        # Convert Decimal String -> Int -> Hex String
                        # e.g. "9359..." -> 0x19ee...
                        first_id = clob_ids[0]
                        if isinstance(first_id, str):
                           id_val = int(first_id)
                        else:
                           id_val = int(first_id)
                           
                        market_id = hex(id_val)
                    except Exception as e:
                        logger.warning(f"Failed to convert token ID to hex: {e}")
                        market_id = market.get("conditionId")
                else:
                    market_id = market.get("conditionId")

                market_slug = market.get("slug", "unknown")
                market_name = market.get("question", "Unknown Market")
                
                if not market_id:
                    continue
                
                # Fetch trades from The Graph
                trades = fetch_trades_graphql(market_id)
                
                if trades:
                    logger.debug(f"Market {market_name[:20]}: {len(trades)} trades fetched.")
                
                for trade in trades:
                    # Parse Graph Data
                    try:
                        amount_usd = float(trade.get('tradeAmount', 0))
                        timestamp = int(trade.get('timestamp', 0))
                        wallet_address = trade.get('user', {}).get('id')
                        tx_id = trade.get('id')
                        
                        # Filter by Volume
                        if amount_usd < MIN_USD_THRESHOLD:
                            continue
                        
                        # Deduplication
                        if tx_id in processed_hashes:
                            continue
                        processed_hashes.add(tx_id)
                        
                        # Log Candidate
                        logger.info(f"Large Trade Found: ${amount_usd:,.2f} on {market_name}")

                        # Check Wallet Nonce
                        nonce = get_nonce(wallet_address)
                        is_suspicious = False
                        if nonce is not None:
                            is_suspicious = nonce < MAX_NONCE_THRESHOLD
                        
                        alert_type = "SUSPICIOUS" if is_suspicious else "WHALE"
                        
                        polymarket_url = f"https://polymarket.com/event/{market_slug}"
                        
                        # Save to DB
                        new_alert = Alert(
                            market_name=market_name,
                            amount_usd=amount_usd,
                            wallet_address=wallet_address,
                            nonce=nonce if nonce is not None else -1,
                            polymarket_url=polymarket_url,
                            tx_hash=str(tx_id),
                            timestamp=datetime.fromtimestamp(timestamp)
                        )
                        session.add(new_alert)
                        session.commit()
                        
                        # Check Notification Settings
                        try:
                            whales_setting = session.query(GlobalSettings).filter_by(key="notify_whales").first()
                            susp_setting = session.query(GlobalSettings).filter_by(key="notify_suspicious").first()
                            
                            notify_whales = whales_setting.value.lower() == "true" if whales_setting else True
                            notify_susp = susp_setting.value.lower() == "true" if susp_setting else True
                        except:
                            notify_whales = True
                            notify_susp = True

                        alert_data = {
                            "amount_usd": amount_usd,
                            "market_name": market_name,
                            "wallet_address": wallet_address,
                            "nonce": nonce,
                            "polymarket_url": polymarket_url,
                            "timestamp": datetime.fromtimestamp(timestamp),
                            "alert_type": alert_type,
                            "config": {
                                "notify_whales": notify_whales,
                                "notify_suspicious": notify_susp
                            }
                        }
                        send_telegram_alert(alert_data)

                    except Exception as e:
                        logger.error(f"Error processing trade: {e}")
                        continue
            
            session.close()
            logger.info("Cycle complete. Sleeping for 30s...")
            time.sleep(30)

        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
