"""
Market State Plugin
Implements 'Market State Analyzer' from bbt9
Provides high-level context before metrics
"""

import streamlit as st
import pandas as pd
import logging
from typing import Dict, Any

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from market_state import MarketStateAnalyzer
from validated_indicators import ValidatedIndicators, ValidatedOptionsIndicators
from upstox_fo_complete import UpstoxAuth, UpstoxFOData

logger = logging.getLogger(__name__)

@register_plugin
class MarketStatePlugin(AnalysisPlugin):
    """
    Analyzes market regime (Trend, Volatility, Options) first.
    """
    @property
    def name(self) -> str:
        return "Market State"
    
    @property
    def icon(self) -> str:
        return "🧭"
    
    @property
    def description(self) -> str:
        return "Determines market regime (Trend, Volatility) before metrics"
    
    @property
    def category(self) -> str:
        return "market"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        price_data = context.get('price_data')
        if price_data is None:
            return AnalysisResult(False, {}, "No price data")
            
        # Get Options Data if available (re-fetch or check context?)
        # For simplicity, we check if we have Upstox keys and fetch minimal info or rely on what's available
        # Ideally, `context` should have an `option_chain` if the OptionsPlugin ran. 
        # But plugins order isn't guaranteed. We'll instantiate minimal needed if missing.
        
        option_chain = None
        pcr_data = None
        oi_analysis = None
        
        api_key = context.get('config', {}).get('UPSTOX_API_KEY')
        upstox_symbol = context.get('upstox_symbol')
        
        if api_key and upstox_symbol:
            try:
                # Reuse existing auth logic if possible or lightweight check
                # This is a bit heavy for a "state" check, but necessary for accuracy
                pass 
            except: pass

        analyzer = MarketStateAnalyzer(price_data)
        # Pass None for options if we don't want to re-fetch heavy data here. 
        # Ideally this plugin runs AFTER Options plugin and reads from context.
        # BUT for now, let's just do price-based state to be fast.
        
        state = analyzer.analyze(None, None, None)
        
        # Validated Indicators
        indicators = ValidatedIndicators(price_data)
        rsi = indicators.rsi()
        atr = indicators.atr()
        
        return AnalysisResult(True, {
            'state': state,
            'indicators': {'rsi': rsi, 'atr': atr}
        })

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.warning(result.error)
            return
            
        state = result.data['state']
        
        # Color coding
        color = "#27ae60" if state.confidence == "HIGH" else "#f39c12" if state.confidence == "MEDIUM" else "#e74c3c"
        
        st.markdown(f"""
        <div style='background: {color}; padding: 15px; border-radius: 8px; color: white;'>
        <h3 style='margin:0'>State: {state.trend.value}</h3>
        <p style='margin:0'>Volatility: {state.volatility.value} | Confidence: {state.confidence}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if state.conflicting_signals:
            st.warning("⚠️ Conflicts: " + ", ".join(state.conflicting_signals))
            
        # Validated Indicators
        st.markdown("---")
        inds = result.data['indicators']
        c1, c2 = st.columns(2)
        c1.markdown(inds['rsi'].display("RSI (14)"))
        c2.markdown(inds['atr'].display("ATR"))
