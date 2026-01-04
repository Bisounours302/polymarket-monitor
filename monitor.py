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

def fetch_trades_graphql(market_id):
    """
    Fetch recent trades using The Graph protocol (Public & Free).
    This bypasses the need for CLOB API Keys.
    """
    url = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets-7"
    
    # GraphQL Query for recent transactions on a specific market
    query = """
    {
      transactions(first: 5, orderBy: timestamp, orderDirection: desc, where: {market: "%s"}) {
        id
        timestamp
        tradeAmount
        user {
          id
        }
        market {
          id
          question
        }
      }
    }
    """ % market_id.lower()

    try:
        response = requests.post(url, json={'query': query}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "transactions" in data["data"]:
                return data["data"]["transactions"]
        return []
    except Exception as e:
        logger.error(f"Graph API Error: {e}")
        return []

def fetch_trades(clob_id):
    """Wrapper to maintain compatibility, now using GraphQL."""
    # Note: The Graph uses the 'conditionId' or 'marketId' address. 
    # Gamma returns 'clobTokenIds' which are conditionIDs usually.
    return fetch_trades_graphql(clob_id)

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
                    logger.info(f"Market {market_name[:20]}: {len(trades)} trades (Auth).")
                
                for trade in trades:
                    # Parse CLOB Data (Back to standard format)
                    # structure: {'price': '0.55', 'size': '100', 'side': 'BUY', 'timestamp': '...', 'transaction_hash': '...'}
                    
                    try:
                        price = float(trade.get('price', 0))
                        size = float(trade.get('size', 0))
                        amount_usd = price * size
                        side = trade.get('side', 'UNKNOWN')
                        
                        # Filter Level 1: Volume
                        if amount_usd < MIN_USD_THRESHOLD:
                            continue
                            
                        logger.info(f"Candidate Trade: ${amount_usd} ({side}) on {market_name}")
                        
                        tx_hash = trade.get('match_id') or trade.get('transaction_hash') or trade.get('hash')
                        if not tx_hash:
                            # Fallback ID for non-tx trades?
                            tx_hash = f"{trade.get('timestamp')}-{size}-{price}"
                         
                        if tx_hash in processed_hashes:
                            continue
                            
                        processed_hashes.add(tx_hash)
                        
                        # Extract wallet address (maker or taker depending on side? CLOB usually gives 'maker_address' or similar if own trade, but public trade feed is anon?)
                        # WARNING: The public/auth feed for "trades" usually does NOT show the wallet address of the OTHER party unless you are admin.
                        # Actually... The /trades endpoint returns 'maker_address' and 'taker_address'? 
                        # Let's check logic. If no wallet, we can't check Nonce.
                        
                        # If CLOB doesn't return address, we CANNOT check nonce.
                        # Checking Gamma/Graph was better for address. 
                        # Users say CLOB /trades returns public match data.
                        
                        # Let's try to get address.
                        wallet_address = trade.get('maker_address') or trade.get('taker_address') or "0xUnknown"
                        
                        if wallet_address == "0xUnknown":
                            # Use transaction hash to fetch from Web3 log if possible?
                            # For now, let's just Log it as Whale w/o Nonce check if missing.
                            check_nonce = False
                        else:
                            check_nonce = True

                        # Check Nonce
                        nonce = get_nonce(wallet_address) if check_nonce else None
                        
                        # If we can't get nonce, we assume WHALE (not suspicious) or ignore?
                        # User wants "Suspicious = New Wallet".
                        # If no address, we can't verify 'Suspicious'. So alert as WHALE.
                        
                        if nonce is not None:
                             is_suspicious = nonce < MAX_NONCE_THRESHOLD
                        else:
                             is_suspicious = False # Default to normal whale if anon
                             
                        alert_type = "SUSPICIOUS" if is_suspicious else "WHALE"
                        
                        # Log detection
                        logger.info(f"[{alert_type}] {amount_usd} USD by {wallet_address} (Nonce: {nonce})")
                        
                        polymarket_url = f"https://polymarket.com/event/{market_slug}"
                        
                        # Save to DB
                        new_alert = Alert(
                            market_name=market_name,
                            amount_usd=amount_usd,
                            wallet_address=wallet_address,
                            nonce=nonce if nonce else 0,
                            polymarket_url=polymarket_url,
                            tx_hash=str(tx_hash),
                            timestamp=datetime.now()
                        )
                        session.add(new_alert)
                        session.commit()
                        
                        # Send Telegram logic...
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

                    except Exception as e:
                        logger.error(f"Error parsing trade: {e}")
                        continue
                        
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
