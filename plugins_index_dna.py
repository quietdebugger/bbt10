"""
Index DNA Plugin
Deep dive into Index Composition, Attribution, and Sector Rotation.
Answers: "What is driving the market today?"
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from typing import Dict, Any
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from index_composition import INDEX_WEIGHTS, STOCK_SECTORS, ETF_MAPPING
from market_symbols import INDICES
from data_fetcher import MultiAssetDataFetcher

logger = logging.getLogger(__name__)

@register_plugin
class IndexDNAPlugin(AnalysisPlugin):
    """
    Index DNA: Attribution & Drivers
    """
    
    @property
    def name(self) -> str:
        return "Index DNA"
    
    @property
    def icon(self) -> str:
        return "🧬"
    
    @property
    def description(self) -> str:
        return "Decompose Index moves: Attribution, Sector Heatmap, Heavyweights."
    
    @property
    def category(self) -> str:
        return "market"
    
    @property
    def enabled_by_default(self) -> bool:
        return True
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            # 1. Identify Index Context
            # Default to NIFTY 50 if symbol is not a known index or is a stock
            symbol = context.get('symbol', '^NSEI')
            
            # Map ticker to internal ID (e.g. ^NSEI -> NIFTY_50)
            index_id = None
            index_name = "Unknown Index"
            
            # Reverse lookup from INDICES
            for name, ticker in INDICES.items():
                if ticker == symbol:
                    index_name = name
                    # Simple mapping logic
                    if "NIFTY 50" in name: index_id = "NIFTY_50"
                    elif "BANK" in name: index_id = "NIFTY_BANK"
                    elif "IT" in name: index_id = "NIFTY_IT"
                    elif "AUTO" in name: index_id = "NIFTY_AUTO"
                    elif "PHARMA" in name: index_id = "NIFTY_PHARMA"
                    elif "FMCG" in name: index_id = "NIFTY_FMCG"
                    elif "METAL" in name: index_id = "NIFTY_METAL"
                    elif "REALTY" in name: index_id = "NIFTY_REALTY"
                    elif "ENERGY" in name: index_id = "NIFTY_ENERGY"
                    elif "PSU BANK" in name: index_id = "NIFTY_PSU_BANK"
                    elif "INFRA" in name: index_id = "NIFTY_INFRA"
                    elif "COMMODITIES" in name: index_id = "NIFTY_COMMODITIES"
                    elif "CPSE" in name: index_id = "NIFTY_CPSE"
                    elif "PSE" in name: index_id = "NIFTY_PSE"
                    elif "MNC" in name: index_id = "NIFTY_MNC"
                    elif "NV20" in name: index_id = "NIFTY_NV20"
                    break
            
            if not index_id or index_id not in INDEX_WEIGHTS:
                # Fallback: If analyzing a stock, show its parent index DNA?
                # For now, default to NIFTY 50 if context is unclear
                index_id = "NIFTY_50"
                index_name = "NIFTY 50 (Default)"
            
            constituents = INDEX_WEIGHTS[index_id]
            tickers = list(constituents.keys())
            
            logger.info(f"Index DNA: Fetching {len(tickers)} constituents for {index_name}")
            
            # 2. Fetch Data (Batch)
            fetcher = MultiAssetDataFetcher()
            # Fetch last 2 days to calc change
            # FIX: yfinance end date is exclusive, so we add 1 day to include today
            end_date = datetime.datetime.now() + datetime.timedelta(days=1)
            start_date = end_date - datetime.timedelta(days=6)
            
            data_map = fetcher.fetch_multiple_assets(tickers, 
                                                   start_date.strftime('%Y-%m-%d'),
                                                   end_date.strftime('%Y-%m-%d'))
            
            # 3. Calculate Attribution
            attribution = []
            total_weighted_change = 0.0
            
            # Debug sample
            if tickers:
                sample_t = tickers[0]
                if sample_t in data_map and data_map[sample_t][0] is not None:
                    logger.info(f"DEBUG: Sample Data for {sample_t}:")
                    logger.info(data_map[sample_t][0].tail())
            
            for stock, weight in constituents.items():
                if stock in data_map and data_map[stock][0] is not None:
                    df = data_map[stock][0]
                    if not df.empty and len(df) >= 2:
                        close_curr = df['close'].iloc[-1]
                        close_prev = df['close'].iloc[-2]
                        
                        # Guard against zero division
                        if close_prev == 0:
                            change_pct = 0.0
                        else:
                            change_pct = ((close_curr - close_prev) / close_prev) * 100
                        
                        # Contribution points approximation
                        contrib_score = weight * change_pct
                        
                        attribution.append({
                            'Symbol': stock.replace('.NS', ''),
                            'Sector': STOCK_SECTORS.get(stock, 'Other'),
                            'Weight': weight,
                            'Price': close_curr,
                            'Change %': change_pct,
                            'Contribution': contrib_score
                        })
                        total_weighted_change += contrib_score
            
            if not attribution:
                 logger.warning("Index DNA: No attribution data calculated.")
                 return AnalysisResult(success=False, data={}, error="No constituent data available")

            df_attr = pd.DataFrame(attribution)
            df_attr = df_attr.sort_values('Contribution', ascending=False)
            
            # 4. Sector Aggregation
            sector_perf = df_attr.groupby('Sector')[['Contribution', 'Weight']].sum().sort_values('Contribution', ascending=False)
            
            return AnalysisResult(
                success=True,
                data={
                    'index_name': index_name,
                    'attribution': df_attr,
                    'sector_perf': sector_perf,
                    'total_score': total_weighted_change
                }
            )
            
        except Exception as e:
            logger.error(f"Index DNA failed: {e}", exc_info=True)
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.error(f"Index DNA error: {result.error}")
            return
            
        data = result.data
        df = data['attribution']
        
        st.markdown(f"**Target Index: {data['index_name']}**")
        
        # 1. Attribution Waterfall (Top 5 Pullers vs Draggers)
        pullers = df.head(5)
        draggers = df.tail(5).sort_values('Contribution', ascending=True) # Sort for display
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("🚀 **Top Pullers**")
            for i, row in pullers.iterrows():
                st.markdown(f"**{row['Symbol']}**: +{row['Contribution']:.2f} pts ({row['Change %']:+.2f}%)")
                try:
                    max_contrib = df['Contribution'].abs().max()
                    val = abs(row['Contribution'])/max_contrib if max_contrib > 0 else 0
                    st.progress(min(1.0, val), text=None)
                except: pass
                
        with c2:
            st.markdown("⚓ **Top Draggers**")
            for i, row in draggers.iterrows():
                st.markdown(f"**{row['Symbol']}**: {row['Contribution']:.2f} pts ({row['Change %']:+.2f}%)")
                try:
                    max_contrib = df['Contribution'].abs().max()
                    val = abs(row['Contribution'])/max_contrib if max_contrib > 0 else 0
                    st.progress(min(1.0, val), text=None)
                except: pass
        
        st.markdown("---")
        
        # 2. Sector Heatmap
        st.markdown("**Sector Performance**")
        sec_df = data['sector_perf'].reset_index()
        
        fig = px.bar(
            sec_df, 
            x='Contribution', 
            y='Sector', 
            orientation='h',
            color='Contribution',
            color_continuous_scale='RdYlGn',
            text_auto='.2f',
            title="Sector Contribution to Index Move"
        )
        fig.update_layout(height=300, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
        
        # 3. Heavyweight Radar (Top 10 by Weight)
        st.markdown("---")
        st.markdown("**Heavyweight Radar (Top 10 Weights)**")
        
        top_weights = df.sort_values('Weight', ascending=False).head(10)
        
        # Prepare for AgGrid (Custom simple table for now to match style)
        # Using columns: Symbol, Price, Change%, Weight%
        
        cols = st.columns(5)
        for i, row in enumerate(top_weights.itertuples()):
            c = cols[i % 5]
            color = "green" if row._5 > 0 else "red" # Change % is index 5
            c.metric(
                label=row.Symbol,
                value=f"{row.Price:.0f}",
                delta=f"{row._5:.2f}%"
            )
