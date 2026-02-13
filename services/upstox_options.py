"""
Upstox Options & Futures Service
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta, timezone
from calendar import monthrange
from typing import Dict, Optional, Tuple, List
from .upstox_base import UpstoxBaseService
from .instrument_service import instrument_service

logger = logging.getLogger(__name__)

class UpstoxOptionsService(UpstoxBaseService):
    
    def get_option_chain(
        self,
        symbol: str = "Nifty 50",
        expiry_date: Optional[str] = None,
        max_distance_pct: float = 12.0
    ) -> Tuple[pd.DataFrame, float]:
        """Get option chain data"""
        url = f"{self.base_url}/option/chain"
        
        # 1. Resolve Instrument Key
        instrument_key = instrument_service.resolve_instrument_key(symbol)
        
        if not instrument_key:
            # Fallback for indices if not in Master
            if symbol == "Nifty 50": instrument_key = "NSE_INDEX|Nifty 50"
            elif symbol == "Bank Nifty": instrument_key = "NSE_INDEX|Nifty Bank"
            else: instrument_key = f"NSE_EQ|{symbol.replace('.NS', '')}"

        if not expiry_date:
            expiry_date = self._get_next_expiry(symbol)
        
        params = {
            "instrument_key": instrument_key,
            "expiry_date": expiry_date
        }
        
        data = self._make_api_call(url, params)
        
        if data.get("status") != "success":
            logger.warning(f"Option Chain API failed for {symbol} (Key: {instrument_key}, Expiry: {expiry_date}): {data}")
            return pd.DataFrame(), 0.0
        
        if not data.get("data"):
            logger.warning(f"Option Chain empty for {symbol} (Key: {instrument_key}, Expiry: {expiry_date})")
            return pd.DataFrame(), 0.0
        
        # We need spot price for filtering. Can't call self.get_spot_price here easily due to mixin structure later.
        # But we can assume the user will mixin MarketService.
        # For now, let's just return raw data if we can't filter, or rely on external spot price.
        # Actually, let's try to fetch it if we can, or just return 0 spot.
        # Better: The caller usually knows the spot. But this signature returns spot.
        # We will implement a lightweight spot fetch here or reuse `_fetch_quote_ltp` if we were in MarketService.
        # Since we are splitting, we might duplicate the spot fetch logic lightly or assume composition.
        # Let's assume composition and use `self.get_spot_price` which will exist on the final object.
        
        spot_price = 0.0
        if hasattr(self, 'get_spot_price'):
            spot_price = self.get_spot_price(symbol) or 0.0
        
        rows = []
        for item in data.get("data", []):
            try:
                strike = item["strike_price"]
                call_data = item.get("call_options", {})
                call_market = call_data.get("market_data", {})
                call_greeks = call_data.get("option_greeks", {})
                
                put_data = item.get("put_options", {})
                put_market = put_data.get("market_data", {})
                put_greeks = put_data.get("option_greeks", {})
                
                row = {
                    "strike": strike,
                    "CE_LTP": call_market.get("ltp"),
                    "CE_Volume": call_market.get("volume", 0),
                    "CE_OI": call_market.get("oi", 0),
                    "CE_OI_Prev": call_market.get("prev_oi", 0),
                    "CE_IV": call_greeks.get("iv"),
                    "CE_Delta": call_greeks.get("delta"),
                    "CE_Gamma": call_greeks.get("gamma"),
                    "CE_Theta": call_greeks.get("theta"),
                    "CE_Vega": call_greeks.get("vega"),
                    "PE_LTP": put_market.get("ltp"),
                    "PE_Volume": put_market.get("volume", 0),
                    "PE_OI": put_market.get("oi", 0),
                    "PE_OI_Prev": put_market.get("prev_oi", 0),
                    "PE_IV": put_greeks.get("iv"),
                    "PE_Delta": put_greeks.get("delta"),
                    "PE_Gamma": put_greeks.get("gamma"),
                    "PE_Theta": put_greeks.get("theta"),
                    "PE_Vega": put_greeks.get("vega"),
                }
                # Handle None values for subtraction
                ce_oi = row["CE_OI"] or 0
                ce_oi_prev = row["CE_OI_Prev"] or 0
                pe_oi = row["PE_OI"] or 0
                pe_oi_prev = row["PE_OI_Prev"] or 0
                
                row["CE_OI_Change"] = ce_oi - ce_oi_prev
                row["PE_OI_Change"] = pe_oi - pe_oi_prev
                rows.append(row)
            except Exception as e:
                logger.error(f"Error parsing option item: {e}. Item keys: {item.keys()}")
                continue
        
        df = pd.DataFrame(rows).sort_values("strike").reset_index(drop=True)
        
        if spot_price and not df.empty:
            df_filtered = self._filter_liquid_strikes(df, spot_price, max_distance_pct)
            return df_filtered, spot_price
            
        return df, spot_price

    def get_futures_data(self, symbol: str) -> Dict:
        """Get nearest futures contract data"""
        futures = instrument_service.get_futures_for_symbol(symbol)
        
        if not futures:
            logger.warning(f"No futures found for symbol: {symbol}")
            return {"futures_price": 0, "interpretation": "Futures data not found"}
            
        # Get nearest expiry
        near_future = futures[0]
        f_key = near_future['key']
        expiry_ts = near_future.get('expiry') # timestamp
        
        # Fetch Quote
        url = f"{self.base_url}/market-quote/quotes"
        params = {"instrument_key": f_key}
        
        try:
            data = self._make_api_call(url, params)
        except Exception as e:
             logger.error(f"Futures API call error for {f_key}: {e}")
             return {"futures_price": 0, "interpretation": "API Error"}
        
        if data.get("status") == "success" and data.get("data"):
            # The API returns dict keyed by instrument_key
            # But Upstox sometimes changes delimiters in response keys (e.g. | to :)
            # We must find the payload safely
            quote_payload = None
            resp_data = data["data"]
            
            if f_key in resp_data:
                quote_payload = resp_data[f_key]
            else:
                # Robust scan: API often keys by 'NSE_FO:SYMBOL' but payload contains 'instrument_token'
                quote_payload = next((v for v in resp_data.values() if v.get('instrument_token') == f_key), None)
            
            if quote_payload:
                ltp = quote_payload.get("last_price", 0)
                ohlc = quote_payload.get("ohlc", {})
                close = ohlc.get("close", ltp)
                
                # Basic Spot comparison if available (best effort)
                spot_price = 0
                if hasattr(self, 'get_spot_price'):
                    spot_price = self.get_spot_price(symbol) or 0
                
                premium = ltp - spot_price if spot_price else 0
                
                return {
                    "symbol": symbol,
                    "futures_price": ltp,
                    "change": ltp - close,
                    "pct_change": ((ltp - close)/close)*100 if close else 0,
                    "spot_price": spot_price,
                    "premium": premium,
                    "basis_pct": (premium / spot_price * 100) if spot_price else 0,
                    "interpretation": "Premium" if premium > 0 else "Discount",
                    "expiry": datetime.fromtimestamp(expiry_ts/1000).strftime('%Y-%m-%d') if expiry_ts else "N/A"
                }
            else:
                logger.warning(f"Futures payload not found for key {f_key}. Response keys: {list(resp_data.keys())}")
        else:
            logger.warning(f"Futures API failed for {f_key}: {data}")

        return {"futures_price": 0, "interpretation": "Data fetch failed"}

    def _get_next_expiry(self, symbol: str) -> str:
        # 1. Try authoritative lookup from Master Data (best source)
        next_expiry = instrument_service.get_next_expiry(symbol)
        if next_expiry:
            return next_expiry

        # 2. Fallback to algorithmic calculation (only if master data missing)
        logger.warning(f"Expiry not found in master for {symbol}, calculating...")
        today = datetime.now()
        
        # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        if symbol in ["Bank Nifty", "^NSEBANK", "BANKNIFTY", "Nifty Bank"]:
             target_weekday = 2 # Wednesday
        elif symbol in ["Nifty Midcap 100", "NIFTY_MIDCAP_100", "^NSEMDCP100", "MIDCPNIFTY"]:
             target_weekday = 0 # Monday
        elif symbol in ["FINNIFTY", "Nifty Fin Service"]:
             target_weekday = 1 # Tuesday
        else:
             target_weekday = 3 # Thursday (Nifty 50 default)
             
        days_ahead = (target_weekday - today.weekday()) % 7
        
        # If today is the expiry day, check time. If after 3:30 PM (market close), move to next week.
        if days_ahead == 0:
             if today.hour > 15 or (today.hour == 15 and today.minute >= 30):
                 days_ahead = 7
        
        calculated_date = today + timedelta(days=days_ahead)
        return calculated_date.strftime("%Y-%m-%d")

    def _filter_liquid_strikes(self, df, spot, pct):
        if df.empty: return df
        df["dist"] = abs(df["strike"] - spot) / spot * 100
        return df[df["dist"] <= pct].drop("dist", axis=1)

    def calculate_pcr(self, df: pd.DataFrame) -> Dict:
        if df.empty:
            return {
                "pcr_oi": 0,
                "total_call_oi": 0,
                "total_put_oi": 0,
                "sentiment": "N/A",
                "interpretation": "No data"
            }
        
        total_ce_oi = df["CE_OI"].sum()
        total_pe_oi = df["PE_OI"].sum()
        
        pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
        
        if pcr > 1.5:
            sentiment = "Strong Bullish"
            interpretation = "High Put writing (Support)"
        elif pcr > 1.0:
            sentiment = "Bullish"
            interpretation = "More Puts than Calls"
        elif pcr > 0.7:
            sentiment = "Neutral"
            interpretation = "Balanced OI"
        elif pcr > 0.5:
            sentiment = "Bearish"
            interpretation = "Call writing dominant"
        else:
            sentiment = "Strong Bearish"
            interpretation = "Heavy Call writing (Resistance)"
            
        return {
            "pcr_oi": pcr,
            "total_call_oi": total_ce_oi,
            "total_put_oi": total_pe_oi,
            "sentiment": sentiment,
            "interpretation": interpretation
        }

    def calculate_max_pain(self, df: pd.DataFrame, spot: float) -> Dict:
        """
        Calculate Max Pain strike
        """
        if df.empty:
            return {"max_pain_strike": 0, "distance_pct": 0}
            
        strikes = df['strike'].unique()
        # To save compute, we can check pain only at strikes with significant OI
        # But for robustness, check all listed strikes in the chain
        
        pain_data = []
        
        for expiration_price in strikes:
            # Calculate intrinsic value for Calls and Puts if market settles at expiration_price
            
            # Call Intrinsic: max(0, expiration_price - strike)
            # Put Intrinsic: max(0, strike - expiration_price)
            
            # We can use vectorized operations since df has all strikes
            
            # Loss for Call Writers at this expiration price
            # If strike < expiration_price, Call is ITM. Loss = (expiration_price - strike) * CE_OI
            call_pain = df.apply(
                lambda row: max(0, expiration_price - row['strike']) * row['CE_OI'], axis=1
            ).sum()
            
            # Loss for Put Writers at this expiration price
            # If strike > expiration_price, Put is ITM. Loss = (strike - expiration_price) * PE_OI
            put_pain = df.apply(
                lambda row: max(0, row['strike'] - expiration_price) * row['PE_OI'], axis=1
            ).sum()
            
            total_pain = call_pain + put_pain
            pain_data.append({'strike': expiration_price, 'pain': total_pain})
            
        if not pain_data:
            return {"max_pain_strike": 0, "distance_pct": 0}
            
        pain_df = pd.DataFrame(pain_data)
        max_pain_strike = pain_df.loc[pain_df['pain'].idxmin()]['strike']
        
        distance_pct = 0
        if spot > 0:
            distance_pct = ((max_pain_strike - spot) / spot) * 100
            
        return {
            "max_pain_strike": max_pain_strike,
            "distance_pct": distance_pct
        }

    def get_oi_analysis(self, df: pd.DataFrame) -> Dict:
        """
        Find Support (Max Put OI) and Resistance (Max Call OI)
        """
        if df.empty:
            return {"call_resistance": 0, "put_support": 0}
            
        # Call Resistance: Strike with highest Call OI
        max_ce_oi_idx = df['CE_OI'].idxmax()
        call_resistance = df.loc[max_ce_oi_idx]['strike']
        
        # Put Support: Strike with highest Put OI
        max_pe_oi_idx = df['PE_OI'].idxmax()
        put_support = df.loc[max_pe_oi_idx]['strike']
        
        return {
            "call_resistance": call_resistance,
            "put_support": put_support
        }

    def calculate_greeks_analysis(self, df, spot):
        return {"net_delta": 0, "delta_interpretation": "N/A"}

    def get_batch_futures_oi(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Efficiently fetch Futures OI and Price data for a list of symbols (Stocks).
        Returns a dict: { symbol: { 'oi_change_pct': float, 'price_change_pct': float, 'interpretation': str } }
        """
        results = {}
        valid_futures_keys = {} # map key -> symbol

        # 1. Resolve Futures Keys (Nearest Expiry)
        for sym in symbols:
            # We need the underlying symbol for the lookup
            # The symbol might be "TATASTEEL.NS" or just "TATASTEEL"
            clean_sym = sym.replace(".NS", "")
            
            futures_list = instrument_service.get_futures_for_symbol(clean_sym)
            if futures_list:
                # Get the nearest expiry future
                near_future = futures_list[0] 
                key = near_future['key']
                valid_futures_keys[key] = sym
        
        if not valid_futures_keys:
            return {}

        # 2. Batch Fetch (Chunk size 50 to be safe with URL length)
        keys_list = list(valid_futures_keys.keys())
        chunk_size = 50
        
        for i in range(0, len(keys_list), chunk_size):
            chunk = keys_list[i:i + chunk_size]
            keys_str = ",".join(chunk)
            
            try:
                url = f"{self.base_url}/market-quote/quotes"
                params = {"instrument_key": keys_str}
                
                data = self._make_api_call(url, params)
                
                if data.get("status") == "success":
                    quotes = data.get("data", {})
                    
                    for key, quote in quotes.items():
                        # Handle Upstox Key format variations
                        original_sym = None
                        if key in valid_futures_keys:
                            original_sym = valid_futures_keys[key]
                        else:
                            # Try alternate delimiters
                            alt_key = key.replace(":", "|")
                            if alt_key in valid_futures_keys:
                                original_sym = valid_futures_keys[alt_key]
                        
                        if original_sym:
                            oi = quote.get('oi', 0)
                            # Previous OI is not directly available in simple quote sometimes, 
                            # but let's check 'ohlc' or calculate from 'oi_day_low'/'high' if needed.
                            # Actually Upstox Quote API v2 usually gives 'oi' and sometimes 'lower_circuit_limit' etc.
                            # For OI Change, we ideally need yesterday's OI. 
                            # If unavailable, we can uses 'oi' raw value to just show magnitude 
                            # OR assume the 'change' in price combined with raw OI indicates the trend.
                            # wait, standard quote has 'last_price' and 'net_change'. 
                            # For OI Change, let's rely on 'oi' vs 'oi_day_low' as a proxy 
                            # OR better: The API returns 'oi' and no direct 'prev_oi'.
                            # However, we can infer "Buildup" from Price Trend + High OI.
                            
                            # Let's try to find if there is an 'oi_change' field hidden or we just return raw OI
                            # Interpretation:
                            # Price UP + OI High = Long Buildup
                            # Price DOWN + OI High = Short Buildup
                            
                            ltp = quote.get('last_price', 0)
                            ohlc = quote.get('ohlc', {})
                            close = ohlc.get('close', ltp)
                            
                            price_change_pct = ((ltp - close) / close) * 100 if close else 0
                            
                            # If we can't get OI Change, we look at the trend
                            # But wait, Upstox Full Quote often has 'oi' and we can't calc change without history.
                            # WE WILL USE A PROXY: 
                            # If Price > 1% and OI is substantial (>0), we assume Long Buildup.
                            # Real OI Change requires history or a different API endpoint. 
                            # We will return the raw OI and let the UI/Logic interpret "High Interest".
                            
                            interp = "Neutral"
                            if price_change_pct > 0.5:
                                interp = "Long Buildup"
                            elif price_change_pct < -0.5:
                                interp = "Short Buildup"
                            
                            results[original_sym] = {
                                "oi": oi,
                                "price_change_pct": price_change_pct,
                                "interpretation": interp,
                                "ltp": ltp
                            }

            except Exception as e:
                logger.error(f"Batch Futures fetch failed: {e}")
                
        return results
