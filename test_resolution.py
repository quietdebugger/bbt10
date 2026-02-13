
import sys
import os
import logging

# Add bbt10 to path
sys.path.append(os.path.join(os.getcwd(), 'bbt10'))

from services.instrument_service import instrument_service

logging.basicConfig(level=logging.INFO)

def test_resolution():
    print("Testing Resolution...")
    
    # 1. Test Nifty 50 Spot
    key = instrument_service.resolve_instrument_key("Nifty 50")
    print(f"Nifty 50 Key: {key}")
    
    # 2. Test Midcap
    key_mid = instrument_service.resolve_instrument_key("NIFTY_MIDCAP_100.NS")
    print(f"Midcap Key: {key_mid}")
    
    # 3. Test Futures
    futures = instrument_service.get_futures_for_symbol("Nifty 50")
    print(f"Nifty Futures Count: {len(futures)}")
    if futures:
        print(f"Nearest Future: {futures[0]}")

if __name__ == "__main__":
    test_resolution()
