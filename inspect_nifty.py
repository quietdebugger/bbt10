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

def find_nifty_instruments():
    """
    Scans NSE.json to find what Nifty 50 instruments look like.
    """
    logger.info(f"Scanning {NSE_JSON_PATH} for Nifty instruments...")

    try:
        with open(NSE_JSON_PATH, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            found_count = 0
            for instrument in parser:
                name = instrument.get('name', '')
                if 'Nifty' in name or 'NIFTY' in name:
                    print(json.dumps(instrument, indent=2, cls=DecimalEncoder))
                    found_count += 1
                    if found_count >= 5:
                        break
                        
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    find_nifty_instruments()