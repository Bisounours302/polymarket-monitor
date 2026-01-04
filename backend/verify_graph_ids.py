import requests
import json
from polymarket import fetch_markets

print("🔍 Validating Graph IDs...")

# 1. Fetch Top 1 Market
markets = fetch_markets()
if not markets:
    print("❌ Failed to fetch markets from Gamma.")
    exit(1)

# Sort by volume to ensure we get a heavy market
top_market = markets[0]
print(f"📉 Market: {top_market.get('question')}")
print(f"📊 Volume: ${top_market.get('volume')}")

cond_id = top_market.get("conditionId")
clob_ids = top_market.get("clobTokenIds", [])

def test_graph(id_val, label):
    if not id_val:
        print(f"   ⚠️ Skipping {label} (No ID provided)")
        return
        
    url = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets-7"
    query = """
    {
      transactions(first: 5, orderBy: timestamp, orderDirection: desc, where: {market: "%s"}) {
        id
        timestamp
        tradeAmount
      }
    }
    """ % (str(id_val).lower())
    
    try:
        response = requests.post(url, json={'query': query}, timeout=5)
        data = response.json()
        txs = data.get("data", {}).get("transactions", [])
        if len(txs) > 0:
            print(f"   ✅ {label}: FOUND {len(txs)} TRADES! (Latest: ${txs[0]['tradeAmount']})")
            return True
        else:
            print(f"   ❌ {label}: No trades found.")
    except Exception as e:
        print(f"   ❌ {label}: Error {e}")
    return False

# Tests
print("\n🧪 Testing IDs:")

# 1. Condition ID
test_graph(cond_id, "Condition ID")

# 2. Clob ID (Decimal)
if clob_ids:
    test_graph(clob_ids[0], "Clob Token ID (Decimal)")

    # 3. Clob ID (Hex)
    try:
        hex_id = hex(int(clob_ids[0]))
        test_graph(hex_id, "Clob Token ID (Hex)")
    except:
        print("   ⚠️ Could not convert Clob ID to Hex")

print("\n🏁 Validation Complete.")
