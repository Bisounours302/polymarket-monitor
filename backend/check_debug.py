import json
import os
import sys

print("Checking debug markets logic...")
try:
    # Mimic the path logic from main.py
    cache_path = "/app/data/debug_markets.json"
    if not os.path.exists(cache_path):
        print(f"Cache not found at {cache_path}, checking local...")
        cache_path = "data/debug_markets.json"
    
    if os.path.exists(cache_path):
        print(f"Found cache at {cache_path}")
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
            print(f"Successfully loaded JSON. Items: {len(data)}")
        except json.JSONDecodeError as je:
            print(f"JSON CORRUPTION DETECTED: {je}")
    else:
        print("No cache file found. Trying fallback import...")
        sys.path.append(os.getcwd()) # Ensure persistent path
        try:
            from polymarket import fetch_markets
            data = fetch_markets()
            print(f"Fallback fetch success. Items: {len(data)}")
        except ImportError as ie:
            print(f"IMPORT ERROR: {ie}")
            print(f"Current Directory: {os.getcwd()}")
            print(f"Directory Contents: {os.listdir('.')}")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
