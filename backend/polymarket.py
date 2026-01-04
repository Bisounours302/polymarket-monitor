import requests
import json
import logging
import os

logger = logging.getLogger(__name__)

def fetch_markets():
    """
    Fetch top active markets by volume from Gamma API.
    Sanitizes response to ensure clobTokenIds is a list, not a string.
    """
    try:
        url = "https://gamma-api.polymarket.com/markets?limit=100&active=true&closed=false&order=volume:desc"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Post-process to fix clobTokenIds
        cleaned_data = []
        for market in data:
            # Parse clobTokenIds if string
            raw_ids = market.get("clobTokenIds")
            if isinstance(raw_ids, str):
                try:
                    market["clobTokenIds"] = json.loads(raw_ids)
                except:
                    market["clobTokenIds"] = []
            elif not isinstance(raw_ids, list):
                market["clobTokenIds"] = []
                
            cleaned_data.append(market)
            
        return cleaned_data
    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        return []

def fetch_trades_graphql(market_id, timestamp_from=None):
    """
    Fetch recent trades using The Graph protocol (Public & Free).
    Bypasses CLOB API Auth requirements.
    timestamp_from: Optional unix timestamp to fetch trades from.
    """
    if not market_id:
        return []

    url = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets-7"
    
    time_filter = ""
    if timestamp_from:
        time_filter = f', timestamp_gt: "{int(timestamp_from)}"'

    # Query uses market ID (Condition ID or Market Address)
    query = """
    {
      transactions(first: 50, orderBy: timestamp, orderDirection: desc, where: {market: "%s"%s}) {
        id
        timestamp
        tradeAmount
        user {
          id
        }
      }
    }
    """ % (str(market_id).lower(), time_filter)

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
