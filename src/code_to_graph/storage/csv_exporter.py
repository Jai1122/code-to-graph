"""CSV exporter for optimized Neo4j imports."""

import csv
from pathlib import Path
from typing import List, Dict, Any, Tuple
import tempfile

from loguru import logger
from pydantic import BaseModel

from ..parsers.hybrid_parser import HybridEntity, HybridRelation


class CSVExportStats(BaseModel):
    """Statistics for CSV export operations."""
    
    entities_exported: int = 0
    relationships_exported: int = 0
    export_time: float = 0.0
    nodes_file_size: int = 0
    relationships_file_size: int = 0


class CSVExporter:
    """Exports parsed entities and relationships to CSV for optimized Neo4j import."""
    
    def __init__(self, output_dir: Path):
        """Initialize CSV exporter.
        
        Args:
            output_dir: Directory to write CSV files
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized CSV exporter: {output_dir}")
    
    def export(
        self, 
        entities: List[HybridEntity], 
        relationships: List[HybridRelation],
        prefix: str = "graph"
    ) -> Tuple[Path, Path]:
        """Export entities and relationships to CSV files.
        
        Args:
            entities: List of entities to export
            relationships: List of relationships to export
            prefix: File name prefix
            
        Returns:
            Tuple of (nodes_file, relationships_file) paths
        """
        nodes_file = self.output_dir / f"{prefix}_nodes.csv"
        relationships_file = self.output_dir / f"{prefix}_relationships.csv"
        
        logger.info(f"Exporting {len(entities)} entities and {len(relationships)} relationships to CSV")
        
        # Export nodes
        self._export_nodes(entities, nodes_file)
        
        # Export relationships
        self._export_relationships(relationships, relationships_file)
        
        logger.info(f"CSV export completed: {nodes_file}, {relationships_file}")
        
        return nodes_file, relationships_file
    
    def _export_nodes(self, entities: List[HybridEntity], output_file: Path) -> None:
        """Export entities as nodes CSV.
        
        Args:
            entities: Entities to export
            output_file: Output CSV file path
        """
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'id', 'name', 'type', 'start_line', 'end_line', 'file_path', 'language',
                'full_name', 'signature', 'code', 'confidence_score', 'source_parsers',
                'ts_parent', 'ts_children', 'joern_id'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for entity in entities:
                row = {
                    'id': entity.id,
                    'name': entity.name,
                    'type': entity.type,
                    'start_line': entity.start_line,
                    'end_line': entity.end_line,
                    'file_path': entity.file_path,
                    'language': entity.language,
                    'full_name': entity.full_name or '',
                    'signature': entity.signature or '',
                    'code': (entity.code or '').replace('\n', '\\n').replace('\r', '\\r'),
                    'confidence_score': entity.confidence_score,
                    'source_parsers': '|'.join(entity.source_parsers),
                    'ts_parent': entity.ts_parent or '',
                    'ts_children': '|'.join(entity.ts_children) if entity.ts_children else '',
                    'joern_id': entity.joern_id or ''
                }
                
                writer.writerow(row)
        
        logger.debug(f"Exported {len(entities)} entities to {output_file}")
    
    def _export_relationships(self, relationships: List[HybridRelation], output_file: Path) -> None:
        """Export relationships CSV.
        
        Args:
            relationships: Relationships to export
            output_file: Output CSV file path
        """
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'source_id', 'target_id', 'relation_type', 'confidence_score', 
                'source_parsers', 'line_number', 'joern_edge_type'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for relationship in relationships:
                row = {
                    'source_id': relationship.source_id,
                    'target_id': relationship.target_id,
                    'relation_type': relationship.relation_type,
                    'confidence_score': relationship.confidence_score,
                    'source_parsers': '|'.join(relationship.source_parsers),
                    'line_number': relationship.line_number or '',
                    'joern_edge_type': relationship.joern_edge_type or ''
                }
                
                writer.writerow(row)
        
        logger.debug(f"Exported {len(relationships)} relationships to {output_file}")
    
    def create_import_script(
        self, 
        nodes_file: Path, 
        relationships_file: Path,
        output_script: Path
    ) -> None:
        """Create Cypher import script for the CSV files.
        
        Args:
            nodes_file: Path to nodes CSV file
            relationships_file: Path to relationships CSV file
            output_script: Path to write import script
        """
        script_content = f"""
// CodeToGraph Neo4j Import Script
// Generated automatically - import nodes and relationships from CSV files

// Clear existing data (uncomment if needed)
// MATCH (n) DETACH DELETE n;

// Create constraints
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;

// Import nodes
LOAD CSV WITH HEADERS FROM 'file:///{nodes_file}' AS row
CALL {{
    WITH row
    CALL apoc.create.node([row.type], {{
        id: row.id,
        name: row.name,
        file_path: row.file_path,
        language: row.language,
        start_line: toInteger(row.start_line),
        end_line: toInteger(row.end_line),
        full_name: CASE WHEN row.full_name <> '' THEN row.full_name ELSE null END,
        signature: CASE WHEN row.signature <> '' THEN row.signature ELSE null END,
        code: CASE WHEN row.code <> '' THEN replace(replace(row.code, '\\\\n', '\\n'), '\\\\r', '\\r') ELSE null END,
        confidence_score: toFloat(row.confidence_score),
        source_parsers: CASE WHEN row.source_parsers <> '' THEN split(row.source_parsers, '|') ELSE [] END,
        ts_parent: CASE WHEN row.ts_parent <> '' THEN row.ts_parent ELSE null END,
        ts_children: CASE WHEN row.ts_children <> '' THEN split(row.ts_children, '|') ELSE [] END,
        joern_id: CASE WHEN row.joern_id <> '' THEN row.joern_id ELSE null END
    }}) YIELD node
    RETURN count(*)
}} IN TRANSACTIONS OF 1000 ROWS;

// Import relationships
LOAD CSV WITH HEADERS FROM 'file:///{relationships_file}' AS row
CALL {{
    WITH row
    MATCH (source {{id: row.source_id}})
    MATCH (target {{id: row.target_id}})
    CALL apoc.create.relationship(source, row.relation_type, {{
        confidence_score: toFloat(row.confidence_score),
        source_parsers: CASE WHEN row.source_parsers <> '' THEN split(row.source_parsers, '|') ELSE [] END,
        line_number: CASE WHEN row.line_number <> '' THEN toInteger(row.line_number) ELSE null END,
        joern_edge_type: CASE WHEN row.joern_edge_type <> '' THEN row.joern_edge_type ELSE null END
    }}, target) YIELD rel
    RETURN count(*)
}} IN TRANSACTIONS OF 1000 ROWS;

// Create performance indexes
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX entity_file IF NOT EXISTS FOR (e:Entity) ON (e.file_path);
CREATE INDEX entity_language IF NOT EXISTS FOR (e:Entity) ON (e.language);

// Show import statistics
MATCH (n) RETURN labels(n) as label, count(n) as count ORDER BY count DESC;
MATCH ()-[r]->() RETURN type(r) as relationship, count(r) as count ORDER BY count DESC;

// Enable full-text search
CREATE FULLTEXT INDEX entity_search IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.full_name, e.code];
"""
        
        with open(output_script, 'w') as f:
            f.write(script_content.strip())
        
        logger.info(f"Created import script: {output_script}")
    
    def export_with_script(
        self,
        entities: List[HybridEntity],
        relationships: List[HybridRelation],
        prefix: str = "graph"
    ) -> Tuple[Path, Path, Path]:
        """Export CSV files and create import script.
        
        Args:
            entities: Entities to export
            relationships: Relationships to export
            prefix: File name prefix
            
        Returns:
            Tuple of (nodes_file, relationships_file, import_script)
        """
        # Export CSV files
        nodes_file, relationships_file = self.export(entities, relationships, prefix)
        
        # Create import script
        import_script = self.output_dir / f"{prefix}_import.cypher"
        self.create_import_script(nodes_file, relationships_file, import_script)
        
        return nodes_file, relationships_file, import_script