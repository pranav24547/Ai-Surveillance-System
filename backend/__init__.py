"""
Smart Surveillance System - Backend Package
"""
from .config import Config, get_config, reload_config, load_config

__version__ = "1.0.0"
__all__ = ["Config", "get_config", "reload_config", "load_config"]
