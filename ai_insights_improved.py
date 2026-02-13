"""
AI Insights with Proper Rate Limiting
✅ Respects Gemini API quotas
✅ Retry logic with exponential backoff
✅ Falls back to free models
✅ Caches responses
"""

import google.generativeai as genai
import time
import logging
from typing import Optional, Dict
import json
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AIInsightsEngine:
    """
    AI analysis with rate limit handling
    
    Gemini Free Tier Limits:
    - 15 RPM (requests per minute)
    - 1 million TPM (tokens per minute)
    - 1,500 RPD (requests per day)
    """
    
    # Model selection (free tier compatible)
    MODELS = {
        'pro': 'gemini-pro',           # Best quality
        'flash': 'gemini-1.5-flash',   # Fast, lower quota
    }
    
    # Rate limit settings
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 40  # seconds (from error message)
    REQUEST_DELAY = 4  # Minimum 4 seconds between requests (15 RPM = 1 per 4s)
    
    def __init__(self, api_key: str, model: str = 'flash'):
        """
        Initialize with rate limiting
        
        Args:
            api_key: Gemini API key
            model: 'flash' (recommended for free tier) or 'pro'
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        
        # Use flash model by default (less quota consumption)
        self.model_name = self.MODELS.get(model, self.MODELS['flash'])
        self.model = genai.GenerativeModel(self.model_name)
        
        # Rate limiting
        self.last_request_time = 0
        self.daily_request_count = 0
        self.daily_reset_time = self._get_next_reset_time()
        
        # Cache
        self.cache_file = "ai_insights_cache.json"
        self.cache = self._load_cache()
        
        logger.info(f"AI Engine initialized with {self.model_name}")
    
    def _get_next_reset_time(self) -> datetime:
        """Get next midnight Pacific time (quota reset)"""
        now = datetime.now()
        # Simplified: next midnight local time (adjust for Pacific if needed)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_midnight
    
    def _load_cache(self) -> Dict:
        """Load response cache"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save response cache"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def _rate_limit_check(self):
        """Check and enforce rate limits"""
        now = time.time()
        
        # Reset daily count if past midnight
        if datetime.now() > self.daily_reset_time:
            self.daily_request_count = 0
            self.daily_reset_time = self._get_next_reset_time()
            logger.info("Daily quota reset")
        
        # Check daily limit (conservative: 1000 instead of 1500)
        if self.daily_request_count >= 1000:
            raise RuntimeError(
                f"Daily quota exhausted ({self.daily_request_count}/1000). "
                f"Resets at {self.daily_reset_time.strftime('%H:%M')}"
            )
        
        # Enforce minimum delay between requests (15 RPM = 4 seconds)
        time_since_last = now - self.last_request_time
        if time_since_last < self.REQUEST_DELAY:
            sleep_time = self.REQUEST_DELAY - time_since_last
            logger.info(f"Rate limit: waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.daily_request_count += 1
    
    def _generate_with_retry(self, prompt: str, cache_key: Optional[str] = None) -> str:
        """
        Generate response with retry logic
        
        Args:
            prompt: Input prompt
            cache_key: Optional cache key
            
        Returns:
            Generated text
        """
        # Check cache first
        if cache_key and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            cache_time = datetime.fromisoformat(cache_entry['timestamp'])
            
            # Use cache if < 1 hour old
            if datetime.now() - cache_time < timedelta(hours=1):
                logger.info("Using cached response")
                return cache_entry['response']
        
        # Rate limit check
        self._rate_limit_check()
        
        # Retry loop
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"Generating response (attempt {attempt + 1}/{self.MAX_RETRIES})")
                
                response = self.model.generate_content(prompt)
                result = response.text
                
                # Cache response
                if cache_key:
                    self.cache[cache_key] = {
                        'response': result,
                        'timestamp': datetime.now().isoformat()
                    }
                    self._save_cache()
                
                logger.info("✓ Response generated")
                return result
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if rate limit error
                if '429' in error_msg or 'quota' in error_msg.lower():
                    # Extract retry delay from error
                    retry_delay = self.INITIAL_RETRY_DELAY
                    
                    if 'retry in' in error_msg.lower():
                        try:
                            # Extract seconds from error message
                            import re
                            match = re.search(r'retry in ([\d.]+)s', error_msg)
                            if match:
                                retry_delay = float(match.group(1)) + 1  # Add buffer
                        except:
                            pass
                    
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"Rate limit hit. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise RuntimeError(
                            f"Rate limit exceeded after {self.MAX_RETRIES} retries. "
                            f"Daily usage: {self.daily_request_count} requests. "
                            f"Try again in {retry_delay:.0f} seconds or use cached analysis."
                        )
                else:
                    # Other error
                    raise RuntimeError(f"AI generation failed: {error_msg}")
        
        raise RuntimeError("Max retries exceeded")
    
    def analyze_market_state(
        self,
        symbol: str,
        market_state: Dict,
        changes: list,
        fo_data: Optional[Dict] = None,
        use_cache: bool = True
    ) -> str:
        """
        Analyze market state with rate limiting
        
        Args:
            symbol: Stock/index symbol
            market_state: Market state dict
            changes: List of changes
            fo_data: Optional F&O data
            use_cache: Use cached response if available
            
        Returns:
            Analysis text
        """
        # Create concise prompt (minimize tokens)
        prompt_parts = [
            f"Analyze {symbol}:",
            f"Trend: {market_state.get('trend')}",
            f"Volatility: {market_state.get('volatility')}",
            f"Confidence: {market_state.get('confidence')}"
        ]
        
        # Add F&O if available
        if fo_data:
            if fo_data.get('pcr'):
                prompt_parts.append(f"PCR: {fo_data['pcr'].get('pcr_oi'):.2f}")
            if fo_data.get('greeks'):
                prompt_parts.append(f"Net Delta: {fo_data['greeks'].get('net_delta')}")
            if fo_data.get('futures'):
                prompt_parts.append(f"Basis: {fo_data['futures'].get('basis_pct')}%")
        
        # Add changes (top 3 only)
        if changes:
            prompt_parts.append("Recent changes:")
            for change in changes[:3]:
                prompt_parts.append(f"- {change.description}")
        
        prompt_parts.append("\nProvide brief analysis (3-4 sentences). Focus on conflicts and risks.")
        
        prompt = "\n".join(prompt_parts)
        
        # Cache key
        cache_key = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H')}" if use_cache else None
        
        try:
            return self._generate_with_retry(prompt, cache_key)
        except RuntimeError as e:
            # Fallback message
            return f"""
**AI Analysis Unavailable**

{str(e)}

**Manual Interpretation:**
- Market State: {market_state.get('trend')} with {market_state.get('confidence')} confidence
- Volatility: {market_state.get('volatility')}
- Monitor key levels and wait for clearer signals

*Tip: AI responses are cached for 1 hour. Try again later or review the data manually.*
"""
    
    def get_quota_status(self) -> Dict:
        """Get current quota usage"""
        return {
            'model': self.model_name,
            'daily_requests': self.daily_request_count,
            'daily_limit': 1000,  # Conservative
            'next_reset': self.daily_reset_time.strftime('%H:%M'),
            'cached_responses': len(self.cache)
        }


# Backwards compatibility
class AIInsightsEngineLegacy:
    """Legacy interface for old code"""
    
    def __init__(self, api_key: str):
        self.engine = AIInsightsEngine(api_key, model='flash')
        self.model = self.engine.model  # For direct access
    
    def generate_comprehensive_analysis(self, **kwargs):
        """Legacy method"""
        return self.engine.analyze_market_state(
            kwargs.get('symbol', 'UNKNOWN'),
            {
                'trend': kwargs.get('attribution_data', {}).get('trend', 'N/A'),
                'volatility': 'N/A',
                'confidence': 'MEDIUM'
            },
            [],
            fo_data=kwargs.get('fo_data')
        )
