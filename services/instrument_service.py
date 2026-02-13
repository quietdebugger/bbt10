"""
Instrument Service
Handles loading and querying of Instrument Master and NSE.json
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Paths
# Assumes this file is in bbt10/services/, so we go up one level to bbt10/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTRUMENT_MASTER_PATH = os.path.join(BASE_DIR, "instrument_master.json")
NSE_JSON_PATH = os.path.join(BASE_DIR, "NSE.json")

class InstrumentService:
    _instance = None
    _master_data: Dict[str, Any] = {}
    _nse_data: Optional[List[Dict]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InstrumentService, cls).__new__(cls)
            cls._instance._load_master()
        return cls._instance

    def _load_master(self):
        """Loads instrument_master.json"""
        if os.path.exists(INSTRUMENT_MASTER_PATH):
            try:
                with open(INSTRUMENT_MASTER_PATH, 'r', encoding='utf-8') as f:
                    self._master_data = json.load(f)
                logger.info(f"Successfully loaded instrument master from {INSTRUMENT_MASTER_PATH}")
            except Exception as e:
                logger.error(f"Error loading instrument master: {e}")
        else:
            logger.warning(f"Instrument master not found at {INSTRUMENT_MASTER_PATH}")

    @property
    def master_data(self) -> Dict[str, Any]:
        return self._master_data

    @property
    def eq_map(self) -> Dict[str, Any]:
        return self._master_data.get("EQ_MAP", {})

    @property
    def indices_map(self) -> Dict[str, Any]:
        return self._master_data.get("INDICES", {})

    @property
    def futures_map(self) -> Dict[str, Any]:
        return self._master_data.get("FUTURES", {})

    @property
    def expiries_map(self) -> Dict[str, Any]:
        return self._master_data.get("EXPIRIES", {})

    def get_nse_json_data(self) -> List[Dict]:
        """Lazy loads NSE.json data if needed"""
        if self._nse_data is None:
            if os.path.exists(NSE_JSON_PATH):
                try:
                    with open(NSE_JSON_PATH, "r", encoding="utf-8") as f:
                        self._nse_data = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading NSE.json: {e}")
                    self._nse_data = []
            else:
                self._nse_data = []
        return self._nse_data

    def resolve_instrument_key(self, symbol: str) -> Optional[str]:
        """Resolves instrument key for a symbol using Master or NSE.json"""
        # 1. Fast Lookup
        if symbol in self.indices_map:
            return self.indices_map[symbol]
        
        # Normalize
        clean_sym = symbol.replace(".NS", "")
        if clean_sym in self.eq_map:
            return self.eq_map[clean_sym]['key']
            
        # 2. Fallback NSE.json search (Slow)
        # Only do this if strictly necessary or for weird symbols
        return None

    def _resolve_underlying_key(self, symbol: str) -> str:
        """Helper to map common names to NSE underlying keys"""
        clean_sym = symbol.replace(".NS", "")
        if symbol in ["Nifty 50", "^NSEI", "Nifty"]: 
            return "NIFTY"
        elif symbol in ["Bank Nifty", "^NSEBANK", "Nifty Bank", "BANKNIFTY"]: 
            return "BANKNIFTY"
        elif symbol in ["Nifty Midcap 100", "NIFTY_MIDCAP_100", "^NSEMDCP100", "NIFTY_MIDCAP_100.NS"]:
            return "MIDCPNIFTY" # Or NIFTY MIDCAP 100? Preprocessor uses NIFTY MIDCAP 100 logic?
            # Wait, preprocessor for FUTURES uses 'underlying' from NSE.json.
            # For Midcap index, underlying is often 'MIDCPNIFTY'.
            # Let's check keys in expiries_map if lookup fails.
            return "MIDCPNIFTY"
        return clean_sym

    def get_next_expiry(self, symbol: str) -> Optional[str]:
        """Get the next valid expiry date (YYYY-MM-DD) from cached data"""
        lookup_sym = self._resolve_underlying_key(symbol)
        
        # Try direct
        expiries = self.expiries_map.get(lookup_sym)
        
        # Fallback for Midcap mismatch
        if not expiries and lookup_sym == "MIDCPNIFTY":
             expiries = self.expiries_map.get("NIFTY MIDCAP 100")

        if not expiries:
            return None
            
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        for date_str in expiries:
            if date_str >= today_str:
                return date_str
        
        return None

    def get_futures_for_symbol(self, symbol: str) -> List[Dict]:
        """Get list of futures keys for a symbol, filtered by expiry"""
        # Mapping for Indices
        clean_sym = symbol.replace(".NS", "")
        
        if symbol in ["Nifty 50", "^NSEI", "Nifty"]: 
            lookup_sym = "NIFTY"
        elif symbol in ["Bank Nifty", "^NSEBANK", "Nifty Bank", "BANKNIFTY"]: 
            lookup_sym = "BANKNIFTY"
        elif symbol in ["Nifty Midcap 100", "NIFTY_MIDCAP_100", "^NSEMDCP100"]:
            lookup_sym = "MIDCPNIFTY" # Check this mapping, standard NSE is MIDCPNIFTY or similar
        else:
            lookup_sym = clean_sym
            
        # Try exact match first
        futures_list = []
        if lookup_sym in self.futures_map:
            futures_list = self.futures_map[lookup_sym]
            
        if not futures_list:
            return []
            
        # Filter expired
        import time
        current_ts = time.time() * 1000
        valid_futures = [f for f in futures_list if f.get('expiry') and f.get('expiry') > current_ts]
        
        # Sort by expiry
        valid_futures.sort(key=lambda x: x['expiry'])
        
        return valid_futures

# Global instance
instrument_service = InstrumentService()
