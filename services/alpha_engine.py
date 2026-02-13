"""
Alpha Engine - Quantitative Scoring System
Proprietary scoring logic for Momentum, Trend, and Volatility.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class AlphaEngine:
    
    def __init__(self, df: pd.DataFrame):
        """
        Expects a DataFrame with OHLCV data.
        """
        self.df = df.copy()
        if not self.df.empty:
            self._calculate_indicators()

    def _calculate_indicators(self):
        """Calculates Technical Indicators manually to avoid dependencies"""
        close = self.df['Close']
        
        # 1. SMAs
        self.df['SMA_20'] = close.rolling(window=20).mean()
        self.df['SMA_50'] = close.rolling(window=50).mean()
        self.df['SMA_200'] = close.rolling(window=200).mean()
        
        # 2. RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        self.df['RSI'] = 100 - (100 / (1 + rs))
        
        # 3. MACD (12, 26, 9)
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        self.df['MACD'] = exp12 - exp26
        self.df['Signal'] = self.df['MACD'].ewm(span=9, adjust=False).mean()
        self.df['MACD_Hist'] = self.df['MACD'] - self.df['Signal']
        
        # 4. Bollinger Bands (20, 2)
        std = close.rolling(window=20).std()
        self.df['BB_Upper'] = self.df['SMA_20'] + (std * 2)
        self.df['BB_Lower'] = self.df['SMA_20'] - (std * 2)
        self.df['BB_Width'] = (self.df['BB_Upper'] - self.df['BB_Lower']) / self.df['SMA_20']
        
        # 5. Volatility (Annualized)
        self.df['Log_Ret'] = np.log(close / close.shift(1))
        self.df['Volatility'] = self.df['Log_Ret'].rolling(window=21).std() * np.sqrt(252)

    def get_momentum_score(self) -> float:
        """Score 0-40 based on RSI and MACD"""
        score = 0
        if self.df.empty: return 0
        
        current = self.df.iloc[-1]
        
        # RSI Logic
        rsi = current['RSI']
        if 50 < rsi < 70: score += 15 # Bullish Zone
        elif 40 < rsi <= 50: score += 5 # Neutral/Recovery
        elif rsi >= 70: score += 10 # Strong Momentum (but watch for OB)
        
        # MACD Logic
        if current['MACD'] > current['Signal']: score += 15 # Bullish Crossover active
        if current['MACD_Hist'] > 0 and current['MACD_Hist'] > self.df.iloc[-2]['MACD_Hist']:
            score += 10 # Accelerating Momentum
            
        return min(40, score)

    def get_trend_score(self) -> float:
        """Score 0-30 based on Moving Averages"""
        score = 0
        if self.df.empty: return 0
        
        current = self.df.iloc[-1]
        close = current['Close']
        
        # Price Position
        if close > current['SMA_20']: score += 10
        if close > current['SMA_50']: score += 10
        if close > current['SMA_200']: score += 10
        
        # Alignment (Golden Cross check is implied by ordering)
        if current['SMA_20'] > current['SMA_50']: score += 5
        
        return min(30, score)

    def get_volatility_score(self) -> float:
        """Score 0-30 based on Volatility Squeeze/Expansion"""
        score = 0
        if self.df.empty: return 0
        
        current = self.df.iloc[-1]
        
        # Low volatility often precedes a move (Squeeze)
        # Compare current BB Width to 6-month average
        avg_width = self.df['BB_Width'].tail(126).mean()
        if current['BB_Width'] < avg_width:
            score += 15 # Squeeze potential
            
        # Breakout check: Price near upper band?
        if current['Close'] > current['SMA_20'] and (current['BB_Upper'] - current['Close']) / current['Close'] < 0.02:
            score += 15 # Near breakout
            
        return min(30, score)

    def analyze(self) -> Dict:
        """Returns comprehensive analysis"""
        if self.df.empty:
            return {"score": 0, "rating": "No Data"}
            
        mom = self.get_momentum_score()
        trend = self.get_trend_score()
        vol = self.get_volatility_score()
        
        total = mom + trend + vol
        
        # Rating
        if total >= 80: rating = "STRONG BUY 🚀"
        elif total >= 60: rating = "BUY ✅"
        elif total >= 40: rating = "HOLD ⏸️"
        elif total >= 20: rating = "WEAK ⚠️"
        else: rating = "SELL 🔻"
        
        return {
            "total_score": total,
            "components": {
                "momentum": mom,
                "trend": trend,
                "volatility": vol
            },
            "rating": rating,
            "indicators": self.df.iloc[-1].to_dict()
        }
