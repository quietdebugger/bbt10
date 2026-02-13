
import json
import requests
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_keys():
    token_file = "upstox_tokens.json"
    if not os.path.exists(token_file):
        print("Token file not found")
        return

    with open(token_file, "r") as f:
        tokens = json.load(f)
        access_token = tokens["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    base_url = "https://api.upstox.com/v2/market-quote/quotes"

    keys_to_test = [
        "NSE_FO|59460",
        "NSE_FO:59460"
    ]

    for key in keys_to_test:
        params = {"instrument_key": key}
        response = requests.get(base_url, headers=headers, params=params)
        print(f"Key: {key}, Status: {response.status_code}")
        try:
            data = response.json()
            if data.get("status") == "success" and data.get("data"):
                # Dump keys to see what we got
                print(f"  Response Keys: {list(data['data'].keys())}")
                if key in data["data"]:
                    print(f"  SUCCESS! Price: {data['data'][key].get('last_price')}")
                elif key.replace(":", "|") in data["data"]:
                     print(f"  SUCCESS (pipe)! Price: {data['data'][key.replace(':', '|')].get('last_price')}")
                else:
                    # Check first key
                    first_key = list(data['data'].keys())[0]
                    print(f"  Found data for {first_key}: {data['data'][first_key].get('last_price')}")
            else:
                print(f"  Failed: {data}")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    test_keys()
