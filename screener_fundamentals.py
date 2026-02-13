"""
Screener.in Style Fundamentals
Comprehensive ratios and metrics like screener.in
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
import yfinance as yf
import time

logger = logging.getLogger(__name__)


class ScreenerFundamentals:
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
        
        # Also get yfinance data for backup
        self.ticker = yf.Ticker(f"{self.symbol}.NS")
        self.info = self._safe_get_info()
        
        logger.info(f"ScreenerFundamentals initialized for {self.symbol}")
    
    def _safe_get_info(self) -> Dict:
        """Safely get ticker info"""
        try:
            return self.ticker.info
        except:
            return {}
    
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
                ratios['market_cap'] = market_cap
            
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
    
    def _get_yfinance_fallback(self) -> Dict:
        """Get ratios from yfinance as fallback"""
        ratios = {}
        
        try:
            ratios['market_cap'] = self.info.get('marketCap', 'N/A')
            ratios['pe_ratio'] = self.info.get('trailingPE')
            ratios['book_value'] = self.info.get('bookValue')
            ratios['dividend_yield'] = self.info.get('dividendYield', 0) * 100 if self.info.get('dividendYield') else None
            ratios['roe'] = self.info.get('returnOnEquity', 0) * 100 if self.info.get('returnOnEquity') else None
            ratios['debt_to_equity'] = self.info.get('debtToEquity')
            ratios['eps_ttm'] = self.info.get('trailingEps')
            ratios['sales_growth_3yr'] = self.info.get('revenueGrowth', 0) * 100 if self.info.get('revenueGrowth') else None
            
            logger.info("Using yfinance data as fallback")
            
        except Exception as e:
            logger.error(f"yfinance fallback failed: {e}")
        
        return ratios
    
    def get_quarterly_results(self) -> pd.DataFrame:
        """Get quarterly results table from screener.in"""
        try:
            response = self.session.get(self.screener_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find quarterly results table
            tables = soup.find_all('table', class_='data-table')
            
            for table in tables:
                caption = table.find('caption')
                if caption and 'Quarterly Results' in caption.get_text():
                    df = pd.read_html(str(table))[0]
                    return df
            
            logger.warning("Quarterly results table not found")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Quarterly results fetch failed: {e}")
            return pd.DataFrame()
    
    def get_annual_results(self) -> pd.DataFrame:
        """Get annual results from screener.in"""
        try:
            response = self.session.get(self.screener_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find annual results table
            tables = soup.find_all('table', class_='data-table')
            
            for table in tables:
                caption = table.find('caption')
                if caption and 'Profit & Loss' in caption.get_text():
                    df = pd.read_html(str(table))[0]
                    return df
            
            logger.warning("Annual results table not found")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Annual results fetch failed: {e}")
            return pd.DataFrame()
    
    def get_comprehensive_ratios(self) -> Dict:
        """
        Get all ratios in one call
        
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


def get_screener_style_ratios(symbol: str) -> Dict:
    """
    Convenience function to get screener.in style ratios
    
    Args:
        symbol: Stock symbol (e.g., 'RELIANCE')
        
    Returns:
        Dict with comprehensive ratios
    """
    screener = ScreenerFundamentals(symbol)
    return screener.get_comprehensive_ratios()
