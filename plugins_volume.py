"""
Volume Analysis Plugin
Integrates volume analysis from bbt2
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, List, Tuple, Optional
import logging
from datetime import datetime

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from data_fetcher import MultiAssetDataFetcher # Assuming DataFetcher from bbt10 can fetch multiple symbols
from ui_components import render_aggrid

logger = logging.getLogger(__name__)

# --- VolumeAnalyzer Class (Ported from bbt2/volume_analyzer.py) ---
class VolumeAnalyzer:
    """
    Professional volume analysis toolkit
    Answers: Is this breakout real? Are smart money accumulating? Volume drying up?
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Initialize volume analyzer
        
        Args:
            data: OHLCV DataFrame with 'Open', 'High', 'Low', 'Close', 'Volume'
        """
        self.data = data.copy()
        # Ensure column names are lowercase for consistency if needed, assuming they are consistent here
        self.data.columns = [col.lower() for col in self.data.columns]
        
        # Pre-calculate returns for efficiency
        self.data['returns'] = self.data['close'].pct_change()
        
        logger.info(f"VolumeAnalyzer initialized")
    
    def calculate_volume_moving_averages(
        self,
        periods: List[int] = [5, 20, 50]
    ) -> pd.DataFrame:
        """
        Calculate volume moving averages
        
        Args:
            periods: MA periods to calculate
            
        Returns:
            DataFrame with volume MAs
        """
        df = self.data.copy()
        
        for period in periods:
            df[f'vol_ma_{period}'] = df['volume'].rolling(window=period).mean()
        
        return df
    
    def detect_volume_spikes(
        self,
        threshold: float = 2.0,
        ma_period: int = 20
    ) -> pd.DataFrame:
        """
        Detect unusual volume spikes
        CRITICAL: Volume spike + price move = institutional activity
        
        Args:
            threshold: Multiple of average volume (2.0 = 2x average)
            ma_period: MA period for baseline
            
        Returns:
            DataFrame with spike information
        """
        df = self.data.copy()
        
        # Calculate average volume
        df['vol_ma'] = df['volume'].rolling(window=ma_period).mean()
        
        # Calculate volume ratio
        df['vol_ratio'] = df['volume'] / df['vol_ma']
        
        # Detect spikes
        df['is_spike'] = df['vol_ratio'] > threshold
        
        # Categorize spikes
        df['spike_type'] = 'normal'
        
        # High volume + strong price move = Breakout
        df.loc[(df['is_spike']) & (abs(df['returns']) > 0.02), 'spike_type'] = 'breakout'
        
        # High volume + weak price move = Exhaustion
        df.loc[(df['is_spike']) & (abs(df['returns']) < 0.005), 'spike_type'] = 'exhaustion'
        
        # High volume + price up = Accumulation climax
        df.loc[(df['is_spike']) & (df['returns'] > 0.02), 'spike_type'] = 'buying_climax'
        
        # High volume + price down = Distribution climax
        df.loc[(df['is_spike']) & (df['returns'] < -0.02), 'spike_type'] = 'selling_climax'
        
        return df
    
    def calculate_obv(self) -> pd.Series:
        """
        Calculate On-Balance Volume (OBV)
        CRITICAL: OBV divergence = smart money moving differently than price
        
        Returns:
            OBV series
        """
        obv = [0]
        
        for i in range(1, len(self.data)):
            if self.data['close'].iloc[i] > self.data['close'].iloc[i-1]:
                obv.append(obv[-1] + self.data['volume'].iloc[i])
            elif self.data['close'].iloc[i] < self.data['close'].iloc[i-1]:
                obv.append(obv[-1] - self.data['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        return pd.Series(obv, index=self.data.index)
    
    def detect_obv_divergence(self, window: int = 20) -> List[Dict]:
        """
        Detect OBV-Price divergence
        CRITICAL SIGNAL: Price making higher highs but OBV not = distribution
        
        Args:
            window: Window for detecting highs/lows
            
        Returns:
            List of divergence events
        """
        df = self.data.copy()
        df['obv'] = self.calculate_obv()
        
        # Find price peaks and troughs
        df['price_peak'] = df['close'] == df['close'].rolling(window=window, center=True).max()
        df['price_trough'] = df['close'] == df['close'].rolling(window=window, center=True).min()
        
        # Find OBV peaks and troughs
        df['obv_peak'] = df['obv'] == df['obv'].rolling(window=window, center=True).max()
        df['obv_trough'] = df['obv'] == df['obv'].rolling(window=window, center=True).min()
        
        divergences = []
        
        # Bearish divergence: Price higher high, OBV lower high
        price_peaks = df[df['price_peak']].index
        for i in range(1, len(price_peaks)):
            date1, date2 = price_peaks[i-1], price_peaks[i]
            
            price_higher = df.loc[date2, 'close'] > df.loc[date1, 'close']
            obv_lower = df.loc[date2, 'obv'] < df.loc[date1, 'obv']
            
            if price_higher and obv_lower:
                divergences.append({
                    'type': 'bearish',
                    'date': date2,
                    'description': 'Price making higher high, but OBV lower = distribution',
                    'price1': df.loc[date1, 'close'],
                    'price2': df.loc[date2, 'close'],
                    'obv1': df.loc[date1, 'obv'],
                    'obv2': df.loc[date2, 'obv']
                })
        
        # Bullish divergence: Price lower low, OBV higher low
        price_troughs = df[df['price_trough']].index
        for i in range(1, len(price_troughs)):
            date1, date2 = price_troughs[i-1], price_troughs[i]
            
            price_lower = df.loc[date2, 'close'] < df.loc[date1, 'close']
            obv_higher = df.loc[date2, 'obv'] > df.loc[date1, 'obv']
            
            if price_lower and obv_higher:
                divergences.append({
                    'type': 'bullish',
                    'date': date2,
                    'description': 'Price making lower low, but OBV higher = accumulation',
                    'price1': df.loc[date1, 'close'],
                    'price2': df.loc[date2, 'close'],
                    'obv1': df.loc[date1, 'obv'],
                    'obv2': df.loc[date2, 'obv']
                })
        
        return divergences
    
    def calculate_vwap(self, period: Optional[int] = None) -> pd.Series:
        """
        Calculate Volume Weighted Average Price (VWAP)
        CRITICAL: Institutional traders use VWAP as benchmark
        
        Args:
            period: Rolling window (None = cumulative from start)
            
        Returns:
            VWAP series
        """
        df = self.data.copy()
        
        # Typical price
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        # Price * Volume
        df['pv'] = df['typical_price'] * df['volume']
        
        if period is None:
            # Cumulative VWAP
            vwap = df['pv'].cumsum() / df['volume'].cumsum()
        else:
            # Rolling VWAP
            vwap = df['pv'].rolling(window=period).sum() / df['volume'].rolling(window=period).sum()
        
        return vwap
    
    def calculate_money_flow_index(self, period: int = 14) -> pd.Series:
        """
        Calculate Money Flow Index (MFI)
        Like RSI but uses volume - shows overbought/oversold with volume confirmation
        
        Args:
            period: MFI period
            
        Returns:
            MFI series
        """
        df = self.data.copy()
        
        # Typical price
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        # Money flow
        df['money_flow'] = df['typical_price'] * df['volume']
        
        # Positive and negative money flow
        df['price_change'] = df['typical_price'].diff()
        df['positive_flow'] = df['money_flow'].where(df['price_change'] > 0, 0)
        df['negative_flow'] = df['money_flow'].where(df['price_change'] < 0, 0)
        
        # Money flow ratio
        positive_sum = df['positive_flow'].rolling(window=period).sum()
        negative_sum = df['negative_flow'].rolling(window=period).sum()
        
        money_ratio = positive_sum / negative_sum
        
        # MFI
        mfi = 100 - (100 / (1 + money_ratio))
        
        return mfi
    
    def calculate_volume_profile(self, bins: int = 50) -> Dict:
        """
        Calculate volume profile (volume at each price level)
        CRITICAL: Shows where most trading happened = support/resistance
        
        Args:
            bins: Number of price bins
            
        Returns:
            Volume profile dict
        """
        df = self.data.copy()
        
        # Create price bins
        price_min = df['low'].min()
        price_max = df['high'].max()
        price_bins = np.linspace(price_min, price_max, bins + 1)
        
        # Bin labels (midpoints)
        bin_labels = (price_bins[:-1] + price_bins[1:]) / 2
        
        # Assign each bar to price bins based on typical price
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['price_bin'] = pd.cut(df['typical_price'], bins=price_bins, labels=bin_labels)
        
        # Sum volume for each price bin
        volume_profile = df.groupby('price_bin')['volume'].sum()
        
        # Find Point of Control (POC) - price level with highest volume
        poc_price = volume_profile.idxmax()
        poc_volume = volume_profile.max()
        
        # Value area (70% of volume)
        total_volume = volume_profile.sum()
        target_volume = total_volume * 0.70
        
        # Sort by volume and find value area
        sorted_profile = volume_profile.sort_values(ascending=False)
        cumsum = sorted_profile.cumsum()
        value_area_prices = sorted_profile[cumsum <= target_volume].index.tolist()
        
        return {
            'profile': volume_profile.to_dict(),
            'poc_price': float(poc_price),
            'poc_volume': float(poc_volume),
            'value_area_high': max(value_area_prices) if value_area_prices else None,
            'value_area_low': min(value_area_prices) if value_area_prices else None,
            'current_price': float(df['close'].iloc[-1]) if not df.empty else None,
            'price_vs_poc': float(((df['close'].iloc[-1] / poc_price) - 1) * 100) if not df.empty else None
        }
    
    def generate_volume_report(self) -> Dict:
        """
        Generate comprehensive volume analysis report
        
        Returns:
            Complete volume analysis
        """
        report = {
            'analysis_date': datetime.now(),
            'data_period': {
                'start': self.data.index[0],
                'end': self.data.index[-1]
            }
        }
        
        # Volume statistics
        report['volume_stats'] = {
            'average': float(self.data['volume'].mean()),
            'median': float(self.data['volume'].median()),
            'std': float(self.data['volume'].std()),
            'latest': float(self.data['volume'].iloc[-1]),
            'latest_vs_avg': float(self.data['volume'].iloc[-1] / self.data['volume'].mean())
        }
        
        # OBV and divergences
        report['obv'] = {
            'current': float(self.calculate_obv().iloc[-1]),
            'divergences': self.detect_obv_divergence()
        }
        
        # VWAP
        vwap = self.calculate_vwap(period=20)
        report['vwap'] = {
            'current': float(vwap.iloc[-1]),
            'price_vs_vwap': float(((self.data['close'].iloc[-1] / vwap.iloc[-1]) - 1) * 100)
        }
        
        # MFI
        mfi = self.calculate_money_flow_index()
        report['mfi'] = {
            'current': float(mfi.iloc[-1]),
            'status': 'overbought' if mfi.iloc[-1] > 80 else 'oversold' if mfi.iloc[-1] < 20 else 'neutral'
        }
        
        # Volume spikes
        spike_df = self.detect_volume_spikes()
        recent_spikes = spike_df[spike_df['is_spike']].tail(5)
        report['recent_spikes'] = recent_spikes[['vol_ratio', 'spike_type', 'returns']].to_dict('records')
        
        # Volume profile
        report['volume_profile'] = self.calculate_volume_profile()
        
        return report

# --- VolumeAnalysisPlugin ---
@register_plugin
class VolumeAnalysisPlugin(AnalysisPlugin):
    """
    Provides professional volume analysis including OBV, VWAP, MFI, volume spikes, and volume profile.
    Ported from bbt2/volume_analyzer.py and bbt2/app_professional.py
    """

    @property
    def name(self) -> str:
        return "Volume Analysis"

    @property
    def icon(self) -> str:
        return "📊"

    @property
    def description(self) -> str:
        return "In-depth volume intelligence: OBV, VWAP, MFI, spikes, profile."

    @property
    def category(self) -> str:
        return "asset"

    @property
    def enabled_by_default(self) -> bool:
        return True # Can be enabled by default

    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        price_data: pd.DataFrame = context.get('price_data')

        if price_data is None or price_data.empty:
            return AnalysisResult(
                success=False,
                data={},
                error="Price data not available for volume analysis."
            )
        
        # Normalize columns to Title Case for consistency
        # Handle MultiIndex if present
        df = price_data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Rename to Title Case
        col_map = {c: c.capitalize() for c in df.columns}
        df.rename(columns=col_map, inplace=True)
        
        # Ensure required columns are present (Open, High, Low, Close, Volume)
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
             return AnalysisResult(
                success=False,
                data={},
                error=f"Missing required columns in price data for volume analysis. Need: {required_cols}. Found: {list(df.columns)}"
            )

        try:
            volume_analyzer = VolumeAnalyzer(df) # Pass the normalized DF
            vol_report = volume_analyzer.generate_volume_report()

            return AnalysisResult(
                success=True,
                data={
                    "volume_report": vol_report,
                    "price_data": df # Pass normalized price data for plotting
                }
            )
        except Exception as e:
            logger.error(f"Error during volume analysis: {e}")
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")

        if not result.success:
            st.error(f"Volume Analysis Error: {result.error}")
            return
        
        vol_report = result.data["volume_report"]
        primary_data = result.data["price_data"]

        # Volume statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Latest Volume",
                f"{vol_report['volume_stats']['latest']:,.0f}"
            )
        
        with col2:
            vs_avg = vol_report['volume_stats']['latest_vs_avg']
            delta_color = "inverse" if vs_avg > 1 else "normal" # Streamlit handles color based on value vs delta
            st.metric(
                "vs Average",
                f"{vs_avg:.2f}x",
                delta=f"{(vs_avg - 1) * 100:.1f}%"
            )
        
        with col3:
            st.metric(
                "MFI",
                f"{vol_report['mfi']['current']:.1f}",
                delta=vol_report['mfi']['status']
            )
        
        with col4:
            st.metric(
                "vs VWAP",
                f"{vol_report['vwap']['price_vs_vwap']:.2f}%"
            )
        
        st.markdown("---")
        
        # OBV Analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📉 On-Balance Volume (OBV)")
            
            # Plot OBV vs Price
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=('Price', 'OBV')
            )
            
            fig.add_trace(
                go.Scatter(x=primary_data.index, y=primary_data['Close'], # Use 'Close' from original price_data
                          name='Price', line=dict(color='blue')),
                row=1, col=1
            )
            
            obv_series = VolumeAnalyzer(primary_data).calculate_obv() # Recalculate OBV for plotting
            fig.add_trace(
                go.Scatter(x=obv_series.index, y=obv_series,
                          name='OBV', line=dict(color='purple')),
                row=2, col=1
            )
            
            fig.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🎯 OBV Divergences")
            
            divergences = vol_report['obv']['divergences']
            
            if divergences:
                st.markdown(f"**Found {len(divergences)} divergence(s):**")
                
                for div in divergences[-5:]:  # Last 5
                    div_type = div['type']
                    color = "green" if div_type == "bullish" else "red" # Use Streamlit's color mapping
                    
                    st.markdown(f"""
                    <span style='color:{color}'>**{div['date'].strftime('%Y-%m-%d')}**: 
                    {div_type.upper()}</span>  
                    *{div['description']}*
                    """, unsafe_allow_html=True)
            else:
                st.info("No significant OBV divergences detected")
        
        st.markdown("---")
        
        # Volume spikes
        st.subheader("⚡ Recent Volume Spikes")
        
        if vol_report['recent_spikes']:
            spike_df = pd.DataFrame(vol_report['recent_spikes'])
            spike_df['vol_ratio'] = spike_df['vol_ratio'].apply(lambda x: f"{x:.2f}x")
            spike_df['returns'] = spike_df['returns'].apply(lambda x: f"{x*100:.2f}%")
            render_aggrid(spike_df, height=250)
        else:
            st.info("No unusual volume spikes recently")
        
        st.markdown("---")
        
        # Volume Profile
        st.subheader("📊 Volume Profile")
        st.markdown("*Where did most trading happen?*")
        
        vol_profile = vol_report['volume_profile']
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Plot volume profile
            profile_data = vol_profile['profile']
            # Convert dictionary to DataFrame for plotting
            profile_df = pd.DataFrame(list(profile_data.items()), columns=['Price', 'Volume'])
            profile_df['Price'] = profile_df['Price'].astype(float)
            profile_df = profile_df.sort_values('Price')

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=profile_df['Volume'],
                y=profile_df['Price'],
                orientation='h',
                marker=dict(color='steelblue')
            ))
            
            # Add POC line
            if vol_profile['poc_price'] is not None:
                fig.add_hline(
                    y=vol_profile['poc_price'],
                    line_dash="dash",
                    line_color="red",
                    annotation_text="POC"
                )
            
            # Add current price line
            if vol_profile['current_price'] is not None:
                fig.add_hline(
                    y=vol_profile['current_price'],
                    line_dash="dot",
                    line_color="green",
                    annotation_text="Current"
                )
            
            fig.update_layout(
                title="Volume by Price Level",
                xaxis_title="Volume",
                yaxis_title="Price",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**Volume Profile Metrics:**")
            if vol_profile['poc_price'] is not None:
                st.metric("POC Price", f"₹{vol_profile['poc_price']:.2f}")
            if vol_profile['value_area_high'] is not None:
                st.metric("Value Area High", f"₹{vol_profile['value_area_high']:.2f}")
            if vol_profile['value_area_low'] is not None:
                st.metric("Value Area Low", f"₹{vol_profile['value_area_low']:.2f}")
            if vol_profile['price_vs_poc'] is not None:
                st.metric("Current vs POC", f"{vol_profile['price_vs_poc']:.2f}%")
