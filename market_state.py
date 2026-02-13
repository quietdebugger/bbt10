"""
Market State Analyzer
Determines market regime (Trend, Volatility, Options Pressure)
BEFORE metrics are calculated.
Borrowed from bbt9
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
from enum import Enum

class TrendState(Enum):
    BULLISH_STRONG = "Strong Uptrend"
    BULLISH_WEAK = "Weak Uptrend"
    SIDEWAYS = "Range Bound"
    BEARISH_WEAK = "Weak Downtrend"
    BEARISH_STRONG = "Strong Downtrend"
    INSUFFICIENT_DATA = "Insufficient data"

class VolatilityState(Enum):
    HIGH_EXPANDING = "High & Expanding"
    HIGH_CONTRACTING = "High & Contracting"
    LOW_EXPANDING = "Low & Expanding"
    LOW_STABLE = "Low & Stable"
    INSUFFICIENT_DATA = "Insufficient data"

class OptionsPressure(Enum):
    BULLISH_PUT_WRITING = "Bullish (Put Writing)"
    BEARISH_CALL_WRITING = "Bearish (Call Writing)"
    LONG_BUILDUP = "Bullish (Long Buildup)"
    SHORT_BUILDUP = "Bearish (Short Buildup)"
    NEUTRAL = "Neutral / Mixed"
    INSUFFICIENT_LIQUIDITY = "Insufficient liquidity"

@dataclass
class DataQuality:
    level: str  # "HIGH", "MEDIUM", "LOW", "CRITICAL"
    reason: str
    
    def is_usable(self) -> bool:
        return self.level != "CRITICAL"

@dataclass
class MarketState:
    trend: TrendState
    volatility: VolatilityState
    options_pressure: OptionsPressure
    confidence: str
    conflicting_signals: List[str]
    price_data_quality: DataQuality
    options_data_quality: Optional[DataQuality]
    
    def get_summary(self) -> str:
        return f"{self.trend.value} | Volatility: {self.volatility.value}"

class MarketStateAnalyzer:
    def __init__(self, price_data: pd.DataFrame):
        self.data = price_data
        self.bars = len(price_data)
        
    def _analyze_trend(self) -> TrendState:
        if self.bars < 50: return TrendState.INSUFFICIENT_DATA
        
        sma20 = self.data['close'].rolling(20).mean().iloc[-1]
        sma50 = self.data['close'].rolling(50).mean().iloc[-1]
        price = self.data['close'].iloc[-1]
        
        if price > sma20 > sma50: return TrendState.BULLISH_STRONG
        if price > sma50 and price < sma20: return TrendState.BULLISH_WEAK
        if price < sma20 < sma50: return TrendState.BEARISH_STRONG
        if price < sma50 and price > sma20: return TrendState.BEARISH_WEAK
        return TrendState.SIDEWAYS

    def _analyze_volatility(self) -> VolatilityState:
        if self.bars < 20: return VolatilityState.INSUFFICIENT_DATA
        
        # Simple ATR based logic
        tr = self.data['high'] - self.data['low']
        atr10 = tr.rolling(10).mean().iloc[-1]
        atr20 = tr.rolling(20).mean().iloc[-1]
        
        avg_price = self.data['close'].mean()
        atr_pct = (atr10 / avg_price) * 100
        
        if atr_pct > 2.0: # High vol
            return VolatilityState.HIGH_EXPANDING if atr10 > atr20 else VolatilityState.HIGH_CONTRACTING
        else:
            return VolatilityState.LOW_EXPANDING if atr10 > atr20 else VolatilityState.LOW_STABLE

    def analyze(self, option_chain: Optional[pd.DataFrame], pcr_data: Optional[Dict], oi_analysis: Optional[Dict]) -> MarketState:
        trend = self._analyze_trend()
        vol = self._analyze_volatility()
        
        # Options Pressure
        opt_pressure = OptionsPressure.INSUFFICIENT_LIQUIDITY
        opt_quality = None
        
        conflicts = []
        
        if option_chain is not None and not option_chain.empty and pcr_data:
            opt_quality = DataQuality("HIGH", "Liquid options data")
            pcr = pcr_data.get('pcr_oi', 1.0)
            
            if pcr > 1.2: opt_pressure = OptionsPressure.BULLISH_PUT_WRITING
            elif pcr < 0.7: opt_pressure = OptionsPressure.BEARISH_CALL_WRITING
            else: opt_pressure = OptionsPressure.NEUTRAL
            
            # Check conflicts
            if "BULLISH" in trend.name and "BEARISH" in opt_pressure.name:
                conflicts.append("Price is Uptrending but Options are Bearish")
            if "BEARISH" in trend.name and "BULLISH" in opt_pressure.name:
                conflicts.append("Price is Downtrending but Options are Bullish")
        
        confidence = "HIGH" if not conflicts and trend != TrendState.INSUFFICIENT_DATA else "LOW"
        
        return MarketState(
            trend=trend,
            volatility=vol,
            options_pressure=opt_pressure,
            confidence=confidence,
            conflicting_signals=conflicts,
            price_data_quality=DataQuality("HIGH", "Data available"),
            options_data_quality=opt_quality
        )
