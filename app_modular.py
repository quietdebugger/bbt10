"""
Modular Market Intelligence Terminal - Bloomberg Edition (Refined UX)
✅ On-Demand Analysis (No more "Run All")
✅ Tabbed Interface (Organized Workspace)
✅ Persistent State (No random refreshes)
✅ Bloomberg-style Dark Theme
"""

import streamlit as st
import pandas as pd
import datetime
import yfinance as yf
import time
import sys
import os
import numpy as np

# Import Logger
from logger import logger

# --- LOGGING SETUP (Transferred from run_app.py) ---
# Redirect stdout and stderr to files for debugging
try:
    # Use absolute paths based on this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    stdout_path = os.path.join(script_dir, "app.out")
    stderr_path = os.path.join(script_dir, "app.err")
    
    # Check if running in a way that we want to redirect (e.g. not dev mode if we want console)
    # But user requested to transfer logic.
    sys.stdout = open(stdout_path, "a", encoding="utf-8")
    sys.stderr = open(stderr_path, "a", encoding="utf-8")
except Exception as e:
    logger.error(f"Failed to redirect stdout/stderr: {e}")

# Import architecture
from architecture_modular import REGISTRY, AnalysisResult
from plugins_core import *  # Auto-registers plugins
from plugins_advanced import *  # Auto-registers plugins
from plugins_correlation import * # Auto-registers Correlation Analysis plugin
from plugins_volume import * # Auto-registers Volume Analysis plugin
from plugins_fundamentals import * # Auto-registers Fundamental Analysis plugin
from plugins_attribution import * # Auto-registers Attribution Analysis plugin
from plugins_forensic import * # Auto-registers Forensic Analysis plugin
from plugins_whale import * # Auto-registers Whale Analysis plugin
from plugins_dashboard import * # Auto-registers Dashboard plugins (Risk, Action, Macro)
from plugins_watch import * # Auto-registers Watch List plugin
from plugins_screener import * # Auto-registers Announcements/Screener plugin
from plugins_honest import * # Auto-registers Change Detection plugin
from plugins_state import * # Auto-registers Market State plugin
from plugins_portfolio import * # Auto-registers Portfolio plugin
from plugins_portfolio_xray import * # Auto-registers X-Ray plugin
from plugins_pro import * # Auto-registers Pro plugins (Alerts, Macro, News)
from plugins_alpha import * # Auto-registers Alpha Fusion
from plugins_chart import * # Auto-registers Interactive Chart Plugin
from plugins_macro_regime import * # Auto-registers Macro Regime Plugin
from plugins_backtester import * # Auto-registers Backtester Plugin
from plugins_index_dna import * # Auto-registers Index DNA Plugin
from plugins_sector_rotation import * # Auto-registers Sector Rotation Plugin
from plugins_global_macro import * # Auto-registers Global Macro Bridge Plugin
from ui_components import render_news_ticker, render_aggrid
from ui_styles import apply_terminal_style
from market_symbols import INDICES, STOCKS, get_stock_dict

# Import config
try:
    from api_config import (
        UPSTOX_API_KEY, UPSTOX_API_SECRET,
        GEMINI_API_KEY
    )
except ImportError:
    st.error("api_config.py not found! Copy api_config.template.py")
    st.stop()

from data_fetcher import MultiAssetDataFetcher

# Configure Page
st.set_page_config(page_title="Bloomberg Terminal", page_icon="🏛️", layout="wide")

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_session_key(plugin_name):
    return f"result_{plugin_name}"

def clear_all_results(rerun=True):
    """Clears all analysis results from session state"""
    for key in list(st.session_state.keys()):
        if key.startswith("result_"):
            del st.session_state[key]
    if rerun:
        st.rerun()

def render_plugin_ui(plugin, context):
    """
    Renders the UI for a single plugin:
    - If result exists in session state: Show Result + Refresh/Clear buttons
    - If no result: Show Run button
    """
    if plugin is None:
        return

    session_key = get_session_key(plugin.name)
    
    # Check for missing config
    missing_config = []
    for req in plugin.requires_config:
        if req == 'UPSTOX_API_KEY' and not context['config'].get('UPSTOX_API_KEY'):
            missing_config.append("Upstox API Key")
        elif req == 'GEMINI_API_KEY' and not context['config'].get('GEMINI_API_KEY'):
            missing_config.append("Gemini API Key")
    
    # Minimal Header
    c_head, c_btn = st.columns([8, 2])
    with c_head:
        st.markdown(f"**{plugin.name.upper()}**")
    
    if missing_config:
        st.error(f"⚠️ Config: {', '.join(missing_config)}")
        return

    # Check if we have a result
    if session_key in st.session_state:
        result = st.session_state[session_key]
        
        # Toolbar (Compact)
        with c_btn:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("↻", key=f"refresh_{plugin.name}", help="Refresh"):
                    with st.spinner("..."):
                        try:
                            logger.info(f"Refreshing plugin: {plugin.name}")
                            new_result = plugin.analyze(context)
                            st.session_state[session_key] = new_result
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
            with c2:
                if st.button("✕", key=f"clear_{plugin.name}", help="Close"):
                    del st.session_state[session_key]
                    st.rerun()
        
        # Render the plugin result
        st.markdown("---")
        try:
            plugin.render(result)
        except Exception as e:
            st.error(f"Render Error: {e}")
            logger.error(f"Error rendering plugin '{plugin.name}': {e}", exc_info=True)
            
    else:
        # Run Button
        if st.button(f"▶ Run", key=f"run_{plugin.name}", type="secondary"):
            with st.spinner("..."):
                try:
                    logger.info(f"Running plugin: {plugin.name}")
                    result = plugin.analyze(context)
                    st.session_state[session_key] = result
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")
                    logger.exception(f"Plugin {plugin.name} failed")

def main():
    apply_terminal_style()
    
    # State management for configuration
    if 'config_state' not in st.session_state:
        st.session_state.config_state = {
            'symbol': "^NSEI",
            'upstox_symbol': "Nifty 50",
            'days_back': 180,
            'compare': ['^NSEBANK', 'RELIANCE.NS', 'HDFCBANK.NS', 'INFY.NS']
        }

    # ==========================================
    # SIDEBAR: SYSTEM & LOGS ONLY
    # ==========================================
    with st.sidebar:
        st.caption("SYSTEM STATUS")
        st.success("● ONLINE")
        
        if st.button("⚠️ EMERGENCY RESET", use_container_width=True):
            logger.warning("Emergency Reset triggered by user")
            clear_all_results(rerun=True)
            
        with st.expander("System Logs"):
            try:
                with open("bbt10/app.log", "r") as f:
                    logs = f.readlines()[-20:]
                    st.code("".join(logs), language="text")
            except:
                st.caption("No logs available")

    # ==========================================
    # MASTER GRID LAYOUT
    # ==========================================
    
    try:
        # --- ROW 1: INDICES (HUD) ---
        # Compact row
        cols = st.columns(6)
        metrics = [
            ("NIFTY 50", "^NSEI"), ("SENSEX", "^BSESN"), ("S&P 500", "^GSPC"),
            ("NASDAQ", "^IXIC"), ("USD/INR", "INR=X"), ("GOLD", "GC=F")
        ]
        
        # Quick fetch for HUD
        try:
            hud_data = yf.download([m[1] for m in metrics], period="2d", progress=False)['Close']
            
            for i, (label, sym) in enumerate(metrics):
                val = 0.0
                delta = 0.0
                if sym in hud_data.columns:
                    series = hud_data[sym].dropna()
                    if len(series) >= 2:
                        val = series.iloc[-1]
                        prev = series.iloc[-2]
                        delta = ((val - prev) / prev) * 100
                    elif len(series) == 1:
                        val = series.iloc[-1]
                
                with cols[i]:
                    st.metric(label, f"{val:,.2f}", f"{delta:+.2f}%")
        except Exception as e:
            logger.error(f"HUD Fetch Error: {e}")

        st.markdown("---")

        # --- ROW 2: COMMAND BAR (Top-Nav) ---
        # [Asset Class] [Ticker] [Timeframe] [Update Button]
        c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
        
        with c1:
            scope = st.selectbox("Asset Class", ["NIFTY 50", "NIFTY MIDCAP", "STOCK"], label_visibility="collapsed")
        
        with c2:
            if scope == "NIFTY 50":
                default_sym = "^NSEI"
                default_upstox = "Nifty 50"
                st.text_input("Ticker", value="NIFTY 50", disabled=True, label_visibility="collapsed")
            elif scope == "NIFTY MIDCAP":
                default_sym = "NIFTY_MIDCAP_100.NS"
                default_upstox = "Nifty Midcap 100"
                st.text_input("Ticker", value="NIFTY MIDCAP", disabled=True, label_visibility="collapsed")
            else:
                # Combined List: Indices + Stocks
                stock_map = get_stock_dict()
                index_map = INDICES
                
                # Merge keys for display
                analysis_options = list(index_map.keys()) + list(stock_map.keys())
                
                symbol_selection = st.selectbox(
                    "Ticker",
                    analysis_options,
                    label_visibility="collapsed"
                )
                
                # Resolve symbol based on selection
                if symbol_selection in index_map:
                    default_sym = index_map[symbol_selection]
                    default_upstox = symbol_selection # Indices usually match their name or need simple mapping
                else:
                    default_sym = stock_map.get(symbol_selection, symbol_selection)
                    default_upstox = symbol_selection
        
        with c3:
            days_back = st.slider("Timeframe", 30, 365, 180, label_visibility="collapsed")
            
        with c4:
            if st.button("UPDATE VIEW", use_container_width=True, type="primary"):
                logger.info(f"Configuration updated: {default_sym}, {days_back} days")
                st.session_state.config_state['symbol'] = default_sym
                st.session_state.config_state['upstox_symbol'] = default_upstox
                st.session_state.config_state['days_back'] = days_back
                clear_all_results(rerun=True)

        st.markdown("---")

        # --- ROW 3: WORKSPACE (70/30 Split) ---
        col_left, col_right = st.columns([7, 3])

        context = {
            'symbol': st.session_state.config_state['symbol'],
            'upstox_symbol': st.session_state.config_state['upstox_symbol'],
            'symbols_to_compare': st.session_state.config_state['compare'],
            'date_range': {
                'start': (datetime.datetime.now() - datetime.timedelta(days=st.session_state.config_state['days_back'])).strftime('%Y-%m-%d'),
                'end': datetime.datetime.now().strftime('%Y-%m-%d')
            },
            'config': {
                'UPSTOX_API_KEY': UPSTOX_API_KEY,
                'UPSTOX_API_SECRET': UPSTOX_API_SECRET,
                'GEMINI_API_KEY': GEMINI_API_KEY
            }
        }
        
        # PRE-FETCH PRICE DATA for Key Levels
        price_data = None
        try:
            fetcher = MultiAssetDataFetcher()
            # We need sufficient history for 52W High/Low (1 year approx)
            start_date_extended = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
            
            price_data = fetcher.fetch_asset(
                context['symbol'],
                start_date_extended, # Fetch 1 year for 52W levels
                context['date_range']['end']
            )
            context['price_data'] = price_data # Inject into context for plugins
        except Exception as e:
            logger.error(f"Price data fetch failed: {e}")

        with col_left:
            # Main Analysis Area
            # Added "Sector Rotation" tab
            tab_dash, tab_port, tab_tech, tab_fund, tab_options, tab_ai, tab_quant, tab_sector = st.tabs([
                "Dashboard", "Portfolio", "Technicals", "Fundamentals", "Options Chain", "AI Insights", "Quant Lab", "Sector Rotation"
            ])

            with tab_dash:
                # Add Index DNA and Macro Regime here
                render_plugin_ui(REGISTRY.get_plugin("Index DNA"), context)
                st.markdown("---")
                render_plugin_ui(REGISTRY.get_plugin("Global Macro Bridge"), context)
                st.markdown("---")
                render_plugin_ui(REGISTRY.get_plugin("Macro Regime"), context)
                st.markdown("---")
                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    render_plugin_ui(REGISTRY.get_plugin("Market State"), context)
                    render_plugin_ui(REGISTRY.get_plugin("Action Items"), context)
                with c_d2:
                    render_plugin_ui(REGISTRY.get_plugin("Risk Radar"), context)
                    render_plugin_ui(REGISTRY.get_plugin("Real-Time Alerts"), context)
            
            with tab_port:
                render_plugin_ui(REGISTRY.get_plugin("My Portfolio"), context)
                render_plugin_ui(REGISTRY.get_plugin("Portfolio X-Ray"), context)

            with tab_tech:
                # --- KEY LEVELS SUB-SECTION (Bloomberg Logic) ---
                if price_data is not None and not price_data.empty:
                    # Rename columns to standard Title Case if needed
                    df = price_data.copy()
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    col_map = {c: c.capitalize() for c in df.columns}
                    df.rename(columns=col_map, inplace=True)
                    
                    if 'Close' in df.columns and 'High' in df.columns and 'Low' in df.columns:
                        latest = df.iloc[-1]
                        prev = df.iloc[-2] if len(df) > 1 else latest
                        
                        # 1. Pivot Points (Classic)
                        # P = (High + Low + Close) / 3 (using Previous Day)
                        pp = (prev['High'] + prev['Low'] + prev['Close']) / 3
                        r1 = (2 * pp) - prev['Low']
                        s1 = (2 * pp) - prev['High']
                        
                        # 2. 52-Week High/Low Proximity
                        # Filter last 252 trading days (approx 1 year)
                        df_1y = df.tail(252)
                        high_52w = df_1y['High'].max()
                        low_52w = df_1y['Low'].min()
                        current_price = latest['Close']
                        
                        prox_high = ((current_price - high_52w) / high_52w) * 100
                        prox_low = ((current_price - low_52w) / low_52w) * 100
                        
                        # 3. Relative Volume (RVOL)
                        # Current Vol / 20-Day Avg Vol
                        if 'Volume' in df.columns:
                            avg_vol_20 = df['Volume'].rolling(20).mean().iloc[-1]
                            curr_vol = latest['Volume']
                            rvol = curr_vol / avg_vol_20 if avg_vol_20 > 0 else 0
                        else:
                            rvol = 0
                        
                        st.subheader("🔑 Key Levels")
                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("Pivot (P)", f"₹{pp:,.2f}")
                        k2.metric("Resistance (R1)", f"₹{r1:,.2f}")
                        k3.metric("Support (S1)", f"₹{s1:,.2f}")
                        k4.metric("RVOL (20D)", f"{rvol:.2f}x")
                        
                        k5, k6 = st.columns(2)
                        k5.metric("52W High Prox", f"{prox_high:.2f}%", f"High: ₹{high_52w:,.2f}")
                        k6.metric("52W Low Prox", f"{prox_low:+.2f}%", f"Low: ₹{low_52w:,.2f}")
                        
                        st.markdown("---")

                # --- INTERACTIVE CHART (Proposal 1) ---
                render_plugin_ui(REGISTRY.get_plugin("Interactive Chart"), context)
                st.markdown("---")

                c_t1, c_t2 = st.columns(2)
                with c_t1:
                     render_plugin_ui(REGISTRY.get_plugin("Volume Analysis"), context)
                with c_t2:
                     render_plugin_ui(REGISTRY.get_plugin("Whale Hunter"), context)

            with tab_fund:
                render_plugin_ui(REGISTRY.get_plugin("Fundamental Analysis"), context)
                render_plugin_ui(REGISTRY.get_plugin("Forensic Lab"), context)
            
            with tab_options:
                c_o1, c_o2 = st.columns(2)
                with c_o1:
                    render_plugin_ui(REGISTRY.get_plugin("Options Analysis"), context)
                with c_o2:
                    render_plugin_ui(REGISTRY.get_plugin("Futures Analysis"), context)

            with tab_ai:
                render_plugin_ui(REGISTRY.get_plugin("Alpha Fusion"), context)
                render_plugin_ui(REGISTRY.get_plugin("AI Insights"), context)
            
            with tab_quant:
                render_plugin_ui(REGISTRY.get_plugin("Quant Lab"), context)
                
            with tab_sector:
                render_plugin_ui(REGISTRY.get_plugin("Sector Rotation & Swing"), context)

        with col_right:
            # Watchlist Area
            st.markdown("**WATCHLIST**")
            
            # Selector for Watchlist Mode
            wl_mode = st.radio("List", ["Top Stocks", "Major Indices"], horizontal=True, label_visibility="collapsed")
            
            if wl_mode == "Top Stocks":
                watchlist_symbols = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ITC.NS', 'SBIN.NS', 'BAJFINANCE.NS', 'BHARTIARTL.NS']
            else:
                # Filter for Indian Indices (NSE/BSE) from INDICES map
                watchlist_symbols = [
                    v for k, v in INDICES.items() 
                    if any(x in k.upper() for x in ["NIFTY", "SENSEX", "BANK", "VIX"])
                ]

            try:
                # Fetch live data using MultiAssetDataFetcher (Upstox First)
                fetcher = MultiAssetDataFetcher()
                
                # Fetch last 2 days to calculate change
                end_date = datetime.datetime.now() + datetime.timedelta(days=1)
                start_date = end_date - datetime.timedelta(days=6)
                
                w_data_map = fetcher.fetch_multiple_assets(
                    watchlist_symbols, 
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                watchlist_rows = []
                for sym in watchlist_symbols:
                    # Resolve display name
                    display_name = sym
                    # Reverse lookup for Index Name if it's an index ticker
                    for name, ticker in INDICES.items():
                        if ticker == sym:
                            display_name = name
                            break
                    if display_name == sym:
                        display_name = sym.replace('.NS', '')

                    if sym in w_data_map and w_data_map[sym][0] is not None:
                        df = w_data_map[sym][0]
                        if not df.empty and len(df) >= 1:
                            curr = df['close'].iloc[-1]
                            # Calculate change
                            if len(df) >= 2:
                                prev = df['close'].iloc[-2]
                                chg = ((curr - prev) / prev) * 100
                            else:
                                chg = 0.0
                            
                            # Get Volume
                            vol = df['volume'].iloc[-1] if 'volume' in df.columns else 0
                            
                            # Format Volume (K, M, B)
                            if vol >= 1_000_000_000:
                                vol_str = f"{vol/1_000_000_000:.2f}B"
                            elif vol >= 1_000_000:
                                vol_str = f"{vol/1_000_000:.2f}M"
                            elif vol >= 1_000:
                                vol_str = f"{vol/1_000:.2f}K"
                            else:
                                vol_str = f"{vol:.0f}"

                            watchlist_rows.append({
                                "Symbol": display_name,
                                "LTP": curr,
                                "Chg%": chg,
                                "Vol": vol_str
                            })
                        else:
                             watchlist_rows.append({"Symbol": display_name, "LTP": 0.0, "Chg%": 0.0, "Vol": "-"})
                    else:
                        watchlist_rows.append({"Symbol": display_name, "LTP": 0.0, "Chg%": 0.0, "Vol": "-"})
                
                if watchlist_rows:
                    w_df = pd.DataFrame(watchlist_rows)
                    # Format
                    w_df['LTP'] = w_df['LTP'].apply(lambda x: f"{x:,.2f}")
                    w_df['Chg%'] = w_df['Chg%'].apply(lambda x: f"{x:+.2f}%")
                    
                    # Use render_aggrid with row_height support
                    render_aggrid(w_df, height=600, row_height=25) 
                else:
                    st.info("No Data")
                    
            except Exception as e:
                logger.error(f"Watchlist Error: {e}", exc_info=True)
                st.error("Watchlist Error")
            
            st.markdown("---")
            st.caption("ALERTS")
            st.warning("High Volatility: Nifty Bank")

    except Exception as e:
        logger.error("Critical System Failure", exc_info=True)
        st.error(f"⚠️ SYSTEM ERROR: {str(e)}")
        st.caption(f"Timestamp: {datetime.datetime.now().strftime('%H:%M:%S')}")
        st.caption("Check app.log for detailed traceback.")

if __name__ == "__main__":
    main()
