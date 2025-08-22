"""Hybrid parser combining Tree-sitter and Joern for optimal performance and accuracy."""

from typing import Dict, List, Tuple, Optional
from pathlib import Path
import time

from loguru import logger
from pydantic import BaseModel

from ..processors.chunked_processor import Chunk
from .tree_sitter_parser import TreeSitterParser, ParsedEntity as TSEntity, ParsedRelation as TSRelation
from .joern_parser import JoernParser, JoernEntity, JoernRelation
from ..core.config import settings


class HybridEntity(BaseModel):
    """Unified entity representation from hybrid parsing."""
    
    id: str
    name: str
    type: str
    start_line: int
    end_line: int
    file_path: str
    language: str
    
    # Tree-sitter specific
    ts_parent: Optional[str] = None
    ts_children: List[str] = []
    ts_metadata: Dict = {}
    
    # Joern specific
    joern_id: Optional[str] = None
    full_name: Optional[str] = None
    signature: Optional[str] = None
    code: Optional[str] = None
    joern_properties: Dict = {}
    
    # Combined metadata
    confidence_score: float = 1.0  # How confident we are in this entity
    source_parsers: List[str] = []  # Which parsers contributed to this entity


class HybridRelation(BaseModel):
    """Unified relationship representation from hybrid parsing."""
    
    source_id: str
    target_id: str
    relation_type: str
    
    # Tree-sitter specific
    ts_metadata: Dict = {}
    
    # Joern specific  
    joern_edge_type: Optional[str] = None
    joern_properties: Dict = {}
    
    # Combined metadata
    confidence_score: float = 1.0
    source_parsers: List[str] = []
    line_number: Optional[int] = None


class HybridParser:
    """Hybrid parser that combines Tree-sitter and Joern for optimal results."""
    
    def __init__(self, enable_tree_sitter: bool = None, enable_joern: bool = None):
        """Initialize hybrid parser.
        
        Args:
            enable_tree_sitter: Enable Tree-sitter parsing
            enable_joern: Enable Joern CPG parsing
        """
        self.enable_tree_sitter = enable_tree_sitter if enable_tree_sitter is not None else settings.processing.enable_tree_sitter
        self.enable_joern = enable_joern if enable_joern is not None else settings.processing.enable_joern
        
        # Initialize parsers
        self.tree_sitter_parser = TreeSitterParser() if self.enable_tree_sitter else None
        self.joern_parser = JoernParser() if self.enable_joern else None
        
        logger.info(f"Initialized hybrid parser - Tree-sitter: {self.enable_tree_sitter}, Joern: {self.enable_joern}")
    
    def parse_chunk(self, chunk: Chunk) -> Tuple[List[HybridEntity], List[HybridRelation]]:
        """Parse a chunk using hybrid approach.
        
        Args:
            chunk: Chunk to parse
            
        Returns:
            Tuple of (entities, relationships)
        """
        logger.info(f"Hybrid parsing chunk {chunk.id} ({chunk.file_count} files)")
        
        start_time = time.time()
        
        # Parse with Tree-sitter (fast, syntactic)
        ts_entities = []
        ts_relations = []
        
        if self.enable_tree_sitter and self.tree_sitter_parser:
            logger.debug("Running Tree-sitter parsing...")
            ts_start = time.time()
            
            for file_info in chunk.files:
                file_entities, file_relations = self.tree_sitter_parser.parse_file(file_info)
                ts_entities.extend(file_entities)
                ts_relations.extend(file_relations)
            
            ts_time = time.time() - ts_start
            logger.debug(f"Tree-sitter parsing completed in {ts_time:.2f}s: {len(ts_entities)} entities, {len(ts_relations)} relations")
        
        # Parse with Joern (slower, semantic)
        joern_entities = []
        joern_relations = []
        
        if self.enable_joern and self.joern_parser:
            logger.debug("Running Joern CPG parsing...")
            joern_start = time.time()
            
            try:
                joern_entities, joern_relations = self.joern_parser.parse_chunk(chunk)
                joern_time = time.time() - joern_start
                logger.debug(f"Joern parsing completed in {joern_time:.2f}s: {len(joern_entities)} entities, {len(joern_relations)} relations")
            except Exception as e:
                logger.warning(f"Joern parsing failed for chunk {chunk.id}: {e}")
        
        # Merge and reconcile results
        hybrid_entities, hybrid_relations = self._merge_results(
            ts_entities, ts_relations, 
            joern_entities, joern_relations,
            chunk
        )
        
        total_time = time.time() - start_time
        logger.info(f"Hybrid parsing completed in {total_time:.2f}s: {len(hybrid_entities)} entities, {len(hybrid_relations)} relations")
        
        return hybrid_entities, hybrid_relations
    
    def _merge_results(
        self,
        ts_entities: List[TSEntity],
        ts_relations: List[TSRelation], 
        joern_entities: List[JoernEntity],
        joern_relations: List[JoernRelation],
        chunk: Chunk
    ) -> Tuple[List[HybridEntity], List[HybridRelation]]:
        """Merge and reconcile results from both parsers.
        
        Args:
            ts_entities: Tree-sitter entities
            ts_relations: Tree-sitter relations
            joern_entities: Joern entities
            joern_relations: Joern relations
            chunk: Original chunk
            
        Returns:
            Tuple of merged (entities, relationships)
        """
        logger.debug("Merging parsing results...")
        
        # Create unified entities
        hybrid_entities = []
        entity_map = {}  # Map unified ID to entity
        
        # First, add Tree-sitter entities
        for ts_entity in ts_entities:
            entity_id = f"{ts_entity.file_path}:{ts_entity.name}:{ts_entity.start_line}"
            
            hybrid_entity = HybridEntity(
                id=entity_id,
                name=ts_entity.name,
                type=ts_entity.type,
                start_line=ts_entity.start_line,
                end_line=ts_entity.end_line,
                file_path=ts_entity.file_path,
                language=ts_entity.language,
                ts_parent=ts_entity.parent,
                ts_children=ts_entity.children,
                ts_metadata=ts_entity.metadata,
                source_parsers=["tree_sitter"]
            )
            
            hybrid_entities.append(hybrid_entity)
            entity_map[entity_id] = hybrid_entity
        
        # Merge with Joern entities
        for joern_entity in joern_entities:
            # Try to find matching Tree-sitter entity
            matching_entity = self._find_matching_entity(joern_entity, entity_map)
            
            if matching_entity:
                # Enhance existing entity with Joern data
                matching_entity.joern_id = joern_entity.id
                matching_entity.full_name = joern_entity.full_name
                matching_entity.signature = joern_entity.signature
                matching_entity.code = joern_entity.code
                matching_entity.joern_properties = joern_entity.properties
                matching_entity.source_parsers.append("joern")
                matching_entity.confidence_score = 1.5  # Higher confidence for dual-source entities
            else:
                # Create new entity from Joern data
                entity_id = f"{joern_entity.filename}:{joern_entity.name}:{joern_entity.line_number or 0}"
                
                hybrid_entity = HybridEntity(
                    id=entity_id,
                    name=joern_entity.name,
                    type=joern_entity.type.lower(),
                    start_line=joern_entity.line_number or 0,
                    end_line=joern_entity.line_number or 0,
                    file_path=joern_entity.filename,
                    language=joern_entity.language,
                    joern_id=joern_entity.id,
                    full_name=joern_entity.full_name,
                    signature=joern_entity.signature,
                    code=joern_entity.code,
                    joern_properties=joern_entity.properties,
                    source_parsers=["joern"]
                )
                
                hybrid_entities.append(hybrid_entity)
                entity_map[entity_id] = hybrid_entity
        
        # Create unified relationships
        hybrid_relations = []
        
        # Add Tree-sitter relationships
        for ts_relation in ts_relations:
            # Map to unified entity IDs
            source_entity = self._find_entity_by_name_file(ts_relation.source, entity_map)
            target_entity = self._find_entity_by_name_file(ts_relation.target, entity_map)
            
            if source_entity and target_entity:
                hybrid_relation = HybridRelation(
                    source_id=source_entity.id,
                    target_id=target_entity.id,
                    relation_type=ts_relation.relation_type,
                    ts_metadata=ts_relation.metadata,
                    source_parsers=["tree_sitter"],
                    line_number=ts_relation.metadata.get("line")
                )
                hybrid_relations.append(hybrid_relation)
        
        # Add Joern relationships
        for joern_relation in joern_relations:
            # Find corresponding entities
            source_entity = self._find_entity_by_joern_id(joern_relation.source_id, entity_map)
            target_entity = self._find_entity_by_joern_id(joern_relation.target_id, entity_map)
            
            if source_entity and target_entity:
                # Check if similar relationship already exists
                existing_relation = self._find_similar_relation(
                    source_entity.id, target_entity.id, joern_relation.edge_type, hybrid_relations
                )
                
                if existing_relation:
                    # Enhance existing relationship
                    existing_relation.joern_edge_type = joern_relation.edge_type
                    existing_relation.joern_properties = joern_relation.properties
                    existing_relation.source_parsers.append("joern")
                    existing_relation.confidence_score = 1.5
                else:
                    # Create new relationship
                    hybrid_relation = HybridRelation(
                        source_id=source_entity.id,
                        target_id=target_entity.id,
                        relation_type=self._map_joern_edge_type(joern_relation.edge_type),
                        joern_edge_type=joern_relation.edge_type,
                        joern_properties=joern_relation.properties,
                        source_parsers=["joern"]
                    )
                    hybrid_relations.append(hybrid_relation)
        
        logger.debug(f"Merged results: {len(hybrid_entities)} entities, {len(hybrid_relations)} relations")
        
        return hybrid_entities, hybrid_relations
    
    def _find_matching_entity(self, joern_entity: JoernEntity, entity_map: Dict[str, HybridEntity]) -> Optional[HybridEntity]:
        """Find matching Tree-sitter entity for a Joern entity.
        
        Args:
            joern_entity: Joern entity to match
            entity_map: Map of existing entities
            
        Returns:
            Matching entity or None
        """
        # Simple matching based on name and file
        for entity in entity_map.values():
            if (entity.name == joern_entity.name and 
                entity.file_path.endswith(joern_entity.filename) and
                abs(entity.start_line - (joern_entity.line_number or 0)) <= 2):  # Allow small line differences
                return entity
        
        return None
    
    def _find_entity_by_name_file(self, name_or_path: str, entity_map: Dict[str, HybridEntity]) -> Optional[HybridEntity]:
        """Find entity by name or file path reference.
        
        Args:
            name_or_path: Entity name or path reference
            entity_map: Map of existing entities
            
        Returns:
            Found entity or None
        """
        # Try direct name match first
        for entity in entity_map.values():
            if entity.name == name_or_path:
                return entity
        
        # Try partial matches
        for entity in entity_map.values():
            if name_or_path in entity.name or entity.name in name_or_path:
                return entity
        
        return None
    
    def _find_entity_by_joern_id(self, joern_id: str, entity_map: Dict[str, HybridEntity]) -> Optional[HybridEntity]:
        """Find entity by Joern ID.
        
        Args:
            joern_id: Joern entity ID
            entity_map: Map of existing entities
            
        Returns:
            Found entity or None
        """
        for entity in entity_map.values():
            if entity.joern_id == joern_id:
                return entity
        
        return None
    
    def _find_similar_relation(
        self, 
        source_id: str, 
        target_id: str, 
        edge_type: str, 
        relations: List[HybridRelation]
    ) -> Optional[HybridRelation]:
        """Find similar existing relationship.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID  
            edge_type: Edge type
            relations: Existing relations
            
        Returns:
            Similar relation or None
        """
        for relation in relations:
            if (relation.source_id == source_id and 
                relation.target_id == target_id and
                (relation.relation_type == edge_type or 
                 relation.joern_edge_type == edge_type)):
                return relation
        
        return None
    
    def _map_joern_edge_type(self, joern_edge_type: str) -> str:
        """Map Joern edge type to standard relation type.
        
        Args:
            joern_edge_type: Joern-specific edge type
            
        Returns:
            Standard relation type
        """
        mapping = {
            "CALL": "calls",
            "AST": "contains",
            "CFG": "flows_to",
            "CDG": "depends_on",
            "DOMINATE": "dominates",
            "REF": "references",
            "INHERITS_FROM": "inherits",
        }
        
        return mapping.get(joern_edge_type, joern_edge_type.lower())