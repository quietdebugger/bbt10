"""
Attribution Analysis Plugin
Integrates Attribution Engine from bbt3 for causal market analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from sklearn.linear_model import Ridge
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from ui_components import render_aggrid

logger = logging.getLogger(__name__)

# --- Ported AttributionEngine from bbt3/attribution_engine.py ---

class AttributionEngine:
    """
    Quantifies causality using rolling regression
    Answers: "Today's -1% move was driven 70% by Nasdaq and 30% by HDFC Bank"
    """
    
    def __init__(self, primary_data: pd.DataFrame, primary_symbol: str):
        """
        Initialize attribution engine
        
        Args:
            primary_data: OHLCV data for primary asset
            primary_symbol: Symbol identifier
        """
        self.primary_data = primary_data.copy()
        self.primary_symbol = primary_symbol
        # Ensure column case consistency
        col_map = {c: c.lower() for c in self.primary_data.columns}
        self.primary_data.rename(columns=col_map, inplace=True)
        
        self.primary_returns = self.primary_data['close'].pct_change()
        
        # Storage for drivers
        self.drivers = {}
        self.driver_returns = {}
        
        logger.info(f"AttributionEngine initialized for {primary_symbol}")
    
    def add_driver(self, symbol: str, data: pd.DataFrame, description: str = ""):
        """
        Add a driver (explanatory variable)
        """
        # Handle yfinance returning tuple (data, meta)
        if isinstance(data, tuple):
            data = data[0]
            
        df = data.copy()
        
        # Handle MultiIndex columns (common in recent yfinance)
        if isinstance(df.columns, pd.MultiIndex):
            # Flatten or drop levels. Usually level 0 is 'Price' (Close, Open)
            # If standard yfinance download: ('Close', 'TICKER')
            df.columns = df.columns.get_level_values(0)

        # Ensure we have a DataFrame
        if not isinstance(df, pd.DataFrame):
             logger.warning(f"Driver data for {symbol} is not a DataFrame: {type(df)}")
             return

        col_map = {c: c.lower() for c in df.columns}
        df.rename(columns=col_map, inplace=True)
        
        if 'close' not in df.columns:
             logger.warning(f"Driver data for {symbol} missing 'close' column. Columns: {df.columns}")
             return

        self.drivers[symbol] = {
            'data': df,
            'description': description or symbol
        }
        self.driver_returns[symbol] = df['close'].pct_change()
        logger.info(f"Added driver: {symbol}")
    
    def attribute_daily_move(
        self,
        date: Optional[datetime] = None,
        window: int = 60
    ) -> Dict:
        """
        Attribute a specific day's move to different drivers
        Uses RECENT regression coefficients (last 60 days)
        """
        # Align returns
        all_returns = pd.DataFrame({
            'target': self.primary_returns
        })
        
        for symbol, returns in self.driver_returns.items():
            all_returns[symbol] = returns
        
        all_returns = all_returns.dropna()
        
        if all_returns.empty:
             return {'error': 'No overlapping data found between target and drivers'}

        if date is None:
            date = all_returns.index[-1]
        elif date not in all_returns.index:
             # Find closest previous date
             idx = all_returns.index.get_indexer([date], method='pad')[0]
             if idx == -1:
                 return {'error': f'Date {date} not found in data'}
             date = all_returns.index[idx]
        
        # Get training window (exclude target date)
        try:
            train_end_idx = all_returns.index.get_loc(date)
            train_start_idx = max(0, train_end_idx - window)
            
            train_data = all_returns.iloc[train_start_idx:train_end_idx]
            
            if len(train_data) < 20:
                return {'error': "Insufficient training data (< 20 days)"}
            
            # Fit model
            X_train = train_data.drop('target', axis=1).values
            y_train = train_data['target'].values
            
            model = Ridge(alpha=0.1)
            model.fit(X_train, y_train)
            
            # Get actual returns on target date
            target_return = all_returns.loc[date, 'target']
            driver_returns_on_date = all_returns.loc[date].drop('target')
            
            # Calculate contributions
            contributions = {}
            total_explained = model.intercept_ * 100 
            
            for i, symbol in enumerate(self.driver_returns.keys()):
                coef = model.coef_[i]
                driver_ret = driver_returns_on_date[symbol]
                
                # Contribution to return
                contribution = coef * driver_ret
                contribution_pct = (contribution / target_return * 100) if target_return != 0 else 0
                
                contributions[symbol] = {
                    'coefficient': coef,
                    'driver_return': driver_ret * 100,
                    'contribution': contribution * 100,
                    'contribution_pct': contribution_pct,
                    'description': self.drivers[symbol]['description']
                }
                
                total_explained += contribution * 100
            
            # Calculate unexplained portion
            unexplained = (target_return * 100) - total_explained
            unexplained_pct = (unexplained / (target_return * 100) * 100) if target_return != 0 else 0
            
            # Sort by absolute contribution
            sorted_contributions = sorted(
                contributions.items(),
                key=lambda x: abs(x[1]['contribution_pct']),
                reverse=True
            )
            
            return {
                'date': date,
                'target_return': target_return * 100,
                'target_symbol': self.primary_symbol,
                'contributions': dict(sorted_contributions),
                'total_explained': total_explained,
                'unexplained': unexplained,
                'unexplained_pct': unexplained_pct,
                'model_r_squared': model.score(X_train, y_train)
            }
        except Exception as e:
            logger.error(f"Error in attribution calculation: {e}")
            return {'error': str(e)}

    def detect_lead_lag_advanced(
        self,
        driver_symbol: str,
        max_lag: int = 5
    ) -> Dict:
        """
        Advanced lead-lag using Granger causality test
        """
        try:
            from statsmodels.tsa.stattools import grangercausalitytests
        except ImportError:
            return {'driver': driver_symbol, 'error': "statsmodels not installed"}

        # Align data
        target = self.primary_returns.dropna()
        driver = self.driver_returns[driver_symbol].dropna()
        
        common_dates = target.index.intersection(driver.index)
        target = target[common_dates]
        driver = driver[common_dates]
        
        if len(target) < 60:
             return {'driver': driver_symbol, 'error': "Insufficient data for Granger test"}

        # Prepare data for Granger test
        data = pd.DataFrame({
            'target': target,
            'driver': driver
        })
        
        try:
            # Granger causality test
            # Tests if driver helps predict target
            # verbose=False suppresses print output
            gc_result = grangercausalitytests(data[['target', 'driver']], max_lag, verbose=False)
            
            # Find optimal lag (lowest p-value)
            p_values = {}
            for lag in range(1, max_lag + 1):
                # Get p-value from F-test (index 0 is test params, index 1 is p-value)
                # Structure: {lag: ({tests}, [objs])}
                # ssr_ftest is usually at key 'ssr_ftest'
                p_value = gc_result[lag][0]['ssr_ftest'][1]
                p_values[lag] = p_value
            
            optimal_lag = min(p_values.keys(), key=lambda k: p_values[k])
            optimal_p_value = p_values[optimal_lag]
            
            # Interpret
            if optimal_p_value < 0.01:
                significance = "Very Strong"
                is_significant = True
            elif optimal_p_value < 0.05:
                significance = "Strong"
                is_significant = True
            elif optimal_p_value < 0.10:
                significance = "Moderate"
                is_significant = True
            else:
                significance = "Weak"
                is_significant = False
            
            return {
                'driver': driver_symbol,
                'optimal_lag': optimal_lag,
                'p_value': optimal_p_value,
                'significance': significance,
                'is_significant': is_significant,
                'interpretation': f"Leads by {optimal_lag} day(s)" if is_significant else "No significant lead"
            }
            
        except Exception as e:
            logger.warning(f"Granger causality test failed: {e}")
            return {
                'driver': driver_symbol,
                'error': str(e)
            }


# --- Attribution Analysis Plugin ---

@register_plugin
class AttributionAnalysisPlugin(AnalysisPlugin):
    """
    Macro attribution analysis to explain market moves
    """
    
    @property
    def name(self) -> str:
        return "Market Attribution"
    
    @property
    def icon(self) -> str:
        return "🧠"
    
    @property
    def description(self) -> str:
        return "Quantifies what drove the market move (e.g., US Tech vs Oil)"
    
    @property
    def category(self) -> str:
        return "macro"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        primary_data = context.get('price_data')
        symbol = context.get('symbol', 'Unknown')
        
        if primary_data is None or primary_data.empty:
            return AnalysisResult(success=False, data={}, error="Primary asset data unavailable")
            
        # Define drivers to fetch
        # Standard macro drivers
        drivers_map = {
            '^GSPC': 'S&P 500 (US Market)',
            '^IXIC': 'Nasdaq (US Tech)',
            'DX-Y.NYB': 'Dollar Index (DXY)',
            'CL=F': 'Crude Oil',
            '^TNX': 'US 10Y Yield',
            '^NSEBANK': 'Bank Nifty' # Internal correlation if analyzing Nifty
        }
        
        # If analyzing a stock, include Nifty
        if '^NSEI' not in symbol:
             drivers_map['^NSEI'] = 'Nifty 50'
        
        engine = AttributionEngine(primary_data, symbol)
        
        # Fetch driver data
        # We need historical data for regression
        start_date = context.get('date_range', {}).get('start')
        end_date = context.get('date_range', {}).get('end')
        
        if not start_date:
             # Default to 1 year back if not provided
             end_date = datetime.now().strftime('%Y-%m-%d')
             start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        fetched_drivers = {}
        
        for driver_sym, desc in drivers_map.items():
            if driver_sym == symbol: continue # Don't correlate with self
            
            try:
                # Use yfinance directly for simplicity here, or use DataFetcher if available in context
                # Assuming simple yf download is robust enough for macro indices
                data = yf.download(driver_sym, start=start_date, end=end_date, progress=False)
                if not data.empty:
                    engine.add_driver(driver_sym, data, desc)
                    fetched_drivers[driver_sym] = True
            except Exception as e:
                logger.warning(f"Failed to fetch driver {driver_sym}: {e}")
        
        if not fetched_drivers:
             return AnalysisResult(success=False, data={}, error="Could not fetch any macro drivers for attribution.")

        # Run Analysis
        daily_attr = engine.attribute_daily_move()
        
        # Run Lead-Lag
        lead_lag_results = {}
        for driver_sym in fetched_drivers.keys():
            ll = engine.detect_lead_lag_advanced(driver_sym)
            if 'error' not in ll:
                lead_lag_results[driver_sym] = ll

        return AnalysisResult(
            success=True,
            data={
                'attribution': daily_attr,
                'lead_lag': lead_lag_results,
                'drivers_fetched': list(fetched_drivers.keys())
            }
        )

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.error(f"Analysis failed: {result.error}")
            return
            
        data = result.data
        attr = data.get('attribution', {})
        
        if 'error' in attr:
            st.warning(f"Attribution calculation error: {attr['error']}")
            return

        # 1. Daily Attribution Display
        date_str = attr['date'].strftime('%Y-%m-%d')
        target_ret = attr['target_return']
        
        color = "green" if target_ret > 0 else "red"
        st.markdown(f"### What drove the move on {date_str}?")
        st.markdown(f"Target Move: **:{color}[{target_ret:.2f}%]**")
        
        # Waterfall chart data preparation
        contributions = attr['contributions']
        
        waterfall_x = []
        waterfall_y = []
        waterfall_text = []
        
        # Add drivers
        for sym, details in contributions.items():
            waterfall_x.append(details['description'])
            waterfall_y.append(details['contribution'])
            waterfall_text.append(f"{details['contribution']:.2f}%")
            
        # Add unexplained
        waterfall_x.append("Unexplained/Alpha")
        waterfall_y.append(attr['unexplained'])
        waterfall_text.append(f"{attr['unexplained']:.2f}%")
        
        fig = go.Figure(go.Waterfall(
            name = "Attribution",
            orientation = "v",
            measure = ["relative"] * len(waterfall_y),
            x = waterfall_x,
            textposition = "outside",
            text = waterfall_text,
            y = waterfall_y,
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        
        fig.update_layout(
            title = "Return Attribution Breakdown",
            showlegend = False,
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 2. Lead-Lag Analysis
        st.subheader("⏱️ Lead-Lag Relationships")
        st.caption("Granger Causality Test (Does the driver predict the asset?)")
        
        lead_lag = data.get('lead_lag', {})
        if lead_lag:
            ll_data = []
            for sym, res in lead_lag.items():
                if res.get('is_significant'):
                    ll_data.append({
                        "Driver": contributions.get(sym, {}).get('description', sym),
                        "Lag (Days)": res['optimal_lag'],
                        "Strength": res['significance'],
                        "Confidence": f"{(1 - res['p_value'])*100:.1f}%"
                    })
            
            if ll_data:
                render_aggrid(pd.DataFrame(ll_data), height=200)
            else:
                st.info("No significant lead-lag relationships detected with current drivers.")
        else:
            st.info("Insufficient data for lead-lag analysis.")
