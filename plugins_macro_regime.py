"""
Macro Regime Classifier Plugin
Classifies the current market environment (Risk-On, Risk-Off, Inflationary)
"""

import streamlit as st
import pandas as pd
import numpy as np
import datetime
from typing import Dict, Any, Tuple
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from ui_components import render_metric_card
from data_fetcher import MultiAssetDataFetcher

logger = logging.getLogger(__name__)

@register_plugin
class MacroRegimePlugin(AnalysisPlugin):
    """
    Automated Market Regime Detector
    Classifies market into: Risk-On, Risk-Off, Inflationary, or Stagflationary
    """
    
    @property
    def name(self) -> str:
        return "Macro Regime"
    
    @property
    def icon(self) -> str:
        return "🧭"
    
    @property
    def description(self) -> str:
        return "Contextualizes price action using Yields, DXY, and Nifty correlations."
    
    @property
    def category(self) -> str:
        return "macro"
    
    @property
    def enabled_by_default(self) -> bool:
        return True
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            # 1. Fetch Key Macro Assets (Last 6 Months)
            tickers = {
                'Nifty': '^NSEI',
                'US10Y': '^TNX',
                'DXY': 'DX-Y.NYB',
                'Oil': 'CL=F'
            }
            
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=180)
            
            # Use robust fetcher
            fetcher = MultiAssetDataFetcher()
            fetch_results = fetcher.fetch_multiple_assets(
                list(tickers.values()),
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            # Reconstruct DataFrame
            combined_data = pd.DataFrame()
            
            for name, symbol in tickers.items():
                if symbol in fetch_results and fetch_results[symbol][0] is not None:
                    df = fetch_results[symbol][0]
                    if not df.empty and 'close' in df.columns:
                        # Align indices if needed, but for now simple assignment
                        # Ideally we join on index
                        series = df['close']
                        series.name = name
                        if combined_data.empty:
                            combined_data = pd.DataFrame(series)
                        else:
                            combined_data = combined_data.join(series, how='outer')
            
            # Fill missing data
            if combined_data.empty:
                 return AnalysisResult(success=False, data={}, error="Macro data unavailable (fetch failed)")

            combined_data.fillna(method='ffill', inplace=True)
            combined_data.dropna(inplace=True)
            
            data = combined_data
            
            if len(data) < 20:
                return AnalysisResult(success=False, data={}, error="Insufficient macro history")
            
            # 2. Calculate Trends (20D Moving Average Slope)
            trends = {}
            for col in data.columns:
                sma20 = data[col].rolling(window=20).mean()
                current_price = data[col].iloc[-1]
                sma_val = sma20.iloc[-1]
                
                # Trend is UP if price > SMA20
                trends[col] = "UP" if current_price > sma_val else "DOWN"
            
            # 3. Calculate Correlations (Rolling 20D)
            # Nifty vs US10Y
            nifty_yield_corr = data['Nifty'].rolling(20).corr(data['US10Y']).iloc[-1]
            
            # Nifty vs DXY
            nifty_dxy_corr = data['Nifty'].rolling(20).corr(data['DXY']).iloc[-1]
            
            # 4. Determine Regime
            regime = "NEUTRAL"
            description = "Market lacks clear macro conviction."
            sectors_in_focus = "Stock Specific"
            
            us10y_trend = trends.get('US10Y')
            dxy_trend = trends.get('DXY')
            nifty_trend = trends.get('Nifty')
            oil_trend = trends.get('Oil')
            
            # Logic Table
            if nifty_trend == "UP" and dxy_trend == "DOWN" and us10y_trend == "DOWN":
                regime = "GOLDILOCKS (Risk-On)"
                description = "Falling yields and dollar support equity valuations."
                sectors_in_focus = "Tech, Realty, Banks"
                
            elif nifty_trend == "DOWN" and (dxy_trend == "UP" or us10y_trend == "UP"):
                regime = "RISK-OFF"
                description = "Capital flight to safety (USD/Bonds) due to rising rates or stress."
                sectors_in_focus = "FMCG, Pharma (Defensives)"
                
            elif us10y_trend == "UP" and oil_trend == "UP":
                regime = "INFLATIONARY"
                description = "Rising costs and yields pressuring margins."
                sectors_in_focus = "Metals, Energy, Commodities"
                
            elif nifty_trend == "UP" and us10y_trend == "UP":
                regime = "REFLATION / GROWTH"
                description = "Economy growing strong enough to withstand higher rates."
                sectors_in_focus = "Capital Goods, Industrials, Auto"
            
            return AnalysisResult(
                success=True,
                data={
                    'regime': regime,
                    'description': description,
                    'focus': sectors_in_focus,
                    'trends': trends,
                    'correlations': {
                        'Nifty_vs_Yield': nifty_yield_corr,
                        'Nifty_vs_DXY': nifty_dxy_corr
                    },
                    'latest_values': data.iloc[-1].to_dict()
                }
            )
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.warning(f"Regime detection failed: {result.error}")
            return
        
        data = result.data
        regime = data['regime']
        
        # Color Coding
        color_map = {
            "GOLDILOCKS (Risk-On)": "green",
            "REFLATION / GROWTH": "blue",
            "INFLATIONARY": "orange",
            "RISK-OFF": "red",
            "NEUTRAL": "gray"
        }
        color = color_map.get(regime, "gray")
        
        # 1. Main Badge
        st.markdown(f"""
        <div style="background-color: #111; border: 1px solid #333; padding: 15px; border-radius: 5px; text-align: center; border-left: 5px solid {color};">
            <h2 style="margin:0; color: {color};">{regime}</h2>
            <p style="margin:5px 0; color: #ccc;">{data['description']}</p>
            <p style="margin:5px 0; font-size: 0.9em; color: #888;">🚀 <strong>Focus:</strong> {data['focus']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 2. Key Trends
        c1, c2, c3, c4 = st.columns(4)
        trends = data['trends']
        vals = data['latest_values']
        
        with c1:
            render_metric_card("Nifty Trend", trends['Nifty'], is_positive=trends['Nifty']=="UP")
        with c2:
            render_metric_card("DXY Trend", trends['DXY'], is_positive=trends['DXY']=="DOWN") # DXY Down is "Positive" for risk
        with c3:
            render_metric_card("US10Y Trend", trends['US10Y'], is_positive=trends['US10Y']=="DOWN") # Yields Down is "Positive"
        with c4:
            render_metric_card("Oil Trend", trends['Oil'], is_positive=trends['Oil']=="DOWN")
            
        # 3. Correlations
        st.caption(f"Rolling 20D Correlations: Nifty vs US10Y ({data['correlations']['Nifty_vs_Yield']:.2f}) | Nifty vs DXY ({data['correlations']['Nifty_vs_DXY']:.2f})")
