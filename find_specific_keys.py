import json
import requests
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_keys():
    token_file = os.path.join(os.path.dirname(__file__), "upstox_tokens.json")
    if not os.path.exists(token_file):
        print(f"Token file not found at {token_file}. Please run the app first.")
        return

    with open(token_file, "r") as f:
        tokens = json.load(f)
        access_token = tokens["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    base_url = "https://api.upstox.com/v2/market-quote/quotes"

    # Variations of keys for SENSEX and USDINR
    # Adding Nifty 50 as a control
    keys_to_test = [
        "NSE_INDEX|Nifty 50",
        "BSE_INDEX|SENSEX",
        "BSE_INDEX|BSE SENSEX",
        "BSE_EQ|SENSEX",
        "NSE_INDEX|SENSEX",
        "BCD|USDINR",
        "CDE|USDINR",
        "CDS|USDINR",
        "NSE_EQ|USDINR",
        "NSE_INDEX|USDINR",
        "BCD|USDINR26FEB",
        "CDE|USDINR26FEB",
        "NSE_FO|USDINR26FEB"
    ]

    print(f"Testing {len(keys_to_test)} candidate keys...")

    for key in keys_to_test:
        params = {"instrument_key": key}
        try:
            response = requests.get(base_url, headers=headers, params=params)
            data = response.json()
            if data.get("status") == "success" and data.get("data"):
                print(f"FOUND: {key}")
                for k, v in data["data"].items():
                    print(f"   Response Key: {k}")
                    print(f"   LTP: {v.get('last_price')}")
            else:
                if data.get("data"):
                    print(f"PARTIAL: {key}")
                    print(f"   Returned: {list(data['data'].keys())}")
                else:
                    print(f"FAILED: {key}")
        except Exception as e:
            print(f"ERROR testing {key}: {e}")

if __name__ == "__main__":
    find_keys()