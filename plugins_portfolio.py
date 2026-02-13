"""
Portfolio Analysis Plugin
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from upstox_fo_complete import UpstoxAuth, UpstoxFOData
from ui_components import render_metric_card, render_aggrid

logger = logging.getLogger(__name__)

@register_plugin
class PortfolioPlugin(AnalysisPlugin):
    """Portfolio & Positions Analysis"""
    
    @property
    def name(self) -> str:
        return "My Portfolio"
    
    @property
    def icon(self) -> str:
        return "💼"
    
    @property
    def description(self) -> str:
        return "Holdings, Positions, and P&L from Upstox"
    
    @property
    def category(self) -> str:
        return "portfolio"
    
    @property
    def requires_config(self):
        return ['UPSTOX_API_KEY', 'UPSTOX_API_SECRET']
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            api_key = context.get('config', {}).get('UPSTOX_API_KEY')
            api_secret = context.get('config', {}).get('UPSTOX_API_SECRET')
            
            if not api_key or not api_secret:
                return AnalysisResult(success=False, data={}, error="Upstox not configured")
            
            auth = UpstoxAuth(api_key, api_secret)
            fo_data = UpstoxFOData(auth)
            
            holdings = fo_data.get_holdings()
            positions = fo_data.get_positions()
            
            # Process Holdings
            holdings_df = pd.DataFrame(holdings) if holdings else pd.DataFrame()
            holdings_summary = {}
            if not holdings_df.empty:
                # Upstox API fields might vary, normalizing...
                # Typically: quantity, average_price, last_price, pnl
                holdings_df['current_val'] = holdings_df['quantity'] * holdings_df['last_price']
                holdings_df['invested_val'] = holdings_df['quantity'] * holdings_df['average_price']
                holdings_df['total_pnl'] = holdings_df['current_val'] - holdings_df['invested_val']
                holdings_df['day_pnl'] = holdings_df['quantity'] * (holdings_df['last_price'] - holdings_df['close_price'])
                
                holdings_summary = {
                    'total_invested': holdings_df['invested_val'].sum(),
                    'current_value': holdings_df['current_val'].sum(),
                    'total_pnl': holdings_df['total_pnl'].sum(),
                    'day_pnl': holdings_df['day_pnl'].sum()
                }
            
            # Process Positions
            positions_df = pd.DataFrame(positions) if positions else pd.DataFrame()
            positions_summary = {}
            if not positions_df.empty:
                # Realized vs Unrealized
                # pnl field in positions is usually realized + unrealized
                positions_summary = {
                    'realized_pnl': positions_df['realized_pnl'].sum() if 'realized_pnl' in positions_df else 0,
                    'unrealized_pnl': positions_df['unrealized_pnl'].sum() if 'unrealized_pnl' in positions_df else 0,
                    'total_pnl': (positions_df['realized_pnl'].sum() + positions_df['unrealized_pnl'].sum()) if 'realized_pnl' in positions_df else 0
                }
            
            return AnalysisResult(
                success=True,
                data={
                    'holdings': holdings, # Raw list
                    'positions': positions, # Raw list
                    'holdings_summary': holdings_summary,
                    'positions_summary': positions_summary
                }
            )
            
        except Exception as e:
            logger.error(f"Portfolio analysis failed: {e}")
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"Portfolio access: {result.error}")
            return
        
        data = result.data
        h_sum = data.get('holdings_summary', {})
        p_sum = data.get('positions_summary', {})
        
        st.subheader(f"{self.icon} {self.name}")
        
        # Tabs
        tab1, tab2 = st.tabs(["Holdings", "Positions"])
        
        with tab1:
            if h_sum:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    render_metric_card("Invested Value", f"₹{h_sum.get('total_invested', 0):,.0f}")
                with col2:
                    render_metric_card("Current Value", f"₹{h_sum.get('current_value', 0):,.0f}")
                with col3:
                    pnl = h_sum.get('total_pnl', 0)
                    render_metric_card("Total P&L", f"₹{pnl:,.0f}", is_positive=pnl>0)
                with col4:
                    dpnl = h_sum.get('day_pnl', 0)
                    render_metric_card("Day's P&L", f"₹{dpnl:,.0f}", is_positive=dpnl>0)
                
                st.markdown("### Holdings Details")
                if data.get('holdings'):
                    df = pd.DataFrame(data['holdings'])
                    cols_to_show = ['trading_symbol', 'quantity', 'average_price', 'last_price', 'pnl']
                    # Filter existing cols
                    cols = [c for c in cols_to_show if c in df.columns]
                    render_aggrid(df[cols], height=300, key="holdings_grid")
            else:
                st.info("No holdings found.")
        
        with tab2:
            if p_sum:
                col1, col2, col3 = st.columns(3)
                with col1:
                    pnl = p_sum.get('total_pnl', 0)
                    render_metric_card("Net P&L", f"₹{pnl:,.0f}", is_positive=pnl>0)
                with col2:
                    rpnl = p_sum.get('realized_pnl', 0)
                    render_metric_card("Realized", f"₹{rpnl:,.0f}", is_positive=rpnl>0)
                with col3:
                    upnl = p_sum.get('unrealized_pnl', 0)
                    render_metric_card("Unrealized", f"₹{upnl:,.0f}", is_positive=upnl>0)
                
                st.markdown("### Active Positions")
                if data.get('positions'):
                    df = pd.DataFrame(data['positions'])
                    cols_to_show = ['trading_symbol', 'quantity', 'buy_price', 'sell_price', 'last_price', 'pnl']
                    cols = [c for c in cols_to_show if c in df.columns]
                    render_aggrid(df[cols], height=300, key="positions_grid")
            else:
                st.info("No active positions.")
