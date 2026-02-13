"""
Dashboard Plugins
High-level executive summaries and decision support tools
(Risk Radar, Action Items, Macro Heatmap)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, List
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from plugins_forensic import ForensicLab
from plugins_attribution import AttributionEngine
from upstox_fo_complete import UpstoxAuth, UpstoxFOData
import yfinance as yf

logger = logging.getLogger(__name__)

@register_plugin
class RiskRadarPlugin(AnalysisPlugin):
    """
    Multi-dimensional risk visualization (Spider Chart)
    Combines Forensics, Options Sentiment, and Volatility
    """
    
    @property
    def name(self) -> str:
        return "Risk Radar"
    
    @property
    def icon(self) -> str:
        return "🕸️"
    
    @property
    def description(self) -> str:
        return "Multi-dimensional risk view (Bankruptcy, Fraud, Sentiment, Volatility)"
    
    @property
    def category(self) -> str:
        return "market"  # High-level market view
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        symbol = context.get('symbol')
        if not symbol or '^' in symbol:
            return AnalysisResult(success=False, data={}, error="Risk Radar requires a stock symbol (not index)")
            
        try:
            # 1. Forensic Risk (Bankruptcy & Fraud)
            lab = ForensicLab(symbol)
            z_score_data = lab.calculate_altman_z_score()
            m_score_data = lab.calculate_beneish_m_score()
            dupont_data = lab.dupont_analysis()
            
            # Normalize scores to 0-100 (Higher = Higher Risk)
            
            # Bankruptcy Risk: Z-Score < 1.8 is high risk
            z = z_score_data.get('z_score', 3.0)
            if z > 2.99: bank_risk = 20
            elif z > 1.81: bank_risk = 50
            else: bank_risk = 90
            
            # Fraud Risk: M-Score > -1.78 is high risk
            m = m_score_data.get('m_score', -3.0)
            fraud_risk = 80 if m > -1.78 else 20
            
            # Quality Risk: Low quality score = high risk
            q = dupont_data.get('quality_score', 50)
            quality_risk = 100 - q
            
            # 2. Options Sentiment Risk (PCR)
            # If Upstox keys available, use them. Else skip or use fallback?
            # We'll skip if no keys, or return partial
            opt_risk = 50
            upstox_symbol = context.get('upstox_symbol')
            api_key = context.get('config', {}).get('UPSTOX_API_KEY')
            api_secret = context.get('config', {}).get('UPSTOX_API_SECRET')
            
            if api_key and api_secret and upstox_symbol:
                try:
                    auth = UpstoxAuth(api_key, api_secret)
                    fo = UpstoxFOData(auth)
                    chain, _ = fo.get_option_chain(upstox_symbol)
                    if not chain.empty:
                        pcr = fo.calculate_pcr(chain)
                        pcr_val = pcr['pcr_oi']
                        # Extremes are risky? Or creates opportunity?
                        # Let's define "Risk" as "Probability of Reversal/Crash"
                        # High PCR (>1.4) = Oversold (Bullish?) -> Low Downside Risk?
                        # Low PCR (<0.6) = Overbought (Bearish?) -> High Downside Risk
                        if pcr_val < 0.6: opt_risk = 80 # Overbought, risk of drop
                        elif pcr_val > 1.4: opt_risk = 30 # Oversold, likely bounce
                        else: opt_risk = 50
                except Exception as e:
                    logger.warning(f"Risk Radar F&O fetch failed: {e}")
            
            # 3. Volatility Risk
            # Use beta if available, or calc from price data
            price_data = context.get('price_data')
            beta_risk = 50
            if price_data is not None:
                # Simple annualized vol
                returns = price_data['close'].pct_change().dropna()
                vol = returns.std() * np.sqrt(252)
                # Normalize: 20% vol = 20 risk, 50% vol = 80 risk
                beta_risk = min(100, max(0, vol * 200)) # Approx scaling
                
            return AnalysisResult(
                success=True,
                data={
                    'scores': {
                        'Bankruptcy Risk': bank_risk,
                        'Fraud Risk': fraud_risk,
                        'Quality Risk': quality_risk,
                        'Sentiment Risk': opt_risk,
                        'Volatility Risk': beta_risk
                    },
                    'details': {
                        'z_score': z,
                        'm_score': m,
                        'quality_score': q
                    }
                }
            )
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        if not result.success:
            st.info(f"Risk Radar skipped: {result.error}")
            return
            
        scores = result.data['scores']
        categories = list(scores.keys())
        values = list(scores.values())
        
        # Close the polygon
        categories += [categories[0]]
        values += [values[0]]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Risk Profile',
            line_color='red'
        ))
        
        # Safe benchmark
        fig.add_trace(go.Scatterpolar(
            r=[30]*len(categories),
            theta=categories,
            name='Safe Zone',
            line_color='green',
            line_dash='dash'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=True,
            height=400,
            title="Risk Profile (Outer Edge = High Risk)"
        )
        
        st.plotly_chart(fig, use_container_width=True)


@register_plugin
class MacroHeatmapPlugin(AnalysisPlugin):
    """
    Global Macro Heatmap
    Visualizes what's driving the market (Attribution)
    """
    
    @property
    def name(self) -> str:
        return "Macro Heatmap"
    
    @property
    def icon(self) -> str:
        return "🌍"
    
    @property
    def description(self) -> str:
        return "Heatmap of global market drivers"
    
    @property
    def category(self) -> str:
        return "macro"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        # Reuse AttributionEngine logic
        # We need to fetch drivers if not present
        symbol = context.get('symbol')
        price_data = context.get('price_data')
        
        if not symbol or price_data is None:
            return AnalysisResult(success=False, data={}, error="Missing data")
            
        engine = AttributionEngine(price_data, symbol)
        
        # Standard macro drivers
        drivers_map = {
            '^GSPC': 'S&P 500',
            '^IXIC': 'Nasdaq',
            'DX-Y.NYB': 'DXY',
            'CL=F': 'Crude Oil',
            '^TNX': 'US 10Y',
            '^VIX': 'VIX'
        }
        
        fetched_data = {}
        for driver_sym, desc in drivers_map.items():
            try:
                # Fast download, 1y history
                data = yf.download(driver_sym, period="1y", progress=False)
                if not data.empty:
                    engine.add_driver(driver_sym, data, desc)
            except:
                pass
        
        if not engine.drivers:
            return AnalysisResult(success=False, data={}, error="Could not fetch macro data")
            
        attr = engine.attribute_daily_move()
        return AnalysisResult(success=True, data={'attribution': attr})

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        if not result.success:
            st.warning("Heatmap unavailable")
            return
            
        contributions = result.data['attribution'].get('contributions', {})
        if not contributions:
            st.info("No attribution data")
            return
            
        # Prepare heatmap data
        labels = []
        values = []
        hover_text = []
        
        for sym, data in contributions.items():
            labels.append(data['description'])
            val = data['contribution_pct']
            values.append(val)
            hover_text.append(f"{val:+.1f}% Contribution")
            
        # Reshape for heatmap (1 row)
        z = [values]
        x = labels
        y = ['Impact']
        
        fig = go.Figure(data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            text=[[f"{v:+.0f}%" for v in values]],
            texttemplate="%{text}",
            colorscale='RdYlGn',
            zmid=0,
            showscale=True
        ))
        
        fig.update_layout(
            title="Global Drivers Impact (%)",
            height=200,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)


@register_plugin
class ActionItemsPlugin(AnalysisPlugin):
    """
    Executive Summary & Action Items
    Aggregates signals into clear decisions
    """
    
    @property
    def name(self) -> str:
        return "Action Items"
    
    @property
    def icon(self) -> str:
        return "💡"
    
    @property
    def description(self) -> str:
        return "Consolidated signals and trade recommendations"
    
    @property
    def category(self) -> str:
        return "market"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        symbol = context.get('symbol')
        signals = []
        
        # 1. Forensic Signal
        if symbol and '^' not in symbol:
            try:
                lab = ForensicLab(symbol)
                z = lab.calculate_altman_z_score().get('z_score', 0)
                if z < 1.81:
                    signals.append({'source': 'Forensics', 'type': 'Bearish', 'msg': 'High Bankruptcy Risk (Z-Score)'})
                elif z > 2.99:
                    signals.append({'source': 'Forensics', 'type': 'Bullish', 'msg': 'Strong Balance Sheet'})
            except: pass
            
        # 2. Options Signal
        api_key = context.get('config', {}).get('UPSTOX_API_KEY')
        upstox_symbol = context.get('upstox_symbol')
        if api_key and upstox_symbol:
            try:
                auth = UpstoxAuth(api_key, context.get('config', {}).get('UPSTOX_API_SECRET'))
                fo = UpstoxFOData(auth)
                chain, _ = fo.get_option_chain(upstox_symbol)
                if not chain.empty:
                    pcr = fo.calculate_pcr(chain).get('pcr_oi', 1.0)
                    if pcr > 1.4:
                        signals.append({'source': 'Options', 'type': 'Bullish', 'msg': 'Oversold (PCR > 1.4) - Potential Bounce'})
                    elif pcr < 0.6:
                        signals.append({'source': 'Options', 'type': 'Bearish', 'msg': 'Overbought (PCR < 0.6) - Caution'})
            except: pass
            
        # 3. Trend Signal (Simple SMA)
        price_data = context.get('price_data')
        if price_data is not None:
            close = price_data['close']
            if len(close) > 200:
                sma200 = close.rolling(200).mean().iloc[-1]
                current = close.iloc[-1]
                if current > sma200:
                    signals.append({'source': 'Trend', 'type': 'Bullish', 'msg': 'Price above 200 DMA'})
                else:
                    signals.append({'source': 'Trend', 'type': 'Bearish', 'msg': 'Price below 200 DMA'})

        return AnalysisResult(success=True, data={'signals': signals})

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        signals = result.data.get('signals', [])
        if not signals:
            st.info("No clear signals detected.")
            return
            
        bullish = [s for s in signals if s['type'] == 'Bullish']
        bearish = [s for s in signals if s['type'] == 'Bearish']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.success(f"✅ Bullish Signals ({len(bullish)})")
            for s in bullish:
                st.write(f"• **{s['source']}**: {s['msg']}")
                
        with col2:
            st.error(f"⚠️ Bearish Signals ({len(bearish)})")
            for s in bearish:
                st.write(f"• **{s['source']}**: {s['msg']}")
        
        # Final Verdict
        score = len(bullish) - len(bearish)
        st.markdown("---")
        if score > 0:
            st.markdown("### 🟢 Verdict: BULLISH BIAS")
        elif score < 0:
            st.markdown("### 🔴 Verdict: BEARISH BIAS")
        else:
            st.markdown("### 🟡 Verdict: NEUTRAL")
