"""
Pre-processes the NSE.json file to create instrument_master.json.
Now captures ALL Equity symbols for ETF decomposition.
"""

import json
import logging
import os
import ijson
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NSE_JSON_PATH = os.path.join(BASE_DIR, "NSE.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "instrument_master.json")

def preprocess_nse_data():
    instrument_master = {
        "EQ_MAP": {}, # Symbol -> Instrument Key
        "INDICES": {}, # Symbol -> Instrument Key
        "FUTURES": {},  # Underlying Symbol -> List of {key, expiry}
        "EXPIRIES": {} # Underlying Symbol -> List of sorted "YYYY-MM-DD"
    }
    
    # Helper to track raw expiries to avoid duplicates before sorting
    raw_expiries = {} 

    logger.info(f"Starting processing of {NSE_JSON_PATH}")

    try:
        if not os.path.exists(NSE_JSON_PATH):
            logger.error(f"NSE.json not found at {NSE_JSON_PATH}")
            return

        with open(NSE_JSON_PATH, 'rb') as f:
            # ijson iteratively parses the file to save memory
            parser = ijson.items(f, 'item')
            
            count = 0
            for instrument in parser:
                count += 1
                if count % 100000 == 0:
                    logger.info(f"Processed {count} instruments...")

                segment = instrument.get('segment')
                symbol = instrument.get('trading_symbol')
                key = instrument.get('instrument_key')
                name = instrument.get('name')
                
                # 1. Capture ALL Equities
                if segment == 'NSE_EQ' and instrument.get('instrument_type') == 'EQ':
                    if symbol and key:
                        instrument_master["EQ_MAP"][symbol] = {
                            "key": key,
                            "name": name
                        }
                
                # 2. Capture Indices (Spot)
                elif segment == 'NSE_INDEX':
                    if symbol and key:
                        instrument_master["INDICES"][symbol] = key
                        # Handle variants based on Upstox 'trading_symbol'
                        if symbol == "NIFTY":
                            instrument_master["INDICES"]["^NSEI"] = key
                            instrument_master["INDICES"]["Nifty 50"] = key
                        elif symbol == "BANKNIFTY":
                            instrument_master["INDICES"]["^NSEBANK"] = key
                            instrument_master["INDICES"]["Nifty Bank"] = key
                            instrument_master["INDICES"]["Bank Nifty"] = key
                        elif symbol == "NIFTY MIDCAP 100":
                            instrument_master["INDICES"]["NIFTY_MIDCAP_100.NS"] = key
                            instrument_master["INDICES"]["^NSEMDCP100"] = key
                            instrument_master["INDICES"]["Nifty Midcap 100"] = key

                # 3. Capture Futures & Options for Expiries
                elif segment == 'NSE_FO':
                    inst_type = instrument.get('instrument_type')
                    underlying = instrument.get('underlying_symbol') or instrument.get('name')
                    expiry = instrument.get('expiry')
                    
                    if underlying and expiry:
                        # Capture Expiry
                        if underlying not in raw_expiries:
                            raw_expiries[underlying] = set()
                        raw_expiries[underlying].add(int(expiry))

                        # Capture Futures Details
                        if inst_type == 'FUT' and key:
                            if underlying not in instrument_master["FUTURES"]:
                                instrument_master["FUTURES"][underlying] = []
                            instrument_master["FUTURES"][underlying].append({
                                "key": key,
                                "expiry": int(expiry)
                            })

        # Process Futures Sorting
        for underlying in instrument_master["FUTURES"]:
            instrument_master["FUTURES"][underlying].sort(key=lambda x: x['expiry'])
            
        # Process Expiries
        for underlying, exp_set in raw_expiries.items():
            sorted_exp = sorted(list(exp_set))
            # Convert to YYYY-MM-DD
            formatted_exp = []
            for ts in sorted_exp:
                try:
                    dt = datetime.fromtimestamp(ts / 1000)
                    formatted_exp.append(dt.strftime('%Y-%m-%d'))
                except Exception:
                    pass
            instrument_master["EXPIRIES"][underlying] = formatted_exp

        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(instrument_master, f, indent=2)
        
        logger.info(f"✓ Instrument master created with {len(instrument_master['EQ_MAP'])} equities, {len(instrument_master['FUTURES'])} futures roots, and {len(instrument_master['EXPIRIES'])} expiry maps.")

    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")

if __name__ == "__main__":
    preprocess_nse_data()