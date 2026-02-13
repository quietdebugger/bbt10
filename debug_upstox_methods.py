import json
import logging
from upstox_fo_complete import UpstoxFOData

logging.basicConfig(level=logging.INFO)

def main():
    print("--- Inspecting UpstoxFOData Class ---")
    method_list = [func for func in dir(UpstoxFOData) if callable(getattr(UpstoxFOData, func)) and not func.startswith("__")]
    
    if 'get_holdings' in method_list:
        print("YES get_holdings() exists.")
    else:
        print("NO get_holdings() MISSING!")

    print("--- Searching Instrument Master for Smallcap ---")
    try:
        with open("bbt10/instrument_master.json", "r") as f:
            data = json.load(f)
            
        found_keys = []
        for key in data.keys():
            if "SMALLCAP" in key.upper():
                found_keys.append(key)
                
        print(f"Found Smallcap Keys: {found_keys}")
        
    except Exception as e:
        print(f"Error reading master: {e}")

if __name__ == "__main__":
    main()