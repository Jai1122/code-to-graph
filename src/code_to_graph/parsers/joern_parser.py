"""Joern CPG integration with memory optimization."""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shutil
import os

from loguru import logger
from pydantic import BaseModel

from ..core.config import settings
from ..processors.chunked_processor import Chunk, FileInfo


class JoernEntity(BaseModel):
    """Joern CPG entity representation."""
    
    id: str
    name: str
    type: str  # METHOD, TYPE_DECL, CALL, etc.
    full_name: str
    signature: Optional[str] = None
    filename: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    code: Optional[str] = None
    language: str
    properties: Dict = {}


class JoernRelation(BaseModel):
    """Joern CPG relationship representation."""
    
    source_id: str
    target_id: str
    edge_type: str  # CFG, AST, CALL, etc.
    properties: Dict = {}


class JoernParser:
    """Joern CPG parser with memory optimization for large repositories."""
    
    def __init__(self, joern_path: Optional[Path] = None):
        """Initialize Joern parser.
        
        Args:
            joern_path: Path to Joern installation
        """
        self.joern_path = joern_path or self._find_joern_installation()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="joern_"))
        
        # Memory settings
        self.heap_size = settings.processing.joern_heap_size
        self.max_memory_gb = settings.processing.max_memory_gb
        
        logger.info(f"Initialized Joern parser at {self.joern_path}")
        logger.info(f"Using heap size: {self.heap_size}, max memory: {self.max_memory_gb}GB")
    
    def parse_chunk(self, chunk: Chunk) -> Tuple[List[JoernEntity], List[JoernRelation]]:
        """Parse a chunk of files using Joern CPG.
        
        Args:
            chunk: Chunk of files to parse
            
        Returns:
            Tuple of (entities, relationships)
        """
        if not self.joern_path:
            logger.error("Joern installation not found")
            return [], []
        
        logger.info(f"Parsing chunk {chunk.id} with Joern ({chunk.file_count} files)")
        
        try:
            # Create temporary directory for this chunk
            chunk_dir = self.temp_dir / f"chunk_{chunk.id}"
            chunk_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy files to temporary directory (maintaining structure)
            source_files = self._prepare_chunk_files(chunk, chunk_dir)
            
            if not source_files:
                logger.warning(f"No files to process in chunk {chunk.id}")
                return [], []
            
            # Run Joern CPG generation
            cpg_file = self._generate_cpg(chunk_dir, chunk.primary_language, chunk.id)
            
            if not cpg_file or not cpg_file.exists():
                logger.error(f"Failed to generate CPG for chunk {chunk.id}")
                return [], []
            
            # Export CPG to JSON
            json_data = self._export_cpg_to_json(cpg_file, chunk.id)
            
            if not json_data:
                logger.error(f"Failed to export CPG to JSON for chunk {chunk.id}")
                return [], []
            
            # Parse JSON data
            entities, relations = self._parse_cpg_json(json_data, chunk)
            
            logger.info(f"Parsed chunk {chunk.id}: {len(entities)} entities, {len(relations)} relations")
            
            return entities, relations
            
        except Exception as e:
            logger.error(f"Failed to parse chunk {chunk.id} with Joern: {e}")
            return [], []
        finally:
            # Clean up temporary files
            self._cleanup_chunk_files(chunk_dir)
    
    def _find_joern_installation(self) -> Optional[Path]:
        """Find Joern installation automatically."""
        # Check JOERN_HOME environment variable first
        joern_home = os.getenv('JOERN_HOME')
        if joern_home:
            joern_home_path = Path(joern_home)
            if (joern_home_path / "joern").exists():
                logger.info(f"Found Joern via JOERN_HOME: {joern_home_path}")
                return joern_home_path
            elif (joern_home_path / "bin" / "joern").exists():
                logger.info(f"Found Joern via JOERN_HOME (bin): {joern_home_path}")
                return joern_home_path
            else:
                logger.warning(f"JOERN_HOME points to {joern_home_path} but joern executable not found there")
        
        current_dir = Path(".")
        
        # Check for various common directory structures
        joern_search_patterns = [
            # Standard installations
            current_dir / "joern-cli" / "joern",
            current_dir / "joern" / "joern", 
            current_dir / "joern" / "bin" / "joern",
            
            # Tools directory patterns (common in enterprise/CI environments)
            current_dir / "tools" / "joern",
            current_dir / "tools" / "joern-cli" / "joern",
            current_dir / "tools" / "joern" / "bin" / "joern",
            current_dir / "tools" / "bin" / "joern",
            
            # Alternative directory patterns
            current_dir / "bin" / "joern",
            current_dir / "external" / "joern" / "joern",
            current_dir / "vendor" / "joern" / "joern",
        ]
        
        # Check each pattern
        for joern_exec in joern_search_patterns:
            if joern_exec.exists() and joern_exec.is_file():
                joern_root = joern_exec.parent
                logger.info(f"Found Joern executable: {joern_exec}")
                logger.info(f"Using Joern root directory: {joern_root}")
                return joern_root
        
        # Check if joern is in PATH
        joern_executable = shutil.which("joern")
        if joern_executable:
            joern_path = Path(joern_executable).parent.parent  # Go up from bin/joern to joern root
            logger.info(f"Found Joern in system PATH: {joern_path}")
            return joern_path
        
        # Check system-wide installation paths
        system_paths = [
            Path.home() / "joern",
            Path("/opt/joern"),
            Path("/usr/local/joern"),
            Path("/usr/local/bin"),  # For system installations
        ]
        
        for path in system_paths:
            if (path / "joern").exists() or (path / "bin" / "joern").exists():
                logger.info(f"Found Joern in system location: {path}")
                return path
        
        # Search recursively in common directories (limited depth to avoid performance issues)
        search_dirs = [current_dir / "tools", current_dir / "bin", current_dir / "external"]
        for search_dir in search_dirs:
            if search_dir.exists():
                for joern_candidate in search_dir.rglob("joern"):
                    if joern_candidate.is_file() and joern_candidate.name == "joern":
                        logger.info(f"Found Joern via recursive search: {joern_candidate}")
                        return joern_candidate.parent
        
        logger.warning("Joern installation not found automatically")
        logger.info("Searched in the following locations:")
        for pattern in joern_search_patterns:
            logger.info(f"  - {pattern}")
        logger.info("Possible solutions:")
        logger.info("  1. Install Joern in './joern-cli/' directory")
        logger.info("  2. Install Joern in './tools/' directory") 
        logger.info("  3. Add Joern to system PATH")
        logger.info("  4. Set JOERN_HOME environment variable")
        logger.info("  5. Disable Joern parsing with --disable-joern")
        return None
    
    def _prepare_chunk_files(self, chunk: Chunk, chunk_dir: Path) -> List[Path]:
        """Prepare files for Joern processing.
        
        Args:
            chunk: Chunk to prepare
            chunk_dir: Directory to copy files to
            
        Returns:
            List of prepared file paths
        """
        source_files = []
        
        for file_info in chunk.files:
            try:
                # Maintain relative directory structure
                rel_path = file_info.path.relative_to(file_info.path.parents[len(file_info.path.parents) - 1])
                target_path = chunk_dir / rel_path
                
                # Create parent directories
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(file_info.path, target_path)
                source_files.append(target_path)
                
            except Exception as e:
                logger.warning(f"Failed to prepare file {file_info.path}: {e}")
                continue
        
        logger.debug(f"Prepared {len(source_files)} files for chunk processing")
        return source_files
    
    def _find_frontend_executable(self, frontend_name: str) -> Optional[Path]:
        """Find the correct path for a Joern frontend executable.
        
        Args:
            frontend_name: Name of the frontend (e.g., 'gosrc2cpg')
            
        Returns:
            Path to the frontend executable or None if not found
        """
        if not self.joern_path:
            return None
        
        # Common paths where frontends might be located
        search_paths = [
            # Standard Joern installation structure
            self.joern_path / "bin" / frontend_name,
            self.joern_path / frontend_name,
            
            # Alternative structures
            self.joern_path / "joern-cli" / "bin" / frontend_name,
            self.joern_path / "joern-cli" / frontend_name,
            
            # Tools directory variations
            self.joern_path / "tools" / frontend_name,
            self.joern_path / "tools" / "bin" / frontend_name,
            
            # Parent directory patterns (if joern_path points to subdirectory)
            self.joern_path.parent / "bin" / frontend_name,
            self.joern_path.parent / frontend_name,
        ]
        
        # Check each possible path
        for path in search_paths:
            if path.exists() and path.is_file():
                # Check if it's executable
                try:
                    if path.stat().st_mode & 0o111:  # Check execute permission
                        logger.debug(f"Found frontend executable: {path}")
                        return path
                except Exception as e:
                    logger.debug(f"Error checking {path}: {e}")
                    continue
        
        # Search recursively in the Joern installation directory
        if self.joern_path.exists():
            for candidate in self.joern_path.rglob(frontend_name):
                if candidate.is_file():
                    try:
                        if candidate.stat().st_mode & 0o111:
                            logger.debug(f"Found frontend via recursive search: {candidate}")
                            return candidate
                    except Exception:
                        continue
        
        logger.warning(f"Frontend '{frontend_name}' not found in Joern installation")
        logger.info(f"Searched in Joern path: {self.joern_path}")
        logger.info("Available files in Joern installation:")
        
        # List available executables for debugging
        try:
            if self.joern_path.exists():
                for path in self.joern_path.rglob("*"):
                    if path.is_file() and path.name.endswith(("2cpg", "src2cpg")):
                        logger.info(f"  Found CPG tool: {path}")
        except Exception as e:
            logger.debug(f"Error listing Joern files: {e}")
        
        return None
    
    def _generate_cpg(self, source_dir: Path, language: str, chunk_id: str) -> Optional[Path]:
        """Generate CPG using appropriate Joern frontend.
        
        Args:
            source_dir: Directory containing source files
            language: Primary language of the chunk
            chunk_id: Identifier for the chunk
            
        Returns:
            Path to generated CPG file
        """
        cpg_file = self.temp_dir / f"{chunk_id}.cpg.bin"
        
        # Select appropriate frontend
        frontend_map = {
            "go": "gosrc2cpg",
            "java": "javasrc2cpg",
            "python": "pysrc2cpg",
            "javascript": "jssrc2cpg",
            "typescript": "jssrc2cpg",
        }
        
        frontend = frontend_map.get(language)
        if not frontend:
            logger.warning(f"No Joern frontend available for language: {language}")
            return None
        
        try:
            # Find the correct frontend executable path
            frontend_path = self._find_frontend_executable(frontend)
            if not frontend_path:
                logger.error(f"Joern frontend '{frontend}' not found in installation")
                return None
            
            # Build command
            cmd = [
                str(frontend_path),
                str(source_dir),
                "-o", str(cpg_file)
            ]
            
            # Memory settings
            env = os.environ.copy()
            env["JAVA_OPTS"] = f"-Xmx{self.heap_size} -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
            
            logger.debug(f"Running Joern command: {' '.join(cmd)}")
            logger.info(f"Using frontend: {frontend_path}")
            
            # Run with timeout to prevent hanging
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per chunk
                env=env
            )
            
            if result.returncode != 0:
                logger.error(f"Joern CPG generation failed: {result.stderr}")
                return None
            
            if cpg_file.exists():
                logger.debug(f"Successfully generated CPG: {cpg_file}")
                return cpg_file
            else:
                logger.error(f"CPG file not created: {cpg_file}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"Joern CPG generation timed out for chunk {chunk_id}")
            return None
        except Exception as e:
            logger.error(f"Error running Joern CPG generation: {e}")
            return None
    
    def _export_cpg_to_json(self, cpg_file: Path, chunk_id: str) -> Optional[Dict]:
        """Export CPG to JSON format.
        
        Args:
            cpg_file: Path to CPG binary file
            chunk_id: Chunk identifier
            
        Returns:
            Parsed JSON data
        """
        json_file = self.temp_dir / f"{chunk_id}.json"
        
        try:
            # Use joern-export for JSON export
            cmd = [
                str(self.joern_path / "bin" / "joern-export"),
                str(cpg_file),
                "--out", str(json_file.parent),
                "--format", "neo4jjson"
            ]
            
            logger.debug(f"Running Joern export command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for export
            )
            
            if result.returncode != 0:
                logger.error(f"Joern export failed: {result.stderr}")
                return None
            
            # Find the generated JSON file (joern-export may create multiple files)
            json_files = list(json_file.parent.glob("*.json"))
            if not json_files:
                logger.error("No JSON files generated by joern-export")
                return None
            
            # Read the JSON data
            with open(json_files[0]) as f:
                data = json.load(f)
            
            logger.debug(f"Successfully exported CPG to JSON: {len(data)} items")
            return data
            
        except subprocess.TimeoutExpired:
            logger.error(f"Joern export timed out for chunk {chunk_id}")
            return None
        except Exception as e:
            logger.error(f"Error exporting CPG to JSON: {e}")
            return None
    
    def _parse_cpg_json(self, json_data: Dict, chunk: Chunk) -> Tuple[List[JoernEntity], List[JoernRelation]]:
        """Parse CPG JSON data into entities and relationships.
        
        Args:
            json_data: CPG JSON data
            chunk: Original chunk information
            
        Returns:
            Tuple of (entities, relationships)
        """
        entities = []
        relations = []
        
        try:
            # Parse nodes (entities)
            if "nodes" in json_data:
                for node_data in json_data["nodes"]:
                    entity = self._parse_cpg_node(node_data, chunk)
                    if entity:
                        entities.append(entity)
            
            # Parse relationships
            if "relationships" in json_data:
                for rel_data in json_data["relationships"]:
                    relation = self._parse_cpg_relationship(rel_data)
                    if relation:
                        relations.append(relation)
            
            logger.debug(f"Parsed CPG JSON: {len(entities)} entities, {len(relations)} relations")
            
        except Exception as e:
            logger.error(f"Error parsing CPG JSON: {e}")
        
        return entities, relations
    
    def _parse_cpg_node(self, node_data: Dict, chunk: Chunk) -> Optional[JoernEntity]:
        """Parse a single CPG node into an entity.
        
        Args:
            node_data: Node data from CPG JSON
            chunk: Chunk information for context
            
        Returns:
            Parsed entity or None
        """
        try:
            properties = node_data.get("properties", {})
            
            entity = JoernEntity(
                id=str(node_data.get("id", "")),
                name=properties.get("NAME", properties.get("name", "unnamed")),
                type=properties.get("LABEL", node_data.get("labels", ["UNKNOWN"])[0]),
                full_name=properties.get("FULL_NAME", ""),
                signature=properties.get("SIGNATURE", properties.get("signature")),
                filename=properties.get("FILENAME", ""),
                line_number=properties.get("LINE_NUMBER"),
                column_number=properties.get("COLUMN_NUMBER"),
                code=properties.get("CODE"),
                language=chunk.primary_language,
                properties=properties
            )
            
            return entity
            
        except Exception as e:
            logger.debug(f"Failed to parse CPG node: {e}")
            return None
    
    def _parse_cpg_relationship(self, rel_data: Dict) -> Optional[JoernRelation]:
        """Parse a single CPG relationship.
        
        Args:
            rel_data: Relationship data from CPG JSON
            
        Returns:
            Parsed relationship or None
        """
        try:
            relation = JoernRelation(
                source_id=str(rel_data.get("start", rel_data.get("source", ""))),
                target_id=str(rel_data.get("end", rel_data.get("target", ""))),
                edge_type=rel_data.get("type", rel_data.get("label", "UNKNOWN")),
                properties=rel_data.get("properties", {})
            )
            
            return relation
            
        except Exception as e:
            logger.debug(f"Failed to parse CPG relationship: {e}")
            return None
    
    def _cleanup_chunk_files(self, chunk_dir: Path) -> None:
        """Clean up temporary files for a chunk.
        
        Args:
            chunk_dir: Directory to clean up
        """
        try:
            if chunk_dir.exists():
                shutil.rmtree(chunk_dir)
                logger.debug(f"Cleaned up chunk directory: {chunk_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup chunk directory {chunk_dir}: {e}")
    
    def __del__(self):
        """Clean up temporary directory on destruction."""
        try:
            if hasattr(self, 'temp_dir') and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass  # Ignore cleanup errors during destruction