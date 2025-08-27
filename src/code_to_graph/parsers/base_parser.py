"""Base parser interface for all code parsers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from ..core.models import Entity, Relationship


class BaseParser(ABC):
    """Base class for all code parsers."""
    
    @abstractmethod
    def parse_repository(self, repo_path: Path, **kwargs) -> Tuple[List[Entity], List[Relationship]]:
        """Parse a repository and return entities and relationships.
        
        Args:
            repo_path: Path to the repository
            **kwargs: Additional parsing options
            
        Returns:
            Tuple of (entities, relationships)
        """
        pass
    
    @abstractmethod
    def get_parser_info(self) -> Dict[str, Any]:
        """Get information about this parser.
        
        Returns:
            Dictionary with parser information
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this parser is available and working.
        
        Returns:
            True if parser is available, False otherwise
        """
        pass
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages.
        
        Returns:
            List of supported language names
        """
        return []
    
    def parse_file(self, file_path: Path, **kwargs) -> Tuple[List[Entity], List[Relationship]]:
        """Parse a single file.
        
        Args:
            file_path: Path to the file to parse
            **kwargs: Additional parsing options
            
        Returns:
            Tuple of (entities, relationships)
        """
        # Default implementation - can be overridden
        return [], []