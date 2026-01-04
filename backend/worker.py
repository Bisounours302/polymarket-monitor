import os
import json
import time
import requests
import logging
from datetime import datetime
from web3 import Web3
from web3.middleware import geth_poa_middleware
from dotenv import load_dotenv
from database import init_db, get_session, Alert, GlobalSettings
from notifications import send_telegram_alert

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POLYGON_RPC_URL = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
# LOWER THRESHOLD FOR DEBUGGING
MIN_USD_THRESHOLD = float(os.getenv("MIN_USD_THRESHOLD", 10)) 
MAX_NONCE_THRESHOLD = int(os.getenv("MAX_NONCE_THRESHOLD", 10))

# ... existing code ...

def main():
    logger.info("Starting Polymarket Public Monitor (Read-Only)...")
    
    # Send Test Notification on Startup
    logger.info("Sending startup test notification...")
    test_sent = send_telegram_alert({"is_test": True})
    if test_sent:
        logger.info("Startup test notification sent successfully.")
    else:
        logger.error("Failed to send startup test notification. Check Telegram Config.")

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
            
            logger.info(f"Scanning {len(markets)} active markets...")
            
            for market in markets:
                # Use conditionId which works with The Graph's "market" field
                # Fallback to clobTokenIds parsing if conditionId is missing
                market_id = market.get("conditionId")
                
                if not market_id:
                    # Legacy/Backup: Handle clobTokenIds
                    raw_clob_ids = market.get("clobTokenIds")
                    if isinstance(raw_clob_ids, str):
                        try:
                            clob_ids = json.loads(raw_clob_ids)
                        except:
                            clob_ids = []
                    elif isinstance(raw_clob_ids, list):
                        clob_ids = raw_clob_ids
                    else:
                        clob_ids = []
                    
                    market_id = clob_ids[0] if clob_ids else None

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
