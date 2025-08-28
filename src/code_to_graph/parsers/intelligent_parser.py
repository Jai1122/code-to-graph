"""
Intelligent parser that automatically selects the best parser for each language.
Uses Go native analysis for Go code and Tree-sitter for other languages.
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import time

from ..core.models import Entity, Relationship
from ..core.config import settings
from .tree_sitter_parser import TreeSitterParser
from .go_native_parser import GoNativeParser, GoNativeParserFactory

logger = logging.getLogger(__name__)


class IntelligentParser:
    """
    Intelligent parser that selects the best parser for each language.
    
    Parser Selection Strategy:
    - Go: Go Native Parser (superior analysis) > Tree-sitter (fallback)
    - Other languages: Tree-sitter
    """
    
    def __init__(self, enable_tree_sitter: bool = None):
        """
        Initialize intelligent parser.
        
        Args:
            enable_tree_sitter: Enable Tree-sitter parsing
        """
        self.enable_tree_sitter = enable_tree_sitter if enable_tree_sitter is not None else settings.processing.enable_tree_sitter
        
        # Initialize available parsers
        self.parsers = self._initialize_parsers()
        
        # Log parser availability
        self._log_parser_status()
    
    def _initialize_parsers(self) -> Dict[str, Any]:
        """Initialize and configure available parsers."""
        parsers = {}
        
        # Initialize Go native parser
        if self._should_use_go_native():
            go_parser = GoNativeParserFactory.create_parser()
            if go_parser:
                parsers['go_native'] = go_parser
                logger.info("✅ Go Native Parser available - will use for Go repositories")
            else:
                logger.info("❌ Go Native Parser not available - falling back to Tree-sitter for Go")
        
        # Initialize Tree-sitter parser
        if self.enable_tree_sitter:
            try:
                parsers['tree_sitter'] = TreeSitterParser()
                logger.info("✅ Tree-sitter Parser available")
            except Exception as e:
                logger.warning(f"❌ Tree-sitter Parser initialization failed: {e}")
        
        return parsers
    
    def _should_use_go_native(self) -> bool:
        """Determine if Go native parser should be used."""
        # Check if Go native parsing is explicitly disabled
        if hasattr(settings.processing, 'enable_go_native'):
            return settings.processing.enable_go_native
        
        # Default: use Go native if available
        return True
    
    def _log_parser_status(self):
        """Log the status of all parsers."""
        logger.info("🧠 Intelligent Parser Configuration:")
        logger.info(f"  📊 Go Native:   {'✅ Available' if 'go_native' in self.parsers else '❌ Not available'}")
        logger.info(f"  🌳 Tree-sitter: {'✅ Enabled' if 'tree_sitter' in self.parsers else '❌ Disabled'}")
    
    def select_parser_for_language(self, language: str) -> Optional[Any]:
        """
        Select the best parser for a given language.
        
        Args:
            language: Programming language (go, java, python, etc.)
            
        Returns:
            Best available parser for the language, or None if no parser available
        """
        language = language.lower()
        
        if language == "go":
            # For Go: Native > Tree-sitter
            if 'go_native' in self.parsers:
                logger.debug("Selected Go Native Parser for Go code")
                return self.parsers['go_native']
            elif 'tree_sitter' in self.parsers:
                logger.debug("Selected Tree-sitter Parser for Go code (fallback)")
                return self.parsers['tree_sitter']
        else:
            # For other languages: Tree-sitter only
            if 'tree_sitter' in self.parsers:
                logger.debug(f"Selected Tree-sitter Parser for {language} code")
                return self.parsers['tree_sitter']
        
        logger.warning(f"No suitable parser available for language: {language}")
        return None
    
    def detect_primary_language(self, repo_path: Path) -> str:
        """
        Detect the primary programming language of a repository.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Primary language name (lowercase)
        """
        # Count files by extension
        language_counts = {}
        
        # Common language extensions
        extension_map = {
            '.go': 'go',
            '.java': 'java',
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.php': 'php',
            '.rs': 'rust',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.swift': 'swift',
        }
        
        try:
            for ext, lang in extension_map.items():
                files = list(repo_path.rglob(f"*{ext}"))
                if files:
                    language_counts[lang] = len(files)
            
            if language_counts:
                primary_language = max(language_counts, key=language_counts.get)
                logger.info(f"Detected primary language: {primary_language} ({language_counts[primary_language]} files)")
                return primary_language
            
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
        
        logger.info("Could not detect primary language, defaulting to 'unknown'")
        return "unknown"
    
    def parse_repository(self, repo_path: Path, **kwargs) -> Tuple[List[Entity], List[Relationship]]:
        """
        Parse a repository using the most appropriate parser.
        
        Args:
            repo_path: Path to repository
            **kwargs: Additional parsing options
            
        Returns:
            Tuple of (entities, relationships)
        """
        start_time = time.time()
        
        # Detect primary language
        primary_language = kwargs.get('language') or self.detect_primary_language(repo_path)
        
        # Select best parser
        parser = self.select_parser_for_language(primary_language)
        if not parser:
            logger.error(f"No parser available for language: {primary_language}")
            return [], []
        
        parser_name = self._get_parser_name(parser)
        logger.info(f"🚀 Parsing {repo_path} using {parser_name}")
        
        try:
            # Use the selected parser
            if hasattr(parser, 'parse_repository'):
                # Direct repository parsing (Go native, etc.)
                entities, relationships = parser.parse_repository(repo_path, **kwargs)
            else:
                # Chunk-based parsing (Tree-sitter)
                entities, relationships = self._parse_with_chunk_parser(parser, repo_path, **kwargs)
            
            duration = time.time() - start_time
            logger.info(f"✅ Parsing completed in {duration:.2f}s: {len(entities)} entities, {len(relationships)} relationships")
            
            return entities, relationships
            
        except Exception as e:
            logger.error(f"❌ Parsing failed with {parser_name}: {e}")
            
            # Try fallback parser if available
            fallback_parser = self._get_fallback_parser(primary_language, parser)
            if fallback_parser:
                logger.info(f"🔄 Attempting fallback to {self._get_parser_name(fallback_parser)}")
                try:
                    if hasattr(fallback_parser, 'parse_repository'):
                        return fallback_parser.parse_repository(repo_path, **kwargs)
                    else:
                        return self._parse_with_chunk_parser(fallback_parser, repo_path, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback parser also failed: {fallback_error}")
            
            # Return empty results if all parsers fail
            logger.error("❌ All parsers failed, returning empty results")
            return [], []
    
    def _parse_with_chunk_parser(self, parser, repo_path: Path, **kwargs) -> Tuple[List[Entity], List[Relationship]]:
        """
        Parse repository using chunk-based parser (Tree-sitter) with proper exclusions.
        
        Args:
            parser: Parser instance
            repo_path: Repository path
            **kwargs: Additional options
            
        Returns:
            Tuple of (entities, relationships)
        """
        from ..processors.repository_analyzer import RepositoryAnalyzer
        
        if isinstance(parser, TreeSitterParser):
            # Extract exclusion patterns from kwargs
            exclude_patterns = kwargs.get('exclude_patterns', [])
            
            # Use RepositoryAnalyzer for proper file discovery with exclusions
            analyzer = RepositoryAnalyzer(
                repo_path, 
                enable_tree_sitter=True,
                exclusion_patterns=exclude_patterns
            )
            
            # Get discovered files through the proper exclusion pipeline
            processor = analyzer.processor
            files = processor.discover_files(force_refresh=True)
            
            logger.info(f"Discovered {len(files)} files for Tree-sitter parsing after exclusions")
            
            entities = []
            relationships = []
            
            # Parse each discovered file
            for file_info in files:
                try:
                    file_entities, file_relationships = parser.parse_file(file_info)
                    entities.extend(file_entities)
                    relationships.extend(file_relationships)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse file {file_info.path}: {e}")
            
            return entities, relationships
        
        # For other parsers, return empty for now
        logger.warning("Chunk-based parsing not fully implemented for this parser type")
        return [], []
    
    def _get_language_from_extension(self, extension: str) -> str:
        """Get language name from file extension."""
        mapping = {
            '.go': 'go',
            '.java': 'java', 
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp'
        }
        return mapping.get(extension, 'unknown')
    
    def _get_parser_name(self, parser) -> str:
        """Get human-readable parser name."""
        if isinstance(parser, GoNativeParser):
            return "Go Native Parser"
        elif isinstance(parser, TreeSitterParser):
            return "Tree-sitter Parser"
        else:
            return type(parser).__name__
    
    def _get_fallback_parser(self, language: str, current_parser) -> Optional[Any]:
        """
        Get fallback parser if current parser fails.
        
        Args:
            language: Programming language
            current_parser: Currently failed parser
            
        Returns:
            Fallback parser or None
        """
        if language == "go":
            if isinstance(current_parser, GoNativeParser) and 'tree_sitter' in self.parsers:
                return self.parsers['tree_sitter']
        
        return None
    
    def get_parser_info(self) -> Dict[str, Any]:
        """Get information about available parsers."""
        info = {
            "intelligent_parser": {
                "description": "Automatically selects best parser for each language",
                "strategy": {
                    "go": "Go Native > Tree-sitter",
                    "other_languages": "Tree-sitter"
                }
            },
            "available_parsers": {}
        }
        
        for parser_type, parser in self.parsers.items():
            if hasattr(parser, 'get_parser_info'):
                info["available_parsers"][parser_type] = parser.get_parser_info()
            else:
                info["available_parsers"][parser_type] = {
                    "name": self._get_parser_name(parser),
                    "available": True
                }
        
        return info
    
    def get_supported_languages(self) -> List[str]:
        """Get list of all supported languages across all parsers."""
        languages = set()
        
        for parser in self.parsers.values():
            if hasattr(parser, 'get_supported_languages'):
                languages.update(parser.get_supported_languages())
        
        return sorted(list(languages))


class IntelligentParserFactory:
    """Factory for creating intelligent parser instances."""
    
    @staticmethod
    def create_parser(enable_tree_sitter: bool = None) -> IntelligentParser:
        """
        Create an intelligent parser instance.
        
        Args:
            enable_tree_sitter: Enable Tree-sitter parsing
            
        Returns:
            Configured intelligent parser
        """
        return IntelligentParser(enable_tree_sitter=enable_tree_sitter)
    
    @staticmethod
    def create_go_optimized_parser() -> IntelligentParser:
        """
        Create an intelligent parser optimized for Go repositories.
        
        Returns:
            Go-optimized parser instance
        """
        parser = IntelligentParser(enable_tree_sitter=True)
        logger.info("🐹 Created Go-optimized parser (Go Native + Tree-sitter fallback)")
        return parser