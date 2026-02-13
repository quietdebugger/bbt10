# 🔌 Plugin Development Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [Plugin Structure](#plugin-structure)
3. [Example Plugins](#example-plugins)
4. [Best Practices](#best-practices)
5. [Testing](#testing)

---

## Quick Start

### Step 1: Create Plugin File

```python
# my_plugin.py

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin
import streamlit as st

@register_plugin
class MyPlugin(AnalysisPlugin):
    @property
    def name(self) -> str:
        return "My Feature"
    
    @property
    def icon(self) -> str:
        return "🚀"
    
    @property
    def description(self) -> str:
        return "Description of what this does"
    
    @property
    def category(self) -> str:
        return "market"  # 'market', 'macro', 'asset', 'sentiment'
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        try:
            # Your analysis logic here
            result_data = {'value': 123}
            
            return AnalysisResult(
                success=True,
                data=result_data
            )
        except Exception as e:
            return AnalysisResult(
                success=False,
                data={},
                error=str(e)
            )
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.error(f"Error: {result.error}")
            return
        
        st.subheader(f"{self.icon} {self.name}")
        st.write(result.data)
```

### Step 2: Import in App

```python
# app_modular.py

from plugins_core import *
from plugins_advanced import *
from my_plugin import *  # Your new plugin
```

### Step 3: Run

```bash
streamlit run app_modular.py
```

Your plugin now appears in the sidebar! ✅

---

## Plugin Structure

### Required Properties

```python
@property
def name(self) -> str:
    """Display name in UI"""
    return "VIX Analysis"

@property
def icon(self) -> str:
    """Emoji icon"""
    return "😱"

@property
def description(self) -> str:
    """Help text"""
    return "India VIX - Market fear gauge"

@property
def category(self) -> str:
    """Category for grouping"""
    return "market"
    # Options: 'market', 'macro', 'asset', 'sentiment'
```

### Optional Properties

```python
@property
def enabled_by_default(self) -> bool:
    """Should be checked by default?"""
    return True  # Default: True

@property
def requires_config(self) -> List[str]:
    """Required API keys"""
    return ['UPSTOX_API_KEY', 'GEMINI_API_KEY']
    # Default: []
```

### Required Methods

#### analyze()

```python
def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
    """
    Run your analysis
    
    Context contains:
    - symbol: Stock/index symbol (e.g., '^NSEI', 'RELIANCE.NS')
    - upstox_symbol: Upstox format (e.g., 'Nifty 50', 'RELIANCE')
    - date_range: {'start': '2024-01-01', 'end': '2025-01-28'}
    - price_data: pandas DataFrame with OHLCV
    - config: API keys and settings
    
    Returns:
    - AnalysisResult with success, data, error
    """
    try:
        # Access context
        symbol = context.get('symbol')
        price_data = context.get('price_data')
        api_key = context.get('config', {}).get('MY_API_KEY')
        
        # Your logic here
        result = do_analysis(symbol, price_data)
        
        return AnalysisResult(
            success=True,
            data={'result': result}
        )
    
    except Exception as e:
        return AnalysisResult(
            success=False,
            data={},
            error=str(e)
        )
```

#### render()

```python
def render(self, result: AnalysisResult):
    """
    Display results using Streamlit
    
    Args:
        result: AnalysisResult from analyze()
    """
    # Always check success first
    if not result.success:
        st.error(f"{self.name} error: {result.error}")
        return
    
    # Render your UI
    st.subheader(f"{self.icon} {self.name}")
    
    data = result.data
    
    # Use Streamlit components
    st.metric("Value", data['result'])
    st.write("Additional info...")
```

---

## Example Plugins

### Example 1: Simple Data Fetch

```python
@register_plugin
class CryptoPlugin(AnalysisPlugin):
    """Bitcoin price"""
    
    @property
    def name(self) -> str:
        return "Bitcoin Price"
    
    @property
    def icon(self) -> str:
        return "₿"
    
    @property
    def description(self) -> str:
        return "BTC/USD current price"
    
    @property
    def category(self) -> str:
        return "macro"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        import yfinance as yf
        
        try:
            btc = yf.Ticker("BTC-USD")
            data = btc.history(period="1d")
            
            current = data['Close'].iloc[-1]
            
            return AnalysisResult(
                success=True,
                data={'price': current}
            )
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.error(f"Error: {result.error}")
            return
        
        st.subheader(f"{self.icon} {self.name}")
        st.metric("BTC/USD", f"${result.data['price']:,.2f}")
```

### Example 2: API Integration

```python
@register_plugin
class EconomicDataPlugin(AnalysisPlugin):
    """India GDP, inflation from API"""
    
    @property
    def name(self) -> str:
        return "Economic Indicators"
    
    @property
    def icon(self) -> str:
        return "📈"
    
    @property
    def description(self) -> str:
        return "GDP, CPI, policy rate"
    
    @property
    def category(self) -> str:
        return "macro"
    
    @property
    def requires_config(self) -> List[str]:
        return ['ECONOMIC_API_KEY']  # If needed
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        import requests
        
        try:
            # Fetch from API
            api_key = context.get('config', {}).get('ECONOMIC_API_KEY')
            
            response = requests.get(
                "https://api.example.com/india/indicators",
                headers={'Authorization': f'Bearer {api_key}'}
            )
            
            data = response.json()
            
            return AnalysisResult(
                success=True,
                data={
                    'gdp_growth': data['gdp'],
                    'inflation': data['cpi'],
                    'repo_rate': data['repo']
                }
            )
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.warning(f"Economic data: {result.error}")
            return
        
        st.subheader(f"{self.icon} {self.name}")
        
        col1, col2, col3 = st.columns(3)
        
        col1.metric("GDP Growth", f"{result.data['gdp_growth']:.1f}%")
        col2.metric("Inflation (CPI)", f"{result.data['inflation']:.1f}%")
        col3.metric("Repo Rate", f"{result.data['repo_rate']:.2f}%")
```

### Example 3: Complex Analysis

```python
@register_plugin
class SectorRotationPlugin(AnalysisPlugin):
    """Sector performance analysis"""
    
    @property
    def name(self) -> str:
        return "Sector Rotation"
    
    @property
    def icon(self) -> str:
        return "🔄"
    
    @property
    def description(self) -> str:
        return "Top/bottom performing sectors"
    
    @property
    def category(self) -> str:
        return "market"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        import yfinance as yf
        
        try:
            sectors = {
                'IT': '^CNXIT',
                'Bank': '^NSEBANK',
                'Pharma': '^CNXPHARMA',
                'Auto': '^CNXAUTO',
                'FMCG': '^CNXFMCG'
            }
            
            performance = {}
            
            for name, symbol in sectors.items():
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="1mo")
                
                if not data.empty:
                    change = ((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100
                    performance[name] = change
            
            # Sort by performance
            sorted_sectors = sorted(
                performance.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            return AnalysisResult(
                success=True,
                data={
                    'performance': performance,
                    'top_3': sorted_sectors[:3],
                    'bottom_3': sorted_sectors[-3:]
                }
            )
        except Exception as e:
            return AnalysisResult(success=False, data={}, error=str(e))
    
    def render(self, result: AnalysisResult):
        if not result.success:
            st.error(f"Error: {result.error}")
            return
        
        st.subheader(f"{self.icon} {self.name}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Top Performers (1M)**")
            for sector, change in result.data['top_3']:
                st.metric(sector, f"{change:+.2f}%")
        
        with col2:
            st.markdown("**Bottom Performers (1M)**")
            for sector, change in result.data['bottom_3']:
                st.metric(sector, f"{change:+.2f}%")
```

---

## Best Practices

### 1. Error Handling

Always wrap in try-except:

```python
def analyze(self, context):
    try:
        # Your code
        return AnalysisResult(success=True, data={...})
    except Exception as e:
        logger.error(f"{self.name} failed: {e}", exc_info=True)
        return AnalysisResult(success=False, data={}, error=str(e))
```

### 2. Check Requirements

```python
def analyze(self, context):
    api_key = context.get('config', {}).get('MY_API_KEY')
    
    if not api_key:
        return AnalysisResult(
            success=False,
            data={},
            error="API key not configured"
        )
    
    # Continue...
```

### 3. Validate Data

```python
def analyze(self, context):
    price_data = context.get('price_data')
    
    if price_data is None or price_data.empty:
        return AnalysisResult(
            success=False,
            data={},
            error="No price data available"
        )
    
    # Continue...
```

### 4. Use Logging

```python
import logging
logger = logging.getLogger(__name__)

def analyze(self, context):
    logger.info(f"Running {self.name} for {context.get('symbol')}")
    
    try:
        # ...
        logger.info(f"{self.name} completed successfully")
    except Exception as e:
        logger.error(f"{self.name} failed: {e}", exc_info=True)
```

### 5. Cache Results

```python
import time
from datetime import datetime

def analyze(self, context):
    cache_file = f"{self.name}_cache.json"
    
    # Check cache
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        
        # Use if < 1 hour old
        if time.time() - cache['timestamp'] < 3600:
            return AnalysisResult(
                success=True,
                data=cache['data'],
                cached=True
            )
    
    # Fetch fresh
    data = fetch_data()
    
    # Save cache
    with open(cache_file, 'w') as f:
        json.dump({
            'timestamp': time.time(),
            'data': data
        }, f)
    
    return AnalysisResult(success=True, data=data)
```

---

## Testing

### Unit Test

```python
# test_my_plugin.py

import unittest
from my_plugin import MyPlugin

class TestMyPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = MyPlugin()
    
    def test_properties(self):
        self.assertEqual(self.plugin.name, "My Feature")
        self.assertEqual(self.plugin.category, "market")
    
    def test_analyze(self):
        context = {
            'symbol': '^NSEI',
            'price_data': pd.DataFrame(...),
            'config': {}
        }
        
        result = self.plugin.analyze(context)
        
        self.assertTrue(result.success)
        self.assertIn('value', result.data)

if __name__ == '__main__':
    unittest.main()
```

### Integration Test

```bash
# Run app and check plugin appears
streamlit run app_modular.py
```

---

## Plugin Ideas

### Market Category
- [ ] Sector rotation analysis
- [ ] Advance/decline ratio
- [ ] New highs/lows
- [ ] Market breadth momentum

### Macro Category
- [ ] Cryptocurrency prices
- [ ] Economic indicators (GDP, CPI)
- [ ] Central bank decisions
- [ ] FII/DII flows

### Asset Category
- [ ] Technical patterns
- [ ] Pivot points
- [ ] Fibonacci levels
- [ ] Volume profile

### Sentiment Category
- [ ] Social media sentiment
- [ ] Analyst ratings
- [ ] IPO calendar
- [ ] Insider trading

---

## Conclusion

The plugin architecture makes it trivial to add new features:

1. Create plugin class
2. Implement analyze() and render()
3. Add @register_plugin decorator
4. Import in app
5. Done!

**No need to edit existing code. Zero risk of breaking existing features.**

This is production-grade, scalable architecture.
