"""
Interactive Charting Plugin
Professional financial charting with overlays and interactive features.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin

logger = logging.getLogger(__name__)

@register_plugin
class InteractiveChartPlugin(AnalysisPlugin):
    """
    Professional Interactive Candlestick Chart
    Includes:
    - Candlesticks
    - Moving Averages (20, 50, 200)
    - VWAP
    - Volume Subplot
    """
    
    @property
    def name(self) -> str:
        return "Interactive Chart"
    
    @property
    def icon(self) -> str:
        return "📈"
    
    @property
    def description(self) -> str:
        return "Professional candlestick chart with technical overlays."
    
    @property
    def category(self) -> str:
        return "asset"
    
    @property
    def enabled_by_default(self) -> bool:
        return True
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        price_data = context.get('price_data')
        symbol = context.get('symbol', 'Unknown')
        
        if price_data is None or price_data.empty:
            return AnalysisResult(success=False, data={}, error="Price data unavailable")
            
        # Ensure we have a clean DataFrame
        df = price_data.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # Standardize columns
        col_map = {c: c.capitalize() for c in df.columns}
        df.rename(columns=col_map, inplace=True)
        
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required):
             return AnalysisResult(success=False, data={}, error=f"Missing columns: {[c for c in required if c not in df.columns]}")

        # Calculate Indicators
        # SMA
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        # VWAP
        df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['PV'] = df['Typical_Price'] * df['Volume']
        df['VWAP'] = df['PV'].cumsum() / df['Volume'].cumsum()
        
        return AnalysisResult(
            success=True,
            data={
                'symbol': symbol,
                'chart_data': df
            }
        )

    def render(self, result: AnalysisResult):
        # We don't want the standard header here as the chart is the main view
        # st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.error(f"Chart Error: {result.error}")
            return
            
        data = result.data
        df = data['chart_data']
        symbol = data['symbol']
        
        # Create Subplots: Row 1 = Price, Row 2 = Volume
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True,
            vertical_spacing=0.03, 
            subplot_titles=(f"{symbol} Price Action", "Volume"),
            row_heights=[0.7, 0.3]
        )
        
        # 1. Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name='Price'
        ), row=1, col=1)
        
        # 2. Overlays
        # SMA 20
        fig.add_trace(go.Scatter(
            x=df.index, y=df['SMA_20'],
            mode='lines', name='SMA 20',
            line=dict(color='yellow', width=1)
        ), row=1, col=1)
        
        # SMA 50
        fig.add_trace(go.Scatter(
            x=df.index, y=df['SMA_50'],
            mode='lines', name='SMA 50',
            line=dict(color='orange', width=1)
        ), row=1, col=1)
        
        # VWAP
        fig.add_trace(go.Scatter(
            x=df.index, y=df['VWAP'],
            mode='lines', name='VWAP',
            line=dict(color='purple', width=1, dash='dot')
        ), row=1, col=1)
        
        # 3. Volume
        colors = ['red' if row['Open'] - row['Close'] >= 0 else 'green' for index, row in df.iterrows()]
        fig.add_trace(go.Bar(
            x=df.index, y=df['Volume'],
            name='Volume',
            marker_color=colors
        ), row=2, col=1)
        
        # Layout
        fig.update_layout(
            height=600,
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
