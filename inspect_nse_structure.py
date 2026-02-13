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

def inspect_structure():
    logger.info(f"Deep scanning {NSE_JSON_PATH}...")

    # We want to find one example of each type
    targets = {
        "Index Option": {"found": False, "criteria": lambda i: i.get('segment') == 'NSE_FO' and i.get('name') == 'NIFTY' and i.get('instrument_type') == 'CE'},
        "Stock Option": {"found": False, "criteria": lambda i: i.get('segment') == 'NSE_FO' and i.get('name') == 'RELIANCE' and i.get('instrument_type') == 'CE'},
        "Index Future": {"found": False, "criteria": lambda i: i.get('segment') == 'NSE_FO' and i.get('name') == 'NIFTY' and i.get('instrument_type') not in ['CE', 'PE']},
        "Stock Future": {"found": False, "criteria": lambda i: i.get('segment') == 'NSE_FO' and i.get('name') == 'RELIANCE' and i.get('instrument_type') not in ['CE', 'PE']},
        "Index Spot":   {"found": False, "criteria": lambda i: i.get('segment') == 'NSE_INDEX' and i.get('name') == 'Nifty 50'},
        "Stock Spot":   {"found": False, "criteria": lambda i: i.get('segment') == 'NSE_EQ' and i.get('name') == 'RELIANCE INDUSTRIES LTD'}
    }

    try:
        with open(NSE_JSON_PATH, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            for instrument in parser:
                # Check if we need to find anything else
                if all(t['found'] for t in targets.values()):
                    break

                for type_name, target in targets.items():
                    if not target['found'] and target['criteria'](instrument):
                        print(f"\n--- Found {type_name} ---")
                        print(json.dumps(instrument, indent=2, cls=DecimalEncoder))
                        target['found'] = True

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    inspect_structure()