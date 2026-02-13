import json
import logging
import ijson
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NSE_JSON_PATH = "C:/Users/Aallamprabhu/Desktop/bbt/bbt11/NSE.json"

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def find_nifty_spot():
    """
    Scans NSE.json to find the Nifty 50 SPOT instrument.
    """
    logger.info(f"Scanning {NSE_JSON_PATH} for Nifty 50 SPOT instrument...")

    try:
        with open(NSE_JSON_PATH, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            found = False
            for instrument in parser:
                segment = instrument.get('segment')
                name = instrument.get('name')
                
                # Check for NSE_INDEX segment and Nifty name
                if segment == 'NSE_INDEX' and ('Nifty 50' in name or 'NIFTY 50' in name or name == 'Nifty 50'):
                    print(json.dumps(instrument, indent=2, cls=DecimalEncoder))
                    found = True
                    break # Found it!
            
            if not found:
                logger.warning("Nifty 50 SPOT instrument not found in the scan.")
                        
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    find_nifty_spot()
