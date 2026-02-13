"""
Screener & Announcements Plugin
Fetches company announcements, PDF filings, and advanced fundamentals
Borrowed from bbt7
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
import logging
import streamlit as st
import json

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin

logger = logging.getLogger(__name__)

class CompanyAnnouncements:
    """
    Fetch company announcements and PDF filings (Screener.in, BSE, NSE)
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol.replace('.NS', '').upper()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.bse_code = self._get_bse_code()
        
    def _get_bse_code(self) -> str:
        # Simplified mapping. In a real app, use a DB or API lookup.
        # This is a fallback for common stocks.
        mapping = {
            'RELIANCE': '500325', 'TCS': '532540', 'HDFCBANK': '500180',
            'INFY': '500209', 'ICICIBANK': '532174', 'HINDUNILVR': '500696',
            'ITC': '500875', 'SBIN': '500112', 'BAJFINANCE': '500034'
        }
        return mapping.get(self.symbol, '')

    def get_screener_announcements(self, max_items: int = 20) -> List[Dict]:
        announcements = []
        try:
            url = f"https://www.screener.in/company/{self.symbol}/consolidated/"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                section = soup.find('section', {'id': 'documents'}) # Screener often puts these in documents or announcements
                
                # Try specific announcements list
                items = soup.find_all('li', class_='announcement')
                
                if not items:
                     # Fallback to links in documents section
                     if section:
                         items = section.find_all('li')

                for item in items[:max_items]:
                    try:
                        text = item.get_text(strip=True)
                        link_elem = item.find('a')
                        link = link_elem['href'] if link_elem else None
                        if link and not link.startswith('http'):
                            link = f"https://www.screener.in{link}"
                            
                        # Extract date if possible (often just text)
                        date_elem = item.find('div', class_='ink-600')
                        date_str = date_elem.get_text(strip=True) if date_elem else None
                        
                        announcements.append({
                            'text': text,
                            'link': link,
                            'date_str': date_str,
                            'source': 'Screener.in'
                        })
                    except: continue
        except Exception as e:
            logger.error(f"Screener announcements failed: {e}")
        return announcements

    def get_bse_announcements(self, max_items: int = 10) -> List[Dict]:
        if not self.bse_code: return []
        announcements = []
        try:
            url = f"https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?security_code={self.bse_code}&strCat=-1&strSubCat=-1"
            # BSE API is tricky with headers
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = self.session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('Table', [])[:max_items]:
                    head = item.get('HEADLINE', '')
                    date = item.get('NEWS_DT', '')
                    pdf = item.get('ATTACHMENTNAME', '')
                    pdf_url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{pdf}" if pdf else None
                    
                    announcements.append({
                        'text': head,
                        'date_str': date,
                        'link': pdf_url,
                        'source': 'BSE'
                    })
        except: pass
        return announcements

    def get_all(self) -> List[Dict]:
        # Combine sources
        all_anns = self.get_screener_announcements()
        all_anns.extend(self.get_bse_announcements())
        return all_anns

@register_plugin
class AnnouncementsPlugin(AnalysisPlugin):
    """
    Company filings and announcements (PDFs)
    """
    @property
    def name(self) -> str:
        return "Company Filings"
    
    @property
    def icon(self) -> str:
        return "📄"
    
    @property
    def description(self) -> str:
        return "Official announcements and PDF filings (BSE/Screener)"
    
    @property
    def category(self) -> str:
        return "sentiment"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        symbol = context.get('symbol')
        if not symbol or '^' in symbol:
            return AnalysisResult(success=False, data={}, error="Filings only for companies")
            
        try:
            fetcher = CompanyAnnouncements(symbol)
            anns = fetcher.get_all()
            return AnalysisResult(success=True, data={'announcements': anns})
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.info(result.error)
            return
            
        anns = result.data.get('announcements', [])
        if not anns:
            st.info("No recent filings found.")
            return
            
        for ann in anns[:10]:
            with st.expander(f"{ann.get('date_str', 'Unknown Date')} - {ann['text'][:80]}..."):
                st.markdown(f"**Source**: {ann['source']}")
                st.markdown(f"**Full Text**: {ann['text']}")
                if ann.get('link'):
                    st.markdown(f"🔗 [View Document]({ann['link']})")
