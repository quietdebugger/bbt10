
import json
import requests
import os

def find_usdinr():
    token_file = os.path.join(os.path.dirname(__file__), "upstox_tokens.json")
    with open(token_file, "r") as f:
        access_token = json.load(f)["access_token"]

    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    base_url = "https://api.upstox.com/v2/market-quote/quotes"

    # More exhaustive currency variants
    keys = [
        "MCX_FO|USDINR",
        "CDE_FO|USDINR",
        "CDS_FO|USDINR",
        "BCD_FO|USDINR",
        "CDE_FO|USDINR26FEBFUT",
        "CDE_FO|USDINR25FEBFUT",
        "NSE_FO|USDINR26FEBFUT",
        "MCX|USDINR",
        "CDE|USDINR",
        "BCD|USDINR",
        "NSE_CUR|USDINR",
        "BSE_CUR|USDINR"
    ]

    for key in keys:
        try:
            response = requests.get(base_url, headers=headers, params={"instrument_key": key})
            data = response.json()
            if data.get("status") == "success" and data.get("data"):
                print(f"FOUND: {key} -> {list(data['data'].keys())}")
            else:
                pass
        except: pass

if __name__ == "__main__":
    find_usdinr()
