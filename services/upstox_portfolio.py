"""
Upstox Portfolio Service
"""

import logging
from typing import List, Dict
from .upstox_base import UpstoxBaseService

logger = logging.getLogger(__name__)

class UpstoxPortfolioService(UpstoxBaseService):
    
    def get_holdings(self) -> List[Dict]:
        """Fetch long-term holdings"""
        try:
            url = f"{self.base_url}/portfolio/long-term-holdings"
            data = self._make_api_call(url, {})
            if data.get("status") == "success":
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Holdings fetch failed: {e}")
            return []

    def get_positions(self) -> List[Dict]:
        """Fetch positions"""
        try:
            url = f"{self.base_url}/portfolio/short-term-positions"
            data = self._make_api_call(url, {})
            if data.get("status") == "success":
                return data.get("data", [])
            return []
        except Exception as e:
            return []
