"""Configuration loader for YAML-based exclusion patterns."""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger


class ConfigLoader:
    """Loads and manages configuration from config.yaml file."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration loader.
        
        Args:
            config_path: Path to config.yaml file. If None, searches in current directory and project root.
        """
        self.config_path = self._find_config_file(config_path)
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _find_config_file(self, config_path: Optional[Path]) -> Optional[Path]:
        """Find the config.yaml file."""
        if config_path and config_path.exists():
            return config_path
        
        # Search in common locations
        search_paths = [
            Path.cwd() / "config.yaml",
            Path(__file__).parent.parent.parent.parent / "config.yaml",  # Project root
            Path.cwd() / "config" / "config.yaml",
            Path(__file__).parent / "config.yaml",
        ]
        
        for path in search_paths:
            if path.exists():
                logger.info(f"Found config file: {path}")
                return path
        
        logger.warning("No config.yaml file found, using default exclusions")
        return None
    
    def _load_config(self):
        """Load configuration from YAML file."""
        if not self.config_path:
            self._config = {}
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            logger.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            self._config = {}
    
    def get_exclusion_directories(self, language: Optional[str] = None) -> List[str]:
        """Get directory exclusion patterns.
        
        Args:
            language: Programming language for language-specific exclusions
            
        Returns:
            List of directory patterns to exclude
        """
        exclusions = []
        
        # General exclusions
        if self._config and 'exclusions' in self._config:
            exclusions.extend(self._config['exclusions'].get('directories', []))
        
        # Language-specific exclusions
        if language and self._config and 'language_exclusions' in self._config:
            lang_config = self._config['language_exclusions'].get(language, {})
            exclusions.extend(lang_config.get('directories', []))
        
        return exclusions
    
    def get_exclusion_file_patterns(self, language: Optional[str] = None) -> List[str]:
        """Get file pattern exclusions.
        
        Args:
            language: Programming language for language-specific exclusions
            
        Returns:
            List of file patterns to exclude
        """
        exclusions = []
        
        # General exclusions
        if self._config and 'exclusions' in self._config:
            exclusions.extend(self._config['exclusions'].get('file_patterns', []))
        
        # Language-specific exclusions
        if language and self._config and 'language_exclusions' in self._config:
            lang_config = self._config['language_exclusions'].get(language, {})
            exclusions.extend(lang_config.get('file_patterns', []))
        
        return exclusions
    
    def get_all_exclusion_patterns(self, language: Optional[str] = None) -> List[str]:
        """Get all exclusion patterns (directories and files) formatted for glob matching.
        
        Args:
            language: Programming language for language-specific exclusions
            
        Returns:
            List of glob patterns to exclude
        """
        patterns = []
        
        # Convert directories to glob patterns
        directories = self.get_exclusion_directories(language)
        for directory in directories:
            # Ensure directory patterns are properly formatted for glob matching
            if not directory.startswith('**/'):
                directory = f"**/{directory}"
            if not directory.endswith('/**'):
                directory = f"{directory}/**"
            patterns.append(directory)
        
        # Add file patterns
        file_patterns = self.get_exclusion_file_patterns(language)
        for pattern in file_patterns:
            # Ensure file patterns work with glob
            if not pattern.startswith('**/') and '/' not in pattern:
                pattern = f"**/{pattern}"
            patterns.append(pattern)
        
        return patterns
    
    def get_visualization_settings(self) -> Dict[str, Any]:
        """Get visualization-specific settings."""
        if not self._config or 'visualization' not in self._config:
            return {}
        
        return self._config['visualization']
    
    def get_analysis_settings(self) -> Dict[str, Any]:
        """Get analysis-specific settings."""
        if not self._config or 'analysis' not in self._config:
            return {}
        
        return self._config['analysis']
    
    def should_hide_external_entities(self) -> bool:
        """Check if external entities should be hidden from visualization."""
        viz_settings = self.get_visualization_settings()
        return viz_settings.get('hide_external_entities', False)
    
    def should_include_tests(self) -> bool:
        """Check if test files should be included in analysis."""
        analysis_settings = self.get_analysis_settings()
        return analysis_settings.get('include_tests', False)
    
    def should_include_generated(self) -> bool:
        """Check if generated files should be included in analysis."""
        analysis_settings = self.get_analysis_settings()
        return analysis_settings.get('include_generated', False)
    
    def get_max_file_size_mb(self) -> int:
        """Get maximum file size to process in MB."""
        analysis_settings = self.get_analysis_settings()
        return analysis_settings.get('max_file_size_mb', 10)
    
    def get_max_entities(self) -> int:
        """Get maximum number of entities to show in visualization."""
        viz_settings = self.get_visualization_settings()
        return viz_settings.get('max_entities', 1000)
    
    def get_max_relationships(self) -> int:
        """Get maximum number of relationships to show in visualization."""
        viz_settings = self.get_visualization_settings()
        return viz_settings.get('max_relationships', 2000)
    
    def reload_config(self):
        """Reload configuration from file."""
        self._load_config()
    
    @property
    def is_loaded(self) -> bool:
        """Check if configuration was successfully loaded."""
        return self._config is not None and len(self._config) > 0
    
    @property
    def config_file_path(self) -> Optional[Path]:
        """Get path to the loaded config file."""
        return self.config_path


# Global config loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """Get the global configuration loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def reload_config():
    """Reload the global configuration."""
    global _config_loader
    if _config_loader:
        _config_loader.reload_config()
    else:
        _config_loader = ConfigLoader()