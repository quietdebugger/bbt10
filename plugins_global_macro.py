"""
Global Macro Bridge Plugin
Inter-market Correlation Engine & Opportunity Scanner.
Connects Global Cues (Nasdaq, Oil, Yields) to Domestic Opportunities.
"""

import streamlit as st
import pandas as pd
import numpy as np
import datetime
from typing import Dict, Any, List
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from data_fetcher import MultiAssetDataFetcher
from market_symbols import INDICES

logger = logging.getLogger(__name__)

# --- CONFIGURATION: LEAD-LAG PAIRS ---
# Global Asset -> Domestic Target
MACRO_PAIRS = [
    {
        "name": "Tech Momentum",
        "global_ticker": "^IXIC",      # Nasdaq Composite
        "global_name": "NASDAQ",
        "domestic_ticker": "^CNXIT",   # Nifty IT
        "domestic_name": "NIFTY IT",
        "correlation_type": "Direct",  # Nasdaq UP -> IT UP
        "lag_days": 1 # Overnight impact
    },
    {
        "name": "Energy Cost",
        "global_ticker": "BZ=F",       # Brent Crude
        "global_name": "BRENT OIL",
        "domestic_ticker": "^CNXENERGY", # Nifty Energy (Producers like ONGC)
        "domestic_name": "NIFTY ENERGY",
        "correlation_type": "Direct",  # Oil UP -> Energy UP (Producers)
        "lag_days": 0
    },
    {
        "name": "Input Cost Stress",
        "global_ticker": "BZ=F",       # Brent Crude
        "global_name": "BRENT OIL",
        "domestic_ticker": "ASIANPAINT.NS", # Paints (Consumers)
        "domestic_name": "PAINTS/TYRES",
        "correlation_type": "Inverse", # Oil UP -> Paints DOWN
        "lag_days": 0
    },
    {
        "name": "Risk Sentiment",
        "global_ticker": "DX-Y.NYB",   # Dollar Index
        "global_name": "DXY",
        "domestic_ticker": "^NSEBANK", # Bank Nifty (FII Sensitivity)
        "domestic_name": "BANK NIFTY",
        "correlation_type": "Inverse", # DXY UP -> Banks DOWN (FII Outflow)
        "lag_days": 0
    },
    {
        "name": "Cost of Capital",
        "global_ticker": "^TNX",       # US 10Y Yield
        "global_name": "US 10Y",
        "domestic_ticker": "^NSEBANK", # Bank Nifty
        "domestic_name": "BANK NIFTY",
        "correlation_type": "Inverse", # Yields UP -> Banks DOWN
        "lag_days": 0
    }
]

@register_plugin
class GlobalMacroBridgePlugin(AnalysisPlugin):
    """
    Analyzes global inter-market relationships to predict domestic sector moves.
    """
    
    @property
    def name(self) -> str:
        return "Global Macro Bridge"
    
    @property
    def icon(self) -> str:
        return "🌐"
    
    @property
    def description(self) -> str:
        return "Predicts domestic sector gaps based on global overnight cues."
    
    @property
    def category(self) -> str:
        return "macro"
    
    @property
    def enabled_by_default(self) -> bool:
        return True
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            fetcher = MultiAssetDataFetcher()
            
            # 1. Collect Tickers
            global_tickers = list(set([p['global_ticker'] for p in MACRO_PAIRS]))
            domestic_tickers = list(set([p['domestic_ticker'] for p in MACRO_PAIRS]))
            all_tickers = global_tickers + domestic_tickers
            
            # 2. Fetch History (Last 60 days for correlation)
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=60)
            
            data_map = fetcher.fetch_multiple_assets(all_tickers, 
                                                   start_date.strftime('%Y-%m-%d'),
                                                   end_date.strftime('%Y-%m-%d'))
            
            results = []
            
            for pair in MACRO_PAIRS:
                g_sym = pair['global_ticker']
                d_sym = pair['domestic_ticker']
                
                if g_sym in data_map and d_sym in data_map:
                    df_g = data_map[g_sym][0]
                    df_d = data_map[d_sym][0]
                    
                    if df_g is None or df_d is None or df_g.empty or df_d.empty:
                        continue
                        
                    # Calculate Overnight/Latest Change for Global
                    # Usually global markets close before our open (US) or trade concurrently (Asia/Commodities)
                    # We take the very last available close vs prev close
                    g_last = df_g.iloc[-1]
                    g_prev = df_g.iloc[-2]
                    g_chg_pct = ((g_last['close'] - g_prev['close']) / g_prev['close']) * 100
                    
                    # Calculate Rolling Correlation (20 Day)
                    # Join on date
                    # Note: Timezones mess this up. Simple join on YYYY-MM-DD usually works for daily.
                    merged = pd.concat([df_g['close'], df_d['close']], axis=1, join='inner')
                    merged.columns = ['Global', 'Domestic']
                    
                    if len(merged) < 20: continue
                    
                    corr_20 = merged['Global'].rolling(20).corr(merged['Domestic']).iloc[-1]
                    
                    # Prediction Logic
                    prediction = "Neutral"
                    impact_score = 0 # -2 to +2
                    
                    # Thresholds
                    SIGNIFICANT_MOVE = 0.75 # % change
                    HIGH_CORR = 0.5
                    
                    if pair['correlation_type'] == "Direct":
                        eff_corr = corr_20
                        if g_chg_pct > SIGNIFICANT_MOVE: impact_score = 1
                        elif g_chg_pct < -SIGNIFICANT_MOVE: impact_score = -1
                    else: # Inverse
                        eff_corr = -corr_20
                        if g_chg_pct > SIGNIFICANT_MOVE: impact_score = -1
                        elif g_chg_pct < -SIGNIFICANT_MOVE: impact_score = 1
                    
                    # Refine Prediction
                    if abs(eff_corr) > HIGH_CORR:
                        if impact_score == 1: prediction = "Bullish / Gap Up"
                        elif impact_score == -1: prediction = "Bearish / Gap Down"
                        
                    # Check "Divergence" Opportunity
                    # If correlation is usually high, but yesterday they moved opposite -> Mean Reversion?
                    # Too complex for now. Stick to "Flow" logic.
                    
                    results.append({
                        "Pair": pair['name'],
                        "Global Asset": pair['global_name'],
                        "Global Chg%": g_chg_pct,
                        "Domestic Target": pair['domestic_name'],
                        "Correlation (20D)": corr_20,
                        "Type": pair['correlation_type'],
                        "Prediction": prediction,
                        "Score": impact_score * abs(eff_corr) # Weighted score
                    })
            
            return AnalysisResult(success=True, data=results)
            
        except Exception as e:
            logger.error(f"Global Macro Bridge failed: {e}", exc_info=True)
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.error(f"Analysis failed: {result.error}")
            return
            
        data = result.data
        if not data:
            st.info("No macro data available.")
            return
            
        df = pd.DataFrame(data)
        
        # Style logic
        def color_prediction(val):
            if "Bullish" in val: return "color: #00FF00; font-weight: bold;"
            if "Bearish" in val: return "color: #FF4444; font-weight: bold;"
            return "color: #AAAAAA;"
            
        # Display Grid
        # Using native Streamlit columns for "Cards" view first
        
        impact_events = [r for r in data if "Neutral" not in r['Prediction']]
        
        if impact_events:
            st.markdown("### 🚨 Market Moving Signals")
            cols = st.columns(len(impact_events))
            for i, row in enumerate(impact_events):
                with cols[i]:
                    with st.container(border=True):
                        st.caption(f"{row['Global Asset']} → {row['Domestic Target']}")
                        st.markdown(f"**{row['Global Chg%']:+.2f}%**")
                        
                        pred_color = "green" if "Bullish" in row['Prediction'] else "red"
                        st.markdown(f":{pred_color}[{row['Prediction']}]")
                        st.caption(f"Corr: {row['Correlation (20D)']:.2f}")

        st.markdown("### 🌍 Global-Domestic Correlation Matrix")
        
        # Clean DF for display
        display_df = df[['Pair', 'Global Asset', 'Global Chg%', 'Domestic Target', 'Correlation (20D)', 'Prediction']]
        
        st.dataframe(
            display_df.style.applymap(color_prediction, subset=['Prediction'])
                            .format({'Global Chg%': '{:+.2f}%', 'Correlation (20D)': '{:.2f}'}),
            use_container_width=True,
            hide_index=True
        )
