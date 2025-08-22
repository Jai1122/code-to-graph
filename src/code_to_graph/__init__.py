"""CodeToGraph: Scalable repository analysis and graph database system."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.config import Settings, settings
from .core.logger import setup_logging

__all__ = ["Settings", "settings", "setup_logging"]