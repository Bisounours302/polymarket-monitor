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

def fetch_trades(market_id, timestamp_from=None):
    """
    Fetch recent trades using the Polymarket Data API (Public).
    Endpoint: https://data-api.polymarket.com/trades
    Params: 
      - market: conditionId
      - limit: 50
    """
    if not market_id:
        return []

    url = "https://data-api.polymarket.com/trades"
    params = {
        "market": market_id,
        "limit": 50
    }
    
    # If we want to filter by time, Data API supports 'start' (unix params)
    # But usually we just get latest 50 and filter in worker
    if timestamp_from:
         params["start"] = int(timestamp_from)

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Data API Error: {e}")
        return []
