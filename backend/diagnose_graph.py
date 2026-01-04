import requests
import json

# Data from Example.txt (MicroStrategy sells any Bitcoin in 2025?)
MARKET_NAME = "MicroStrategy sells any Bitcoin in 2025?"
CONDITION_ID = "0x19ee98e348c0ccb341d1b9566fa14521566e9b2ea7aed34dc407a0ec56be36a2"
CLOB_ID_DECIMAL = "93592949212798121127213117304912625505836768562433217537850469496310204567695"

def query_graph(id_value, label):
    url = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets-7"
    query = """
    {
      transactions(first: 5, orderBy: timestamp, orderDirection: desc, where: {market: "%s"}) {
        id
        timestamp
        tradeAmount
        user {
          id
        }
      }
    }
    """ % (str(id_value).lower())
    
    with open("diagnostic_results.txt", "a") as f:
        try:
            f.write(f"Testing {label}: {id_value} ...\n")
            response = requests.post(url, json={'query': query}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "transactions" in data["data"]:
                    txs = data["data"]["transactions"]
                    f.write(f"✅ SUCCESS! Found {len(txs)} trades.\n")
                    if txs:
                        f.write(f"   Sample Trade: ${txs[0]['tradeAmount']} at {txs[0]['timestamp']}\n")
                    return True
                else:
                    f.write(f"❌ Response OK but no data: {data}\n")
            else:
                f.write(f"❌ HTTP Error: {response.status_code}\n")
        except Exception as e:
            f.write(f"❌ Exception: {e}\n")
    return False

# Clear file first
with open("diagnostic_results.txt", "w") as f:
    f.write("Starting Diagnostic...\n")

# 1. Test Condition ID
query_graph(CONDITION_ID, "Condition ID")

# 2. Test CLOB ID (Decimal)
query_graph(CLOB_ID_DECIMAL, "CLOB ID (Decimal)")

# 3. Test CLOB ID (Hex)
try:
    clob_hex = hex(int(CLOB_ID_DECIMAL))
    query_graph(clob_hex, "CLOB ID (Hex)")
except:
    pass

with open("diagnostic_results.txt", "a") as f:
    f.write("\nDiagnostic Complete.\n")
