
import sys
import os
import logging
from datetime import datetime

# Add current dir to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from services.upstox_auth import UpstoxAuth
from services.upstox_options import UpstoxOptionsService
from services.instrument_service import instrument_service
import api_config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fetching():
    logger.info("Initializing Upstox Service...")
    try:
        auth = UpstoxAuth(api_config.UPSTOX_API_KEY, api_config.UPSTOX_API_SECRET)
        service = UpstoxOptionsService(auth)
    except Exception as e:
        logger.error(f"Auth Init Failed: {e}")
        return

    symbols = ["Nifty 50", "Nifty Midcap 100", "Bank Nifty"]
    
    for sym in symbols:
        logger.info(f"--- Testing {sym} ---")
        
        # 1. Resolve Key
        key = instrument_service.resolve_instrument_key(sym)
        logger.info(f"Resolved Key: {key}")
        
        if not key:
            logger.error(f"Failed to resolve key for {sym}")
            continue

        # 2. Futures
        try:
            fut_data = service.get_futures_data(sym)
            logger.info(f"Futures Data: Price={fut_data.get('futures_price')}, Expiry={fut_data.get('expiry')}, Interpretation={fut_data.get('interpretation')}")
        except Exception as e:
            logger.error(f"Futures fetch error: {e}")

        # 3. Options
        try:
            chain, spot = service.get_option_chain(sym)
            logger.info(f"Option Chain: {len(chain)} rows. Spot={spot}")
        except Exception as e:
            logger.error(f"Option Chain error: {e}")

if __name__ == "__main__":
    test_fetching()
