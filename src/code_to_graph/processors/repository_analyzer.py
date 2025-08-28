"""Main repository analyzer that orchestrates the analysis pipeline."""

from pathlib import Path
from typing import List, Optional, Dict, Any
import time

from loguru import logger
from pydantic import BaseModel

from .chunked_processor import ChunkedRepositoryProcessor, Chunk
from ..parsers.intelligent_parser import IntelligentParserFactory
from ..core.models import Entity, Relationship
from ..core.config import settings


class AnalysisResult(BaseModel):
    """Results from repository analysis."""
    
    repository_path: str
    total_files: int
    total_chunks: int
    total_entities: int
    total_relations: int
    processing_time: float
    language_breakdown: Dict[str, int]
    entity_breakdown: Dict[str, int]
    relation_breakdown: Dict[str, int]
    chunks_processed: List[str]


class RepositoryAnalyzer:
    """Main analyzer that coordinates the repository analysis pipeline."""
    
    def __init__(
        self,
        repo_path: Path,
        enable_tree_sitter: bool = None,
        chunk_size: Optional[int] = None,
        chunk_strategy: Optional[str] = None,
        exclusion_patterns: Optional[List[str]] = None
    ):
        """Initialize the repository analyzer.
        
        Args:
            repo_path: Path to repository to analyze
            enable_tree_sitter: Enable Tree-sitter parsing
            chunk_size: Override chunk size
            chunk_strategy: Override chunk strategy
            exclusion_patterns: Custom exclusion patterns
        """
        self.repo_path = repo_path
        
        # Initialize components
        self.processor = ChunkedRepositoryProcessor(repo_path, exclusion_patterns=exclusion_patterns)
        self.parser = IntelligentParserFactory.create_parser(
            enable_tree_sitter=enable_tree_sitter
        )
        
        # Override settings if provided
        if chunk_size:
            settings.processing.max_chunk_size = chunk_size
        if chunk_strategy:
            settings.processing.chunk_strategy = chunk_strategy
        
        logger.info(f"Initialized repository analyzer for {repo_path}")
    
    def analyze(self, force_refresh: bool = False) -> AnalysisResult:
        """Perform complete repository analysis.
        
        Args:
            force_refresh: Force rediscovery of files
            
        Returns:
            Analysis results
        """
        start_time = time.time()
        
        logger.info(f"Starting analysis of {self.repo_path}")
        
        # Discover files
        files = self.processor.discover_files(force_refresh=force_refresh)
        if not files:
            raise ValueError(f"No source files found in {self.repo_path}")
        
        logger.info(f"Found {len(files)} source files")
        
        # Create chunks
        chunks = self.processor.create_chunks(files)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Process chunks
        all_entities = []
        all_relations = []
        chunks_processed = []
        
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)}: {chunk.id}")
            
            try:
                entities, relations = self.parser.parse_repository(chunk.path)
                
                all_entities.extend(entities)
                all_relations.extend(relations)
                chunks_processed.append(chunk.id)
                
                logger.info(f"Chunk {chunk.id}: {len(entities)} entities, {len(relations)} relations")
                
            except Exception as e:
                logger.error(f"Failed to process chunk {chunk.id}: {e}")
                continue
        
        processing_time = time.time() - start_time
        
        # Compile statistics
        language_breakdown = self._get_language_breakdown(files)
        entity_breakdown = self._get_entity_breakdown(all_entities)
        relation_breakdown = self._get_relation_breakdown(all_relations)
        
        result = AnalysisResult(
            repository_path=str(self.repo_path),
            total_files=len(files),
            total_chunks=len(chunks),
            total_entities=len(all_entities),
            total_relations=len(all_relations),
            processing_time=processing_time,
            language_breakdown=language_breakdown,
            entity_breakdown=entity_breakdown,
            relation_breakdown=relation_breakdown,
            chunks_processed=chunks_processed
        )
        
        logger.info(f"Analysis completed in {processing_time:.2f}s: {result}")
        
        return result
    
    def _get_language_breakdown(self, files) -> Dict[str, int]:
        """Get breakdown of files by language."""
        breakdown = {}
        for file_info in files:
            lang = file_info.language
            breakdown[lang] = breakdown.get(lang, 0) + 1
        return breakdown
    
    def _get_entity_breakdown(self, entities: List[Entity]) -> Dict[str, int]:
        """Get breakdown of entities by type."""
        breakdown = {}
        for entity in entities:
            entity_type = entity.type
            breakdown[entity_type] = breakdown.get(entity_type, 0) + 1
        return breakdown
    
    def _get_relation_breakdown(self, relations: List[Relationship]) -> Dict[str, int]:
        """Get breakdown of relations by type."""
        breakdown = {}
        for relation in relations:
            rel_type = relation.relation_type
            breakdown[rel_type] = breakdown.get(rel_type, 0) + 1
        return breakdown