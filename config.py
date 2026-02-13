"""
Advanced Configuration for Professional Financial Analysis
Includes multi-asset correlation tracking, volume analysis, and fundamental data
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# ============================================================================
# MULTI-ASSET CORRELATION FRAMEWORK
# ============================================================================

@dataclass
class MarketRelationship:
    """Defines relationship between assets for correlation analysis"""
    primary_asset: str
    related_assets: List[str]
    relationship_type: str  # 'leading', 'lagging', 'concurrent'
    typical_lag_days: int
    description: str

# Define key market relationships for Indian equity analysis
MARKET_RELATIONSHIPS = {
    'nifty_ecosystem': MarketRelationship(
        primary_asset='^NSEI',
        related_assets=[
            '^GSPC',      # S&P 500 - US equity
            '^IXIC',      # NASDAQ - Tech sector
            '^DJI',       # Dow Jones
            'DX-Y.NYB',   # US Dollar Index
            '^TNX',       # US 10-Year Treasury Yield
            '^TYX',       # US 30-Year Treasury Yield
            'GC=F',       # Gold futures
            'CL=F',       # Crude oil
            'INR=X',      # USD/INR exchange rate
            '^VIX',       # VIX (fear index)
        ],
        relationship_type='concurrent',
        typical_lag_days=0,
        description='NIFTY 50 moves with global risk sentiment, especially US markets'
    ),
    
    'nifty_bank_ecosystem': MarketRelationship(
        primary_asset='^NSEBANK',
        related_assets=[
            '^NSEI',      # NIFTY 50
            '^TNX',       # US 10Y (interest rates)
            'INR=X',      # USD/INR
            '^GSPC',      # S&P 500
        ],
        relationship_type='concurrent',
        typical_lag_days=0,
        description='NIFTY Bank sensitive to interest rates and currency'
    ),
}

# Specific asset correlations to track
CORRELATION_PAIRS = {
    'india_us_equity': {
        'asset1': '^NSEI',
        'asset2': '^GSPC',
        'expected_correlation': 0.7,  # Typically positive correlation
        'interpretation': 'Indian markets follow US equity trends'
    },
    'nifty_dollar': {
        'asset1': '^NSEI',
        'asset2': 'DX-Y.NYB',
        'expected_correlation': -0.3,  # Typically negative
        'interpretation': 'Strong dollar can pressure Indian markets (FII outflows)'
    },
    'nifty_crude': {
        'asset1': '^NSEI',
        'asset2': 'CL=F',
        'expected_correlation': -0.2,  # Negative (India is oil importer)
        'interpretation': 'Higher oil prices increase import bill, pressure markets'
    },
    'nifty_vix': {
        'asset1': '^NSEI',
        'asset2': '^VIX',
        'expected_correlation': -0.6,  # Strong negative
        'interpretation': 'VIX spikes = global fear = Indian market selloff'
    },
}

# ============================================================================
# VOLUME ANALYSIS CONFIGURATION
# ============================================================================

VOLUME_ANALYSIS_CONFIG = {
    'volume_ma_periods': [5, 20, 50],  # Moving averages for volume
    'volume_spike_threshold': 2.0,      # 2x average = spike
    'thin_volume_threshold': 0.5,       # 0.5x average = thin
    'vwap_periods': [20],               # VWAP calculation periods
    'volume_profile_bins': 50,          # For volume profile histogram
    'obv_enabled': True,                # On-Balance Volume
    'mfi_period': 14,                   # Money Flow Index period
    'volume_rsi_period': 14,            # Volume RSI
}

# Volume event detection
VOLUME_EVENTS = {
    'breakout': {
        'volume_threshold': 2.0,  # 2x average
        'price_move_threshold': 2.0,  # 2% price move
        'description': 'High volume breakout'
    },
    'exhaustion': {
        'volume_threshold': 2.5,
        'price_move_threshold': 0.5,  # High vol, low price move
        'description': 'Volume exhaustion (possible reversal)'
    },
    'accumulation': {
        'volume_threshold': 1.5,
        'price_trend': 'sideways',
        'description': 'Accumulation phase (rising volume, flat price)'
    },
    'distribution': {
        'volume_threshold': 1.5,
        'price_trend': 'topping',
        'description': 'Distribution phase (rising volume at top)'
    }
}

# ============================================================================
# FUNDAMENTAL DATA SOURCES
# ============================================================================

@dataclass
class FundamentalDataConfig:
    """Configuration for fundamental data retrieval"""
    source: str
    enabled: bool
    api_key_required: bool
    free_tier_limit: Optional[int]
    data_points: List[str]

FUNDAMENTAL_SOURCES = {
    'yahoo_finance': FundamentalDataConfig(
        source='yahoo',
        enabled=True,
        api_key_required=False,
        free_tier_limit=None,
        data_points=[
            'sector', 'industry', 'employees', 'market_cap',
            'pe_ratio', 'forward_pe', 'peg_ratio', 'ps_ratio', 'pb_ratio',
            'enterprise_value', 'profit_margin', 'operating_margin',
            'roe', 'revenue_growth', 'earnings_growth',
            'debt_to_equity', 'current_ratio', 'quick_ratio',
            'dividend_yield', 'payout_ratio',
            'beta', '52w_high', '52w_low',
            'short_ratio', 'short_percent',
            'institutional_holders', 'insider_ownership',
            'analyst_recommendations', 'target_price'
        ]
    ),
    
    'news_sentiment': FundamentalDataConfig(
        source='news_api',
        enabled=True,
        api_key_required=False,  # Will use free sources
        free_tier_limit=100,
        data_points=[
            'recent_news', 'sentiment_score', 'news_volume',
            'major_events', 'earnings_dates'
        ]
    ),
    
    'screener_in': FundamentalDataConfig(
        source='screener',
        enabled=True,
        api_key_required=False,
        free_tier_limit=None,
        data_points=[
            'competitors', 'peer_comparison', 'shareholding_pattern',
            'quarterly_results', 'profit_loss', 'balance_sheet',
            'cash_flow', 'ratios', 'valuations'
        ]
    )
}

# Peer analysis configuration
PEER_ANALYSIS_CONFIG = {
    'auto_detect_peers': True,
    'max_peers': 5,
    'comparison_metrics': [
        'market_cap', 'pe_ratio', 'pb_ratio', 'roe', 'debt_to_equity',
        'revenue_growth', 'profit_margin', 'dividend_yield'
    ],
    'peer_groups': {
        'RELIANCE.NS': ['ONGC.NS', 'IOC.NS', 'BPCL.NS'],
        'TCS.NS': ['INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS'],
        'HDFCBANK.NS': ['ICICIBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'AXISBANK.NS'],
        'ITC.NS': ['HINDUNILVR.NS', 'NESTLEIND.NS', 'BRITANNIA.NS'],
    }
}

# ============================================================================
# NIFTY 50 CONSTITUENTS & HEAVYWEIGHTS
# ============================================================================

NIFTY50_HEAVYWEIGHTS = {
    'RELIANCE.NS': {'weight': 10.2, 'sector': 'Energy'},
    'HDFCBANK.NS': {'weight': 9.8, 'sector': 'Financials'},
    'INFY.NS': {'weight': 7.5, 'sector': 'IT'},
    'ICICIBANK.NS': {'weight': 7.2, 'sector': 'Financials'},
    'TCS.NS': {'weight': 6.9, 'sector': 'IT'},
    'HINDUNILVR.NS': {'weight': 4.8, 'sector': 'FMCG'},
    'ITC.NS': {'weight': 4.2, 'sector': 'FMCG'},
    'KOTAKBANK.NS': {'weight': 3.8, 'sector': 'Financials'},
    'SBIN.NS': {'weight': 3.5, 'sector': 'Financials'},
    'BHARTIARTL.NS': {'weight': 3.4, 'sector': 'Telecom'},
}

NIFTY50_SECTORS = {
    'Financials': ['HDFCBANK.NS', 'ICICIBANK.NS', 'KOTAKBANK.NS', 'SBIN.NS', 'AXISBANK.NS'],
    'IT': ['TCS.NS', 'INFY.NS', 'HCLTECH.NS', 'WIPRO.NS', 'TECHM.NS'],
    'Energy': ['RELIANCE.NS', 'ONGC.NS', 'BPCL.NS', 'IOC.NS'],
    'FMCG': ['HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS', 'BRITANNIA.NS'],
    'Auto': ['MARUTI.NS', 'M&M.NS', 'TATAMOTORS.NS', 'BAJAJ-AUTO.NS'],
}

# ============================================================================
# ADVANCED TECHNICAL INDICATORS
# ============================================================================

TECHNICAL_INDICATORS = {
    # Volume indicators
    'volume': {
        'OBV': True,           # On-Balance Volume
        'VWAP': True,          # Volume Weighted Average Price
        'MFI': True,           # Money Flow Index
        'CMF': True,           # Chaikin Money Flow
        'Volume_RSI': True,    # RSI on volume
    },
    
    # Momentum
    'momentum': {
        'RSI': True,
        'MACD': True,
        'Stochastic': True,
        'ADX': True,           # Trend strength
        'CCI': True,           # Commodity Channel Index
    },
    
    # Trend
    'trend': {
        'SMA': [20, 50, 100, 200],
        'EMA': [12, 26, 50],
        'Ichimoku': True,
        'Parabolic_SAR': True,
    },
    
    # Volatility
    'volatility': {
        'Bollinger_Bands': True,
        'ATR': True,           # Average True Range
        'Keltner_Channels': True,
    }
}

# ============================================================================
# NEWS & EVENT TRACKING
# ============================================================================

NEWS_SOURCES = {
    'moneycontrol': 'https://www.moneycontrol.com/news/tags/{symbol}.html',
    'economic_times': 'https://economictimes.indiatimes.com/topic/{symbol}',
    'reuters': 'https://www.reuters.com/search/news?blob={symbol}',
    'bloomberg': 'https://www.bloomberg.com/search?query={symbol}',
}

EVENT_TYPES = [
    'earnings', 'dividends', 'splits', 'management_change',
    'merger_acquisition', 'regulatory', 'product_launch',
    'contract_win', 'expansion', 'debt_restructuring'
]

# ============================================================================
# ALERT THRESHOLDS (Enhanced)
# ============================================================================

ADVANCED_ALERTS = {
    # Correlation alerts
    'correlation_breakdown': {
        'threshold': 0.3,  # If correlation drops by 0.3
        'description': 'Major correlation breakdown detected'
    },
    
    # Volume alerts
    'volume_spike': {
        'threshold': 2.0,
        'description': 'Unusual volume spike'
    },
    'volume_dry_up': {
        'threshold': 0.3,
        'description': 'Volume dried up significantly'
    },
    
    # Multi-asset divergence
    'nifty_us_divergence': {
        'threshold': 3.0,  # 3% divergence
        'description': 'NIFTY diverging from US markets'
    },
    
    # Fundamental alerts
    'peer_undervaluation': {
        'threshold': 0.2,  # 20% undervalued vs peers
        'description': 'Asset undervalued relative to peers'
    },
    
    # Technical alerts
    'volume_breakout': {
        'volume_threshold': 2.0,
        'price_threshold': 2.0,
        'description': 'High-volume breakout detected'
    }
}

# ============================================================================
# DATA UPDATE FREQUENCIES
# ============================================================================

UPDATE_FREQUENCIES = {
    'intraday_data': '15min',      # For live tracking
    'daily_data': '1h',             # Update hourly during market
    'fundamental_data': '1d',       # Once per day
    'news_data': '30min',           # Every 30 minutes
    'correlation_calc': '1h',       # Recalculate hourly
}

# ============================================================================
# EXPORT SETTINGS
# ============================================================================

EXPORT_FORMATS = {
    'correlation_matrix': ['csv', 'html', 'png'],
    'volume_analysis': ['csv', 'pdf'],
    'fundamental_comparison': ['xlsx', 'pdf'],
    'alerts': ['json', 'csv'],
}

# Cache settings
CACHE_SETTINGS = {
    'price_data': 3600,        # 1 hour
    'fundamental_data': 86400,  # 24 hours
    'news_data': 1800,          # 30 minutes
    'correlation_data': 3600,   # 1 hour
}
