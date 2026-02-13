"""
Data Fetcher - Multi-asset data acquisition
Fetches price data for primary asset and all related assets for correlation analysis.
Prioritizes Upstox for ALL Indian assets (Spot/Latest Price) and falls back to Yahoo Finance.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

# Upstox Integration
try:
    from api_config import UPSTOX_API_KEY, UPSTOX_API_SECRET
    from upstox_fo_complete import UpstoxAuth, UpstoxFOData
    from services.instrument_service import instrument_service
    from market_symbols import INDICES
    UPSTOX_AVAILABLE = True
except ImportError:
    UPSTOX_AVAILABLE = False

logger = logging.getLogger(__name__)

class MultiAssetDataFetcher:
    """
    Fetch data for multiple assets simultaneously.
    - Uses Upstox for real-time Indian market data (Synthetic History)
    - Uses yfinance for global assets and full history
    """
    
    def __init__(self):
        """Initialize fetcher"""
        self.upstox = None
        if UPSTOX_AVAILABLE and UPSTOX_API_KEY and UPSTOX_API_SECRET:
            try:
                auth = UpstoxAuth(UPSTOX_API_KEY, UPSTOX_API_SECRET)
                self.upstox = UpstoxFOData(auth)
                logger.info("Upstox Client Initialized")
            except Exception as e:
                logger.error(f"Upstox init failed: {e}")
        
        logger.info("MultiAssetDataFetcher initialized")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def fetch_asset(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Fetch single asset data (Full History for Charts/Backtest)
        """
        logger.info(f"Fetching {symbol} (Historical)...")
        
        try:
            # Single fetch usually safe with threads (default) or False
            data = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=False # Changed for stability
            )
            
            if data is None or data.empty:
                raise ValueError(f"No data for {symbol}")
            
            # Standardize columns
            if isinstance(data.columns, pd.MultiIndex):
                try:
                    data.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in data.columns]
                except:
                    data.columns = [str(c).lower() for c in data.columns]
            else:
                data.columns = [str(col).lower() for col in data.columns]
            
            if not isinstance(data.index, pd.DatetimeIndex):
                data.index = pd.to_datetime(data.index)

            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            raise
    
    def fetch_multiple_assets(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, Tuple[Optional[pd.DataFrame], Optional[str]]]:
        """
        Fetch multiple assets. 
        PRIORITY: Upstox (Resolution via Instrument Master) -> Synthetic DataFrame
        FALLBACK: yfinance
        
        NOTE: Upstox Batch Quote API only provides SPOT (LTP/Close). 
        If the requested duration is long (> 7 days), we assume HISTORY is needed 
        and skip Upstox Spot to force yfinance (until Upstox Candle API is integrated).
        """
        results = {}
        if not symbols:
            return results

        unique_symbols = list(set(symbols))
        
        # Check duration
        try:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            duration_days = (end_dt - start_dt).days
        except:
            duration_days = 0
            
        use_upstox_spot = self.upstox and duration_days <= 7
        
        # 1. Identify Upstox-eligible symbols
        upstox_candidates = {} # {yf_symbol: upstox_lookup_symbol}
        yf_symbols = []
        
        # Create reverse map for indices (Ticker -> Name)
        index_ticker_to_name = {v: k for k, v in INDICES.items()}
        
        if use_upstox_spot:
            for sym in unique_symbols:
                # Resolve key
                lookup_sym = sym
                
                # Check if it's a known index ticker
                if sym in index_ticker_to_name:
                    lookup_sym = index_ticker_to_name[sym]
                
                # Special Manual overrides
                elif sym == '^NSEI': lookup_sym = 'Nifty 50'
                elif sym == '^NSEBANK': lookup_sym = 'Nifty Bank'
                elif sym == '^NSEMDCP100': lookup_sym = 'Nifty Midcap 100'
                elif sym == 'NIFTY_MIDCAP_100.NS': lookup_sym = 'Nifty Midcap 100'
                
                # Standard Stock Handling
                elif sym.endswith('.NS'):
                    lookup_sym = sym.replace('.NS', '')
                
                # Check if resolvable
                key = instrument_service.resolve_instrument_key(lookup_sym)
                
                if key:
                    upstox_candidates[sym] = lookup_sym
                else:
                    yf_symbols.append(sym)
        else:
            if self.upstox:
                logger.info(f"Request duration {duration_days} days > 7. Skipping Upstox Spot (LTP only) to fetch History via YF.")
            yf_symbols = unique_symbols
        
        # 2. Fetch from Upstox (Spot Quotes)
        if use_upstox_spot and upstox_candidates:
            logger.info(f"Upstox Candidates: {len(upstox_candidates)} symbols")
            try:
                # Pass the LIST of mapped symbols
                # get_batch_stock_quotes handles the internal resolution to keys
                quotes = self.upstox.get_batch_stock_quotes(list(upstox_candidates.values()))
                
                # Process results
                for yf_sym, u_sym in upstox_candidates.items():
                    # Quote keys might be the u_sym
                    quote_data = None
                    if u_sym in quotes:
                        quote_data = quotes[u_sym]
                    elif u_sym in quotes.values(): 
                         pass
                    
                    if quote_data:
                        # Construct Synthetic DataFrame
                        prev = quote_data.get('close') 
                        ltp = quote_data.get('ltp')
                        
                        if prev and ltp:
                            # Create DataFrame with 2 rows
                            idx = [datetime.datetime.now() - datetime.timedelta(days=1), datetime.datetime.now()]
                            df_synth = pd.DataFrame({
                                'close': [prev, ltp],
                                'open': [prev, ltp], 
                                'high': [prev, ltp],
                                'low': [prev, ltp],
                                'volume': [0, quote_data.get('volume', 0)]
                            }, index=idx)
                            
                            results[yf_sym] = (df_synth, None)
                        else:
                            yf_symbols.append(yf_sym) # Data missing
                    else:
                        yf_symbols.append(yf_sym) # No quote
                        
            except Exception as e:
                logger.error(f"Upstox batch fetch error: {e}")
                # Fallback failed ones
                yf_symbols.extend([s for s in upstox_candidates.keys() if s not in results])

        # 3. Fetch remaining from yfinance
        if yf_symbols:
            logger.info(f"Fetching {len(yf_symbols)} assets via yfinance (Fallback)...")
            try:
                # Batch download with THREADS=FALSE to avoid NoneType error
                data = yf.download(
                    yf_symbols,
                    start=start_date,
                    end=end_date,
                    progress=False,
                    auto_adjust=False, # Changed for stability
                    group_by='ticker',
                    threads=False # CRITICAL FIX for TypeError
                )
                
                if data is not None and not data.empty:
                    is_multi = isinstance(data.columns, pd.MultiIndex)
                    
                    for sym in yf_symbols:
                        try:
                            sym_data = pd.DataFrame()
                            if len(yf_symbols) == 1:
                                sym_data = data
                            elif is_multi and sym in data.columns.levels[0]:
                                sym_data = data[sym].copy()
                            
                            if not sym_data.empty:
                                # Clean
                                sym_data.dropna(how='all', inplace=True)
                                if not sym_data.empty:
                                    # Normalize columns
                                    if isinstance(sym_data.columns, pd.MultiIndex):
                                        sym_data.columns = [c[0].lower() for c in sym_data.columns]
                                    else:
                                        sym_data.columns = [str(c).lower() for c in sym_data.columns]
                                    
                                    if 'close' in sym_data.columns:
                                        results[sym] = (sym_data, None)
                                    else:
                                        results[sym] = (None, "Missing close")
                                else:
                                    results[sym] = (None, "Empty data")
                            else:
                                results[sym] = (None, "No data")
                        except Exception as ex:
                            results[sym] = (None, str(ex))
                else:
                    # Mark all as failed
                    for sym in yf_symbols:
                        results[sym] = (None, "YF batch returned empty")
                        
            except Exception as e:
                logger.error(f"YF batch failed: {e}")
                for sym in yf_symbols:
                    results[sym] = (None, str(e))

        return results
