"""
Upstox Market Data Service
"""

import logging
from typing import Dict, List, Optional
from .upstox_base import UpstoxBaseService
from .instrument_service import instrument_service

logger = logging.getLogger(__name__)

class UpstoxMarketService(UpstoxBaseService):
    
    def get_spot_price(self, symbol: str) -> Optional[float]:
        """Get real-time spot price"""
        
        # 1. Fast Lookup via Instrument Service
        key = instrument_service.resolve_instrument_key(symbol)
        
        if key:
            return self._fetch_quote_ltp(key)
        
        # 2. Fallback Logic (simplified from original)
        # Assuming Instrument Service is robust now
        logger.warning(f"Instrument key not found for {symbol} in Master.")
        return None

    def get_spot_quote(self, symbol: str) -> Dict:
        """Get full spot quote"""
        key = instrument_service.resolve_instrument_key(symbol)
        
        # Fallback for manual keys if passed directly
        if not key and "|" in symbol:
             key = symbol

        if key:
            return self._fetch_full_quote(key, symbol)
            
        return {}

    def get_batch_stock_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Efficiently fetch real-time quotes for a list of stock symbols.
        """
        results = {}
        keys_to_fetch = []
        key_to_symbol = {} # Maps Instrument Key -> Requested Symbol
        
        # 1. Resolve Keys
        for sym in symbols:
            clean_sym = sym.replace(".NS", "")
            key = instrument_service.resolve_instrument_key(clean_sym)
            
            if key:
                if key not in keys_to_fetch:
                    keys_to_fetch.append(key)
                    # Store mapping. Upstox might return 'NSE_EQ:INFY' for 'NSE_EQ|INE...' request?
                    # No, usually it respects the key format or returns 'NSE_EQ:Symbol'
                    # We map strict key first
                    key_to_symbol[key] = sym
            else:
                 # Guess key if not in master (unlikely for Nifty 50 but possible)
                 # Note: Upstox EQ keys are usually ISIN based (NSE_EQ|INE...)
                 # If we guess 'NSE_EQ|INFY', it might fail. 
                 # But let's try strict symbol match as fallback
                 pass

        if not keys_to_fetch:
            return {}

        # 2. Batch Fetch (Chunk size 50 to be safe)
        chunk_size = 50
        for i in range(0, len(keys_to_fetch), chunk_size):
            chunk = keys_to_fetch[i:i + chunk_size]
            keys_str = ",".join(chunk)
            
            try:
                url = f"{self.base_url}/market-quote/quotes"
                params = {"instrument_key": keys_str}
                
                data = self._make_api_call(url, params)
                
                if data.get("status") == "success":
                    quotes = data.get("data", {})
                    
                    for resp_key, quote in quotes.items():
                        # The response key might differ from requested key (e.g. delimiters)
                        # OR it might be the Symbol Key 'NSE_EQ:INFY' while we sent 'NSE_EQ|INE...'
                        
                        original_sym = None
                        
                        # 1. Direct Match
                        if resp_key in key_to_symbol:
                            original_sym = key_to_symbol[resp_key]
                        
                        # 2. Token Match (The reliable way)
                        # Upstox quote usually contains 'instrument_token' field which matches what we sent
                        if not original_sym:
                            token = quote.get('instrument_token')
                            if token and token in key_to_symbol:
                                original_sym = key_to_symbol[token]
                        
                        if original_sym:
                            ltp = quote.get("last_price", 0.0)
                            ohlc = quote.get("ohlc", {})
                            close = ohlc.get("close", 0.0) # This is usually Previous Close or Close
                            
                            # USE EXPLICIT NET CHANGE IF AVAILABLE
                            # This fixes the 0.00% issue when ohlc.close == ltp
                            net_change = quote.get("net_change")
                            
                            if net_change is not None:
                                change = float(net_change)
                                # Recalculate pct based on (LTP - Change) = PrevClose
                                prev_close = ltp - change
                                pct_change = (change / prev_close * 100) if prev_close != 0 else 0.0
                            else:
                                # Fallback
                                change = ltp - close if close else 0.0
                                pct_change = (change / close * 100) if close else 0.0
                                
                            results[original_sym] = {
                                "ltp": ltp,
                                "close": close,
                                "change": change,
                                "change_pct": pct_change,
                                "volume": quote.get("volume", 0)
                            }
            except Exception as e:
                logger.error(f"Batch fetch failed for chunk: {e}")
                
        return results

    def _fetch_quote_ltp(self, key: str) -> Optional[float]:
        url = f"{self.base_url}/market-quote/quotes"
        params = {"instrument_key": key}
        data = self._make_api_call(url, params)
        if data.get("status") == "success":
            for k, v in data["data"].items():
                return float(v["last_price"])
        return None

    def _fetch_full_quote(self, key: str, symbol: str) -> Dict:
        url = f"{self.base_url}/market-quote/quotes"
        params = {"instrument_key": key}
        data = self._make_api_call(url, params)
        if data.get("status") == "success":
            for k, v in data["data"].items():
                ohlc = v.get("ohlc", {})
                ltp = v.get("last_price")
                
                # Use net_change logic here too
                net_change = v.get("net_change")
                if net_change is not None:
                    change = float(net_change)
                    prev_close = ltp - change
                    change_pct = (change / prev_close * 100) if prev_close != 0 else 0.0
                else:
                    prev_close = ohlc.get("close")
                    change = ltp - prev_close if ltp and prev_close else 0.0
                    change_pct = (change / prev_close) * 100 if prev_close else 0.0
                
                return {
                    "symbol": symbol,
                    "ltp": ltp,
                    "change": change,
                    "change_pct": change_pct,
                    "previous_close": prev_close,
                    "volume": v.get("volume")
                }
        return {}
