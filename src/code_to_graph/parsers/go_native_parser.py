"""
Go Native Parser using Go's AST and package analysis tools.
Provides superior analysis for Go codebases compared to Tree-sitter.
"""

import json
import logging
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import os

from ..core.models import Entity, Relationship
from ..core.config import settings
from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class GoNativeParser(BaseParser):
    """Go Native Parser using Go's built-in AST and package analysis tools."""
    
    def __init__(self):
        self.go_binary = self._find_go_binary()
        self.analyzer_binary = self._get_analyzer_binary_path()
        self._verify_analyzer_binary()
        
    def _find_go_binary(self) -> Optional[str]:
        """Find Go binary in system PATH."""
        go_binary = shutil.which("go")
        if go_binary:
            try:
                # Verify Go is working
                result = subprocess.run(
                    [go_binary, "version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info(f"Found Go binary: {go_binary} ({result.stdout.strip()})")
                    return go_binary
            except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                logger.warning(f"Go binary found but not working: {e}")
        
        logger.warning("Go binary not found in PATH")
        return None
    
    def _get_analyzer_binary_path(self) -> Path:
        """Get path to the Go analyzer binary."""
        return Path(__file__).parent.parent.parent.parent / "cmd" / "go-analyzer"
    
    def _verify_analyzer_binary(self) -> None:
        """Verify and build the Go analyzer binary if needed."""
        if not self.go_binary:
            raise RuntimeError("Go binary required for Go native analysis")
            
        analyzer_dir = self.analyzer_binary
        if not analyzer_dir.exists():
            raise RuntimeError(f"Go analyzer source not found at {analyzer_dir}")
        
        # Check if binary exists and is recent
        binary_path = analyzer_dir / "go-analyzer"
        main_go_path = analyzer_dir / "main.go"
        
        needs_build = True
        if binary_path.exists() and main_go_path.exists():
            binary_mtime = binary_path.stat().st_mtime
            source_mtime = main_go_path.stat().st_mtime
            if binary_mtime > source_mtime:
                needs_build = False
        
        if needs_build:
            logger.info("Building Go analyzer binary...")
            self._build_analyzer_binary()
    
    def _build_analyzer_binary(self) -> None:
        """Build the Go analyzer binary."""
        try:
            # Change to analyzer directory and build
            original_cwd = os.getcwd()
            os.chdir(self.analyzer_binary)
            
            # Initialize Go module if go.mod doesn't exist
            if not (self.analyzer_binary / "go.mod").exists():
                subprocess.run([self.go_binary, "mod", "init", "go-analyzer"], 
                             check=True, capture_output=True)
            
            # Get dependencies
            subprocess.run([self.go_binary, "mod", "tidy"], 
                         check=True, capture_output=True)
            
            # Build binary
            result = subprocess.run(
                [self.go_binary, "build", "-o", "go-analyzer", "main.go"],
                check=True,
                capture_output=True,
                text=True
            )
            
            logger.info("Go analyzer binary built successfully")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build Go analyzer: {e}")
            logger.error(f"Stdout: {e.stdout}")
            logger.error(f"Stderr: {e.stderr}")
            raise RuntimeError(f"Failed to build Go analyzer binary: {e}")
        finally:
            os.chdir(original_cwd)
    
    def is_available(self) -> bool:
        """Check if Go native parser is available."""
        if not self.go_binary:
            return False
            
        try:
            binary_path = self.analyzer_binary / "go-analyzer"
            return binary_path.exists() and binary_path.is_file()
        except Exception as e:
            logger.warning(f"Go native parser availability check failed: {e}")
            return False
    
    def can_parse_language(self, language: str) -> bool:
        """Check if this parser can handle the given language."""
        return language.lower() == "go" and self.is_available()
    
    def parse_repository(self, repo_path: Path, **kwargs) -> Tuple[List[Entity], List[Relationship]]:
        """
        Parse a Go repository using native Go analysis tools.
        
        Args:
            repo_path: Path to the repository
            **kwargs: Additional parsing options
            
        Returns:
            Tuple of (entities, relationships)
        """
        if not self.is_available():
            raise RuntimeError("Go native parser is not available")
        
        # Check if this is a Go repository
        if not self._is_go_repository(repo_path):
            logger.warning(f"Path {repo_path} doesn't appear to be a Go repository")
            return [], []
        
        logger.info(f"Analyzing Go repository: {repo_path}")
        
        try:
            # Run Go analyzer
            result = self._run_analyzer(repo_path, **kwargs)
            
            # Parse results
            entities, relationships = self._parse_analyzer_output(result)
            
            logger.info(f"Go native analysis completed: {len(entities)} entities, {len(relationships)} relationships")
            return entities, relationships
            
        except Exception as e:
            logger.error(f"Go native analysis failed: {e}")
            raise
    
    def _is_go_repository(self, repo_path: Path) -> bool:
        """Check if the given path is a Go repository."""
        # Check for go.mod file
        if (repo_path / "go.mod").exists():
            return True
            
        # Check for .go files
        go_files = list(repo_path.rglob("*.go"))
        if go_files:
            return True
            
        logger.debug(f"No Go files found in {repo_path}")
        return False
    
    def _run_analyzer(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        """Run the Go analyzer binary and return parsed results."""
        binary_path = self.analyzer_binary / "go-analyzer"
        
        # Prepare command arguments
        cmd = [str(binary_path)]
        cmd.extend(["--repo-path", str(repo_path)])
        
        # Add optional arguments
        if kwargs.get("include_code", False):
            cmd.append("--include-code")
        
        if kwargs.get("verbose", False):
            cmd.append("--verbose")
        
        pattern = kwargs.get("pattern", "./...")
        cmd.extend(["--pattern", pattern])
        
        # Use temporary file for large outputs
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            cmd.extend(["--output", temp_path])
            
            logger.debug(f"Running Go analyzer: {' '.join(cmd)}")
            
            # Run analyzer with timeout
            timeout = kwargs.get("timeout", 300)  # 5 minutes default
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(repo_path)
            )
            
            if result.returncode != 0:
                logger.error(f"Go analyzer failed with code {result.returncode}")
                logger.error(f"Stderr: {result.stderr}")
                raise RuntimeError(f"Go analyzer execution failed: {result.stderr}")
            
            # Read results from temporary file
            with open(temp_path, 'r') as f:
                analysis_result = json.load(f)
            
            if not analysis_result.get("success", False):
                error_msg = analysis_result.get("error", "Unknown error")
                raise RuntimeError(f"Go analysis failed: {error_msg}")
            
            return analysis_result
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    
    def _parse_analyzer_output(self, result: Dict[str, Any]) -> Tuple[List[Entity], List[Relationship]]:
        """Parse the output from the Go analyzer into Entity and Relationship objects."""
        entities = []
        relationships = []
        
        # Parse entities
        for entity_data in result.get("entities", []):
            entity = self._create_entity_from_data(entity_data)
            entities.append(entity)
        
        # Parse relationships
        for rel_data in result.get("relationships", []):
            relationship = self._create_relationship_from_data(rel_data)
            relationships.append(relationship)
        
        return entities, relationships
    
    def _create_entity_from_data(self, data: Dict[str, Any]) -> Entity:
        """Create an Entity object from analyzer output data."""
        return Entity(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", ""),
            file_path=data.get("file", ""),
            language="go",
            package=data.get("package", ""),
            start_line=data.get("start_line", 0),
            end_line=data.get("end_line", 0),
            code=data.get("code", ""),
            doc_string=data.get("doc_string", ""),
            signature=data.get("signature", ""),
            return_type=data.get("return_type", ""),
            parameters=data.get("metadata", {}).get("parameters", ""),
            metadata={
                "receiver_type": data.get("receiver_type", ""),
                "interfaces": ",".join(data.get("interfaces", [])),
                "fields": ",".join(data.get("fields", [])),
                "methods": ",".join(data.get("methods", [])),
                "visibility": data.get("metadata", {}).get("visibility", ""),
                "kind": data.get("metadata", {}).get("kind", ""),
                **data.get("metadata", {})
            }
        )
    
    def _create_relationship_from_data(self, data: Dict[str, Any]) -> Relationship:
        """Create a Relationship object from analyzer output data."""
        return Relationship(
            id=data.get("id", ""),
            source_entity_id=data.get("source_id", ""),
            target_entity_id=data.get("target_id", ""),
            source_entity_name=data.get("source_name", ""),
            target_entity_name=data.get("target_name", ""),
            relation_type=data.get("type", ""),
            line_number=data.get("line", 0),
            metadata=data.get("metadata", {})
        )
    
    def get_supported_languages(self) -> List[str]:
        """Get list of languages supported by this parser."""
        return ["go"] if self.is_available() else []
    
    def get_parser_info(self) -> Dict[str, Any]:
        """Get information about this parser."""
        info = {
            "name": "Go Native Parser",
            "description": "Uses Go's native AST and package analysis tools",
            "supported_languages": self.get_supported_languages(),
            "available": self.is_available(),
            "features": [
                "Complete type information",
                "Interface implementation detection", 
                "Cross-package analysis",
                "Method sets and receivers",
                "Go-specific constructs",
                "Package dependency resolution"
            ]
        }
        
        if self.go_binary:
            try:
                result = subprocess.run([self.go_binary, "version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info["go_version"] = result.stdout.strip()
            except Exception:
                pass
        
        return info


class GoNativeParserFactory:
    """Factory for creating Go native parser instances."""
    
    @staticmethod
    def create_parser() -> Optional[GoNativeParser]:
        """Create a Go native parser if available."""
        try:
            parser = GoNativeParser()
            if parser.is_available():
                return parser
            else:
                logger.info("Go native parser not available, Go runtime not found")
                return None
        except Exception as e:
            logger.warning(f"Failed to create Go native parser: {e}")
            return None
    
    @staticmethod
    def is_available() -> bool:
        """Check if Go native parser can be created."""
        try:
            parser = GoNativeParser()
            return parser.is_available()
        except Exception:
            return False