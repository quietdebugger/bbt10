"""
Forensic Analysis Plugin
Integrates Forensic Lab from bbt3 for deep fundamental analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin

logger = logging.getLogger(__name__)

# --- Ported ForensicLab from bbt3/forensic_lab.py ---

class ForensicLab:
    """
    Forensic accounting analysis
    Detect bankruptcy risk 2 years in advance and spot fraud
    """
    
    def __init__(self, symbol: str):
        """
        Initialize forensic lab
        
        Args:
            symbol: Stock symbol
        """
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        self.info = self._safe_get_info()
        self.financials = self._get_financials()
        
        logger.info(f"ForensicLab initialized for {symbol}")
    
    def _safe_get_info(self) -> Dict:
        """Safely get ticker info"""
        try:
            return self.ticker.info
        except:
            return {}
    
    def _get_financials(self) -> Dict:
        """Get financial statements"""
        try:
            return {
                'balance_sheet': self.ticker.balance_sheet,
                'income_stmt': self.ticker.income_stmt,
                'cash_flow': self.ticker.cash_flow
            }
        except:
            return {}
    
    def calculate_altman_z_score(self) -> Dict:
        """
        Calculate Altman Z-Score for bankruptcy prediction
        """
        try:
            bs = self.financials.get('balance_sheet')
            income = self.financials.get('income_stmt')
            
            if bs is None or bs.empty or income is None or income.empty:
                return {'error': 'Financial data not available'}
            
            # Get most recent values (first column)
            latest_bs = bs.iloc[:, 0]
            latest_income = income.iloc[:, 0]
            
            # Extract required values with safe fallbacks
            total_assets = latest_bs.get('Total Assets', 0)
            current_assets = latest_bs.get('Current Assets', 0)
            current_liabilities = latest_bs.get('Current Liabilities', 0)
            total_liabilities = latest_bs.get('Total Liabilities Net Minority Interest', 0)
            retained_earnings = latest_bs.get('Retained Earnings', 0)
            ebit = latest_income.get('EBIT', latest_income.get('Operating Income', 0))
            revenue = latest_income.get('Total Revenue', 0)
            
            # Market value of equity
            market_cap = self.info.get('marketCap', 0)
            
            # Working capital
            working_capital = current_assets - current_liabilities
            
            if total_assets == 0:
                return {'error': 'Invalid financial data (Total Assets = 0)'}
            
            # Z-Score components
            X1 = working_capital / total_assets
            X2 = retained_earnings / total_assets
            X3 = ebit / total_assets
            X4 = market_cap / total_liabilities if total_liabilities != 0 else 0
            X5 = revenue / total_assets
            
            # Z-Score Formula (Original for Public Manufacturing)
            # Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5
            z_score = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
            
            # Interpretation
            if z_score > 2.99:
                zone = "SAFE ZONE"
                risk_level = "LOW"
                interpretation = "Strong financial health, low bankruptcy risk"
            elif z_score > 1.81:
                zone = "GREY ZONE"
                risk_level = "MODERATE"
                interpretation = "Moderate risk, monitor carefully"
            else:
                zone = "DISTRESS ZONE"
                risk_level = "HIGH"
                interpretation = "⚠️ HIGH BANKRUPTCY RISK - Avoid or exit position"
            
            return {
                'z_score': z_score,
                'zone': zone,
                'risk_level': risk_level,
                'interpretation': interpretation,
                'components': {
                    'Working Capital/Assets': X1,
                    'Retained Earnings/Assets': X2,
                    'EBIT/Assets': X3,
                    'Market Cap/Liabilities': X4,
                    'Sales/Assets': X5
                }
            }
            
        except Exception as e:
            logger.error(f"Z-Score calculation failed: {e}")
            return {'error': str(e)}
    
    def calculate_beneish_m_score(self) -> Dict:
        """
        Calculate Beneish M-Score for earnings manipulation detection
        """
        try:
            bs = self.financials.get('balance_sheet')
            income = self.financials.get('income_stmt')
            
            if bs is None or bs.empty or income is None or income.empty:
                return {'error': 'Financial data not available'}
            
            # Need 2 years of data
            if len(bs.columns) < 2 or len(income.columns) < 2:
                return {'error': 'Insufficient historical data (need 2 years)'}
            
            # Year 1 (most recent) and Year 0 (previous)
            bs_y1 = bs.iloc[:, 0]
            bs_y0 = bs.iloc[:, 1]
            income_y1 = income.iloc[:, 0]
            income_y0 = income.iloc[:, 1]
            
            # Extract values
            revenue_y1 = income_y1.get('Total Revenue', 0)
            revenue_y0 = income_y0.get('Total Revenue', 0)
            
            receivables_y1 = bs_y1.get('Receivables', 0)
            receivables_y0 = bs_y0.get('Receivables', 0)
            
            cogs_y1 = income_y1.get('Cost Of Revenue', 0)
            cogs_y0 = income_y0.get('Cost Of Revenue', 0)
            
            current_assets_y1 = bs_y1.get('Current Assets', 0)
            current_assets_y0 = bs_y0.get('Current Assets', 0)
            
            ppe_y1 = bs_y1.get('Net PPE', 0)
            ppe_y0 = bs_y0.get('Net PPE', 0)
            
            total_assets_y1 = bs_y1.get('Total Assets', 0)
            total_assets_y0 = bs_y0.get('Total Assets', 0)
            
            # Calculate ratios
            # DSRI (Days Sales in Receivables Index)
            dsr_y1 = receivables_y1 / revenue_y1 if revenue_y1 != 0 else 0
            dsr_y0 = receivables_y0 / revenue_y0 if revenue_y0 != 0 else 0
            DSRI = dsr_y1 / dsr_y0 if dsr_y0 != 0 else 1
            
            # GMI (Gross Margin Index)
            gm_y0 = (revenue_y0 - cogs_y0) / revenue_y0 if revenue_y0 != 0 else 0
            gm_y1 = (revenue_y1 - cogs_y1) / revenue_y1 if revenue_y1 != 0 else 0
            GMI = gm_y0 / gm_y1 if gm_y1 != 0 else 1
            
            # AQI (Asset Quality Index)
            nca_y1 = (total_assets_y1 - current_assets_y1 - ppe_y1) / total_assets_y1 if total_assets_y1 != 0 else 0
            nca_y0 = (total_assets_y0 - current_assets_y0 - ppe_y0) / total_assets_y0 if total_assets_y0 != 0 else 0
            AQI = nca_y1 / nca_y0 if nca_y0 != 0 else 1
            
            # SGI (Sales Growth Index)
            SGI = revenue_y1 / revenue_y0 if revenue_y0 != 0 else 1
            
            # Simplified M-Score (using 5 variables)
            m_score = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
            
            # Interpretation
            if m_score > -1.78:
                status = "⚠️ LIKELY MANIPULATOR"
                risk = "HIGH"
                interpretation = "Red flag: Possible earnings manipulation detected"
            else:
                status = "UNLIKELY MANIPULATOR"
                risk = "LOW"
                interpretation = "No significant signs of earnings manipulation"
            
            return {
                'm_score': m_score,
                'status': status,
                'fraud_risk': risk,
                'interpretation': interpretation,
                'threshold': -1.78,
                'components': {
                    'DSRI (Receivables)': DSRI,
                    'GMI (Gross Margin)': GMI,
                    'AQI (Asset Quality)': AQI,
                    'SGI (Sales Growth)': SGI
                }
            }
            
        except Exception as e:
            logger.error(f"M-Score calculation failed: {e}")
            return {'error': str(e)}
    
    def dupont_analysis(self) -> Dict:
        """
        DuPont Analysis - Decompose ROE
        """
        try:
            # Get metrics
            roe = self.info.get('returnOnEquity', 0)
            profit_margin = self.info.get('profitMargins', 0)
            
            bs = self.financials.get('balance_sheet')
            income = self.financials.get('income_stmt')
            
            if bs is None or income is None:
                return {'error': 'Financial data not available'}
            
            latest_bs = bs.iloc[:, 0]
            latest_income = income.iloc[:, 0]
            
            total_assets = latest_bs.get('Total Assets', 0)
            total_equity = latest_bs.get('Total Equity Gross Minority Interest', 0)
            revenue = latest_income.get('Total Revenue', 0)
            net_income = latest_income.get('Net Income', 0)
            
            if total_assets == 0 or total_equity == 0 or revenue == 0:
                return {'error': 'Invalid financial data'}
            
            # DuPont components
            net_margin = (net_income / revenue) * 100
            asset_turnover = revenue / total_assets
            equity_multiplier = total_assets / total_equity
            
            # Calculated ROE
            roe_calculated = (net_margin / 100) * asset_turnover * equity_multiplier * 100
            
            # Interpretation
            quality_score = 0
            factors = []
            
            if net_margin > 15:
                quality_score += 40
                factors.append("Strong profitability")
            elif net_margin > 5:
                quality_score += 20
            else:
                factors.append("Weak profitability")
            
            if asset_turnover > 1.0:
                quality_score += 30
                factors.append("Efficient asset usage")
            elif asset_turnover > 0.5:
                quality_score += 15
            
            if equity_multiplier < 2.0:
                quality_score += 30
                factors.append("Conservative leverage")
            elif equity_multiplier < 3.0:
                quality_score += 15
            else:
                factors.append("⚠️ High leverage (risky)")
            
            if quality_score >= 70:
                quality = "EXCELLENT"
                interpretation = "High-quality ROE from profitability and efficiency"
            elif quality_score >= 50:
                quality = "GOOD"
                interpretation = "Decent ROE, monitor leverage"
            else:
                quality = "CONCERNING"
                interpretation = "ROE may be driven by excessive leverage"
            
            return {
                'roe': roe * 100 if roe else roe_calculated,
                'net_margin': net_margin,
                'asset_turnover': asset_turnover,
                'equity_multiplier': equity_multiplier,
                'quality': quality,
                'quality_score': quality_score,
                'interpretation': interpretation,
                'key_factors': factors
            }
            
        except Exception as e:
            logger.error(f"DuPont analysis failed: {e}")
            return {'error': str(e)}
    
    def generate_forensic_report(self) -> Dict:
        """Generate comprehensive forensic analysis"""
        report = {
            'symbol': self.symbol,
            'analysis_date': datetime.now()
        }
        
        # Altman Z-Score
        z_score = self.calculate_altman_z_score()
        report['altman_z_score'] = z_score
        
        # Beneish M-Score
        m_score = self.calculate_beneish_m_score()
        report['beneish_m_score'] = m_score
        
        # DuPont Analysis
        dupont = self.dupont_analysis()
        report['dupont_analysis'] = dupont
        
        # Overall assessment
        red_flags = []
        
        if not z_score.get('error') and z_score.get('risk_level') == 'HIGH':
            red_flags.append("High bankruptcy risk (Z-Score)")
        
        if not m_score.get('error') and m_score.get('fraud_risk') == 'HIGH':
            red_flags.append("Possible earnings manipulation (M-Score)")
        
        if not dupont.get('error') and dupont.get('quality') == 'CONCERNING':
            red_flags.append("Poor quality ROE (excessive leverage)")
        
        report['red_flags'] = red_flags
        report['overall_risk'] = 'HIGH' if len(red_flags) >= 2 else 'MODERATE' if len(red_flags) == 1 else 'LOW'
        
        return report


# --- Forensic Analysis Plugin ---

@register_plugin
class ForensicAnalysisPlugin(AnalysisPlugin):
    """
    Deep fundamental analysis for bankruptcy and fraud risk
    """
    
    @property
    def name(self) -> str:
        return "Forensic Lab"
    
    @property
    def icon(self) -> str:
        return "🕵️‍♂️"
    
    @property
    def description(self) -> str:
        return "Altman Z-Score (Bankruptcy), Beneish M-Score (Fraud), DuPont Analysis"
    
    @property
    def category(self) -> str:
        return "asset"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        symbol = context.get('symbol')
        if not symbol:
            return AnalysisResult(success=False, data={}, error="No symbol provided for forensic analysis.")
        
        if '^' in symbol: # Skip for indices
             return AnalysisResult(success=False, data={}, error="Forensic analysis is for companies, not indices.")

        try:
            lab = ForensicLab(symbol)
            report = lab.generate_forensic_report()
            
            return AnalysisResult(
                success=True,
                data={'report': report}
            )
        except Exception as e:
            logger.error(f"Error during forensic analysis for {symbol}: {e}")
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.warning(f"Forensic analysis skipped: {result.error}")
            return
            
        report = result.data.get('report', {})
        
        # 1. Altman Z-Score
        z_score = report.get('altman_z_score', {})
        st.markdown("#### 📉 Altman Z-Score (Bankruptcy Risk)")
        
        if 'error' in z_score:
            st.warning(f"Z-Score unavailable: {z_score['error']}")
        else:
            val = z_score['z_score']
            zone = z_score['zone']
            color = "green" if zone == "SAFE ZONE" else "red" if zone == "DISTRESS ZONE" else "orange"
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Z-Score", f"{val:.2f}", delta=zone, delta_color="normal" if color=="green" else "inverse")
            with col2:
                st.info(f"**Interpretation**: {z_score['interpretation']}")
            
            # Gauge chart
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = val,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Bankruptcy Risk"},
                gauge = {
                    'axis': {'range': [0, 5], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': "darkblue"},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 1.81], 'color': 'red'},
                        {'range': [1.81, 2.99], 'color': 'orange'},
                        {'range': [2.99, 5], 'color': 'green'}],
                }
            ))
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # 2. Beneish M-Score
        m_score = report.get('beneish_m_score', {})
        st.markdown("#### 🤥 Beneish M-Score (Fraud Detection)")
        
        if 'error' in m_score:
            st.warning(f"M-Score unavailable: {m_score['error']}")
        else:
            val = m_score['m_score']
            status = m_score['status']
            color = "green" if status == "UNLIKELY MANIPULATOR" else "red"
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("M-Score", f"{val:.2f}", delta=status, delta_color="normal" if color=="green" else "inverse")
            with col2:
                st.info(f"**Interpretation**: {m_score['interpretation']}")
                if m_score.get('components'):
                    st.json(m_score['components']) # Show components for details

        st.markdown("---")

        # 3. DuPont Analysis
        dupont = report.get('dupont_analysis', {})
        st.markdown("#### 🏗️ DuPont Analysis (ROE Decomposition)")
        
        if 'error' in dupont:
            st.warning(f"DuPont analysis unavailable: {dupont['error']}")
        else:
            roe = dupont['roe']
            st.metric("ROE", f"{roe:.2f}%")
            
            # 3-way breakdown visualization
            col1, col2, col3 = st.columns(3)
            col1.metric("Net Margin", f"{dupont['net_margin']:.2f}%", "Profitability")
            col2.metric("Asset Turnover", f"{dupont['asset_turnover']:.2f}", "Efficiency")
            col3.metric("Equity Multiplier", f"{dupont['equity_multiplier']:.2f}", "Leverage")
            
            st.success(f"**Quality**: {dupont['quality']} - {dupont['interpretation']}")
