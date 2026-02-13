"""
Upstox Base API Service
"""

import requests
import logging
from typing import Dict
from .upstox_auth import UpstoxAuth

logger = logging.getLogger(__name__)

class UpstoxBaseService:
    def __init__(self, auth: UpstoxAuth):
        self.auth = auth
        self.base_url = "https://api.upstox.com/v2"
    
    def get_headers(self) -> Dict:
        access_token = self.auth.get_access_token()
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
    
    def _make_api_call(self, url: str, params: Dict) -> Dict:
        headers = self.get_headers()
        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            
            if data.get("status") == "error":
                errors = data.get("errors", [])
                if errors and errors[0].get("errorCode") == "UDAPI100050":
                    logger.warning("Token invalid. Retrying...")
                    self.auth.invalidate_token()
                    headers = self.get_headers() 
                    response = requests.get(url, headers=headers, params=params)
                    data = response.json()
            
            return data
        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise
