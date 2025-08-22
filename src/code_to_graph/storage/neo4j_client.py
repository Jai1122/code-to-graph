"""Optimized Neo4j client for large-scale graph operations."""

import time
from typing import Dict, List, Optional, Any, Iterator, Tuple
from pathlib import Path
import csv
import tempfile

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import Neo4jError
from loguru import logger
from pydantic import BaseModel

from ..core.config import settings


class Neo4jStats(BaseModel):
    """Statistics for Neo4j operations."""
    
    nodes_created: int = 0
    relationships_created: int = 0
    nodes_updated: int = 0
    relationships_updated: int = 0
    execution_time: float = 0.0
    memory_usage: float = 0.0


class Neo4jClient:
    """High-performance Neo4j client optimized for large graph imports."""
    
    def __init__(self, driver: Optional[Driver] = None):
        """Initialize Neo4j client.
        
        Args:
            driver: Existing Neo4j driver (optional)
        """
        if driver:
            self.driver = driver
        else:
            self.driver = self._create_driver()
        
        self._session_count = 0
        logger.info(f"Initialized Neo4j client: {settings.neo4j.uri}")
    
    def _create_driver(self) -> Driver:
        """Create Neo4j driver with optimized settings."""
        try:
            driver = GraphDatabase.driver(
                settings.neo4j.uri,
                auth=(settings.neo4j.username, settings.neo4j.password),
                max_connection_lifetime=settings.neo4j.max_connection_lifetime,
                max_connection_pool_size=settings.neo4j.max_connection_pool_size,
                connection_acquisition_timeout=30.0,
                connection_timeout=15.0
            )
            
            # Test connection
            driver.verify_connectivity()
            logger.info("Neo4j connection verified successfully")
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self) -> None:
        """Close Neo4j driver."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j driver closed")
    
    def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict] = None,
        database: Optional[str] = None
    ) -> List[Dict]:
        """Execute a single Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name (optional)
            
        Returns:
            Query results as list of dictionaries
        """
        database = database or settings.neo4j.database
        parameters = parameters or {}
        
        try:
            with self.driver.session(database=database) as session:
                result = session.run(query, parameters)
                return [record.data() for record in result]
                
        except Neo4jError as e:
            logger.error(f"Neo4j query failed: {e}")
            raise
    
    def execute_write_transaction(
        self,
        query: str,
        parameters: Optional[Dict] = None,
        database: Optional[str] = None
    ) -> Neo4jStats:
        """Execute a write transaction with statistics.
        
        Args:
            query: Cypher query string
            parameters: Query parameters  
            database: Database name (optional)
            
        Returns:
            Execution statistics
        """
        database = database or settings.neo4j.database
        parameters = parameters or {}
        
        start_time = time.time()
        
        try:
            with self.driver.session(database=database) as session:
                result = session.run(query, parameters)
                summary = result.consume()
                
                stats = Neo4jStats(
                    nodes_created=summary.counters.nodes_created,
                    relationships_created=summary.counters.relationships_created,
                    nodes_updated=summary.counters.properties_set,
                    execution_time=time.time() - start_time
                )
                
                return stats
                
        except Neo4jError as e:
            logger.error(f"Neo4j write transaction failed: {e}")
            raise
    
    def batch_execute(
        self,
        queries: List[Tuple[str, Dict]],
        batch_size: int = 1000,
        database: Optional[str] = None
    ) -> Neo4jStats:
        """Execute multiple queries in batches.
        
        Args:
            queries: List of (query, parameters) tuples
            batch_size: Number of queries per batch
            database: Database name (optional)
            
        Returns:
            Combined execution statistics
        """
        database = database or settings.neo4j.database
        total_stats = Neo4jStats()
        
        logger.info(f"Executing {len(queries)} queries in batches of {batch_size}")
        
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            batch_start = time.time()
            
            try:
                with self.driver.session(database=database) as session:
                    with session.begin_transaction() as tx:
                        for query, params in batch:
                            result = tx.run(query, params)
                            summary = result.consume()
                            
                            total_stats.nodes_created += summary.counters.nodes_created
                            total_stats.relationships_created += summary.counters.relationships_created
                            total_stats.nodes_updated += summary.counters.properties_set
                
                batch_time = time.time() - batch_start
                total_stats.execution_time += batch_time
                
                logger.debug(f"Batch {i//batch_size + 1} completed in {batch_time:.2f}s")
                
            except Neo4jError as e:
                logger.error(f"Batch execution failed at batch {i//batch_size + 1}: {e}")
                raise
        
        logger.info(f"Batch execution completed: {total_stats}")
        return total_stats
    
    def bulk_import_entities(
        self,
        entities: List,
        relationships: List,
        database: Optional[str] = None
    ) -> Neo4jStats:
        """Bulk import entities and relationships directly.
        
        Args:
            entities: List of entity objects 
            relationships: List of relationship objects
            database: Target database name
            
        Returns:
            Import statistics
        """
        database = database or settings.neo4j.database
        total_stats = Neo4jStats()
        start_time = time.time()
        
        logger.info(f"Starting bulk entity import: {len(entities)} entities, {len(relationships)} relationships")
        
        try:
            with self.driver.session(database=database) as session:
                
                # Create constraints first
                constraint_queries = [
                    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE"
                ]
                
                for constraint in constraint_queries:
                    try:
                        session.run(constraint)
                    except Neo4jError as e:
                        if "already exists" not in str(e).lower():
                            logger.warning(f"Constraint creation failed: {e}")
                
                # Import entities in batches
                batch_size = 1000
                for i in range(0, len(entities), batch_size):
                    batch = entities[i:i + batch_size]
                    
                    # Prepare batch data
                    entity_params = []
                    for entity in batch:
                        entity_params.append({
                            'id': entity.id,
                            'name': entity.name,
                            'file_path': entity.file_path,
                            'language': entity.language,
                            'start_line': entity.start_line,
                            'end_line': entity.end_line,
                            'full_name': entity.full_name,
                            'signature': entity.signature,
                            'code': entity.code,
                            'confidence_score': entity.confidence_score,
                            'source_parsers': [p.value if hasattr(p, 'value') else str(p) for p in entity.source_parsers],
                            'entity_type': entity.type
                        })
                    
                    # Create entities
                    create_query = """
                    UNWIND $entities AS entity
                    CREATE (n:Entity {
                        id: entity.id,
                        name: entity.name,
                        file_path: entity.file_path,
                        language: entity.language,
                        start_line: entity.start_line,
                        end_line: entity.end_line,
                        full_name: entity.full_name,
                        signature: entity.signature,
                        code: entity.code,
                        confidence_score: entity.confidence_score,
                        source_parsers: entity.source_parsers,
                        entity_type: entity.entity_type
                    })
                    """
                    
                    result = session.run(create_query, {'entities': entity_params})
                    summary = result.consume()
                    total_stats.nodes_created += summary.counters.nodes_created
                    
                    logger.info(f"Imported batch {i//batch_size + 1}: {summary.counters.nodes_created} nodes")
                
                # Import relationships in batches
                for i in range(0, len(relationships), batch_size):
                    batch = relationships[i:i + batch_size]
                    
                    # Prepare batch data
                    rel_params = []
                    for rel in batch:
                        rel_params.append({
                            'source_id': rel.source_id,
                            'target_id': rel.target_id,
                            'relation_type': rel.relation_type,
                            'confidence_score': rel.confidence_score,
                            'source_parsers': [p.value if hasattr(p, 'value') else str(p) for p in rel.source_parsers],
                            'line_number': rel.line_number
                        })
                    
                    # Create relationships
                    rel_query = """
                    UNWIND $relationships AS rel
                    MATCH (source:Entity {id: rel.source_id})
                    MATCH (target:Entity {id: rel.target_id})
                    CREATE (source)-[r:RELATES {
                        relation_type: rel.relation_type,
                        confidence_score: rel.confidence_score,
                        source_parsers: rel.source_parsers,
                        line_number: rel.line_number
                    }]->(target)
                    """
                    
                    result = session.run(rel_query, {'relationships': rel_params})
                    summary = result.consume()
                    total_stats.relationships_created += summary.counters.relationships_created
                    
                    logger.info(f"Imported batch {i//batch_size + 1}: {summary.counters.relationships_created} relationships")
                
                total_stats.execution_time = time.time() - start_time
                logger.info(f"Bulk import completed in {total_stats.execution_time:.2f}s")
                
        except Neo4jError as e:
            logger.error(f"Bulk entity import failed: {e}")
            raise
        
        return total_stats
    
    def bulk_import_csv(
        self,
        nodes_file: Optional[Path] = None,
        relationships_file: Optional[Path] = None,
        database: Optional[str] = None
    ) -> Neo4jStats:
        """Bulk import from CSV files using LOAD CSV.
        
        Args:
            nodes_file: Path to nodes CSV file
            relationships_file: Path to relationships CSV file
            database: Database name (optional)
            
        Returns:
            Import statistics
        """
        database = database or settings.neo4j.database
        total_stats = Neo4jStats()
        start_time = time.time()
        
        logger.info("Starting bulk CSV import...")
        
        try:
            with self.driver.session(database=database) as session:
                
                # Import nodes if provided
                if nodes_file and nodes_file.exists():
                    logger.info(f"Importing nodes from {nodes_file}")
                    
                    # Create constraints first
                    constraint_queries = [
                        "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                        "CREATE CONSTRAINT function_id IF NOT EXISTS FOR (f:Function) REQUIRE f.id IS UNIQUE",
                        "CREATE CONSTRAINT class_id IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE",
                        "CREATE CONSTRAINT method_id IF NOT EXISTS FOR (m:Method) REQUIRE m.id IS UNIQUE"
                    ]
                    
                    for constraint in constraint_queries:
                        try:
                            session.run(constraint)
                        except Neo4jError as e:
                            if "already exists" not in str(e).lower():
                                logger.warning(f"Constraint creation failed: {e}")
                    
                    # Load nodes using standard CREATE 
                    nodes_query = f"""
                    LOAD CSV WITH HEADERS FROM 'file:///{nodes_file.absolute()}' AS row
                    WITH row
                    WHERE row.id IS NOT NULL
                    CREATE (n:Entity {{
                        id: row.id,
                        name: row.name,
                        file_path: row.file_path,
                        language: row.language,
                        start_line: toInteger(row.start_line),
                        end_line: toInteger(row.end_line),
                        full_name: row.full_name,
                        signature: row.signature,
                        code: row.code,
                        confidence_score: toFloat(row.confidence_score),
                        source_parsers: split(row.source_parsers, '|'),
                        entity_type: row.type
                    }})
                    """
                    
                    result = session.run(nodes_query)
                    summary = result.consume()
                    total_stats.nodes_created += summary.counters.nodes_created
                    
                    logger.info(f"Imported {summary.counters.nodes_created} nodes")
                
                # Import relationships if provided
                if relationships_file and relationships_file.exists():
                    logger.info(f"Importing relationships from {relationships_file}")
                    
                    relationships_query = f"""
                    LOAD CSV WITH HEADERS FROM 'file:///{relationships_file.absolute()}' AS row
                    WITH row
                    WHERE row.source_id IS NOT NULL AND row.target_id IS NOT NULL
                    MATCH (source:Entity {{id: row.source_id}})
                    MATCH (target:Entity {{id: row.target_id}})
                    CREATE (source)-[r:RELATES {{
                        relation_type: row.relation_type,
                        confidence_score: toFloat(row.confidence_score),
                        source_parsers: split(row.source_parsers, '|'),
                        line_number: toInteger(row.line_number)
                    }}]->(target)
                    """
                    
                    result = session.run(relationships_query)
                    summary = result.consume()
                    total_stats.relationships_created += summary.counters.relationships_created
                    
                    logger.info(f"Imported {summary.counters.relationships_created} relationships")
                
                total_stats.execution_time = time.time() - start_time
                
        except Neo4jError as e:
            logger.error(f"Bulk CSV import failed: {e}")
            raise
        
        logger.info(f"Bulk import completed: {total_stats}")
        return total_stats
    
    def create_indexes(self, database: Optional[str] = None) -> None:
        """Create performance indexes for the graph.
        
        Args:
            database: Database name (optional)
        """
        database = database or settings.neo4j.database
        
        index_queries = [
            # Entity indexes
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_file IF NOT EXISTS FOR (e:Entity) ON (e.file_path)",
            "CREATE INDEX entity_language IF NOT EXISTS FOR (e:Entity) ON (e.language)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            
            # Function indexes
            "CREATE INDEX function_name IF NOT EXISTS FOR (f:Function) ON (f.name)",
            "CREATE INDEX function_file IF NOT EXISTS FOR (f:Function) ON (f.file_path)",
            
            # Class indexes  
            "CREATE INDEX class_name IF NOT EXISTS FOR (c:Class) ON (c.name)",
            "CREATE INDEX class_file IF NOT EXISTS FOR (c:Class) ON (c.file_path)",
            
            # Method indexes
            "CREATE INDEX method_name IF NOT EXISTS FOR (m:Method) ON (m.name)",
            "CREATE INDEX method_file IF NOT EXISTS FOR (m:Method) ON (m.file_path)",
            
            # Full-text indexes for search
            "CREATE FULLTEXT INDEX entity_search IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.full_name, e.code]",
        ]
        
        logger.info("Creating performance indexes...")
        
        try:
            with self.driver.session(database=database) as session:
                for query in index_queries:
                    try:
                        session.run(query)
                        logger.debug(f"Created index: {query}")
                    except Neo4jError as e:
                        if "already exists" not in str(e).lower():
                            logger.warning(f"Index creation failed: {e}")
            
            logger.info("Index creation completed")
            
        except Neo4jError as e:
            logger.error(f"Failed to create indexes: {e}")
            raise
    
    def get_database_stats(self, database: Optional[str] = None) -> Dict[str, Any]:
        """Get database statistics.
        
        Args:
            database: Database name (optional)
            
        Returns:
            Database statistics
        """
        database = database or settings.neo4j.database
        
        try:
            with self.driver.session(database=database) as session:
                # Node counts by label
                node_stats = {}
                result = session.run("CALL db.labels()")
                labels = [record["label"] for record in result]
                
                for label in labels:
                    count_result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                    count = count_result.single()["count"]
                    node_stats[label] = count
                
                # Relationship counts by type
                rel_stats = {}
                result = session.run("CALL db.relationshipTypes()")
                rel_types = [record["relationshipType"] for record in result]
                
                for rel_type in rel_types:
                    count_result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
                    count = count_result.single()["count"]
                    rel_stats[rel_type] = count
                
                # Total counts
                total_nodes_result = session.run("MATCH (n) RETURN count(n) as count")
                total_nodes = total_nodes_result.single()["count"]
                
                total_rels_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                total_rels = total_rels_result.single()["count"]
                
                return {
                    "total_nodes": total_nodes,
                    "total_relationships": total_rels,
                    "nodes_by_label": node_stats,
                    "relationships_by_type": rel_stats,
                    "database": database
                }
                
        except Neo4jError as e:
            logger.error(f"Failed to get database stats: {e}")
            raise
    
    def clear_database(self, database: Optional[str] = None, confirm: bool = False) -> None:
        """Clear all data from the database.
        
        Args:
            database: Database name (optional)
            confirm: Confirmation flag (required for safety)
        """
        if not confirm:
            raise ValueError("Database clearing requires explicit confirmation")
        
        database = database or settings.neo4j.database
        
        logger.warning(f"Clearing all data from database: {database}")
        
        try:
            with self.driver.session(database=database) as session:
                # Delete all relationships first
                session.run("MATCH ()-[r]->() DELETE r")
                
                # Delete all nodes
                session.run("MATCH (n) DELETE n")
                
                logger.info("Database cleared successfully")
                
        except Neo4jError as e:
            logger.error(f"Failed to clear database: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()