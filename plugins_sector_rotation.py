"""
Sector Rotation Alpha Plugin
Visualizes money flow between sectors using Relative Rotation Graphs (RRG) logic
and identifies "Swing Trading" breakout candidates within leading sectors.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
from typing import Dict, Any, List
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from market_symbols import INDICES, SECTOR_CONSTITUENTS
from data_fetcher import MultiAssetDataFetcher
# We need UpstoxFOData for the derivatives check, likely passed in context or re-instantiated if needed.
# Ideally use the one from context if available, or lightweight instantiation.
try:
    from api_config import UPSTOX_API_KEY, UPSTOX_API_SECRET
    from upstox_fo_complete import UpstoxAuth, UpstoxFOData
    UPSTOX_AVAILABLE = True
except:
    UPSTOX_AVAILABLE = False

logger = logging.getLogger(__name__)

@register_plugin
class SectorRotationPlugin(AnalysisPlugin):
    """
    Sector Rotation Engine: RRG & Swing Setup Scanner
    """
    
    @property
    def name(self) -> str:
        return "Sector Rotation & Swing"
    
    @property
    def icon(self) -> str:
        return "🔄"
    
    @property
    def description(self) -> str:
        return "RRG Visualization + Top Stock Picks for 5% Swing Targets."
    
    @property
    def category(self) -> str:
        return "market"
    
    @property
    def enabled_by_default(self) -> bool:
        return True
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            # Initialize Upstox Client if keys exist (for derivatives check)
            upstox_client = None
            if UPSTOX_AVAILABLE and context['config'].get('UPSTOX_API_KEY'):
                try:
                    auth = UpstoxAuth(context['config']['UPSTOX_API_KEY'], context['config']['UPSTOX_API_SECRET'])
                    upstox_client = UpstoxFOData(auth)
                except Exception as e:
                    logger.warning(f"Sector Rotation: Upstox client init failed: {e}")

            # --- PHASE 1: SECTOR RRG ANALYSIS ---
            
            benchmark = "NIFTY 50"
            benchmark_sym = INDICES.get(benchmark, '^NSEI')
            
            # Filter only Indian Sectoral/Thematic indices + Benchmark
            sectors = {k: v for k, v in INDICES.items() if "NIFTY" in k and "VIX" not in k and "NEXT" not in k and "MIDCAP" not in k}
            all_tickers = list(sectors.values())
            
            fetcher = MultiAssetDataFetcher()
            # Need ~100 days for RRG smoothing
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=150)
            
            logger.info(f"Sector Rotation: Fetching {len(all_tickers)} indices...")
            data_map = fetcher.fetch_multiple_assets(all_tickers, 
                                                   start_date.strftime('%Y-%m-%d'),
                                                   end_date.strftime('%Y-%m-%d'))
            
            if benchmark_sym not in data_map or data_map[benchmark_sym][0] is None:
                return AnalysisResult(success=False, data={}, error="Benchmark data missing")
                
            bench_df = data_map[benchmark_sym][0]
            if bench_df.empty:
                return AnalysisResult(success=False, data={}, error="Benchmark data empty")
            
            rrg_data = []
            leading_sectors = []
            
            for name, ticker in sectors.items():
                if name == benchmark: continue
                
                if ticker in data_map and data_map[ticker][0] is not None:
                    df = data_map[ticker][0]
                    if df.empty or len(df) < 20: continue
                    
                    # Align indices
                    closes = df['close']
                    bench_closes = bench_df['close']
                    merged = pd.concat([closes, bench_closes], axis=1, join='inner')
                    merged.columns = ['Sector', 'Bench']
                    
                    # RRG Logic (Simplified)
                    rs = 100 * (merged['Sector'] / merged['Bench'])
                    rs_mean = rs.rolling(window=10).mean()
                    rs_std = rs.rolling(window=10).std()
                    
                    # RS Ratio (Trend)
                    rs_ratio = 100 + ((rs - rs_mean) / rs_std)
                    
                    # RS Momentum (ROC of Ratio)
                    rs_mom = 100 + ((rs_ratio - rs_ratio.shift(1)) * 10)
                    
                    curr_ratio = rs_ratio.iloc[-1]
                    curr_mom = rs_mom.iloc[-1]
                    
                    # Quadrant
                    if curr_ratio > 100 and curr_mom > 100: quadrant = "Leading"
                    elif curr_ratio > 100 and curr_mom < 100: quadrant = "Weakening"
                    elif curr_ratio < 100 and curr_mom < 100: quadrant = "Lagging"
                    else: quadrant = "Improving"
                    
                    rrg_data.append({
                        'Symbol': name,
                        'Ticker': ticker,
                        'RS_Ratio': curr_ratio,
                        'RS_Momentum': curr_mom,
                        'Quadrant': quadrant,
                        'PctChange': ((df['close'].iloc[-1]/df['close'].iloc[-2])-1)*100
                    })
                    
                    # Identify Focus Sectors for Phase 2
                    # We want Leading (Strong trend) or Improving (Momentum shift)
                    if quadrant in ["Leading", "Improving"]:
                        leading_sectors.append(name)
            
            # --- PHASE 2: STOCK DRILL-DOWN ---
            # For the top sectors, find constituent stocks that are primed for a move.
            
            swing_candidates = []
            
            # Limit to top 3 sectors to save API calls/time
            # Sort by Momentum first (capture the turn)
            leading_sectors = sorted(
                [x for x in rrg_data if x['Quadrant'] in ['Leading', 'Improving']],
                key=lambda x: x['RS_Momentum'], 
                reverse=True
            )[:3]
            
            target_sector_names = [x['Symbol'] for x in leading_sectors]
            logger.info(f"Drilling down into top sectors: {target_sector_names}")
            
            stocks_to_fetch = []
            stock_sector_map = {}
            
            for sec_name in target_sector_names:
                constituents = SECTOR_CONSTITUENTS.get(sec_name, [])
                for stock in constituents:
                    stocks_to_fetch.append(stock)
                    stock_sector_map[stock] = sec_name
            
            if stocks_to_fetch:
                # Shorter history needed for stock scan (50 days)
                stock_start = end_date - datetime.timedelta(days=60)
                stock_data = fetcher.fetch_multiple_assets(list(set(stocks_to_fetch)), 
                                                         stock_start.strftime('%Y-%m-%d'),
                                                         end_date.strftime('%Y-%m-%d'))
                
                # --- NEW: Phase 3 - DERIVATIVES CONFIRMATION ---
                # Fetch Futures OI for all candidates in one batch
                futures_oi_map = {}
                if upstox_client:
                    try:
                        logger.info(f"Fetching Futures OI for {len(stocks_to_fetch)} stocks...")
                        futures_oi_map = upstox_client.get_batch_futures_oi(stocks_to_fetch)
                    except Exception as e:
                        logger.error(f"Futures Batch Fetch Failed: {e}")

                for stock, (df, err) in stock_data.items():
                    if df is None or df.empty or len(df) < 20: continue
                    
                    close = df['close'].iloc[-1]
                    sma20 = df['close'].rolling(20).mean().iloc[-1]
                    
                    # Filter 1: Trend (Price > SMA20) - Basic Bullishness
                    if close > sma20:
                        
                        # Filter 2: RSI (Momentum check)
                        delta = df['close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                        rs_val = gain / loss
                        rsi = 100 - (100 / (1 + rs_val))
                        curr_rsi = rsi.iloc[-1]
                        
                        # Swing Sweet Spot: RSI 50-70
                        if 50 <= curr_rsi <= 75:
                            
                            # Filter 3: Volatility Contraction / Consolidation
                            recent_volatility = ((df['high'] - df['low']) / df['close']).rolling(3).mean().iloc[-1]
                            is_tight = recent_volatility < 0.03
                            
                            # Filter 4: Relative Volume (RVOL)
                            vol_sma = df['volume'].rolling(20).mean().iloc[-1]
                            curr_vol = df['volume'].iloc[-1]
                            rvol = curr_vol / vol_sma if vol_sma > 0 else 0
                            
                            has_volume = rvol > 1.2 # At least 20% above avg
                            
                            # --- OI CONFIRMATION ---
                            oi_data = futures_oi_map.get(stock, {})
                            oi_interp = oi_data.get('interpretation', 'No Data')
                            oi_value = oi_data.get('oi', 0)
                            
                            # Refine Interpretation based on Price & OI
                            # If we have real OI data
                            deriv_signal = "Neutral"
                            if oi_interp == "Long Buildup":
                                deriv_signal = "Bullish (Long Buildup)"
                            elif oi_interp == "Short Covering":
                                deriv_signal = "Bullish (Short Covering)"
                            
                            # Score the setup
                            score = 0
                            if is_tight: score += 1
                            if has_volume: score += 1
                            if curr_rsi > 60: score += 1 
                            if "Bullish" in deriv_signal: score += 2 # Big bonus for F&O confirmation
                            if rvol > 2.0: score += 1 # Huge Volume Spike
                            
                            # Add to candidates
                            swing_candidates.append({
                                'Symbol': stock,
                                'Sector': stock_sector_map.get(stock, 'Unknown'),
                                'Price': close,
                                'RSI': curr_rsi,
                                'RVOL': rvol,
                                'Setup Score': score,
                                'OI Signal': deriv_signal,
                                'OI': oi_value,
                                'Target (5%)': close * 1.05,
                                'Stop Loss (-2%)': close * 0.98,
                                'Pattern': 'VCP' if is_tight else ('Momentum' if curr_rsi > 60 else 'Trend')
                            })

            return AnalysisResult(
                success=True,
                data={
                    'rrg': rrg_data,
                    'candidates': swing_candidates,
                    'focus_sectors': target_sector_names
                }
            )
            
        except Exception as e:
            logger.error(f"Sector Rotation logic failed: {e}", exc_info=True)
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.error(f"Analysis failed: {result.error}")
            return
            
        rrg_data = result.data.get('rrg', [])
        candidates = result.data.get('candidates', [])
        focus_sectors = result.data.get('focus_sectors', [])
        
        # --- TAB 1: RRG VISUALIZATION ---
        tab1, tab2 = st.tabs(["Sector RRG", "Swing Picks (5% Target)"])
        
        with tab1:
            if rrg_data:
                df = pd.DataFrame(rrg_data)
                
                # Plotly Scatter
                fig = go.Figure()
                
                # Quadrants
                fig.add_shape(type="line", x0=100, y0=90, x1=100, y1=110, line=dict(color="gray", dash="dash"))
                fig.add_shape(type="line", x0=90, y0=100, x1=110, y1=100, line=dict(color="gray", dash="dash"))
                
                colors = {"Leading": "#00ff00", "Weakening": "#ffff00", "Lagging": "#ff0000", "Improving": "#0000ff"}
                
                for q, color in colors.items():
                    subset = df[df['Quadrant'] == q]
                    if not subset.empty:
                        fig.add_trace(go.Scatter(
                            x=subset['RS_Ratio'],
                            y=subset['RS_Momentum'],
                            mode='markers+text',
                            name=q,
                            text=subset['Symbol'],
                            textposition="top center",
                            marker=dict(color=color, size=12)
                        ))
                
                fig.update_layout(
                    title="Sector Relative Rotation Graph (RRG)",
                    xaxis_title="Relative Strength (Trend)",
                    yaxis_title="Momentum (Speed of Trend)",
                    height=500,
                    template="plotly_dark",
                    xaxis=dict(range=[96, 104]), # Tighter range for better view
                    yaxis=dict(range=[96, 104])
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"Drill-down Focus: {', '.join(focus_sectors)}")
        
        with tab2:
            st.markdown("### 🎯 Swing Trading Opportunities")
            st.caption("Scan Criteria: Leading Sector + Price > SMA20 + RSI(50-75) + F&O Confirmation")
            
            if candidates:
                # Convert to DF
                df_scan = pd.DataFrame(candidates)
                
                # Sort by Score desc
                df_scan = df_scan.sort_values(['Setup Score', 'RVOL'], ascending=False)
                
                # Display High Probability setups first
                best_picks = df_scan[df_scan['Setup Score'] >= 3]
                other_picks = df_scan[df_scan['Setup Score'] < 3]
                
                if not best_picks.empty:
                    st.success(f"🔥 **Top Picks ({len(best_picks)})** - High Conviction (Sector + Technicals + F&O)")
                    
                    # Custom Grid for Top Picks
                    cols = st.columns(3)
                    for idx, row in enumerate(best_picks.itertuples()):
                        with cols[idx % 3]:
                            with st.container(border=True):
                                st.markdown(f"**{row.Symbol}**")
                                st.caption(f"{row.Sector}")
                                
                                c1, c2 = st.columns(2)
                                c1.metric("Price", f"{row.Price:.2f}")
                                c2.metric("Target", f"{getattr(row, '_9'):.2f}") # _9 is Target
                                
                                # OI Signal Badge
                                if "Bullish" in row._7: # _7 is OI Signal
                                    st.markdown(f"🟢 **{row._7}**")
                                else:
                                    st.markdown(f"⚪ {row._7}")
                                    
                                st.progress(min(row.RSI/100, 1.0), text=f"RSI: {row.RSI:.1f}")
                                st.metric("RVOL", f"{row.RVOL:.2f}x")
                
                if not other_picks.empty:
                    st.markdown(f"**Watchlist ({len(other_picks)})** - Developing Setups")
                    st.dataframe(
                        other_picks[['Symbol', 'Sector', 'Price', 'RSI', 'RVOL', 'OI Signal', 'Target (5%)']],
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.warning("No high-probability swing setups found in the top sectors today.")

