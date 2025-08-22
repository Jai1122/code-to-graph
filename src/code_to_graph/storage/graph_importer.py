"""Graph importer that coordinates CSV export and Neo4j import."""

from pathlib import Path
from typing import List, Optional
import time

from loguru import logger

from .csv_exporter import CSVExporter
from .neo4j_client import Neo4jClient
from ..parsers.hybrid_parser import HybridEntity, HybridRelation
from ..core.config import settings


class GraphImporter:
    """Coordinates the export and import of graph data to Neo4j."""
    
    def __init__(self, output_dir: Optional[Path] = None, neo4j_client: Optional[Neo4jClient] = None):
        """Initialize graph importer.
        
        Args:
            output_dir: Directory for CSV export (defaults to settings.data_dir)
            neo4j_client: Neo4j client (creates new one if not provided)
        """
        self.output_dir = output_dir or settings.data_dir / "export"
        self.csv_exporter = CSVExporter(self.output_dir)
        self.neo4j_client = neo4j_client or Neo4jClient()
        
        logger.info(f"Initialized graph importer with output dir: {self.output_dir}")
    
    def import_graph(
        self,
        entities: List[HybridEntity],
        relationships: List[HybridRelation],
        clear_existing: bool = False,
        create_indexes: bool = True,
        prefix: str = "graph"
    ) -> None:
        """Import graph data to Neo4j.
        
        Args:
            entities: Entities to import
            relationships: Relationships to import
            clear_existing: Clear existing data before import
            create_indexes: Create performance indexes after import
            prefix: File prefix for CSV exports
        """
        start_time = time.time()
        
        logger.info(f"Starting graph import: {len(entities)} entities, {len(relationships)} relationships")
        
        try:
            # Clear existing data if requested
            if clear_existing:
                logger.warning("Clearing existing Neo4j data")
                self.neo4j_client.clear_database(confirm=True)
            
            # Export to CSV files
            logger.info("Exporting to CSV files...")
            nodes_file, relationships_file, import_script = self.csv_exporter.export_with_script(
                entities, relationships, prefix
            )
            
            # Import using direct entity import (bypassing CSV file issues)
            logger.info("Importing to Neo4j...")
            stats = self.neo4j_client.bulk_import_entities(entities, relationships)
            
            # Create indexes if requested
            if create_indexes:
                logger.info("Creating performance indexes...")
                self.neo4j_client.create_indexes()
            
            # Show final stats
            db_stats = self.neo4j_client.get_database_stats()
            
            import_time = time.time() - start_time
            
            logger.info(f"Graph import completed in {import_time:.2f}s")
            logger.info(f"Database stats: {db_stats['total_nodes']} nodes, {db_stats['total_relationships']} relationships")
            
        except Exception as e:
            logger.error(f"Graph import failed: {e}")
            raise
    
    def export_only(
        self,
        entities: List[HybridEntity],
        relationships: List[HybridRelation],
        prefix: str = "graph"
    ) -> tuple[Path, Path, Path]:
        """Export graph data to CSV files only (no Neo4j import).
        
        Args:
            entities: Entities to export
            relationships: Relationships to export
            prefix: File prefix for exports
            
        Returns:
            Tuple of (nodes_file, relationships_file, import_script)
        """
        logger.info(f"Exporting graph data: {len(entities)} entities, {len(relationships)} relationships")
        
        nodes_file, relationships_file, import_script = self.csv_exporter.export_with_script(
            entities, relationships, prefix
        )
        
        logger.info(f"Export completed: {nodes_file}, {relationships_file}")
        logger.info(f"Import script created: {import_script}")
        
        return nodes_file, relationships_file, import_script
    
    def close(self) -> None:
        """Close the Neo4j client."""
        if self.neo4j_client:
            self.neo4j_client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()