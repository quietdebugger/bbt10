"""
Data Fetcher - Multi-asset data acquisition
Fetches price data for primary asset and all related assets for correlation analysis
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class MultiAssetDataFetcher:
    """
    Fetch data for multiple assets simultaneously for correlation analysis
    """
    
    def __init__(self):
        """Initialize fetcher"""
        self.cache = {}
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
        Fetch single asset data with retry
        
        Args:
            symbol: Asset symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            OHLCV DataFrame
        """
        logger.info(f"Fetching {symbol}...")
        
        try:
            data = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=True
            )
            
            if data.empty:
                raise ValueError(f"No data for {symbol}")
            
            # Standardize columns
            data.columns = [col[0].lower() for col in data.columns]
            
            logger.info(f"✓ Fetched {len(data)} rows for {symbol}")
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
        Fetch multiple assets
        
        Args:
            symbols: List of symbols
            start_date: Start date
            end_date: End date
            
        Returns:
            Dict mapping symbol to (data, error_message)
        """
        results = {}
        
        for symbol in symbols:
            try:
                data = self.fetch_asset(symbol, start_date, end_date)
                results[symbol] = (data, None)
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Could not fetch {symbol}: {error_msg}")
                results[symbol] = (None, error_msg)
        
        # Count successes
        successes = sum(1 for d, e in results.values() if d is not None)
        logger.info(f"Fetched {successes}/{len(symbols)} assets successfully")
        
        return results
