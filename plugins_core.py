"""
Core Analysis Plugins
Each plugin is independent and can be enabled/disabled
"""

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Any
import logging
import plotly.graph_objects as go

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from upstox_fo_complete import UpstoxAuth, UpstoxFOData
from ui_components import render_metric_card, render_ticker_tape

logger = logging.getLogger(__name__)


# ==========================================
# MARKET OVERVIEW PLUGINS
# ==========================================

@register_plugin
class VixAnalysisPlugin(AnalysisPlugin):
    """VIX (Fear Index) Analysis"""
    
    @property
    def name(self) -> str:
        return "VIX Analysis"
    
    @property
    def icon(self) -> str:
        return "😱"
    
    @property
    def description(self) -> str:
        return "India VIX - Market fear gauge"
    
    @property
    def category(self) -> str:
        return "market"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            # Fetch India VIX
            vix = yf.Ticker("^INDIAVIX")
            vix_data = vix.history(period="1mo")
            
            if vix_data.empty:
                return AnalysisResult(
                    success=False,
                    data={},
                    error="VIX data unavailable"
                )
            
            current_vix = vix_data['Close'].iloc[-1]
            vix_change = ((current_vix / vix_data['Close'].iloc[0]) - 1) * 100
            vix_52w_high = vix_data['Close'].max()
            vix_52w_low = vix_data['Close'].min()
            
            # Interpretation
            if current_vix < 12:
                sentiment = "COMPLACENT"
                interpretation = "Very low fear - market complacent, breakout possible"
            elif current_vix < 18:
                sentiment = "NORMAL"
                interpretation = "Normal volatility - stable market conditions"
            elif current_vix < 25:
                sentiment = "ELEVATED"
                interpretation = "Elevated fear - increased uncertainty"
            else:
                sentiment = "PANIC"
                interpretation = "Extreme fear - potential capitulation/reversal"
            
            return AnalysisResult(
                success=True,
                data={
                    'current': current_vix,
                    'change_1m': vix_change,
                    '52w_high': vix_52w_high,
                    '52w_low': vix_52w_low,
                    'sentiment': sentiment,
                    'interpretation': interpretation,
                    'history': vix_data
                }
            )
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.error(f"VIX error: {result.error}")
            return
        
        data = result.data
        
        st.subheader(f"{self.icon} {self.name}")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_metric_card("India VIX", f"{data['current']:.2f}")
        with col2:
            render_metric_card("1M Change", f"{data['change_1m']:+.2f}%", is_positive=data['change_1m']<0) # VIX down is good
        with col3:
            render_metric_card("52W High", f"{data['52w_high']:.2f}")
        with col4:
            render_metric_card("52W Low", f"{data['52w_low']:.2f}")
        
        sentiment_color = {
            'COMPLACENT': '🟢',
            'NORMAL': '🔵',
            'ELEVATED': '🟡',
            'PANIC': '🔴'
        }.get(data['sentiment'], '⚪')
        
        st.markdown(f"**Sentiment:** {sentiment_color} {data['sentiment']}")
        st.caption(data['interpretation'])
        
        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['history'].index,
            y=data['history']['Close'],
            name='VIX',
            line=dict(color='red', width=2)
        ))
        fig.update_layout(title="India VIX - 1 Month", height=300, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)


@register_plugin
class MarketBreadthPlugin(AnalysisPlugin):
    """Multi-index market breadth"""
    
    @property
    def name(self) -> str:
        return "Market Overview"
    
    @property
    def icon(self) -> str:
        return "📊"
    
    @property
    def description(self) -> str:
        return "NIFTY 50, Bank Nifty, Midcap, Smallcap"
    
    @property
    def category(self) -> str:
        return "market"
    
    @property
    def requires_config(self):
        return ['UPSTOX_API_KEY', 'UPSTOX_API_SECRET']
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            indices = {
                'NIFTY 50': 'Nifty 50',
                'Bank Nifty': 'Bank Nifty',
                'Midcap 100': 'Nifty Midcap 100',
                'Smallcap 100': 'Nifty Smallcap 100'
            }
            
            # Check for Upstox
            api_key = context.get('config', {}).get('UPSTOX_API_KEY')
            api_secret = context.get('config', {}).get('UPSTOX_API_SECRET')
            
            results = {}
            source = "Yahoo Finance"
            
            if api_key and api_secret:
                try:
                    auth = UpstoxAuth(api_key, api_secret)
                    fo_data = UpstoxFOData(auth)
                    source = "Upstox (Real-time)"
                    
                    for name, symbol in indices.items():
                        quote = fo_data.get_spot_quote(symbol)
                        if quote:
                            results[name] = {
                                'price': quote['ltp'],
                                'change': quote['change'],
                                'change_pct': quote['change_pct']
                            }
                        else:
                            # Fallback if Upstox fails for specific symbol
                            results[name] = {'price': None, 'change': None, 'change_pct': None}
                except Exception as e:
                    logger.error(f"Upstox breadth fetch failed: {e}")
                    results = {} # Trigger fallback
            
            # Fallback to yfinance if Upstox failed or not configured
            if not results:
                source = "Yahoo Finance (Delayed)"
                yf_map = {
                    'NIFTY 50': '^NSEI',
                    'Bank Nifty': '^NSEBANK',
                    'Midcap 100': 'NIFTY_MIDCAP_100.NS',
                    'Smallcap 100': '^CNXSC'
                }
                
                for name, symbol in yf_map.items():
                    try:
                        ticker = yf.Ticker(symbol)
                        data = ticker.history(period="5d")
                        
                        if not data.empty:
                            current = data['Close'].iloc[-1]
                            prev = data['Close'].iloc[-2] if len(data) > 1 else data['Open'].iloc[-1]
                            change = current - prev
                            change_pct = (change / prev) * 100
                            
                            results[name] = {
                                'price': current,
                                'change': change,
                                'change_pct': change_pct
                            }
                    except:
                        results[name] = {'price': None, 'change': None, 'change_pct': None}
            
            # Market breadth interpretation
            positive = sum(1 for v in results.values() if v['change_pct'] and v['change_pct'] > 0)
            total = len([v for v in results.values() if v['change_pct'] is not None])
            
            if total > 0:
                breadth_pct = (positive / total) * 100
                
                if breadth_pct >= 75:
                    breadth = "STRONG BULLISH"
                elif breadth_pct >= 50:
                    breadth = "MILDLY BULLISH"
                elif breadth_pct >= 25:
                    breadth = "MILDLY BEARISH"
                else:
                    breadth = "STRONG BEARISH"
            else:
                breadth = "UNKNOWN"
            
            return AnalysisResult(
                success=True,
                data={
                    'indices': results,
                    'breadth': breadth,
                    'breadth_pct': breadth_pct if total > 0 else 0,
                    'source': source
                }
            )
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.error(f"Breadth error: {result.error}")
            return
        
        data = result.data
        
        st.subheader(f"{self.icon} {self.name}")
        st.caption(f"Data Source: {data['source']}")
        
        cols = st.columns(len(data['indices']))
        
        for col, (name, info) in zip(cols, data['indices'].items()):
            with col:
                if info['price']:
                    is_pos = info['change_pct'] > 0 if info['change_pct'] is not None else None
                    change_txt = f"{info['change_pct']:+.2f}%" if info['change_pct'] is not None else "0.00%"
                    render_metric_card(
                        name,
                        f"₹{info['price']:,.2f}",
                        change_txt,
                        is_positive=is_pos
                    )
                else:
                    render_metric_card(name, "N/A", "0.00%")

    """VIX (Fear Index) Analysis"""
    
    @property
    def name(self) -> str:
        return "VIX Analysis"
    
    @property
    def icon(self) -> str:
        return "😱"
    
    @property
    def description(self) -> str:
        return "India VIX - Market fear gauge"
    
    @property
    def category(self) -> str:
        return "market"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            # Fetch India VIX
            vix = yf.Ticker("^INDIAVIX")
            vix_data = vix.history(period="1mo")
            
            if vix_data.empty:
                return AnalysisResult(
                    success=False,
                    data={},
                    error="VIX data unavailable"
                )
            
            current_vix = vix_data['Close'].iloc[-1]
            vix_change = ((current_vix / vix_data['Close'].iloc[0]) - 1) * 100
            vix_52w_high = vix_data['Close'].max()
            vix_52w_low = vix_data['Close'].min()
            
            # Interpretation
            if current_vix < 12:
                sentiment = "COMPLACENT"
                interpretation = "Very low fear - market complacent, breakout possible"
            elif current_vix < 18:
                sentiment = "NORMAL"
                interpretation = "Normal volatility - stable market conditions"
            elif current_vix < 25:
                sentiment = "ELEVATED"
                interpretation = "Elevated fear - increased uncertainty"
            else:
                sentiment = "PANIC"
                interpretation = "Extreme fear - potential capitulation/reversal"
            
            return AnalysisResult(
                success=True,
                data={
                    'current': current_vix,
                    'change_1m': vix_change,
                    '52w_high': vix_52w_high,
                    '52w_low': vix_52w_low,
                    'sentiment': sentiment,
                    'interpretation': interpretation,
                    'history': vix_data
                }
            )
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.error(f"VIX error: {result.error}")
            return
        
        data = result.data
        
        st.subheader(f"{self.icon} {self.name}")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("India VIX", f"{data['current']:.2f}")
        col2.metric("1M Change", f"{data['change_1m']:+.2f}%")
        col3.metric("52W High", f"{data['52w_high']:.2f}")
        col4.metric("52W Low", f"{data['52w_low']:.2f}")
        
        sentiment_color = {
            'COMPLACENT': '🟢',
            'NORMAL': '🔵',
            'ELEVATED': '🟡',
            'PANIC': '🔴'
        }.get(data['sentiment'], '⚪')
        
        st.info(f"{sentiment_color} **{data['sentiment']}**: {data['interpretation']}")
        
        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['history'].index,
            y=data['history']['Close'],
            name='VIX',
            line=dict(color='red', width=2)
        ))
        fig.update_layout(title="India VIX - 1 Month", height=300)
        st.plotly_chart(fig, use_container_width=True)


@register_plugin
class MarketBreadthPlugin(AnalysisPlugin):
    """Multi-index market breadth"""
    
    @property
    def name(self) -> str:
        return "Market Breadth"
    
    @property
    def icon(self) -> str:
        return "📊"
    
    @property
    def description(self) -> str:
        return "NIFTY 50, Bank Nifty, Midcap, Smallcap"
    
    @property
    def category(self) -> str:
        return "market"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            indices = {
                'NIFTY 50': '^NSEI',
                'Bank Nifty': '^NSEBANK',
                'Midcap 100': 'NIFTY_MIDCAP_100.NS', # Corrected symbol
                'Smallcap 100': '^CNXSC'
            }
            
            results = {}
            
            for name, symbol in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period="5d")
                    
                    if not data.empty:
                        current = data['Close'].iloc[-1]
                        prev = data['Close'].iloc[0]
                        change = ((current / prev) - 1) * 100
                        
                        results[name] = {
                            'price': current,
                            'change': change
                        }
                except:
                    results[name] = {'price': None, 'change': None}
            
            # Market breadth interpretation
            positive = sum(1 for v in results.values() if v['change'] and v['change'] > 0)
            total = len([v for v in results.values() if v['change'] is not None])
            
            if total > 0:
                breadth_pct = (positive / total) * 100
                
                if breadth_pct >= 75:
                    breadth = "STRONG BULLISH"
                elif breadth_pct >= 50:
                    breadth = "MILDLY BULLISH"
                elif breadth_pct >= 25:
                    breadth = "MILDLY BEARISH"
                else:
                    breadth = "STRONG BEARISH"
            else:
                breadth = "UNKNOWN"
            
            return AnalysisResult(
                success=True,
                data={
                    'indices': results,
                    'breadth': breadth,
                    'breadth_pct': breadth_pct if total > 0 else 0
                }
            )
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.error(f"Breadth error: {result.error}")
            return
        
        data = result.data
        
        st.subheader(f"{self.icon} {self.name}")
        
        st.markdown(f"**Market Breadth: {data['breadth']}** ({data['breadth_pct']:.0f}% positive)")
        
        cols = st.columns(len(data['indices']))
        
        for col, (name, info) in zip(cols, data['indices'].items()):
            if info['price']:
                col.metric(
                    name,
                    f"₹{info['price']:.2f}",
                    f"{info['change']:+.2f}%"
                )
            else:
                col.metric(name, "N/A")


# ==========================================
# GLOBAL MACRO PLUGINS
# ==========================================

@register_plugin
class GlobalMarketsPlugin(AnalysisPlugin):
    """US markets, DXY, Gold, Silver"""
    
    @property
    def name(self) -> str:
        return "Global Markets"
    
    @property
    def icon(self) -> str:
        return "🌍"
    
    @property
    def description(self) -> str:
        return "US indices, DXY, Gold, Silver"
    
    @property
    def category(self) -> str:
        return "macro"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            tickers = {
                'S&P 500': '^GSPC',
                'Nasdaq': '^IXIC',
                'DXY (Dollar)': 'DX-Y.NYB',
                'Gold': 'GC=F',
                'Silver': 'SI=F',
                'Crude Oil': 'CL=F'
            }
            
            results = {}
            
            for name, symbol in tickers.items():
                try:
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period="5d")
                    
                    if not data.empty:
                        current = data['Close'].iloc[-1]
                        prev = data['Close'].iloc[0]
                        change = ((current / prev) - 1) * 100
                        
                        results[name] = {
                            'price': current,
                            'change': change
                        }
                except:
                    results[name] = {'price': None, 'change': None}
            
            return AnalysisResult(
                success=True,
                data={'assets': results}
            )
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.error(f"Global markets error: {result.error}")
            return
        
        data = result.data
        
        st.subheader(f"{self.icon} {self.name}")
        
        # US Markets
        st.markdown("**US Markets**")
        col1, col2 = st.columns(2)
        
        us_markets = ['S&P 500', 'Nasdaq']
        for i, name in enumerate(us_markets):
            col = col1 if i == 0 else col2
            info = data['assets'].get(name, {})
            if info.get('price'):
                col.metric(name, f"{info['price']:.2f}", f"{info['change']:+.2f}%")
        
        # Commodities
        st.markdown("**Commodities & FX**")
        cols = st.columns(4)
        
        commodities = ['DXY (Dollar)', 'Gold', 'Silver', 'Crude Oil']
        for col, name in zip(cols, commodities):
            info = data['assets'].get(name, {})
            if info.get('price'):
                col.metric(name, f"{info['price']:.2f}", f"{info['change']:+.2f}%")


@register_plugin
class BondMarketPlugin(AnalysisPlugin):
    """US Treasury yields"""
    
    @property
    def name(self) -> str:
        return "Bond Market"
    
    @property
    def icon(self) -> str:
        return "📈"
    
    @property
    def description(self) -> str:
        return "US Treasury yields (10Y, 2Y)"
    
    @property
    def category(self) -> str:
        return "macro"
    
    @property
    def enabled_by_default(self) -> bool:
        return False  # Advanced feature
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            bonds = {
                '10Y Treasury': '^TNX',
                '2Y Treasury': '^IRX'
            }
            
            results = {}
            
            for name, symbol in bonds.items():
                try:
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period="1mo")
                    
                    if not data.empty:
                        current = data['Close'].iloc[-1]
                        prev = data['Close'].iloc[0]
                        change = current - prev  # Absolute change in bps
                        
                        results[name] = {
                            'yield': current,
                            'change_bps': change * 100  # Convert to basis points
                        }
                except:
                    results[name] = {'yield': None, 'change_bps': None}
            
            # Yield curve (10Y - 2Y)
            if results.get('10Y Treasury', {}).get('yield') and results.get('2Y Treasury', {}).get('yield'):
                spread = results['10Y Treasury']['yield'] - results['2Y Treasury']['yield']
                
                if spread < 0:
                    curve = "INVERTED (Recession signal)"
                elif spread < 0.5:
                    curve = "FLAT (Slowdown)"
                else:
                    curve = "NORMAL (Healthy)"
            else:
                spread = None
                curve = "N/A"
            
            return AnalysisResult(
                success=True,
                data={
                    'yields': results,
                    'spread': spread,
                    'curve': curve
                }
            )
            
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.error(f"Bond market error: {result.error}")
            return
        
        data = result.data
        
        st.subheader(f"{self.icon} {self.name}")
        
        col1, col2, col3 = st.columns(3)
        
        # 10Y
        y10 = data['yields'].get('10Y Treasury', {})
        if y10.get('yield'):
            col1.metric("10Y Yield", f"{y10['yield']:.2f}%", f"{y10['change_bps']:+.0f} bps")
        
        # 2Y
        y2 = data['yields'].get('2Y Treasury', {})
        if y2.get('yield'):
            col2.metric("2Y Yield", f"{y2['yield']:.2f}%", f"{y2['change_bps']:+.0f} bps")
        
        # Spread
        if data['spread'] is not None:
            col3.metric("10Y-2Y Spread", f"{data['spread']:.2f}%")
        
        st.info(f"**Yield Curve**: {data['curve']}")


# ==========================================
# NEWS & SENTIMENT PLUGINS
# ==========================================

@register_plugin
class NewsPlugin(AnalysisPlugin):
    """Latest market news"""
    
    @property
    def name(self) -> str:
        return "Market News"
    
    @property
    def icon(self) -> str:
        return "📰"
    
    @property
    def description(self) -> str:
        return "Latest news from Google News"
    
    @property
    def category(self) -> str:
        return "sentiment"
    
    @property
    def enabled_by_default(self) -> bool:
        return False  # Can be slow
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            from gnews import GNews
            
            symbol = context.get('symbol', 'NIFTY')
            
            # Get news
            gnews = GNews(language='en', country='IN', period='1d', max_results=5)
            
            # Search query
            if symbol == '^NSEI':
                query = 'NIFTY stock market'
            else:
                query = symbol.replace('.NS', '') + ' stock'
            
            articles = gnews.get_news(query)
            
            return AnalysisResult(
                success=True,
                data={'articles': articles}
            )
            
        except ImportError:
            return AnalysisResult(
                success=False,
                data={},
                error="gnews library not installed. Run: pip install gnews"
            )
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"News unavailable: {result.error}")
            return
        
        data = result.data
        articles = data.get('articles', [])
        
        st.subheader(f"{self.icon} {self.name}")
        
        if not articles:
            st.info("No recent news found")
            return
        
        for article in articles[:5]:
            title = article.get('title', 'No title')
            desc = article.get('description', '')
            url = article.get('url', '#')
            published = article.get('published date', '')
            
            st.markdown(f"**{title}**")
            if desc:
                st.markdown(f"_{desc}_")
            st.markdown(f"[Read more]({url}) • {published}")
            st.markdown("---")


# Registry automatically populated via @register_plugin decorator
