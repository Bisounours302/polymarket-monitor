import requests
from polymarket import fetch_markets

print("🔍 TESTING CLOB REST API...")

# 1. Get Top Market ID
markets = fetch_markets()
if not markets:
    print("❌ Failed to fetch markets.")
    exit(1)

market = markets[0]
cond_id = market.get("conditionId")
slug = market.get("slug")

print(f"📉 Market: {slug}")
print(f"🔑 Condition ID: {cond_id}")

if not cond_id:
    print("❌ No Condition ID found.")
    exit(1)

# 2. Query CLOB API
# Endpoint found in docs: https://clob.polymarket.com/trades
url = "https://clob.polymarket.com/trades"
params = {
    "market": cond_id,
    "limit": 5
}

print(f"\n👉 Requesting {url} with market={cond_id}...")

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        trades = response.json()
        # Response might be a list or {"data": ...}
        if isinstance(trades, list):
            print(f"   ✅ SUCCESS! Found {len(trades)} trades.")
            if len(trades) > 0:
                t = trades[0]
                print(f"   Latest: {t.get('size')} shares @ {t.get('price')} (Side: {t.get('side')})")
        else:
            print(f"   ⚠️ Unexpected structure: {trades.keys()}")
    else:
        print(f"   ❌ Failed: {response.text}")

except Exception as e:
    print(f"   ❌ Error: {e}")
