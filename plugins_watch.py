"""
Watch List Plugin
Monitors critical macro levels (US 10Y, DXY, VIX, Oil) for alerts
Borrowed from bbt5
"""

import streamlit as st
import pandas as pd
import yfinance as yf
from typing import Dict, Any, List, Optional
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from ui_components import render_aggrid

logger = logging.getLogger(__name__)

# --- Ported Logic from bbt5/ticker_names.py ---

WATCH_RELATIONSHIPS = {
    'us_10y': {
        'symbol': '^TNX',
        'name': 'US 10Y Yield',
        'threshold': 4.5,
        'direction': 'above',
        'impact': 'Risk-off: High yields hurt equities, especially Tech & EM',
        'alert': '⚠️ ALERT: US 10Y Yield > 4.5% (High Pressure)'
    },
    'dxy': {
        'symbol': 'DX-Y.NYB',
        'name': 'US Dollar Index',
        'threshold': 105.0,
        'direction': 'above',
        'impact': 'Currency Risk: Strong Dollar hurts Rupee & FII flows',
        'alert': '⚠️ ALERT: DXY > 105 (Capital Outflow Risk)'
    },
    'vix': {
        'symbol': '^VIX',
        'name': 'CBOE VIX',
        'threshold': 20.0,
        'direction': 'above',
        'impact': 'Fear: High volatility implies market stress',
        'alert': '⚠️ ALERT: VIX > 20 (High Fear)'
    },
    'oil': {
        'symbol': 'CL=F',
        'name': 'Crude Oil',
        'threshold': 90.0,
        'direction': 'above',
        'impact': 'Inflation: High oil prices hurt India (importer)',
        'alert': '⚠️ ALERT: Crude Oil > $90 (Inflation Risk)'
    },
    'india_vix': {
        'symbol': '^INDIAVIX',
        'name': 'India VIX',
        'threshold': 18.0,
        'direction': 'above',
        'impact': 'Domestic Fear: Expect sharp swings',
        'alert': '⚠️ ALERT: India VIX > 18'
    }
}

def check_watch_alerts(symbol: str, current_price: float) -> Optional[Dict]:
    """Check if a symbol triggers a watch alert"""
    for key, data in WATCH_RELATIONSHIPS.items():
        if data['symbol'] == symbol:
            threshold = data['threshold']
            direction = data['direction']
            
            triggered = False
            if direction == 'above' and current_price > threshold:
                triggered = True
            elif direction == 'below' and current_price < threshold:
                triggered = True
                
            if triggered:
                return {
                    'alert': data['alert'],
                    'impact': data['impact'],
                    'threshold': threshold
                }
    return None


@register_plugin
class WatchListPlugin(AnalysisPlugin):
    """
    Monitors critical macro levels (US 10Y, DXY, VIX, Oil)
    """
    
    @property
    def name(self) -> str:
        return "Important Watch List"
    
    @property
    def icon(self) -> str:
        return "🚨"
    
    @property
    def description(self) -> str:
        return "Alerts for US 10Y > 4.5%, DXY > 105, Oil > $90"
    
    @property
    def category(self) -> str:
        return "macro"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        results = {}
        
        # We need to fetch these specific symbols
        symbols_to_check = [d['symbol'] for d in WATCH_RELATIONSHIPS.values()]
        
        # Use existing context data if available, or fetch
        # For macro watch list, we need the LATEST price
        
        try:
            # Quick fetch for latest values
            data = yf.download(
                symbols_to_check, 
                period="5d", 
                progress=False
            )['Close']
            
            # Handle single vs multi-index columns
            if isinstance(data, pd.Series):
                # Single symbol returned? Rare if we asked for list
                # Reformat to match expected structure if needed
                pass 
            
            alerts = []
            status_table = []
            
            for key, info in WATCH_RELATIONSHIPS.items():
                sym = info['symbol']
                if sym in data.columns:
                    # Get latest non-NaN value
                    series = data[sym].dropna()
                    if not series.empty:
                        curr_val = series.iloc[-1]
                        
                        # Check alert
                        alert_data = check_watch_alerts(sym, curr_val)
                        
                        status_item = {
                            'Indicator': info['name'],
                            'Current': curr_val,
                            'Threshold': f"{info['direction'].upper()} {info['threshold']}",
                            'Status': 'OK'
                        }
                        
                        if alert_data:
                            status_item['Status'] = '⚠️ ALERT'
                            status_item['Impact'] = alert_data['impact']
                            alerts.append(alert_data)
                        
                        status_table.append(status_item)
            
            return AnalysisResult(
                success=True,
                data={
                    'alerts': alerts,
                    'table': status_table
                }
            )
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.warning(f"Watch list unavailable: {result.error}")
            return
            
        data = result.data
        alerts = data.get('alerts', [])
        table = data.get('table', [])
        
        # 1. Show Active Alerts
        if alerts:
            st.error(f"🚨 {len(alerts)} CRITICAL ALERTS TRIGGERED")
            for alert in alerts:
                st.markdown(f"**{alert['alert']}**")
                st.caption(f"Impact: {alert['impact']}")
        else:
            st.success("✅ No critical macro alerts. Market conditions stable.")
            
        st.markdown("---")
        
        # 2. Status Table
        if table:
            df = pd.DataFrame(table)
            # Formatting
            render_aggrid(df, height=200)
        
        # 3. Legend
        with st.expander("ℹ️ Why watch these levels?"):
            st.markdown("""
            - **US 10Y Yield (>4.5%)**: High yields make bonds attractive vs stocks; hurts Tech/EM valuations.
            - **Dollar Index (>105)**: Strong DXY causes capital outflow from Emerging Markets (India).
            - **VIX (>20)**: High fear index indicates stress and potential capitulation.
            - **Crude Oil (>$90)**: Import inflation for India; hurts margins of paints, tires, FMCG.
            """)
