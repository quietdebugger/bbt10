"""
Advanced Analysis Plugins (F&O, AI, Fundamentals)
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from upstox_fo_complete import UpstoxAuth, UpstoxFOData
from ai_insights_improved import AIInsightsEngine
from screener_fundamentals import ScreenerFundamentals
from ui_components import render_aggrid

logger = logging.getLogger(__name__)

# ... (Previous plugins remain unchanged) ...

@register_plugin
class AIInsightsPlugin(AnalysisPlugin):
    """AI-powered market analysis"""
    
    @property
    def name(self) -> str:
        return "AI Insights"
    
    @property
    def icon(self) -> str:
        return "🤖"
    
    @property
    def description(self) -> str:
        return "Gemini AI analysis with rate limiting"
    
    @property
    def category(self) -> str:
        return "sentiment"
    
    @property
    def enabled_by_default(self) -> bool:
        return False  # User opt-in
    
    @property
    def requires_config(self):
        return ['GEMINI_API_KEY']
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        # Check config
        api_key = context.get('config', {}).get('GEMINI_API_KEY')
        if not api_key:
            return AnalysisResult(success=False, data={}, error="Gemini API Key missing")
            
        return AnalysisResult(success=True, data={'api_key': api_key, 'context': context})
    
    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.warning(f"AI Unavailable: {result.error}")
            return
            
        api_key = result.data['api_key']
        context = result.data['context']
        symbol = context.get('symbol', 'Unknown')
        
        # Initialize Engine
        engine = AIInsightsEngine(api_key)
        status = engine.get_quota_status()
        
        col1, col2 = st.columns(2)
        col1.caption(f"Model: {status['model']}")
        col2.caption(f"Quota: {status['daily_requests']}/{status['daily_limit']} (Resets {status['next_reset']})")
        
        if st.button("Generate Market Analysis", key="btn_ai_gen"):
            with st.spinner("🤖 AI is thinking... (This may take a few seconds)"):
                # Gather data for prompt
                # In a real scenario, we'd pass the actual results from other plugins
                # For now, we construct a basic state from context
                market_state = {
                    'trend': 'Neutral', # Placeholder
                    'volatility': 'Medium',
                    'confidence': 'Low (Data Missing)'
                }
                
                # Check for cached results in session state if available?
                # Or just rely on what we have.
                
                analysis = engine.analyze_market_state(
                    symbol=symbol,
                    market_state=market_state,
                    changes=[],
                    fo_data=None # We could pass this if we had it easily accessible
                )
                
                st.markdown("### 🧠 Gemini Analysis")
                st.markdown(analysis)
                st.success("Analysis generated successfully")


@register_plugin
class OptionsAnalysisPlugin(AnalysisPlugin):
    """Options analysis (PCR, Max Pain, OI)"""
    
    @property
    def name(self) -> str:
        return "Options Analysis"
    
    @property
    def icon(self) -> str:
        return "💎"
    
    @property
    def description(self) -> str:
        return "PCR, Max Pain, OI levels from Upstox"
    
    @property
    def category(self) -> str:
        return "asset"
    
    @property
    def requires_config(self):
        return ['UPSTOX_API_KEY', 'UPSTOX_API_SECRET']
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            api_key = context.get('config', {}).get('UPSTOX_API_KEY')
            api_secret = context.get('config', {}).get('UPSTOX_API_SECRET')
            
            if not api_key or not api_secret:
                return AnalysisResult(
                    success=False,
                    data={},
                    error="Upstox API keys not configured"
                )
            
            symbol = context.get('upstox_symbol', 'Nifty 50')
            
            # Fetch data
            auth = UpstoxAuth(api_key, api_secret)
            fo_data = UpstoxFOData(auth)
            
            option_chain, spot_price = fo_data.get_option_chain(symbol, max_distance_pct=12.0)
            
            if option_chain.empty:
                return AnalysisResult(
                    success=False,
                    data={},
                    error=f"No liquid options data found for {symbol}"
                )
            
            pcr_data = fo_data.calculate_pcr(option_chain)
            max_pain = fo_data.calculate_max_pain(option_chain, spot_price)
            oi_analysis = fo_data.get_oi_analysis(option_chain)
            
            return AnalysisResult(
                success=True,
                data={
                    'option_chain': option_chain,
                    'spot_price': spot_price,
                    'pcr': pcr_data,
                    'max_pain': max_pain,
                    'oi': oi_analysis
                }
            )
            
        except Exception as e:
            logger.error(f"Options analysis failed: {e}", exc_info=True)
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"Options: {result.error}")
            return
        
        data = result.data
        pcr = data['pcr']
        
        # --- COMPACT DATA TABLE (Replaces Metrics) ---
        snapshot_data = [{
            'PCR (OI)': f"{pcr['pcr_oi']:.2f}",
            'Sentiment': pcr['sentiment'],
            'Total OI': f"{(pcr['total_call_oi'] + pcr['total_put_oi'])/1e6:.1f}M",
            'Max Pain': f"₹{data['max_pain']['max_pain_strike']:.0f}",
            'Pain Dist%': f"{data['max_pain']['distance_pct']:+.2f}%",
            'Call Res.': f"₹{data['oi']['call_resistance']:.0f}",
            'Put Supp.': f"₹{data['oi']['put_support']:.0f}"
        }]
        
        snapshot_df = pd.DataFrame(snapshot_data)
        render_aggrid(snapshot_df, height=65) # Single row height
        
        st.caption(f"Interpretation: {pcr['interpretation']}")

        # Option Chain Table (ATM)
        st.markdown("**Option Chain (ATM)**")
        
        option_chain = data.get('option_chain')
        spot_price = data.get('spot_price')
        
        if option_chain is not None and not option_chain.empty and spot_price:
            # Find ATM index
            atm_idx = (option_chain['strike'] - spot_price).abs().idxmin()
            
            # Select range around ATM (e.g., 5 above, 5 below)
            start_idx = max(0, atm_idx - 5)
            end_idx = min(len(option_chain), atm_idx + 6)
            
            atm_chain = option_chain.iloc[start_idx:end_idx].copy()
            
            # Format for display
            # Column names from upstox_fo_complete.py are Uppercase (CE_LTP, PE_LTP, etc.)
            display_cols = ['strike', 'CE_LTP', 'PE_LTP', 'CE_OI', 'PE_OI', 'CE_Volume', 'PE_Volume']
            
            # Check if columns exist (handle potential case mismatch)
            available_cols = [c for c in display_cols if c in atm_chain.columns]
            
            if available_cols:
                # Use render_aggrid instead of st.dataframe
                render_aggrid(atm_chain[available_cols], height=300)
            else:
                render_aggrid(atm_chain, height=300)


@register_plugin
class GreeksAnalysisPlugin(AnalysisPlugin):
    """Greeks (Delta, Gamma, Theta, Vega)"""
    
    @property
    def name(self) -> str:
        return "Greeks Analysis"
    
    @property
    def icon(self) -> str:
        return "🧬"
    
    @property
    def description(self) -> str:
        return "Delta, Gamma, Theta, Vega from Upstox"
    
    @property
    def category(self) -> str:
        return "asset"
    
    @property
    def enabled_by_default(self) -> bool:
        return False  # Advanced
    
    @property
    def requires_config(self):
        return ['UPSTOX_API_KEY', 'UPSTOX_API_SECRET']
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            api_key = context.get('config', {}).get('UPSTOX_API_KEY')
            api_secret = context.get('config', {}).get('UPSTOX_API_SECRET')
            
            if not api_key or not api_secret:
                return AnalysisResult(success=False, data={}, error="Upstox not configured")
            
            symbol = context.get('upstox_symbol', 'Nifty 50')
            
            auth = UpstoxAuth(api_key, api_secret)
            fo_data = UpstoxFOData(auth)
            
            option_chain, spot_price = fo_data.get_option_chain(symbol)
            greeks = fo_data.calculate_greeks_analysis(option_chain, spot_price)
            
            return AnalysisResult(
                success=True,
                data={'greeks': greeks, 'spot_price': spot_price}
            )
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"Greeks: {result.error}")
            return
        
        data = result.data['greeks']
        
        st.subheader(f"{self.icon} {self.name}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Net Delta", f"{data['net_delta']:,.0f}")
            st.caption(data['delta_interpretation'])
        
        with col2:
            st.metric("Max Gamma Strike", f"₹{data['max_gamma_strike']:.0f}")
            st.caption(data['gamma_interpretation'])


@register_plugin
class FuturesAnalysisPlugin(AnalysisPlugin):
    """Futures basis analysis"""
    
    @property
    def name(self) -> str:
        return "Futures Analysis"
    
    @property
    def icon(self) -> str:
        return "📈"
    
    @property
    def description(self) -> str:
        return "Futures basis, premium/discount"
    
    @property
    def category(self) -> str:
        return "asset"
    
    @property
    def enabled_by_default(self) -> bool:
        return False
    
    @property
    def requires_config(self):
        return ['UPSTOX_API_KEY', 'UPSTOX_API_SECRET']
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            api_key = context.get('config', {}).get('UPSTOX_API_KEY')
            api_secret = context.get('config', {}).get('UPSTOX_API_SECRET')
            
            if not api_key or not api_secret:
                return AnalysisResult(success=False, data={}, error="Upstox not configured")
            
            symbol = context.get('upstox_symbol', 'Nifty 50')
            
            auth = UpstoxAuth(api_key, api_secret)
            fo_data = UpstoxFOData(auth)
            
            futures = fo_data.get_futures_data(symbol)
            
            return AnalysisResult(success=True, data={'futures': futures})
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"Futures: {result.error}")
            return
        
        data = result.data['futures']
        
        if not data.get('futures_price'):
            st.info("Futures data unavailable")
            return
        
        st.subheader(f"{self.icon} {self.name}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Futures", f"₹{data['futures_price']:.2f}")
        col2.metric("Spot", f"₹{data['spot_price']:.2f}")
        col3.metric("Basis", f"{data['basis_pct']:+.2f}%")
        
        st.info(data['interpretation'])


@register_plugin
class FundamentalsPlugin(AnalysisPlugin):
    """Fundamental ratios from Screener.in"""
    
    @property
    def name(self) -> str:
        return "Fundamentals"
    
    @property
    def icon(self) -> str:
        return "📊"
    
    @property
    def description(self) -> str:
        return "PE, ROE, Debt/Equity from Screener.in"
    
    @property
    def category(self) -> str:
        return "asset"
    
    @property
    def enabled_by_default(self) -> bool:
        return False
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            symbol = context.get('symbol', '')
            
            if symbol.startswith('^'):
                return AnalysisResult(
                    success=False,
                    data={},
                    error="Fundamentals only for stocks"
                )
            
            screener = ScreenerFundamentals(symbol)
            ratios = screener.get_comprehensive_ratios()
            
            return AnalysisResult(success=True, data={'ratios': ratios})
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.info(f"Fundamentals: {result.error}")
            return
        
        data = result.data['ratios']
        
        st.subheader(f"{self.icon} {self.name}")
        
        col1, col2, col3 = st.columns(3)
        
        pe = data.get('valuation', {}).get('P/E Ratio')
        roe = data.get('profitability', {}).get('ROE %')
        de = data.get('financial_health', {}).get('Debt to Equity')
        
        if pe:
            col1.metric("P/E Ratio", f"{pe:.2f}")
        if roe:
            col2.metric("ROE", f"{roe:.2f}%")
        if de:
            col3.metric("Debt/Equity", f"{de:.2f}")
