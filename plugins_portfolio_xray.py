"""
Portfolio X-Ray Plugin (Enhanced)
Decomposes ETFs into underlying constituents for true exposure analysis.
Includes Attribution Analysis (Pullers & Draggers) and ETF Health Check.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from upstox_fo_complete import UpstoxAuth, UpstoxFOData
from index_composition import ETF_MAPPING, INDEX_WEIGHTS, STOCK_SECTORS
from ui_components import render_aggrid
from data_fetcher import MultiAssetDataFetcher
from services.instrument_service import instrument_service # Import service for key resolution

logger = logging.getLogger(__name__)

@register_plugin
class PortfolioXRayPlugin(AnalysisPlugin):
    """Portfolio X-Ray: ETF Decomposition & True Exposure"""
    
    @property
    def name(self) -> str:
        return "Portfolio X-Ray"
    
    @property
    def icon(self) -> str:
        return "🔬"
    
    @property
    def description(self) -> str:
        return "See inside your ETFs: True exposure, Attribution & Health Check."
    
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
            
            # Fetch Holdings
            holdings = fo_data.get_holdings()
            if not holdings:
                return AnalysisResult(success=True, data={'empty': True})
            
            # --- PHASE 1: DECOMPOSITION ENGINE ---
            
            processed_holdings = []
            etf_holdings = [] # List of ETFs for Health Check
            
            for h in holdings:
                sym = h.get('trading_symbol', '').upper()
                qty = int(h.get('quantity', 0))
                ltp = float(h.get('last_price', 0))
                val = qty * ltp
                
                is_etf = sym in ETF_MAPPING or "BEES" in sym or "ETF" in sym
                
                item = {
                    'symbol': sym,
                    'qty': qty,
                    'ltp': ltp,
                    'value': val,
                    'type': 'ETF' if is_etf else 'STOCK'
                }
                processed_holdings.append(item)
                
                if is_etf:
                    etf_holdings.append(item)
            
            total_portfolio_value = sum(x['value'] for x in processed_holdings)
            
            # Exposure Map: Stock -> {value, sources, weight}
            exposure_map = {}
            
            for item in processed_holdings:
                sym = item['symbol']
                val = item['value']
                
                # Check ETF Mapping
                index_id = ETF_MAPPING.get(sym)
                if not index_id and sym.replace('.NS', '') in ETF_MAPPING:
                    index_id = ETF_MAPPING[sym.replace('.NS', '')]
                
                if index_id and index_id in INDEX_WEIGHTS:
                    constituents = INDEX_WEIGHTS[index_id]
                    for stock, weight in constituents.items():
                        stock_val = val * (weight / 100.0)
                        if stock not in exposure_map:
                            exposure_map[stock] = {'value': 0.0, 'sources': set()}
                        exposure_map[stock]['value'] += stock_val
                        exposure_map[stock]['sources'].add(f"{sym}")
                else:
                    # Direct Stock or Unmapped ETF
                    stock_key = f"{sym}.NS" if not sym.endswith(".NS") and not "BEES" in sym else sym
                    if stock_key not in exposure_map:
                        exposure_map[stock_key] = {'value': 0.0, 'sources': set()}
                    exposure_map[stock_key]['value'] += val
                    exposure_map[stock_key]['sources'].add('Direct')
            
            # --- PREPARE QUOTE FETCH LIST ---
            # 1. Top Portfolio Exposures
            top_stocks = sorted(exposure_map.keys(), key=lambda k: exposure_map[k]['value'], reverse=True)[:50]
            stocks_to_quote = set(top_stocks)
            
            # 2. Generals (Top 3 Constituents) of held ETFs
            etf_generals_map = {} 
            
            for etf in etf_holdings:
                raw_sym = etf['symbol']
                index_id = ETF_MAPPING.get(raw_sym)
                if not index_id: index_id = ETF_MAPPING.get(raw_sym.replace('.NS', ''))
                
                if index_id and index_id in INDEX_WEIGHTS:
                    top_3 = list(INDEX_WEIGHTS[index_id].keys())[:3]
                    etf_generals_map[raw_sym] = top_3
                    for g in top_3:
                        stocks_to_quote.add(g)
            
            # FIX: Resolve to Symbols that get_batch_stock_quotes understands.
            # get_batch_stock_quotes in upstox_market.py ALREADY does key resolution internally 
            # if we pass symbols.
            # However, it expects "INFY" or "RELIANCE", not "INFY.NS".
            # AND it's failing. So let's be explicit and pass the Clean Symbols.
            
            clean_stocks_list = [s.replace('.NS', '') for s in stocks_to_quote]
            
            logger.info(f"Fetching quotes for {len(clean_stocks_list)} stocks...")
            quotes = fo_data.get_batch_stock_quotes(clean_stocks_list)
            
            # --- PHASE 2: ATTRIBUTION (PULLERS & DRAGGERS) ---
            attribution = []
            
            for stock in top_stocks:
                data_source = exposure_map[stock]
                sector = STOCK_SECTORS.get(stock, 'Other')
                weight_pct = (data_source['value'] / total_portfolio_value)
                
                change_pct = 0.0
                
                # Robust Lookup
                lookup_sym = stock.replace(".NS", "")
                
                if lookup_sym in quotes:
                    change_pct = quotes[lookup_sym].get('change_pct', 0.0)
                elif stock in quotes:
                    change_pct = quotes[stock].get('change_pct', 0.0)
                
                if change_pct is None: change_pct = 0.0
                
                impact = change_pct * weight_pct
                
                attribution.append({
                    'Stock': lookup_sym,
                    'Sector': sector,
                    'Value': data_source['value'],
                    'Weight %': weight_pct * 100,
                    'Sources': ", ".join(data_source['sources']),
                    'Change %': change_pct,
                    'Impact': impact
                })

            df_exposure = pd.DataFrame(attribution)
            
            # --- PHASE 3: ETF HEALTH CHECK ---
            etf_health_report = []
            
            if etf_holdings:
                fetcher = MultiAssetDataFetcher()
                import datetime
                end_d = datetime.datetime.now()
                start_d = end_d - datetime.timedelta(days=60)
                
                etf_symbols = [x['symbol'] for x in etf_holdings]
                yf_etf_syms = [s if s.endswith('.NS') else f"{s}.NS" for s in etf_symbols]
                
                etf_data_map = fetcher.fetch_multiple_assets(yf_etf_syms, start_d.strftime('%Y-%m-%d'), end_d.strftime('%Y-%m-%d'))
                
                for idx, etf_item in enumerate(etf_holdings):
                    raw_sym = etf_item['symbol']
                    yf_sym = yf_etf_syms[idx]
                    
                    status = "Unknown"
                    trend_score = 0
                    
                    if yf_sym in etf_data_map and etf_data_map[yf_sym][0] is not None:
                        df = etf_data_map[yf_sym][0]
                        if not df.empty and len(df) > 20:
                            close = df['close'].iloc[-1]
                            sma20 = df['close'].rolling(20).mean().iloc[-1]
                            sma50 = df['close'].rolling(50).mean().iloc[-1]
                            
                            if close > sma20: trend_score += 1
                            if close > sma50: trend_score += 1
                            
                            if trend_score == 2: status = "Bullish (Strong)"
                            elif trend_score == 1: status = "Neutral / Weak"
                            else: status = "Bearish (Broken Trend)"
                    
                    # Detailed Generals Check
                    generals_info = []
                    if raw_sym in etf_generals_map:
                        for gen in etf_generals_map[raw_sym]:
                            # Get change from quotes
                            chg = 0.0
                            lookup_gen = gen.replace('.NS', '')
                            
                            if lookup_gen in quotes:
                                chg = quotes[lookup_gen].get('change_pct', 0.0)
                            
                            if chg is None: chg = 0.0
                            
                            short_name = lookup_gen
                            sign = "+" if chg >= 0 else ""
                            color = "green" if chg >= 0 else "red"
                            formatted = f":{color}[{short_name} {sign}{chg:.2f}%]"
                            generals_info.append(formatted)
                            
                    breadth_str = ", ".join(generals_info) if generals_info else "Data N/A"
                    
                    etf_health_report.append({
                        "ETF": raw_sym,
                        "Trend": status,
                        "Generals": breadth_str,
                        "Value": etf_item['value']
                    })

            # Create Sector DF
            if not df_exposure.empty:
                df_sector = df_exposure.groupby('Sector')['Value'].sum().reset_index()
                df_sector['Weight %'] = (df_sector['Value'] / total_portfolio_value) * 100
                df_sector = df_sector.sort_values('Value', ascending=False)
            else:
                df_sector = pd.DataFrame()

            return AnalysisResult(
                success=True,
                data={
                    'exposure': df_exposure,
                    'sectors': df_sector,
                    'etf_health': etf_health_report,
                    'total_value': total_portfolio_value,
                    'attribution_ready': not df_exposure.empty
                }
            )
            
        except Exception as e:
            logger.error(f"X-Ray analysis failed: {e}", exc_info=True)
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"X-Ray: {result.error}")
            return
        
        data = result.data
        if data.get('empty'):
            st.info("Portfolio is empty. Add holdings to see X-Ray.")
            return
            
        df_exp = data['exposure']
        etf_health = data.get('etf_health', [])
        total_val = data['total_value']
        
        st.subheader(f"{self.icon} {self.name}")
        
        # --- TAB STRUCTURE ---
        tab_health, tab_comp, tab_attrib = st.tabs(["🏥 ETF Health", "🧬 Composition", "🚀 Attribution"])
        
        with tab_health:
            if etf_health:
                st.markdown("### ETF Trend & Breadth Monitor")
                cols = st.columns(3)
                for i, row in enumerate(etf_health):
                    with cols[i % 3]:
                        color = "green" if "Bullish" in row['Trend'] else "red" if "Bearish" in row['Trend'] else "orange"
                        with st.container(border=True):
                            st.markdown(f"**{row['ETF']}**")
                            st.caption(f"₹{row['Value']:,.0f}")
                            st.markdown(f"Trend: :{color}[**{row['Trend']}**]")
                            st.divider()
                            st.caption("Top 3 Generals:")
                            st.markdown(row['Generals'])
            else:
                st.info("No ETF holdings found for Health Check.")

        with tab_comp:
            if not df_exp.empty:
                col1, col2 = st.columns([3, 2])
                with col1:
                    fig = px.treemap(
                        df_exp,
                        path=[px.Constant("Portfolio"), 'Sector', 'Stock'],
                        values='Value',
                        color='Sector',
                        color_discrete_sequence=px.colors.qualitative.Dark24
                    )
                    fig.update_layout(height=450, margin=dict(t=0, l=0, r=0, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.markdown("**Top Effective Holdings**")
                    # Display table with Change %
                    df_disp = df_exp[['Stock', 'Weight %', 'Change %', 'Sources']].head(10).copy()
                    df_disp['Change %'] = df_disp['Change %'].apply(lambda x: f"{x:+.2f}%")
                    df_disp['Weight %'] = df_disp['Weight %'].apply(lambda x: f"{x:.2f}%")
                    render_aggrid(df_disp, height=400)

        with tab_attrib:
            if not df_exp.empty:
                # Ensure float
                df_exp['Impact'] = df_exp['Impact'].astype(float)
                
                # Filter out zero impact to avoid clutter
                # But keep significant ones
                df_movers = df_exp[df_exp['Impact'].abs() > 0.001]
                
                if df_movers.empty:
                     st.info("No significant movers today (Impact close to 0).")
                else:
                    pullers = df_movers[df_movers['Impact'] > 0].nlargest(5, 'Impact')
                    draggers = df_movers[df_movers['Impact'] < 0].nsmallest(5, 'Impact')
                    waterfall_data = pd.concat([pullers, draggers]).sort_values('Impact', ascending=False)
                    
                    if not waterfall_data.empty:
                        fig = go.Figure(go.Waterfall(
                            name = "Attribution", orientation = "v",
                            measure = ["relative"] * len(waterfall_data),
                            x = waterfall_data['Stock'],
                            text = [f"{x:+.2f}%" for x in waterfall_data['Impact']],
                            y = waterfall_data['Impact'],
                            connector = {"line":{"color":"#666666"}},
                            increasing = {"marker":{"color":"#00E676"}},
                            decreasing = {"marker":{"color":"#FF5252"}}
                        ))
                        fig.update_layout(title="Top Portfolio Movers (Impact %)", height=500)
                        st.plotly_chart(fig, use_container_width=True)
