"""
Upstox F&O Complete - Facade
Compiles all services into a single class for backward compatibility.
"""

from services.upstox_auth import UpstoxAuth
from services.upstox_market import UpstoxMarketService
from services.upstox_options import UpstoxOptionsService
from services.upstox_portfolio import UpstoxPortfolioService
from services.instrument_service import instrument_service

# Facade Class
class UpstoxFOData(UpstoxMarketService, UpstoxOptionsService, UpstoxPortfolioService):
    """
    Unified Upstox Data Client
    Inherits from:
    - UpstoxMarketService (Spot, Quotes, Batch)
    - UpstoxOptionsService (Chain, Greeks)
    - UpstoxPortfolioService (Holdings, Positions)
    """
    def __init__(self, auth: UpstoxAuth):
        # Initialize Base (which they all share)
        super().__init__(auth)