"""
Alpha Fusion Plugin
Quantitative Scoring & Signal Generation
"""

import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
from typing import Dict, Any
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from services.alpha_engine import AlphaEngine
from ui_styles import render_cyber_metric, apply_terminal_style

logger = logging.getLogger(__name__)

@register_plugin
class AlphaFusionPlugin(AnalysisPlugin):
    """Alpha Fusion: Quantitative Technical Scoring"""
    
    @property
    def name(self) -> str:
        return "Alpha Fusion"
    
    @property
    def icon(self) -> str:
        return "⚡"
    
    @property
    def description(self) -> str:
        return "Quantitative Multi-Factor Scoring (Momentum + Trend + Volatility)"
    
    @property
    def category(self) -> str:
        return "asset"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            symbol = context.get('symbol')
            # Fetch 1 year of history for robust indicators
            data = yf.download(symbol, period="1y", progress=False)
            
            if data.empty:
                return AnalysisResult(success=False, data={}, error=f"No data found for {symbol}")

            engine = AlphaEngine(data)
            result = engine.analyze()
            
            return AnalysisResult(success=True, data=result)
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        apply_terminal_style()
        
        if not result.success:
            st.warning(f"Alpha Engine: {result.error}")
            return
        
        data = result.data
        comp = data['components']
        inds = data['indicators']
        
        st.subheader(f"{self.icon} {self.name} - {data['rating']}")
        
        # Main Score
        c1, c2, c3 = st.columns([2, 1, 1])
        
        with c1:
            score_color = True if data['total_score'] > 60 else False
            render_cyber_metric("Total Alpha Score", f"{data['total_score']}/100", large=True, is_positive=score_color)
            
        with c2:
            st.markdown(f"**RSI:** {inds['RSI']:.1f}")
            st.markdown(f"**MACD:** {inds['MACD']:.2f}")
            
        with c3:
            st.markdown(f"**Vol (Ann):** {inds['Volatility']:.1%}")
            st.markdown(f"**Trend:** {'Bullish' if inds['Close'] > inds['SMA_200'] else 'Bearish'}")
            
        st.markdown("---")
        
        # Radar Chart
        categories = ['Momentum', 'Trend', 'Volatility']
        values = [comp['momentum'], comp['trend'], comp['volatility']]
        max_values = [40, 30, 30] # Normalized max for scaling
        
        # Normalize to 100 for chart
        scaled_values = [v/m*100 for v, m in zip(values, max_values)]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=scaled_values,
            theta=categories,
            fill='toself',
            name='Alpha Factors',
            line_color='#00FFA3',
            fillcolor='rgba(0, 255, 163, 0.2)'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], color='#8B949E'),
                bgcolor='#161B22'
            ),
            showlegend=False,
            height=350,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            st.markdown("### Factor Analysis")
            st.progress(comp['momentum'] / 40, text=f"Momentum ({comp['momentum']}/40)")
            st.progress(comp['trend'] / 30, text=f"Trend ({comp['trend']}/30)")
            st.progress(comp['volatility'] / 30, text=f"Volatility ({comp['volatility']}/30)")
            
            st.info("💡 **Momentum** tracks RSI & MACD strength. **Trend** checks SMA alignment. **Volatility** looks for Squeezes.")
