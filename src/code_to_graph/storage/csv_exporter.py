"""CSV exporter for optimized Neo4j imports."""

import csv
from pathlib import Path
from typing import List, Dict, Any, Tuple
import tempfile

from loguru import logger
from pydantic import BaseModel

from ..core.models import Entity, Relationship


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
        entities: List[Entity], 
        relationships: List[Relationship],
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
    
    def _export_nodes(self, entities: List[Entity], output_file: Path) -> None:
        """Export entities as nodes CSV.
        
        Args:
            entities: Entities to export
            output_file: Output CSV file path
        """
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'id', 'name', 'type', 'line_number', 'end_line_number', 'file_path', 'language',
                'package', 'signature', 'return_type', 'access_modifier', 'is_static',
                'properties', 'annotations'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for entity in entities:
                row = {
                    'id': entity.id,
                    'name': entity.name,
                    'type': entity.type.value if hasattr(entity.type, 'value') else str(entity.type),
                    'line_number': entity.line_number or '',
                    'end_line_number': entity.end_line_number or '',
                    'file_path': entity.file_path or '',
                    'language': entity.language or '',
                    'package': entity.package or '',
                    'signature': entity.signature or '',
                    'return_type': entity.return_type or '',
                    'access_modifier': entity.access_modifier or '',
                    'is_static': entity.is_static or False,
                    'properties': str(entity.properties) if entity.properties else '',
                    'annotations': '|'.join(entity.annotations) if entity.annotations else '',
                }
                
                writer.writerow(row)
        
        logger.debug(f"Exported {len(entities)} entities to {output_file}")
    
    def _export_relationships(self, relationships: List[Relationship], output_file: Path) -> None:
        """Export relationships CSV with comprehensive validation.
        CSV_VALIDATION_FIX_APPLIED - Validates and fixes null IDs before export
        """
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'id', 'source_id', 'target_id', 'relation_type', 'file_path',
                'line_number', 'column_number', 'properties'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            valid_relationships = 0
            skipped_relationships = 0
            
            for relationship in relationships:
                # Comprehensive validation
                if not relationship.source_id:
                    logger.warning(f"⚠️  Skipping relationship with null source_id: {relationship.id}")
                    skipped_relationships += 1
                    continue
                
                if not relationship.target_id:
                    logger.warning(f"⚠️  Skipping relationship with null target_id: {relationship.id}")
                    logger.warning(f"     Properties: {relationship.properties}")
                    skipped_relationships += 1
                    continue
                
                if relationship.source_id.lower() == 'null' or relationship.target_id.lower() == 'null':
                    logger.warning(f"⚠️  Skipping relationship with 'null' string IDs: {relationship.id}")
                    skipped_relationships += 1
                    continue
                
                # Export valid relationship
                row = {
                    'id': relationship.id,
                    'source_id': relationship.source_id,
                    'target_id': relationship.target_id,
                    'relation_type': relationship.relation_type.value if hasattr(relationship.relation_type, 'value') else str(relationship.relation_type),
                    'file_path': relationship.file_path or '',
                    'line_number': relationship.line_number or '',
                    'column_number': relationship.column_number or '',
                    'properties': str(relationship.properties) if relationship.properties else '',
                }
                
                writer.writerow(row)
                valid_relationships += 1
            
            logger.info(f"📊 CSV Export Summary: {valid_relationships} valid, {skipped_relationships} skipped relationships")
        
        logger.debug(f"Exported {valid_relationships} relationships to {output_file}")
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
        file_path: CASE WHEN row.file_path <> '' THEN row.file_path ELSE null END,
        language: CASE WHEN row.language <> '' THEN row.language ELSE null END,
        line_number: CASE WHEN row.line_number <> '' THEN toInteger(row.line_number) ELSE null END,
        end_line_number: CASE WHEN row.end_line_number <> '' THEN toInteger(row.end_line_number) ELSE null END,
        package: CASE WHEN row.package <> '' THEN row.package ELSE null END,
        signature: CASE WHEN row.signature <> '' THEN row.signature ELSE null END,
        return_type: CASE WHEN row.return_type <> '' THEN row.return_type ELSE null END,
        access_modifier: CASE WHEN row.access_modifier <> '' THEN row.access_modifier ELSE null END,
        is_static: toBoolean(row.is_static),
        properties: CASE WHEN row.properties <> '' THEN row.properties ELSE null END,
        annotations: CASE WHEN row.annotations <> '' THEN split(row.annotations, '|') ELSE [] END
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
        id: row.id,
        file_path: CASE WHEN row.file_path <> '' THEN row.file_path ELSE null END,
        line_number: CASE WHEN row.line_number <> '' THEN toInteger(row.line_number) ELSE null END,
        column_number: CASE WHEN row.column_number <> '' THEN toInteger(row.column_number) ELSE null END,
        properties: CASE WHEN row.properties <> '' THEN row.properties ELSE null END
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
        entities: List[Entity],
        relationships: List[Relationship],
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