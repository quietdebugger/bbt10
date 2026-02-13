"""
Honest Market Plugins
Implements 'Change Detection' and 'Market State' from bbt8
Focuses on tracking changes rather than absolute values
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

from architecture_modular import AnalysisPlugin, AnalysisResult, register_plugin

logger = logging.getLogger(__name__)

# --- Ported Logic from bbt8/change_detection.py ---

@dataclass
class MarketSnapshot:
    """Snapshot of market state"""
    timestamp: str
    symbol: str
    price: float
    # Simplified snapshot for plugin
    volume_avg: float
    rsi: Optional[float] = None
    pcr: Optional[float] = None

@dataclass
class Change:
    category: str
    description: str
    significance: str
    direction: str

class ChangeDetector:
    """Detects what changed since last run"""
    SNAPSHOT_FILE = "bbt10_snapshots.json"
    
    def __init__(self):
        self.snapshots = self._load_snapshots()
    
    def _load_snapshots(self) -> Dict:
        if os.path.exists(self.SNAPSHOT_FILE):
            try:
                with open(self.SNAPSHOT_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_snapshots(self):
        with open(self.SNAPSHOT_FILE, 'w') as f:
            json.dump(self.snapshots, f, indent=2)
    
    def save_snapshot(self, snapshot: MarketSnapshot):
        self.snapshots[snapshot.symbol] = asdict(snapshot)
        self._save_snapshots()
    
    def get_changes(self, current: MarketSnapshot) -> List[Change]:
        prev_data = self.snapshots.get(current.symbol)
        if not prev_data:
            return [Change("INFO", "First run - no history", "LOW", "NEUTRAL")]
        
        changes = []
        
        # Price Change
        prev_price = prev_data.get('price')
        if prev_price:
            pct = ((current.price - prev_price) / prev_price) * 100
            if abs(pct) > 1.5:
                direction = "BULLISH" if pct > 0 else "BEARISH"
                sig = "HIGH" if abs(pct) > 3 else "MEDIUM"
                changes.append(Change("PRICE", f"Price moved {pct:+.1f}% (₹{prev_price:.0f} -> ₹{current.price:.0f})", sig, direction))
        
        # Volume Change
        prev_vol = prev_data.get('volume_avg')
        if prev_vol and current.volume_avg:
            vol_pct = ((current.volume_avg - prev_vol) / prev_vol) * 100
            if abs(vol_pct) > 20:
                changes.append(Change("VOLUME", f"Volume trend changed {vol_pct:+.0f}%", "MEDIUM", "NEUTRAL"))
                
        # PCR Change
        prev_pcr = prev_data.get('pcr')
        if prev_pcr and current.pcr:
            pcr_diff = current.pcr - prev_pcr
            if abs(pcr_diff) > 0.2:
                direction = "BULLISH" if pcr_diff < 0 else "BEARISH" # Falling PCR often bullish contrarian? Or rising puts bearish? 
                # Standard: High PCR = Bearish puts, Low PCR = Bullish calls? 
                # Actually High PCR (>1) = Oversold/Bullish, Low (<0.6) = Overbought/Bearish
                # Let's stick to simple change: "PCR Rose/Fell"
                changes.append(Change("OPTIONS", f"PCR changed {pcr_diff:+.2f} ({prev_pcr:.2f} -> {current.pcr:.2f})", "MEDIUM", "NEUTRAL"))

        return changes

@register_plugin
class ChangeDetectionPlugin(AnalysisPlugin):
    """
    Tracks market changes since last session
    """
    @property
    def name(self) -> str:
        return "Change Detection"
    
    @property
    def icon(self) -> str:
        return "🔄"
    
    @property
    def description(self) -> str:
        return "Tracks significant changes (Price, Volume, PCR) since last run"
    
    @property
    def category(self) -> str:
        return "market"
    
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        symbol = context.get('symbol')
        price_data = context.get('price_data')
        
        if not symbol or price_data is None:
            return AnalysisResult(success=False, data={}, error="Missing data")
            
        # Get latest metrics
        price = price_data['close'].iloc[-1]
        volume_avg = price_data['volume'].iloc[-20:].mean()
        
        # Try to get PCR if available (from context or previous plugins)
        # In modular app, context is shared. If Options plugin ran, we might have it?
        # For now, we'll leave it simple or rely on independent fetch if critical
        pcr = None # Placeholder for now
        
        snapshot = MarketSnapshot(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            price=price,
            volume_avg=volume_avg,
            pcr=pcr
        )
        
        detector = ChangeDetector()
        changes = detector.get_changes(snapshot)
        detector.save_snapshot(snapshot)
        
        return AnalysisResult(success=True, data={'changes': changes, 'snapshot': asdict(snapshot)})

    def render(self, result: AnalysisResult):
        st.subheader(f"{self.icon} {self.name}")
        
        if not result.success:
            st.warning("Change detection failed")
            return
            
        changes = result.data.get('changes', [])
        if not changes:
            st.info("No significant changes detected since last run.")
            return
            
        for change in changes:
            icon = "🔴" if change.significance == "HIGH" else "🟡"
            st.markdown(f"{icon} **{change.category}**: {change.description}")
