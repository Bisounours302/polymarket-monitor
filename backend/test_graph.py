import requests
import json
from polymarket import fetch_markets

print("🔍 DIAGNOSTIC GRAPH PROTOCOL...")

# 1. Recuperer le Top Market
markets = fetch_markets()
if not markets:
    print("❌ ECHEC: Impossible de recuperer les marches Gamma.")
    exit(1)

# On prend le premier marché (le plus gros volume)
market = markets[0]
print(f"📉 Marché Test: {market.get('question')}")
print(f"   Slug: {market.get('slug')}")

cond_id = market.get("conditionId")
raw_clob = market.get("clobTokenIds", [])
# clobTokenIds est deja une liste grace a polymarket.py
if isinstance(raw_clob, str):
    raw_clob = json.loads(raw_clob)
clob_id_dec = raw_clob[0] if raw_clob else None

def try_query(id_val, type_label):
    if not id_val:
        return
        
    print(f"\n👉 Test {type_label}: {id_val}")
    
    # Subgraph URL standard
    url = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets-7"
    
    query = """
    {
      transactions(first: 5, orderBy: timestamp, orderDirection: desc, where: {market: "%s"}) {
        id
        timestamp
        tradeAmount
        user { id }
      }
    }
    """ % str(id_val).lower()
    
    try:
        r = requests.post(url, json={'query': query}, timeout=5)
        data = r.json()
        txs = data.get("data", {}).get("transactions", [])
        if len(txs) > 0:
            print(f"   ✅ SUCCES! {len(txs)} trades trouvés.")
            print(f"   Exemple: ${txs[0]['tradeAmount']} par {txs[0]['user']['id']}")
            return True
        else:
            print("   ❌ Aucun trade (Réponse vide)")
            # print(f"   Debug: {data}")
    except Exception as e:
        print(f"   ❌ Erreur Technique: {e}")
    return False

# Test 1: Condition ID
try_query(cond_id, "Condition ID")

# Test 2: CLOB ID (Decimal)
try_query(clob_id_dec, "Clob ID (Décimal)")

# Test 3: CLOB ID (Hex)
if clob_id_dec:
    try:
        hex_id = hex(int(clob_id_dec))
        try_query(hex_id, "Clob ID (Hexadécimal)")
    except:
        pass
