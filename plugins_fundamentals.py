"""
Fundamental Analysis Plugin
Integrates comprehensive fundamental analysis from bbt2 and screener.in (bbt10)
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
from ui_components import render_aggrid

logger = logging.getLogger(__name__)

# --- Ported FundamentalAnalyzer from bbt2/fundamental_analyzer.py ---
# Note: For simplicity and to avoid circular imports, 
# I will embed the necessary parts of FundamentalAnalyzer and ScreenerFundamentals here.
# A more refactored approach might involve having them as separate modules
# and importing them, but for direct porting, this is fine.

class FundamentalAnalyzer:
    """
    Comprehensive fundamental analysis - company context beyond just price
    Answers: Who are competitors? Financial health? Recent news? Supply chain?
    """
    
    def __init__(self, symbol: str):
        """
        Initialize fundamental analyzer
        
        Args:
            symbol: Stock symbol
        """
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        self.info = self._safe_get_info()
        
        logger.info(f"FundamentalAnalyzer initialized for {symbol}")
    
    def _safe_get_info(self) -> Dict:
        """Safely get ticker info, handling errors"""
        try:
            return self.ticker.info
        except Exception as e:
            logger.warning(f"Could not fetch info for {self.symbol}: {e}")
            return {}
    
    def get_company_profile(self) -> Dict:
        """
        Get basic company information
        
        Returns:
            Company profile dict
        """
        profile = {
            'symbol': self.symbol,
            'name': self.info.get('longName', 'N/A'),
            'sector': self.info.get('sector', 'N/A'),
            'industry': self.info.get('industry', 'N/A'),
            'country': self.info.get('country', 'N/A'),
            'website': self.info.get('website', 'N/A'),
            'employees': self.info.get('fullTimeEmployees', 'N/A'),
            'description': self.info.get('longBusinessSummary', 'N/A'),
            'exchange': self.info.get('exchange', 'N/A'),
            'currency': self.info.get('currency', 'N/A'),
        }
        
        return profile
    
    def get_key_metrics(self) -> Dict:
        """
        Get key financial metrics
        
        Returns:
            Dict of key metrics
        """
        metrics = {
            # Valuation
            'market_cap': self.info.get('marketCap', None),
            'enterprise_value': self.info.get('enterpriseValue', None),
            'pe_ratio': self.info.get('trailingPE', None),
            'forward_pe': self.info.get('forwardPE', None),
            'peg_ratio': self.info.get('pegRatio', None),
            'price_to_book': self.info.get('priceToBook', None),
            'price_to_sales': self.info.get('priceToSalesTrailing12Months', None),
            'ev_to_revenue': self.info.get('enterpriseToRevenue', None),
            'ev_to_ebitda': self.info.get('enterpriseToEbitda', None),
            
            # Profitability
            'profit_margin': self.info.get('profitMargins', None),
            'operating_margin': self.info.get('operatingMargins', None),
            'gross_margin': self.info.get('grossMargins', None),
            'roe': self.info.get('returnOnEquity', None),
            'roa': self.info.get('returnOnAssets', None),
            
            # Growth
            'revenue_growth': self.info.get('revenueGrowth', None),
            'earnings_growth': self.info.get('earningsGrowth', None),
            
            # Financial Health
            'debt_to_equity': self.info.get('debtToEquity', None),
            'current_ratio': self.info.get('currentRatio', None),
            'quick_ratio': self.info.get('quickRatio', None),
            'total_cash': self.info.get('totalCash', None),
            'total_debt': self.info.get('totalDebt', None),
            'free_cash_flow': self.info.get('freeCashflow', None),
            
            # Dividends
            'dividend_yield': self.info.get('dividendYield', None),
            'dividend_rate': self.info.get('dividendRate', None),
            'payout_ratio': self.info.get('payoutRatio', None),
            
            # Trading
            'beta': self.info.get('beta', None),
            '52w_high': self.info.get('fiftyTwoWeekHigh', None),
            '52w_low': self.info.get('fiftyTwoWeekLow', None),
            'avg_volume': self.info.get('averageVolume', None),
            
            # Ownership
            'shares_outstanding': self.info.get('sharesOutstanding', None),
            'float_shares': self.info.get('floatShares', None),
            'insider_ownership': self.info.get('heldPercentInsiders', None),
            'institutional_ownership': self.info.get('heldPercentInstitutions', None),
            
            # Analyst coverage
            'analyst_recommendations': self.info.get('recommendationKey', None),
            'target_price': self.info.get('targetMeanPrice', None),
            'number_of_analysts': self.info.get('numberOfAnalystOpinions', None),
        }
        
        # Calculate some derived metrics
        if metrics['target_price'] and self.info.get('currentPrice'):
            current = self.info.get('currentPrice')
            target = metrics['target_price']
            metrics['upside_to_target'] = ((target / current) - 1) * 100
        
        return metrics
    
    def get_institutional_holders(self) -> pd.DataFrame:
        """
        Get institutional holder information
        CRITICAL: Who owns this stock? Smart money positions?
        
        Returns:
            DataFrame of institutional holders
        """
        try:
            holders = self.ticker.institutional_holders
            if holders is not None and not holders.empty:
                # Calculate percentage of outstanding shares
                shares_out = self.info.get('sharesOutstanding', 1)
                holders['pct_outstanding'] = (holders['Shares'] / shares_out) * 100
                return holders
        except Exception as e:
            logger.warning(f"Could not fetch institutional holders: {e}")
        
        return pd.DataFrame()
    
    def detect_financial_red_flags(self) -> List[Dict]:
        """
        Detect potential financial red flags
        CRITICAL: Warning signs of trouble
        
        Returns:
            List of red flags
        """
        red_flags = []
        metrics = self.get_key_metrics()
        
        # High debt
        if metrics.get('debt_to_equity') and metrics['debt_to_equity'] > 2.0:
            red_flags.append({
                'severity': 'high',
                'category': 'financial_health',
                'flag': 'High debt-to-equity ratio',
                'value': metrics['debt_to_equity'],
                'description': 'Debt > 2x equity, high financial risk'
            })
        
        # Negative profit margins
        if metrics.get('profit_margin') and metrics['profit_margin'] < 0:
            red_flags.append({
                'severity': 'high',
                'category': 'profitability',
                'flag': 'Negative profit margins',
                'value': metrics['profit_margin'],
                'description': 'Company is losing money'
            })
        
        # Low current ratio (liquidity issue)
        if metrics.get('current_ratio') and metrics['current_ratio'] < 1.0:
            red_flags.append({
                'severity': 'medium',
                'category': 'liquidity',
                'flag': 'Low current ratio',
                'value': metrics['current_ratio'],
                'description': 'May struggle to pay short-term obligations'
            })
        
        # Declining revenue
        if metrics.get('revenue_growth') and metrics['revenue_growth'] and metrics['revenue_growth'] < -0.10:
            red_flags.append({
                'severity': 'medium',
                'category': 'growth',
                'flag': 'Declining revenue',
                'value': metrics['revenue_growth'],
                'description': 'Revenue falling > 10%'
            })
        
        # Very high PE (overvaluation)
        if metrics.get('pe_ratio') and metrics['pe_ratio'] > 50:
            red_flags.append({
                'severity': 'low',
                'category': 'valuation',
                'flag': 'Very high PE ratio',
                'value': metrics['pe_ratio'],
                'description': 'Stock may be overvalued'
            })
        
        # Low institutional ownership (lack of confidence)
        if metrics.get('institutional_ownership') and metrics['institutional_ownership'] < 0.10:
            red_flags.append({
                'severity': 'low',
                'category': 'ownership',
                'flag': 'Low institutional ownership',
                'value': metrics['institutional_ownership'],
                'description': 'Institutions avoiding this stock'
            })
        
        return red_flags
    
    def detect_positive_signals(self) -> List[Dict]:
        """
        Detect positive fundamental signals
        
        Returns:
            List of positive signals
        """
        signals = []
        metrics = self.get_key_metrics()
        
        # High ROE
        if metrics.get('roe') and metrics['roe'] > 0.15:
            signals.append({
                'category': 'profitability',
                'signal': 'Strong return on equity',
                'value': metrics['roe'],
                'description': 'ROE > 15%, efficient capital usage'
            })
        
        # Low debt
        if metrics.get('debt_to_equity') and metrics['debt_to_equity'] < 0.5:
            signals.append({
                'category': 'financial_health',
                'signal': 'Low debt levels',
                'value': metrics['debt_to_equity'],
                'description': 'Conservative balance sheet'
            })
        
        # Revenue growth
        if metrics.get('revenue_growth') and metrics['revenue_growth'] > 0.15:
            signals.append({
                'category': 'growth',
                'signal': 'Strong revenue growth',
                'value': metrics['revenue_growth'],
                'description': 'Revenue growing > 15%'
            })
        
        # High institutional ownership
        if metrics.get('institutional_ownership') and metrics['institutional_ownership'] > 0.70:
            signals.append({
                'category': 'ownership',
                'signal': 'High institutional ownership',
                'value': metrics['institutional_ownership'],
                'description': 'Strong institutional confidence'
            })
        
        # Dividend yield
        if metrics.get('dividend_yield') and metrics['dividend_yield'] > 0.03:
            signals.append({
                'category': 'income',
                'signal': 'Attractive dividend yield',
                'value': metrics['dividend_yield'],
                'description': 'Dividend yield > 3%'
            })
        
        return signals

    def get_moneycontrol_news(self, max_items: int = 10) -> List[Dict]:
        """Scrape news from MoneyControl (Indian stocks)"""
        news_items = []
        if not self.symbol.endswith('.NS') and self.symbol not in ['^NSEI', '^NSEBANK']:
            return []
        try:
            clean_symbol = self.symbol.replace('.NS', '').replace('^', '').lower()
            url = f"https://www.moneycontrol.com/news/tags/{clean_symbol}.html"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                news_list = soup.find_all('li', class_='clearfix', limit=max_items)
                for item in news_list:
                    try:
                        title_tag = item.find('h2')
                        link_tag = item.find('a')
                        if title_tag and link_tag:
                            news_items.append({
                                'date': datetime.now(),
                                'title': title_tag.get_text(strip=True),
                                'publisher': 'MoneyControl',
                                'link': link_tag.get('href', '#'),
                                'type': 'news'
                            })
                    except: continue
        except Exception as e:
            logger.warning(f"MoneyControl scraping failed: {e}")
        return news_items

    def get_economic_times_news(self, max_items: int = 10) -> List[Dict]:
        """Get news from Economic Times RSS/search"""
        news_items = []
        if not self.symbol.endswith('.NS') and self.symbol not in ['^NSEI', '^NSEBANK']:
            return []
        try:
            clean_symbol = self.symbol.replace('.NS', '').replace('^', '').lower()
            url = f"https://economictimes.indiatimes.com/topic/{clean_symbol}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                story_divs = soup.find_all('div', class_='eachStory', limit=max_items)
                for story in story_divs:
                    try:
                        title_tag = story.find('h3')
                        link_tag = story.find('a')
                        if title_tag and link_tag:
                            news_items.append({
                                'date': datetime.now(),
                                'title': title_tag.get_text(strip=True),
                                'publisher': 'Economic Times',
                                'link': link_tag.get('href', '#'),
                                'type': 'news'
                            })
                    except: continue
        except Exception as e:
            logger.warning(f"Economic Times scraping failed: {e}")
        return news_items

    def get_recent_news(self, days_back: int = 7) -> List[Dict]:
        """
        Get recent news about the company from multiple sources
        """
        news_items = []
        
        # 1. Yahoo Finance
        try:
            news = self.ticker.news
            cutoff_date = datetime.now() - timedelta(days=days_back)
            for item in news:
                if 'providerPublishTime' in item and item['providerPublishTime'] is not None:
                    pub_date = datetime.fromtimestamp(item['providerPublishTime'])
                else:
                    continue
                
                if pub_date >= cutoff_date:
                    news_items.append({
                        'date': pub_date,
                        'title': item.get('title', ''),
                        'publisher': item.get('publisher', ''),
                        'link': item.get('link', ''),
                        'type': item.get('type', 'news')
                    })
        except Exception as e:
            logger.warning(f"Could not fetch yfinance news for {self.symbol}: {e}")

        # 2. MoneyControl
        news_items.extend(self.get_moneycontrol_news())

        # 3. Economic Times
        news_items.extend(self.get_economic_times_news())
        
        # Sort and dedup
        seen = set()
        unique_news = []
        for item in news_items:
            if item['title'] not in seen:
                seen.add(item['title'])
                unique_news.append(item)
        
        unique_news.sort(key=lambda x: x['date'], reverse=True)
        return unique_news


# --- Ported ScreenerFundamentals from bbt10/screener_fundamentals.py ---
class ScreenerFundamentalsFetcher:
    """
    Get screener.in quality fundamentals
    Uses web scraping + yfinance combination
    """
    
    def __init__(self, symbol: str):
        """
        Initialize screener fundamentals
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS' or 'RELIANCE')
        """
        self.symbol = symbol.replace('.NS', '').upper()
        self.screener_url = f"https://www.screener.in/company/{self.symbol}/consolidated/"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Also get yfinance data for backup (used within _get_yfinance_fallback)
        self.ticker = yf.Ticker(f"{self.symbol}.NS")
        self.info = self._safe_get_info() # using local _safe_get_info
        
        logger.info(f"ScreenerFundamentalsFetcher initialized for {self.symbol}")
    
    def _safe_get_info(self) -> Dict:
        """Safely get ticker info"""
        try:
            return self.ticker.info
        except:
            return {}

    def _get_yfinance_fallback(self) -> Dict:
        """Get ratios from yfinance as fallback"""
        ratios = {}
        
        try:
            ratios['market_cap'] = self.info.get('marketCap', None)
            ratios['pe_ratio'] = self.info.get('trailingPE')
            ratios['book_value'] = self.info.get('bookValue')
            ratios['dividend_yield'] = self.info.get('dividendYield', 0) * 100 if self.info.get('dividendYield') else None
            ratios['roe'] = self.info.get('returnOnEquity', 0) * 100 if self.info.get('returnOnEquity') else None
            ratios['debt_to_equity'] = self.info.get('debtToEquity')
            ratios['eps_ttm'] = self.info.get('trailingEps')
            ratios['sales_growth_3yr'] = self.info.get('revenueGrowth', 0) * 100 if self.info.get('revenueGrowth') else None
            
            logger.info("Using yfinance data as fallback for ScreenerFundamentalsFetcher")
            
        except Exception as e:
            logger.error(f"yfinance fallback for ScreenerFundamentalsFetcher failed: {e}")
        
        return ratios

    def scrape_screener_ratios(self) -> Dict:
        """
        Scrape key ratios from screener.in
        
        Returns:
            Dict with comprehensive ratios
        """
        ratios = {}
        
        try:
            logger.info(f"Scraping screener.in for {self.symbol}")
            
            response = self.session.get(self.screener_url, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Screener.in returned {response.status_code}")
                return self._get_yfinance_fallback()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Market Cap
            market_cap_elem = soup.find('span', string='Market Cap')
            if market_cap_elem:
                market_cap = market_cap_elem.find_next('span', class_='number').get_text(strip=True)
                ratios['market_cap'] = market_cap # Keep as string for now, convert later if needed
            
            # Stock P/E
            pe_elem = soup.find('span', string='Stock P/E')
            if pe_elem:
                pe = pe_elem.find_next('span', class_='number').get_text(strip=True)
                ratios['pe_ratio'] = float(pe) if pe != '-' else None
            
            # Book Value
            bv_elem = soup.find('span', string='Book Value')
            if bv_elem:
                bv = bv_elem.find_next('span', class_='number').get_text(strip=True)
                ratios['book_value'] = float(bv.replace(',', '')) if bv != '-' else None
            
            # Dividend Yield
            div_elem = soup.find('span', string='Dividend Yield')
            if div_elem:
                div_yield = div_elem.find_next('span', class_='number').get_text(strip=True)
                ratios['dividend_yield'] = float(div_yield.replace('%', '')) if div_yield != '-' else None
            
            # ROCE
            roce_elem = soup.find('span', string='ROCE')
            if roce_elem:
                roce = roce_elem.find_next('span', class_='number').get_text(strip=True)
                ratios['roce'] = float(roce.replace('%', '')) if roce != '-' else None
            
            # ROE
            roe_elem = soup.find('span', string='ROE')
            if roe_elem:
                roe = roe_elem.find_next('span', class_='number').get_text(strip=True)
                ratios['roe'] = float(roe.replace('%', '')) if roe != '-' else None
            
            # Face Value
            fv_elem = soup.find('span', string='Face Value')
            if fv_elem:
                fv = fv_elem.find_next('span', class_='number').get_text(strip=True)
                ratios['face_value'] = float(fv.replace(',', '')) if fv != '-' else None
            
            # Debt to Equity
            de_elem = soup.find('span', string='Debt to equity')
            if de_elem:
                de = de_elem.find_next('span', class_='number').get_text(strip=True)
                ratios['debt_to_equity'] = float(de) if de != '-' else None
            
            # EPS (TTM)
            eps_elem = soup.find('span', string='EPS (TTM)')
            if eps_elem:
                eps = eps_elem.find_next('span', class_='number').get_text(strip=True)
                ratios['eps_ttm'] = float(eps.replace(',', '')) if eps != '-' else None
            
            # Sales Growth (3Yr CAGR)
            sales_growth = soup.find('span', string='Sales growth')
            if sales_growth:
                parent = sales_growth.find_parent('li')
                if parent:
                    small = parent.find('small')
                    if small:
                        growth = small.get_text(strip=True).replace('%', '')
                        try:
                            ratios['sales_growth_3yr'] = float(growth)
                        except:
                            pass
            
            # Profit Growth (3Yr CAGR)
            profit_growth = soup.find('span', string='Profit growth')
            if profit_growth:
                parent = profit_growth.find_parent('li')
                if parent:
                    small = parent.find('small')
                    if small:
                        growth = small.get_text(strip=True).replace('%', '')
                        try:
                            ratios['profit_growth_3yr'] = float(growth)
                        except:
                            pass
            
            # Promoter Holding
            promoter = soup.find(text=lambda t: t and 'Promoters' in t)
            if promoter:
                parent = promoter.find_parent('td')
                if parent:
                    next_td = parent.find_next_sibling('td')
                    if next_td:
                        holding = next_td.get_text(strip=True).replace('%', '')
                        try:
                            ratios['promoter_holding'] = float(holding)
                        except:
                            pass
            
            # FII Holding
            fii = soup.find(text=lambda t: t and 'FIIs' in t)
            if fii:
                parent = fii.find_parent('td')
                if parent:
                    next_td = parent.find_next_sibling('td')
                    if next_td:
                        holding = next_td.get_text(strip=True).replace('%', '')
                        try:
                            ratios['fii_holding'] = float(holding)
                        except:
                            pass
            
            # DII Holding
            dii = soup.find(text=lambda t: t and 'DIIs' in t)
            if dii:
                parent = dii.find_parent('td')
                if parent:
                    next_td = parent.find_next_sibling('td')
                    if next_td:
                        holding = next_td.get_text(strip=True).replace('%', '')
                        try:
                            ratios['dii_holding'] = float(holding)
                        except:
                            pass
            
            logger.info(f"✓ Scraped {len(ratios)} metrics from screener.in")
            
        except Exception as e:
            logger.error(f"Screener.in scraping failed: {e}")
            return self._get_yfinance_fallback()
        
        # If we got data, merge with yfinance for missing fields
        if ratios:
            yf_ratios = self._get_yfinance_fallback()
            
            # Fill in missing fields
            for key, value in yf_ratios.items():
                if key not in ratios or ratios[key] is None:
                    ratios[key] = value
        
        return ratios

    def get_comprehensive_screener_ratios(self) -> Dict:
        """
        Get all ratios from screener.in in one call, categorized.
        
        Returns:
            Dict with categories: valuation, profitability, financial_health, growth, ownership
        """
        all_ratios = self.scrape_screener_ratios()
        
        return {
            'valuation': {
                'Market Cap': all_ratios.get('market_cap', 'N/A'),
                'P/E Ratio': all_ratios.get('pe_ratio'),
                'Book Value': all_ratios.get('book_value'),
                'P/B Ratio': all_ratios.get('pe_ratio') / all_ratios.get('book_value') if all_ratios.get('book_value') else None,
                'Dividend Yield %': all_ratios.get('dividend_yield'),
                'Face Value': all_ratios.get('face_value')
            },
            'profitability': {
                'ROE %': all_ratios.get('roe'),
                'ROCE %': all_ratios.get('roce'),
                'EPS (TTM)': all_ratios.get('eps_ttm')
            },
            'financial_health': {
                'Debt to Equity': all_ratios.get('debt_to_equity')
            },
            'growth': {
                'Sales Growth (3Yr) %': all_ratios.get('sales_growth_3yr'),
                'Profit Growth (3Yr) %': all_ratios.get('profit_growth_3yr')
            },
            'ownership': {
                'Promoter Holding %': all_ratios.get('promoter_holding'),
                'FII Holding %': all_ratios.get('fii_holding'),
                'DII Holding %': all_ratios.get('dii_holding')
            }
        }


# --- FundamentalAnalysisPlugin ---
@register_plugin
class FundamentalAnalysisPlugin(AnalysisPlugin):
    """
    Provides comprehensive fundamental analysis including company profile, key metrics,
    institutional holdings, red flags, positive signals, and recent news.
    Combines data from yfinance (bbt2) and screener.in (bbt10).
    """

    @property
    def name(self) -> str:
        return "Fundamental Analysis"

    @property
    def icon(self) -> str:
        return "🏢"

    @property
    def description(self) -> str:
        return "Bloomberg-style company intelligence: financials, news, ownership, red flags."

    @property
    def category(self) -> str:
        return "asset"

    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        symbol = context.get('symbol')
        if not symbol:
            return AnalysisResult(success=False, data={}, error="No symbol provided for fundamental analysis.")

        try:
            # Use FundamentalAnalyzer (bbt2 version) for core yfinance data, red flags, positive signals
            fa = FundamentalAnalyzer(symbol)
            profile = fa.get_company_profile()
            key_metrics = fa.get_key_metrics()
            institutional_holders = fa.get_institutional_holders()
            red_flags = fa.detect_financial_red_flags()
            positive_signals = fa.detect_positive_signals()
            recent_news = fa.get_recent_news()

            # Use ScreenerFundamentalsFetcher (bbt10 version) for screener.in specific ratios
            sf_fetcher = ScreenerFundamentalsFetcher(symbol)
            screener_ratios = sf_fetcher.get_comprehensive_screener_ratios()
            
            # Combine metrics, prioritizing screener.in for specific Indian market data
            combined_metrics = key_metrics.copy()
            for category, ratios in screener_ratios.items():
                for key, value in ratios.items():
                    # Harmonize keys if necessary, or just add directly
                    # For simplicity, if key exists in yfinance metrics and in screener, screener wins for now
                    # This would need careful mapping for production
                    harmonized_key = key.replace(' ', '_').replace('%', 'pct').lower()
                    if value is not None:
                         combined_metrics[harmonized_key] = value

            return AnalysisResult(
                success=True,
                data={
                    "symbol": symbol,
                    "company_profile": profile,
                    "key_metrics": combined_metrics,
                    "screener_ratios": screener_ratios, # Keep separate for specific display if needed
                    "institutional_holders": institutional_holders.to_dict('records') if not institutional_holders.empty else [],
                    "red_flags": red_flags,
                    "positive_signals": positive_signals,
                    "recent_news": recent_news,
                }
            )
        except Exception as e:
            logger.error(f"Error during fundamental analysis for {symbol}: {e}")
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")

        if not result.success:
            st.error(f"Fundamental Analysis Error: {result.error}")
            return
        
        data = result.data
        profile = data["company_profile"]
        metrics = data["key_metrics"]
        red_flags = data["red_flags"]
        positive_signals = data["positive_signals"]
        recent_news = data["recent_news"]
        institutional_holders = data["institutional_holders"]
        screener_ratios = data["screener_ratios"]


        st.subheader("🏢 Company Profile")
        col1, col2 = st.columns(2)
        
        with col1:
            employees = f"{profile['employees']:,}" if isinstance(profile['employees'], (int, float)) else "N/A"
            st.markdown(f"""
            **Name**: {profile['name']}  
            **Sector**: {profile['sector']}  
            **Industry**: {profile['industry']}  
            **Country**: {profile['country']}  
            **Employees**: {employees}
            """)

        with col2:
            st.markdown(f"""
            **Exchange**: {profile['exchange']}  
            **Currency**: {profile['currency']}  
            **Website**: {profile['website']}
            """)
        
        if profile['description'] != 'N/A':
            with st.expander("Company Description"):
                st.write(profile['description'])
        
        st.markdown("---")
        
        # Key metrics (using combined and screener ratios)
        st.subheader("💰 Key Financial Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("**Valuation**")
            st.metric("Market Cap", screener_ratios.get('valuation', {}).get('Market Cap', 'N/A'))
            st.metric("P/E Ratio", f"{metrics.get('pe_ratio', 'N/A'):.2f}" if metrics.get('pe_ratio') else 'N/A')
            st.metric("P/B Ratio", f"{screener_ratios.get('valuation', {}).get('P/B Ratio', 'N/A'):.2f}" if screener_ratios.get('valuation', {}).get('P/B Ratio') else 'N/A')
            st.metric("Dividend Yield", f"{screener_ratios.get('valuation', {}).get('Dividend Yield %', 'N/A'):.2f}%" if screener_ratios.get('valuation', {}).get('Dividend Yield %') else 'N/A')

        with col2:
            st.markdown("**Profitability**")
            st.metric("ROE", f"{screener_ratios.get('profitability', {}).get('ROE %', 'N/A'):.2f}%" if screener_ratios.get('profitability', {}).get('ROE %') else 'N/A')
            st.metric("ROCE", f"{screener_ratios.get('profitability', {}).get('ROCE %', 'N/A'):.2f}%" if screener_ratios.get('profitability', {}).get('ROCE %') else 'N/A')
            st.metric("Profit Margin", f"{metrics.get('profit_margin', 'N/A')*100:.2f}%" if metrics.get('profit_margin') else 'N/A')
        
        with col3:
            st.markdown("**Growth**")
            st.metric("Sales Growth (3Y)", f"{screener_ratios.get('growth', {}).get('Sales Growth (3Yr) %', 'N/A'):.2f}%" if screener_ratios.get('growth', {}).get('Sales Growth (3Yr) %') else 'N/A')
            st.metric("Profit Growth (3Y)", f"{screener_ratios.get('growth', {}).get('Profit Growth (3Yr) %', 'N/A'):.2f}%" if screener_ratios.get('growth', {}).get('Profit Growth (3Yr) %') else 'N/A')
            st.metric("Revenue Growth (yfin)", f"{metrics.get('revenue_growth', 'N/A')*100:.2f}%" if metrics.get('revenue_growth') else 'N/A')

        with col4:
            st.markdown("**Financial Health**")
            st.metric("Debt/Equity", f"{metrics.get('debt_to_equity', 'N/A'):.2f}" if metrics.get('debt_to_equity') else 'N/A')
            st.metric("Current Ratio", f"{metrics.get('current_ratio', 'N/A'):.2f}" if metrics.get('current_ratio') else 'N/A')
            st.metric("Promoter Holding", f"{screener_ratios.get('ownership', {}).get('Promoter Holding %', 'N/A'):.2f}%" if screener_ratios.get('ownership', {}).get('Promoter Holding %') else 'N/A')
        
        st.markdown("---")
        
        # Red flags and positives
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🚩 Red Flags")
            
            if red_flags:
                for flag in red_flags:
                    severity_color = {
                        'high': 'red',
                        'medium': 'orange',
                        'low': 'gray'
                    }.get(flag['severity'], 'gray')
                    
                    st.markdown(f"""
                    <span style='color:{severity_color}'>**{flag['flag']}**</span>  
                    *{flag['description']}*
                    """, unsafe_allow_html=True)
            else:
                st.success("No major red flags detected!")
        
        with col2:
            st.subheader("✅ Positive Signals")
            
            if positive_signals:
                for signal in positive_signals:
                    st.markdown(f"""
                    <span style='color:green'>**{signal['signal']}**</span>  
                    *{signal['description']}*
                    """, unsafe_allow_html=True)
            else:
                st.info("No standout positive signals")
        
        st.markdown("---")

        # Institutional Holders
        st.subheader("Institutional Holdings")
        if institutional_holders:
            holders_df = pd.DataFrame(institutional_holders)
            # Display top 10 holders
            render_aggrid(holders_df.head(10), height=200)
        else:
            st.info("No institutional holder data available.")
        
        st.markdown("---")
        
        # Recent news
        st.subheader("📰 Recent News")
        
        if recent_news:
            for item in recent_news[:5]:
                st.markdown(f"""
                **{item['date'].strftime('%Y-%m-%d')}**: [{item['title']}]({item['link']})  
                *{item['publisher']}*
                """)
        else:
            st.info("No recent news found")
