"""
Correlation Analysis Plugin
Integrates correlation analysis from bbt2
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from typing import Dict, Any, List, Tuple
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from data_fetcher import MultiAssetDataFetcher # Corrected import

logger = logging.getLogger(__name__)

@register_plugin
class CorrelationAnalysisPlugin(AnalysisPlugin):
    """
    Analyzes correlations between multiple selected symbols.
    Ported from bbt2/correlation_analyzer.py and bbt2/app_professional.py
    """

    @property
    def name(self) -> str:
        return "Correlation Analysis"

    @property
    def icon(self) -> str:
        return "🔗"

    @property
    def description(self) -> str:
        return "Analyzes price correlation between multiple assets."

    @property
    def category(self) -> str:
        return "asset" # This seems like an asset-specific analysis

    @property
    def enabled_by_default(self) -> bool:
        return False # This is a more advanced feature, not enabled by default

    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        symbols_to_compare: List[str] = context.get('symbols_to_compare', [])
        # Ensure the primary symbol is also in the list if not already there
        primary_symbol = context.get('symbol')
        if primary_symbol and primary_symbol not in symbols_to_compare:
            symbols_to_compare.insert(0, primary_symbol)
        
        if not symbols_to_compare or len(symbols_to_compare) < 2:
            return AnalysisResult(
                success=False,
                data={},
                error="Please select at least two symbols for correlation analysis."
            )
        
        start_date = context.get('date_range', {}).get('start')
        end_date = context.get('date_range', {}).get('end')

        if not start_date or not end_date:
            return AnalysisResult(
                success=False,
                data={},
                error="Date range is required for correlation analysis."
            )
        
        data_fetcher = MultiAssetDataFetcher() 
        all_data: Dict[str, pd.DataFrame] = {}
        
        for symbol in symbols_to_compare:
            try:
                # fetch_asset returns a DataFrame or None
                data = data_fetcher.fetch_asset(symbol, start_date, end_date)
                
                if data is not None and not data.empty:
                    # MultiAssetDataFetcher returns Close, High, Low, Open, Volume
                    # We need 'Close' for correlation
                    # Handle if columns are MultiIndex or Title Case
                    if 'Close' in data.columns:
                        all_data[symbol] = data['Close']
                    elif 'close' in data.columns:
                        all_data[symbol] = data['close']
                    else:
                        # Fallback for MultiIndex
                        all_data[symbol] = data.iloc[:, 0] # Assume first col is close-like if ambiguous
                else:
                    logger.warning(f"Could not fetch data for {symbol}")
            except Exception as e:
                logger.warning(f"Error fetching {symbol}: {e}")

        if len(all_data) < 2:
            return AnalysisResult(
                success=False,
                data={},
                error="Insufficient data to perform correlation (need at least 2 symbols with data)."
            )

        combined_df = pd.DataFrame(all_data).dropna()

        if combined_df.empty:
            return AnalysisResult(
                success=False,
                data={},
                error="No common data points for selected symbols in the given date range after dropping NaNs."
            )

        returns_df = combined_df.pct_change().dropna()

        if returns_df.empty:
            return AnalysisResult(
                success=False,
                data={},
                error="Not enough data to calculate returns after dropping NaNs."
            )

        correlation_matrix = returns_df.corr()

        return AnalysisResult(
            success=True,
            data={
                "correlation_matrix": correlation_matrix,
                "symbols": symbols_to_compare,
                "combined_price_data": combined_df
            }
        )

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")

        if not result.success:
            st.error(f"Correlation Analysis Error: {result.error}")
            return
        
        correlation_matrix = result.data["correlation_matrix"]
        symbols = result.data["symbols"]
        combined_price_data = result.data["combined_price_data"]

        st.markdown("### Correlation Matrix")
        # Display the correlation matrix as a heatmap
        fig = px.imshow(correlation_matrix,
                        text_auto=True,
                        aspect="auto",
                        color_continuous_scale='RdBu_r', # Red-Blue diverging scale
                        range_color=[-1, 1], # Ensure color scale is -1 to 1
                        title="Asset Correlation Heatmap")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            """
            <small>
            **Interpretation:**
            - **Positive correlation (closer to +1):** Assets tend to move in the same direction.
            - **Negative correlation (closer to -1):** Assets tend to move in opposite directions.
            - **Zero correlation (closer to 0):** Assets move independently.
            </small>
            """,
            unsafe_allow_html=True
        )

        st.markdown("### Price Performance Comparison")
        # Plot price performance for visual comparison
        # Normalize prices to start at 100 for better comparison
        normalized_df = combined_price_data.copy()
        for col in normalized_df.columns:
            normalized_df[col] = normalized_df[col] / normalized_df[col].iloc[0] * 100
            
        fig_price = px.line(normalized_df,
                            x=normalized_df.index,
                            y=normalized_df.columns,
                            title="Normalized Price Performance (Base 100)")
        
        fig_price.update_layout(yaxis_title="Normalized Price (Base 100)", xaxis_title="Date")
        st.plotly_chart(fig_price, use_container_width=True)
