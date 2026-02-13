"""
Professional Analysis Plugins (Phase 1 Port from bbt11)
Includes: Economic Indicators, Insider Trading, Global Markets, News Sentiment, Alerts
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from ui_components import render_aggrid

logger = logging.getLogger(__name__)

@register_plugin
class RealTimeAlertsPlugin(AnalysisPlugin):
    """Real-time price alerts and notifications"""

    @property
    def name(self) -> str:
        return "Real-Time Alerts"

    @property
    def icon(self) -> str:
        return "🚨"

    @property
    def description(self) -> str:
        return "Price alerts, volume spikes, and market notifications"

    @property
    def category(self) -> str:
        return "market"

    @property
    def enabled_by_default(self) -> bool:
        return False

    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            # Placeholder alert data - would monitor real-time data
            alerts_data = {
                'price_alerts': [
                    {'symbol': 'RELIANCE', 'type': 'ABOVE', 'price': 2700, 'current': 2650, 'status': 'ACTIVE'},
                    {'symbol': 'TCS', 'type': 'BELOW', 'price': 3400, 'current': 3450, 'status': 'TRIGGERED'}
                ],
                'volume_alerts': [
                    {'symbol': 'HDFC', 'threshold': 1000000, 'current_volume': 1200000, 'status': 'TRIGGERED'}
                ],
                'news_alerts': [
                    {'keyword': 'Fed Rate Cut', 'occurrences': 3, 'last_seen': '2024-01-15 14:30'}
                ]
            }

            return AnalysisResult(success=True, data={'alerts': alerts_data})

        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"Alerts: {result.error}")
            return

        data = result.data['alerts']

        st.subheader(f"{self.icon} {self.name}")

        # Active alerts
        st.markdown("**🔔 Active Price Alerts**")
        if data['price_alerts']:
            for alert in data['price_alerts']:
                status_color = '🟢' if alert['status'] == 'ACTIVE' else '🔴'
                st.markdown(f"{status_color} **{alert['symbol']}** {alert['type']} ₹{alert['price']} (Current: ₹{alert['current']})")
        else:
            st.info("No active price alerts")

        # Volume alerts
        st.markdown("---")
        st.markdown("**📊 Volume Alerts**")
        if data['volume_alerts']:
            for alert in data['volume_alerts']:
                status_icon = '🔴' if alert['status'] == 'TRIGGERED' else '🟡'
                st.markdown(f"{status_icon} **{alert['symbol']}** Volume: {alert['current_volume']:,} (Threshold: {alert['threshold']:,})")
        else:
            st.info("No volume alerts triggered")

        # News alerts
        st.markdown("---")
        st.markdown("**📰 News Alerts**")
        if data['news_alerts']:
            for alert in data['news_alerts']:
                st.markdown(f"📰 **{alert['keyword']}** - {alert['occurrences']} mentions (Last: {alert['last_seen']})")
        else:
            st.info("No news alerts")

        # Alert configuration
        with st.expander("⚙️ Configure Alerts"):
            st.markdown("**Add Price Alert**")
            col1, col2, col3 = st.columns(3)
            with col1:
                symbol = st.selectbox("Symbol", ["RELIANCE", "TCS", "HDFC", "INFY"])
            with col2:
                alert_type = st.selectbox("Type", ["ABOVE", "BELOW"])
            with col3:
                price = st.number_input("Price", min_value=0.0, step=0.1)

            if st.button("Add Alert"):
                st.success(f"Alert added: {symbol} {alert_type} ₹{price}")


@register_plugin
class GlobalMarketsPlugin(AnalysisPlugin):
    """Global market indices and commodities"""

    @property
    def name(self) -> str:
        return "Global Markets"

    @property
    def icon(self) -> str:
        return "🌐"

    @property
    def description(self) -> str:
        return "SPX, FTSE, NIKKEI, Gold, Oil, Crypto"

    @property
    def category(self) -> str:
        return "macro"

    @property
    def enabled_by_default(self) -> bool:
        return False

    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            # Global market data - would integrate with real APIs
            global_data = {
                'indices': {
                    'SPX': {'price': 4800.50, 'change': '+0.8%', 'change_pct': 0.8},
                    'NASDAQ': {'price': 15800.25, 'change': '+1.2%', 'change_pct': 1.2},
                    'DOW': {'price': 37800.75, 'change': '+0.5%', 'change_pct': 0.5},
                    'FTSE': {'price': 7520.30, 'change': '-0.2%', 'change_pct': -0.2},
                    'DAX': {'price': 16850.90, 'change': '+0.7%', 'change_pct': 0.7},
                    'CAC': {'price': 7250.45, 'change': '+0.3%', 'change_pct': 0.3},
                    'NIKKEI': {'price': 38200.80, 'change': '+1.5%', 'change_pct': 1.5},
                    'HSI': {'price': 16500.60, 'change': '-0.8%', 'change_pct': -0.8},
                    'SSE': {'price': 3100.25, 'change': '+0.4%', 'change_pct': 0.4}
                },
                'commodities': {
                    'GOLD': {'price': 2050.30, 'change': '+0.6%', 'change_pct': 0.6, 'unit': 'USD/oz'},
                    'SILVER': {'price': 23.45, 'change': '+1.2%', 'change_pct': 1.2, 'unit': 'USD/oz'},
                    'BRENT_OIL': {'price': 78.50, 'change': '+1.8%', 'change_pct': 1.8, 'unit': 'USD/bbl'},
                    'WTI_OIL': {'price': 74.20, 'change': '+1.5%', 'change_pct': 1.5, 'unit': 'USD/bbl'},
                    'COPPER': {'price': 3.85, 'change': '+0.9%', 'change_pct': 0.9, 'unit': 'USD/lb'},
                    'NATURAL_GAS': {'price': 2.65, 'change': '-2.1%', 'change_pct': -2.1, 'unit': 'USD/MMBtu'}
                },
                'crypto': {
                    'BTC': {'price': 45120.50, 'change': '+2.1%', 'change_pct': 2.1, 'unit': 'USD'},
                    'ETH': {'price': 2450.75, 'change': '+1.8%', 'change_pct': 1.8, 'unit': 'USD'},
                    'BNB': {'price': 315.20, 'change': '+0.5%', 'change_pct': 0.5, 'unit': 'USD'},
                    'ADA': {'price': 0.48, 'change': '+3.2%', 'change_pct': 3.2, 'unit': 'USD'},
                    'SOL': {'price': 98.75, 'change': '+4.1%', 'change_pct': 4.1, 'unit': 'USD'}
                },
                'currencies': {
                    'EUR/USD': {'price': 1.0850, 'change': '+0.15%', 'change_pct': 0.15},
                    'GBP/USD': {'price': 1.2750, 'change': '+0.25%', 'change_pct': 0.25},
                    'USD/JPY': {'price': 148.50, 'change': '-0.35%', 'change_pct': -0.35},
                    'USD/CHF': {'price': 0.9150, 'change': '+0.05%', 'change_pct': 0.05},
                    'AUD/USD': {'price': 0.6720, 'change': '+0.45%', 'change_pct': 0.45},
                    'USD/CAD': {'price': 1.3450, 'change': '-0.20%', 'change_pct': -0.20},
                    'USD/CNY': {'price': 7.1250, 'change': '+0.10%', 'change_pct': 0.10}
                }
            }

            return AnalysisResult(success=True, data={'global': global_data})

        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"Global: {result.error}")
            return

        data = result.data['global']

        st.subheader(f"{self.icon} {self.name}")

        # Global Indices
        st.markdown("**🌍 Global Indices**")
        indices_df = pd.DataFrame(data['indices']).T
        indices_df['formatted_price'] = indices_df.apply(
            lambda x: f"{x['price']:,.0f}", axis=1
        )
        render_aggrid(
            indices_df[['formatted_price', 'change']].rename(
                columns={'formatted_price': 'Price', 'change': 'Change'}
            ),
            height=250
        )

        # Commodities
        st.markdown("---")
        st.markdown("**⛽ Commodities**")
        commodities_df = pd.DataFrame(data['commodities']).T
        commodities_df['formatted_price'] = commodities_df.apply(
            lambda x: f"{x['price']:.2f} {x['unit']}", axis=1
        )
        render_aggrid(
            commodities_df[['formatted_price', 'change']].rename(
                columns={'formatted_price': 'Price', 'change': 'Change'}
            ),
            height=250
        )

        # Cryptocurrencies
        st.markdown("---")
        st.markdown("**₿ Cryptocurrencies**")
        crypto_df = pd.DataFrame(data['crypto']).T
        crypto_df['formatted_price'] = crypto_df.apply(
            lambda x: f"${x['price']:,.2f}", axis=1
        )
        render_aggrid(
            crypto_df[['formatted_price', 'change']].rename(
                columns={'formatted_price': 'Price', 'change': 'Change'}
            ),
            height=200
        )

        # Currencies
        st.markdown("---")
        st.markdown("**💱 Major Currencies**")
        currencies_df = pd.DataFrame(data['currencies']).T
        currencies_df['formatted_price'] = currencies_df.apply(
            lambda x: f"{x['price']:.4f}", axis=1
        )
        render_aggrid(
            currencies_df[['formatted_price', 'change']].rename(
                columns={'formatted_price': 'Rate', 'change': 'Change'}
            ),
            height=250
        )


@register_plugin
class EconomicIndicatorsPlugin(AnalysisPlugin):
    """Economic indicators and global market data"""

    @property
    def name(self) -> str:
        return "Economic Indicators"

    @property
    def icon(self) -> str:
        return "🌍"

    @property
    def description(self) -> str:
        return "GDP, Inflation, Interest Rates, Global indices"

    @property
    def category(self) -> str:
        return "macro"

    @property
    def enabled_by_default(self) -> bool:
        return False

    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            # This would integrate with economic data APIs
            # For now, return placeholder data
            economic_data = {
                'us_gdp': {'value': 2.1, 'change': 0.2, 'period': 'Q4 2023'},
                'us_inflation': {'value': 3.1, 'change': -0.3, 'period': 'Jan 2024'},
                'fed_rate': {'value': 5.25, 'change': 0.0, 'period': 'Current'},
                'global_indices': {
                    'SPX': {'price': 4800, 'change_pct': 0.8},
                    'FTSE': {'price': 7500, 'change_pct': -0.2},
                    'NIKKEI': {'price': 38000, 'change_pct': 1.2}
                }
            }

            return AnalysisResult(success=True, data={'economic': economic_data})

        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"Economic: {result.error}")
            return

        data = result.data['economic']

        st.subheader(f"{self.icon} {self.name}")

        # US Economic Indicators
        st.markdown("**US Economic Indicators**")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("GDP Growth", f"{data['us_gdp']['value']}%",
                     f"{data['us_gdp']['change']:+.1f}%")
        with col2:
            st.metric("Inflation (CPI)", f"{data['us_inflation']['value']}%",
                     f"{data['us_inflation']['change']:+.1f}%")
        with col3:
            st.metric("Fed Funds Rate", f"{data['fed_rate']['value']}%",
                     f"{data['fed_rate']['change']:+.1f}%")

        # Global Indices
        st.markdown("---")
        st.markdown("**Global Market Indices**")

        indices_df = pd.DataFrame(data['global_indices']).T
        indices_df['change_pct'] = indices_df['change_pct'].apply(lambda x: f"{x:+.1f}%")

        render_aggrid(indices_df, height=200)


@register_plugin
class NewsSentimentPlugin(AnalysisPlugin):
    """News sentiment analysis"""

    @property
    def name(self) -> str:
        return "News Sentiment"

    @property
    def icon(self) -> str:
        return "📰"

    @property
    def description(self) -> str:
        return "Market news sentiment and key headlines"

    @property
    def category(self) -> str:
        return "sentiment"

    @property
    def enabled_by_default(self) -> bool:
        return False

    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            symbol = context.get('upstox_symbol', 'Nifty 50')

            # Placeholder news data - would integrate with news APIs
            news_data = {
                'overall_sentiment': 'NEUTRAL',
                'sentiment_score': 0.15,
                'headlines': [
                    {'title': f'{symbol} shows resilience amid global uncertainty', 'sentiment': 'POSITIVE', 'source': 'Bloomberg'},
                    {'title': f'Analysts cautious on {symbol} near-term outlook', 'sentiment': 'NEGATIVE', 'source': 'Reuters'},
                    {'title': f'{symbol} technicals suggest consolidation phase', 'sentiment': 'NEUTRAL', 'source': 'CNBC'}
                ],
                'sector_news': [
                    'Technology sector leads gains',
                    'Banking stocks under pressure from rate concerns'
                ]
            }

            return AnalysisResult(success=True, data={'news': news_data})

        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"News: {result.error}")
            return

        data = result.data['news']

        st.subheader(f"{self.icon} {self.name}")

        # Overall sentiment
        sentiment_color = {'POSITIVE': 'green', 'NEGATIVE': 'red', 'NEUTRAL': 'orange'}
        color = sentiment_color.get(data['overall_sentiment'], 'gray')

        st.markdown(f"**Overall Sentiment: <span style='color:{color}'>{data['overall_sentiment']}</span>** (Score: {data['sentiment_score']:+.2f})", unsafe_allow_html=True)

        # Headlines
        st.markdown("**Key Headlines**")
        for headline in data['headlines']:
            sentiment_icon = {'POSITIVE': '🟢', 'NEGATIVE': '🔴', 'NEUTRAL': '🟡'}
            icon = sentiment_icon.get(headline['sentiment'], '⚪')
            st.markdown(f"{icon} **{headline['title']}** - {headline['source']}")

        # Sector news
        st.markdown("---")
        st.markdown("**Sector News**")
        for news in data['sector_news']:
            st.markdown(f"• {news}")


@register_plugin
class InsiderTradingPlugin(AnalysisPlugin):
    """Insider trading and bulk deals"""

    @property
    def name(self) -> str:
        return "Insider Trading"

    @property
    def icon(self) -> str:
        return "👥"

    @property
    def description(self) -> str:
        return "Insider transactions and bulk deals"

    @property
    def category(self) -> str:
        return "sentiment"

    @property
    def enabled_by_default(self) -> bool:
        return False

    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            symbol = context.get('symbol', '')

            # Placeholder insider data - would integrate with NSE/ BSE APIs
            insider_data = {
                'recent_transactions': [
                    {'date': '2024-01-15', 'type': 'BUY', 'quantity': 50000, 'price': 2450.50, 'person': 'Promoter'},
                    {'date': '2024-01-10', 'type': 'SELL', 'quantity': 25000, 'price': 2420.75, 'person': 'Director'}
                ],
                'bulk_deals': [
                    {'date': '2024-01-14', 'type': 'BUY', 'quantity': 200000, 'price': 2435.00, 'client': 'Foreign Institutional'}
                ],
                'pledged_shares': {'total': 2.1, 'promoter': 1.8}
            }

            return AnalysisResult(success=True, data={'insider': insider_data})

        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"Insider: {result.error}")
            return

        data = result.data['insider']

        st.subheader(f"{self.icon} {self.name}")

        # Recent transactions
        st.markdown("**Recent Insider Transactions**")
        if data['recent_transactions']:
            trans_df = pd.DataFrame(data['recent_transactions'])
            trans_df['value'] = (trans_df['quantity'] * trans_df['price']).map('₹{:,.0f}'.format)
            trans_df['quantity'] = trans_df['quantity'].map('{:,.0f}'.format)
            trans_df['price'] = trans_df['price'].map('₹{:.2f}'.format)
            render_aggrid(trans_df, height=200)
        else:
            st.info("No recent insider transactions")

        # Bulk deals
        st.markdown("---")
        st.markdown("**Bulk Deals**")
        if data['bulk_deals']:
            bulk_df = pd.DataFrame(data['bulk_deals'])
            bulk_df['value'] = (bulk_df['quantity'] * bulk_df['price']).map('₹{:,.0f}'.format)
            bulk_df['quantity'] = bulk_df['quantity'].map('{:,.0f}'.format)
            bulk_df['price'] = bulk_df['price'].map('₹{:.2f}'.format)
            render_aggrid(bulk_df, height=200)
        else:
            st.info("No recent bulk deals")

        # Pledged shares
        st.markdown("---")
        st.markdown("**Share Pledging**")
        col1, col2 = st.columns(2)
        col1.metric("Total Pledged", f"{data['pledged_shares']['total']}%")
        col2.metric("Promoter Pledged", f"{data['pledged_shares']['promoter']}%")


@register_plugin
class PortfolioTrackerPlugin(AnalysisPlugin):
    """Portfolio tracking and performance"""

    @property
    def name(self) -> str:
        return "Portfolio Tracker"

    @property
    def icon(self) -> str:
        return "📊"

    @property
    def description(self) -> str:
        return "Track portfolio performance and holdings"

    @property
    def category(self) -> str:
        return "asset"

    @property
    def enabled_by_default(self) -> bool:
        return False

    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            # Placeholder portfolio data - would load from user data
            portfolio_data = {
                'holdings': [
                    {'symbol': 'RELIANCE', 'shares': 100, 'avg_price': 2500, 'current_price': 2650, 'value': 265000},
                    {'symbol': 'TCS', 'shares': 50, 'avg_price': 3200, 'current_price': 3450, 'value': 172500},
                    {'symbol': 'HDFC', 'shares': 75, 'avg_price': 1600, 'current_price': 1680, 'value': 126000}
                ],
                'summary': {
                    'total_value': 563500,
                    'total_invested': 527500,
                    'total_pnl': 36000,
                    'total_pnl_pct': 6.8
                }
            }

            return AnalysisResult(success=True, data={'portfolio': portfolio_data})

        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"Portfolio: {result.error}")
            return

        data = result.data['portfolio']

        st.subheader(f"{self.icon} {self.name}")

        # Portfolio summary
        summary = data['summary']
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Value", f"₹{summary['total_value']:,.0f}")
        col2.metric("Total Invested", f"₹{summary['total_invested']:,.0f}")
        col3.metric("P&L", f"₹{summary['total_pnl']:,.0f}", f"{summary['total_pnl_pct']:+.1f}%")
        col4.metric("Return %", f"{summary['total_pnl_pct']:+.1f}%")

        # Holdings table
        st.markdown("---")
        st.markdown("**Holdings**")

        holdings_df = pd.DataFrame(data['holdings'])
        holdings_df['pnl'] = (holdings_df['current_price'] - holdings_df['avg_price']) * holdings_df['shares']
        holdings_df['pnl_pct'] = ((holdings_df['current_price'] - holdings_df['avg_price']) / holdings_df['avg_price']) * 100

        # Format columns
        holdings_df['avg_price'] = holdings_df['avg_price'].map('₹{:.0f}'.format)
        holdings_df['current_price'] = holdings_df['current_price'].map('₹{:.0f}'.format)
        holdings_df['value'] = holdings_df['value'].map('₹{:,.0f}'.format)
        holdings_df['pnl'] = holdings_df['pnl'].map('₹{:,.0f}'.format)
        holdings_df['pnl_pct'] = holdings_df['pnl_pct'].map('{:+.1f}%'.format)

        render_aggrid(holdings_df[['symbol', 'shares', 'avg_price', 'current_price', 'value', 'pnl', 'pnl_pct']], height=300)
