"""
Modular Plugin Architecture
✅ Add features without touching existing code
✅ Each feature is independent module
✅ Enable/disable via checkboxes
✅ Easy to extend
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import pandas as pd


@dataclass
class AnalysisResult:
    """Standard result format for all plugins"""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    cached: bool = False
    timestamp: Optional[str] = None


class AnalysisPlugin(ABC):
    """Base class for all analysis plugins"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name for UI"""
        pass
    
    @property
    @abstractmethod
    def icon(self) -> str:
        """Icon for UI (emoji)"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """What this plugin does"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> str:
        """Category: 'market', 'asset', 'macro', 'sentiment'"""
        pass
    
    @property
    def enabled_by_default(self) -> bool:
        """Should be checked by default"""
        return True
    
    @property
    def requires_config(self) -> List[str]:
        """List of config keys required (e.g., ['api_key'])"""
        return []
    
    @abstractmethod
    def analyze(self, context: Dict[str, Any]) -> AnalysisResult:
        """
        Run analysis
        
        Args:
            context: Shared context (symbol, date_range, price_data, etc.)
            
        Returns:
            AnalysisResult with data or error
        """
        pass
    
    @abstractmethod
    def render(self, result: AnalysisResult) -> None:
        """
        Render results in Streamlit
        
        Args:
            result: Analysis result from analyze()
        """
        pass


class PluginRegistry:
    """Registry for all plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, AnalysisPlugin] = {}
        self.categories: Dict[str, List[str]] = {}
    
    def register(self, plugin: AnalysisPlugin):
        """Register a plugin"""
        name = plugin.name
        self.plugins[name] = plugin
        
        # Add to category
        category = plugin.category
        if category not in self.categories:
            self.categories[category] = []
            
        if name not in self.categories[category]:
            self.categories[category].append(name)
    
    def get_plugin(self, name: str) -> Optional[AnalysisPlugin]:
        """Get plugin by name"""
        return self.plugins.get(name)
    
    def get_by_category(self, category: str) -> List[AnalysisPlugin]:
        """Get all plugins in category"""
        names = self.categories.get(category, [])
        return [self.plugins[name] for name in names]
    
    def get_all(self) -> List[AnalysisPlugin]:
        """Get all plugins"""
        return list(self.plugins.values())
    
    def get_enabled_defaults(self) -> List[str]:
        """Get plugins enabled by default"""
        return [name for name, p in self.plugins.items() if p.enabled_by_default]


# Global registry
REGISTRY = PluginRegistry()


def register_plugin(plugin_class):
    """Decorator to auto-register plugins"""
    plugin = plugin_class()
    REGISTRY.register(plugin)
    return plugin_class
