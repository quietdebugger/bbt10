"""
Whale Hunter Plugin
Integrates Whale Hunter from bbt3 for smart money detection
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from ui_components import render_aggrid

logger = logging.getLogger(__name__)

# --- Ported WhaleHunter from bbt3/whale_hunter.py ---

class WhaleHunter:
    """
    Detect smart money activity vs retail speculation
    Delivery % scanner, OBV divergences, dark pool logic
    """
    
    def __init__(self, data: pd.DataFrame, symbol: str):
        """
        Initialize whale hunter
        
        Args:
            data: OHLCV data with volume
            symbol: Symbol identifier
        """
        self.data = data.copy()
        self.symbol = symbol
        
        # Ensure lowercase columns
        col_map = {c: c.lower() for c in self.data.columns}
        self.data.rename(columns=col_map, inplace=True)
        
        # Calculate returns
        self.data['returns'] = self.data['close'].pct_change()
        
        # For NSE stocks, we'll estimate delivery %
        # (In reality, this comes from NSE delivery data)
        self._estimate_delivery_percentage()
        
        logger.info(f"WhaleHunter initialized for {symbol}")
    
    def _estimate_delivery_percentage(self):
        """
        Estimate delivery percentage
        
        For NSE stocks, delivery data should be fetched separately.
        Here we estimate using volume patterns (placeholder logic).
        """
        # Placeholder: estimate based on volume volatility
        # Low volume volatility = more delivery
        # High volume volatility = more intraday
        
        vol_ma = self.data['volume'].rolling(window=20).mean()
        vol_std = self.data['volume'].rolling(window=20).std()
        
        # Normalized volume
        vol_zscore = (self.data['volume'] - vol_ma) / (vol_std + 1e-10)
        
        # Estimate: baseline 40%, adjusted by volume stability
        # More stable volume = higher delivery %
        self.data['delivery_pct_est'] = 40 + 20 * (1 / (1 + np.abs(vol_zscore)))
        
        # Cap between 20% and 80%
        self.data['delivery_pct_est'] = self.data['delivery_pct_est'].clip(20, 80)
    
    def scan_high_delivery_days(
        self,
        delivery_threshold: float = 60.0,
        volume_threshold: float = 1.5
    ) -> pd.DataFrame:
        """
        Scan for high delivery percentage days
        HIGH DELIVERY + HIGH VOLUME = INSTITUTIONAL ACCUMULATION
        """
        df = self.data.copy()
        
        # Volume ratio
        vol_ma_20 = df['volume'].rolling(window=20).mean()
        df['vol_ratio'] = df['volume'] / vol_ma_20
        
        # Filter high delivery days
        high_delivery = df[
            (df['delivery_pct_est'] >= delivery_threshold) &
            (df['vol_ratio'] >= volume_threshold)
        ].copy()
        
        # Categorize
        high_delivery['signal_type'] = 'accumulation'
        high_delivery.loc[high_delivery['returns'] < 0, 'signal_type'] = 'distribution'
        
        # Strength score (0-100)
        high_delivery['strength_score'] = (
            (high_delivery['delivery_pct_est'] / 80) * 50 +
            (high_delivery['vol_ratio'] / 3) * 50
        ).clip(0, 100)
        
        return high_delivery[['close', 'volume', 'vol_ratio', 'delivery_pct_est', 
                             'returns', 'signal_type', 'strength_score']]
    
    def detect_obv_divergence_precise(
        self,
        window: int = 20,
        sensitivity: float = 0.02
    ) -> List[Dict]:
        """
        Precise OBV divergence detection
        SPECIFIC ALERT: Price lower low, OBV higher low = HIDDEN BULLISHNESS
        """
        df = self.data.copy()
        
        # Calculate OBV
        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        df['obv'] = obv
        
        # Find local peaks and troughs
        df['price_local_max'] = df['close'].rolling(window=window, center=True).max()
        df['price_local_min'] = df['close'].rolling(window=window, center=True).min()
        
        df['obv_local_max'] = df['obv'].rolling(window=window, center=True).max()
        df['obv_local_min'] = df['obv'].rolling(window=window, center=True).min()
        
        df['is_price_peak'] = df['close'] == df['price_local_max']
        df['is_price_trough'] = df['close'] == df['price_local_min']
        
        df['is_obv_peak'] = df['obv'] == df['obv_local_max']
        df['is_obv_trough'] = df['obv'] == df['obv_local_min']
        
        divergences = []
        
        # BULLISH DIVERGENCE: Price makes lower low, OBV makes higher low
        price_troughs = df[df['is_price_trough']].index
        
        for i in range(1, len(price_troughs)):
            date1, date2 = price_troughs[i-1], price_troughs[i]
            
            price1 = df.loc[date1, 'close']
            price2 = df.loc[date2, 'close']
            
            obv1 = df.loc[date1, 'obv']
            obv2 = df.loc[date2, 'obv']
            
            # Price lower low
            price_lower = (price2 - price1) / price1 < -sensitivity
            
            # OBV higher low
            obv_higher = (obv2 - obv1) / abs(obv1) > sensitivity if obv1 != 0 else False
            
            if price_lower and obv_higher:
                divergences.append({
                    'type': 'BULLISH',
                    'date': date2,
                    'price1': price1,
                    'price2': price2,
                    'price_change_pct': ((price2 - price1) / price1) * 100,
                    'obv1': obv1,
                    'obv2': obv2,
                    'obv_change_pct': ((obv2 - obv1) / abs(obv1)) * 100 if obv1 != 0 else 0,
                    'description': 'HIDDEN BULLISHNESS: Price lower low but OBV higher low',
                    'signal_strength': min(100, abs((price2 - price1) / price1) * 100 * 5),
                    'action': 'BUY SIGNAL - Smart money accumulating despite price weakness'
                })
        
        # BEARISH DIVERGENCE: Price makes higher high, OBV makes lower high
        price_peaks = df[df['is_price_peak']].index
        
        for i in range(1, len(price_peaks)):
            date1, date2 = price_peaks[i-1], price_peaks[i]
            
            price1 = df.loc[date1, 'close']
            price2 = df.loc[date2, 'close']
            
            obv1 = df.loc[date1, 'obv']
            obv2 = df.loc[date2, 'obv']
            
            # Price higher high
            price_higher = (price2 - price1) / price1 > sensitivity
            
            # OBV lower high
            obv_lower = (obv2 - obv1) / abs(obv1) < -sensitivity if obv1 != 0 else False
            
            if price_higher and obv_lower:
                divergences.append({
                    'type': 'BEARISH',
                    'date': date2,
                    'price1': price1,
                    'price2': price2,
                    'price_change_pct': ((price2 - price1) / price1) * 100,
                    'obv1': obv1,
                    'obv2': obv2,
                    'obv_change_pct': ((obv2 - obv1) / abs(obv1)) * 100 if obv1 != 0 else 0,
                    'description': 'DISTRIBUTION ALERT: Price higher high but OBV lower high',
                    'signal_strength': min(100, abs((price2 - price1) / price1) * 100 * 5),
                    'action': 'SELL SIGNAL - Smart money distributing despite price strength'
                })
        
        return divergences
    
    def detect_dark_pool_activity(
        self,
        vwap_deviation_threshold: float = 2.0,
        volume_threshold: float = 2.0
    ) -> pd.DataFrame:
        """
        Estimate institutional positioning using VWAP deviations
        LARGE BLOCKS + VWAP DEVIATION = DARK POOL ACTIVITY
        """
        df = self.data.copy()
        
        # Calculate VWAP
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['pv'] = df['typical_price'] * df['volume']
        
        df['vwap_20'] = df['pv'].rolling(window=20).sum() / df['volume'].rolling(window=20).sum()
        
        # VWAP deviation
        df['vwap_deviation'] = ((df['close'] - df['vwap_20']) / df['vwap_20']) * 100
        
        # Volume spike
        vol_ma = df['volume'].rolling(window=20).mean()
        df['vol_ratio'] = df['volume'] / vol_ma
        
        # Large block detection
        # High volume + significant VWAP deviation = institutions
        df['dark_pool_score'] = 0
        
        # Buying pressure: Price > VWAP + high volume
        df.loc[
            (df['vwap_deviation'] > vwap_deviation_threshold) &
            (df['vol_ratio'] > volume_threshold),
            'dark_pool_score'
        ] = df['vol_ratio'] * abs(df['vwap_deviation'])
        
        # Selling pressure: Price < VWAP + high volume
        df.loc[
            (df['vwap_deviation'] < -vwap_deviation_threshold) &
            (df['vol_ratio'] > volume_threshold),
            'dark_pool_score'
        ] = -df['vol_ratio'] * abs(df['vwap_deviation'])
        
        # Filter significant activity
        dark_pool_days = df[df['dark_pool_score'] != 0].copy()
        
        dark_pool_days['activity_type'] = 'BUYING'
        dark_pool_days.loc[dark_pool_days['dark_pool_score'] < 0, 'activity_type'] = 'SELLING'
        
        dark_pool_days['strength'] = abs(dark_pool_days['dark_pool_score'])
        
        return dark_pool_days[['close', 'volume', 'vol_ratio', 'vwap_deviation', 
                               'dark_pool_score', 'activity_type', 'strength']].sort_values('strength', ascending=False)
    
    def calculate_accumulation_distribution_line(self) -> pd.Series:
        """
        Calculate Accumulation/Distribution Line
        Shows money flow (buying vs selling pressure)
        """
        df = self.data.copy()
        
        # Money Flow Multiplier
        mfm = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
        mfm = mfm.fillna(0)
        
        # Money Flow Volume
        mfv = mfm * df['volume']
        
        # A/D Line (cumulative)
        ad_line = mfv.cumsum()
        
        return ad_line
    
    def detect_smart_money_vs_retail(self) -> Dict:
        """
        Distinguish smart money (delivery) from retail (intraday)
        """
        df = self.data.copy()
        
        # Recent 20 days
        recent = df.tail(20)
        
        # Average delivery %
        avg_delivery = recent['delivery_pct_est'].mean()
        
        # Trend in delivery %
        delivery_trend = recent['delivery_pct_est'].iloc[-1] - recent['delivery_pct_est'].iloc[0]
        
        # Volume trend
        vol_ma_recent = recent['volume'].mean()
        vol_ma_overall = df['volume'].mean()
        vol_trend = (vol_ma_recent / vol_ma_overall - 1) * 100
        
        # OBV trend
        obv = self.calculate_obv()
        obv_recent = obv.iloc[-1]
        obv_20_days_ago = obv.iloc[-20]
        obv_trend = ((obv_recent - obv_20_days_ago) / abs(obv_20_days_ago)) * 100 if obv_20_days_ago != 0 else 0
        
        # Classification
        if avg_delivery > 60:
            market_type = "INSTITUTIONAL DOMINATED"
            interpretation = "Strong delivery % indicates smart money participation"
        elif avg_delivery > 45:
            market_type = "BALANCED"
            interpretation = "Mix of institutional and retail participation"
        else:
            market_type = "RETAIL DOMINATED"
            interpretation = "Low delivery % indicates speculative trading"
        
        # Momentum
        if delivery_trend > 5:
            momentum = "INSTITUTIONS ENTERING"
        elif delivery_trend < -5:
            momentum = "INSTITUTIONS EXITING"
        else:
            momentum = "STABLE"
        
        return {
            'market_type': market_type,
            'avg_delivery_pct': avg_delivery,
            'delivery_trend': delivery_trend,
            'interpretation': interpretation,
            'momentum': momentum,
            'volume_trend_pct': vol_trend,
            'obv_trend_pct': obv_trend,
            'current_participation': {
                'institutional_est': f"{avg_delivery:.1f}%",
                'retail_est': f"{100 - avg_delivery:.1f}%"
            }
        }
    
    def calculate_obv(self) -> pd.Series:
        """Calculate On-Balance Volume"""
        obv = [0]
        for i in range(1, len(self.data)):
            if self.data['close'].iloc[i] > self.data['close'].iloc[i-1]:
                obv.append(obv[-1] + self.data['volume'].iloc[i])
            elif self.data['close'].iloc[i] < self.data['close'].iloc[i-1]:
                obv.append(obv[-1] - self.data['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        return pd.Series(obv, index=self.data.index)
    
    def generate_whale_report(self) -> Dict:
        """
        Generate comprehensive smart money report
        """
        report = {
            'symbol': self.symbol,
            'analysis_date': datetime.now()
        }
        
        # High delivery days
        high_delivery = self.scan_high_delivery_days()
        report['high_delivery_days'] = {
            'count': len(high_delivery),
            'recent': high_delivery.tail(5).to_dict('records') if not high_delivery.empty else []
        }
        
        # OBV divergences
        divergences = self.detect_obv_divergence_precise()
        report['obv_divergences'] = {
            'count': len(divergences),
            'recent': divergences[-5:] if divergences else [],
            'latest': divergences[-1] if divergences else None
        }
        
        # Dark pool activity
        dark_pool = self.detect_dark_pool_activity()
        report['dark_pool'] = {
            'count': len(dark_pool),
            'top_events': dark_pool.head(5).to_dict('records') if not dark_pool.empty else []
        }
        
        # Smart money vs retail
        participation = self.detect_smart_money_vs_retail()
        report['market_participation'] = participation
        
        # A/D line
        ad_line = self.calculate_accumulation_distribution_line()
        report['ad_line'] = {
            'current': float(ad_line.iloc[-1]) if not ad_line.empty else 0,
            'trend': 'ACCUMULATION' if not ad_line.empty and ad_line.iloc[-1] > ad_line.iloc[-20] else 'DISTRIBUTION'
        }
        
        return report


# --- Whale Hunter Plugin ---

@register_plugin
class WhaleAnalysisPlugin(AnalysisPlugin):
    """
    Detects smart money, dark pools, and delivery patterns
    """
    
    @property
    def name(self) -> str:
        return "Whale Hunter"
    
    @property
    def icon(self) -> str:
        return "🐋"
    
    @property
    def description(self) -> str:
        return "Institutional tracking: Dark pools, delivery %, OBV divergence"
    
    @property
    def category(self) -> str:
        return "asset"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        primary_data = context.get('price_data')
        symbol = context.get('symbol', 'Unknown')
        
        if primary_data is None or primary_data.empty:
            return AnalysisResult(success=False, data={}, error="Price data unavailable")
            
        try:
            hunter = WhaleHunter(primary_data, symbol)
            report = hunter.generate_whale_report()
            
            return AnalysisResult(
                success=True,
                data={'report': report}
            )
        except Exception as e:
            logger.error(f"Error during whale analysis for {symbol}: {e}")
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.warning(f"Whale analysis unavailable: {result.error}")
            return
            
        report = result.data.get('report', {})
        participation = report.get('market_participation', {})
        
        # 1. Market Participation
        st.markdown("#### 🏛️ Market Participation")
        market_type = participation.get('market_type', 'UNKNOWN')
        color = "green" if "INSTITUTIONAL" in market_type else "orange" if "BALANCED" in market_type else "red"
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Market Type", market_type)
        col2.metric("Est. Delivery %", f"{participation.get('avg_delivery_pct', 0):.1f}%")
        col3.metric("Momentum", participation.get('momentum', 'STABLE'))
        
        st.info(f"**Insight**: {participation.get('interpretation', 'N/A')}")
        
        st.markdown("---")
        
        # 2. Dark Pool Activity
        dark_pool = report.get('dark_pool', {})
        st.markdown("#### 🌑 Dark Pool / Large Block Activity")
        
        if dark_pool.get('count', 0) > 0:
            st.warning(f"Detected {dark_pool['count']} significant block trades/dark pool events recently.")
            events = pd.DataFrame(dark_pool['top_events'])
            if not events.empty:
                # Format for display
                display_events = events[['activity_type', 'strength', 'vwap_deviation', 'vol_ratio']].copy()
                display_events.columns = ['Action', 'Strength', 'VWAP Dev %', 'Vol Ratio']
                render_aggrid(display_events, height=200)
        else:
            st.success("No suspicious dark pool activity detected recently.")
            
        st.markdown("---")
        
        # 3. OBV Divergences
        obv = report.get('obv_divergences', {})
        st.markdown("#### 📉 Smart Money Divergences (OBV)")
        
        if obv.get('count', 0) > 0:
            latest = obv.get('latest')
            if latest:
                type_ = latest['type']
                color = "green" if type_ == "BULLISH" else "red"
                st.markdown(f"**Latest Signal**: :{color}[{type_}] on {latest['date'].strftime('%Y-%m-%d')}")
                st.write(latest['description'])
                st.write(f"**Action**: {latest['action']}")
        else:
            st.info("Price and volume are moving in sync (no divergence).")
