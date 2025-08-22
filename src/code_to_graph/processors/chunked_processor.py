"""Chunked repository processor for handling large codebases efficiently."""

import hashlib
import json
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

from loguru import logger
from pydantic import BaseModel

from ..core.config import settings


class FileInfo(BaseModel):
    """Information about a source file."""
    
    path: Path
    language: str
    size: int
    hash: str
    last_modified: float
    package: Optional[str] = None
    
    @classmethod
    def from_path(cls, file_path: Path, language: str) -> "FileInfo":
        """Create FileInfo from file path."""
        stat = file_path.stat()
        content = file_path.read_bytes()
        
        return cls(
            path=file_path,
            language=language,
            size=len(content),
            hash=hashlib.sha256(content).hexdigest(),
            last_modified=stat.st_mtime,
            package=cls._extract_package(file_path, language, content.decode('utf-8', errors='ignore'))
        )
    
    @staticmethod
    def _extract_package(file_path: Path, language: str, content: str) -> Optional[str]:
        """Extract package/module name from file content."""
        if language == "go":
            for line in content.split('\n')[:20]:  # Check first 20 lines
                if line.strip().startswith('package '):
                    return line.strip().split()[1]
        elif language == "java":
            for line in content.split('\n')[:20]:
                if line.strip().startswith('package '):
                    return line.strip().split()[1].rstrip(';')
        elif language == "python":
            # Use directory structure for Python packages
            parts = file_path.parts[:-1]  # Exclude filename
            if '__init__.py' in [p.name for p in file_path.parent.rglob('__init__.py')]:
                return '.'.join(parts[-3:])  # Last 3 directory levels
        
        return None


class Chunk(BaseModel):
    """A chunk of files to process together."""
    
    id: str
    files: List[FileInfo]
    total_size: int
    primary_language: str
    packages: Set[str]
    
    @property
    def file_count(self) -> int:
        """Number of files in this chunk."""
        return len(self.files)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Convert packages to set if it's a list
        if isinstance(self.packages, list):
            self.packages = set(self.packages)


class ChunkedRepositoryProcessor:
    """Processes repositories in memory-efficient chunks."""
    
    def __init__(self, repo_path: Path, cache_dir: Optional[Path] = None):
        """Initialize the chunked processor.
        
        Args:
            repo_path: Path to the repository to process
            cache_dir: Directory for caching analysis results
        """
        self.repo_path = repo_path
        self.cache_dir = cache_dir or settings.cache_dir
        self.cache_file = self.cache_dir / f"{repo_path.name}_file_info.json"
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # File tracking
        self._file_info_cache: Dict[str, FileInfo] = {}
        self._load_file_cache()
        
        logger.info(f"Initialized chunked processor for {repo_path}")
    
    def discover_files(self, force_refresh: bool = False) -> List[FileInfo]:
        """Discover all source files in the repository.
        
        Args:
            force_refresh: Force rediscovery of files
            
        Returns:
            List of discovered source files
        """
        if not force_refresh and self._file_info_cache:
            logger.info(f"Using cached file info ({len(self._file_info_cache)} files)")
            return list(self._file_info_cache.values())
        
        logger.info("Discovering source files...")
        
        # Language file extensions
        extensions = {
            "go": [".go"],
            "java": [".java"],
            "python": [".py"],
            "javascript": [".js", ".jsx"],
            "typescript": [".ts", ".tsx"],
        }
        
        # Build extension to language mapping
        ext_to_lang = {}
        for lang, exts in extensions.items():
            if lang in settings.processing.supported_languages:
                for ext in exts:
                    ext_to_lang[ext] = lang
        
        discovered_files = []
        
        for file_path in self.repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Check if file extension is supported
            if file_path.suffix not in ext_to_lang:
                continue
            
            # Check exclude patterns
            if self._should_exclude(file_path):
                continue
            
            language = ext_to_lang[file_path.suffix]
            
            try:
                # Check if file changed (for incremental processing)
                file_key = str(file_path.relative_to(self.repo_path))
                cached_info = self._file_info_cache.get(file_key)
                
                current_stat = file_path.stat()
                if (cached_info and 
                    cached_info.last_modified == current_stat.st_mtime and 
                    not force_refresh):
                    discovered_files.append(cached_info)
                    continue
                
                # Create new file info
                file_info = FileInfo.from_path(file_path, language)
                discovered_files.append(file_info)
                self._file_info_cache[file_key] = file_info
                
            except Exception as e:
                logger.warning(f"Failed to process file {file_path}: {e}")
                continue
        
        logger.info(f"Discovered {len(discovered_files)} source files")
        
        # Save cache
        self._save_file_cache()
        
        return discovered_files
    
    def create_chunks(self, files: List[FileInfo], strategy: Optional[str] = None) -> List[Chunk]:
        """Create processing chunks from discovered files.
        
        Args:
            files: List of files to chunk
            strategy: Chunking strategy ('package', 'size', 'hybrid')
            
        Returns:
            List of file chunks
        """
        strategy = strategy or settings.processing.chunk_strategy
        max_chunk_size = settings.processing.max_chunk_size
        
        logger.info(f"Creating chunks using {strategy} strategy (max size: {max_chunk_size})")
        
        if strategy == "package":
            chunks = self._chunk_by_package(files, max_chunk_size)
        elif strategy == "size":
            chunks = self._chunk_by_size(files, max_chunk_size)
        elif strategy == "hybrid":
            chunks = self._chunk_hybrid(files, max_chunk_size)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
        
        logger.info(f"Created {len(chunks)} chunks")
        
        return chunks
    
    def _chunk_by_package(self, files: List[FileInfo], max_size: int) -> List[Chunk]:
        """Chunk files by package/module."""
        # Group files by package
        packages: Dict[str, List[FileInfo]] = {}
        
        for file_info in files:
            package = file_info.package or "unknown"
            if package not in packages:
                packages[package] = []
            packages[package].append(file_info)
        
        chunks = []
        for package_name, package_files in packages.items():
            # Split large packages
            for i in range(0, len(package_files), max_size):
                chunk_files = package_files[i:i + max_size]
                
                chunk = Chunk(
                    id=f"{package_name}_{i // max_size}",
                    files=chunk_files,
                    total_size=sum(f.size for f in chunk_files),
                    primary_language=self._get_primary_language(chunk_files),
                    packages={package_name}
                )
                chunks.append(chunk)
        
        return chunks
    
    def _chunk_by_size(self, files: List[FileInfo], max_size: int) -> List[Chunk]:
        """Chunk files by number of files."""
        chunks = []
        
        for i in range(0, len(files), max_size):
            chunk_files = files[i:i + max_size]
            
            chunk = Chunk(
                id=f"chunk_{i // max_size}",
                files=chunk_files,
                total_size=sum(f.size for f in chunk_files),
                primary_language=self._get_primary_language(chunk_files),
                packages={f.package for f in chunk_files if f.package}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_hybrid(self, files: List[FileInfo], max_size: int) -> List[Chunk]:
        """Hybrid chunking: try package-based first, fall back to size-based."""
        # First try package-based chunking
        package_chunks = self._chunk_by_package(files, max_size)
        
        # If all chunks are reasonably sized, use them
        oversized_chunks = [c for c in package_chunks if c.file_count > max_size * 1.5]
        
        if not oversized_chunks:
            return package_chunks
        
        # Re-chunk oversized chunks by size
        final_chunks = []
        for chunk in package_chunks:
            if chunk.file_count > max_size * 1.5:
                # Split this chunk by size
                size_chunks = self._chunk_by_size(chunk.files, max_size)
                final_chunks.extend(size_chunks)
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def _get_primary_language(self, files: List[FileInfo]) -> str:
        """Determine the primary language for a group of files."""
        lang_counts = {}
        for file_info in files:
            lang_counts[file_info.language] = lang_counts.get(file_info.language, 0) + 1
        
        return max(lang_counts.items(), key=lambda x: x[1])[0]
    
    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded based on patterns."""
        relative_path = file_path.relative_to(self.repo_path)
        path_str = str(relative_path)
        
        for pattern in settings.processing.exclude_patterns:
            if Path(path_str).match(pattern.replace('**/', '*/')):
                return True
        
        return False
    
    def _load_file_cache(self) -> None:
        """Load file information cache."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file) as f:
                cache_data = json.load(f)
            
            for key, data in cache_data.items():
                # Convert path string back to Path object
                data['path'] = Path(data['path'])
                self._file_info_cache[key] = FileInfo(**data)
                
            logger.debug(f"Loaded {len(self._file_info_cache)} files from cache")
        except Exception as e:
            logger.warning(f"Failed to load file cache: {e}")
            self._file_info_cache = {}
    
    def _save_file_cache(self) -> None:
        """Save file information cache."""
        try:
            cache_data = {}
            for key, file_info in self._file_info_cache.items():
                data = file_info.dict()
                data['path'] = str(data['path'])  # Convert Path to string for JSON
                cache_data[key] = data
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logger.debug(f"Saved {len(cache_data)} files to cache")
        except Exception as e:
            logger.warning(f"Failed to save file cache: {e}")
    
    def get_changed_files(self, since_hash: Optional[str] = None) -> List[FileInfo]:
        """Get files that have changed since a specific commit or timestamp.
        
        Args:
            since_hash: Git commit hash or timestamp to compare against
            
        Returns:
            List of changed files
        """
        # For now, implement simple file modification time checking
        # TODO: Add Git integration for proper diff detection
        
        all_files = self.discover_files()
        
        if not since_hash:
            return all_files
        
        # Simple timestamp-based filtering (if since_hash is a timestamp)
        try:
            since_timestamp = float(since_hash)
            return [f for f in all_files if f.last_modified > since_timestamp]
        except ValueError:
            # If not a timestamp, return all files for now
            logger.warning(f"Git hash comparison not implemented yet: {since_hash}")
            return all_files
    
    def process_chunks(self) -> Iterator[Chunk]:
        """Process repository in chunks.
        
        Yields:
            Processed chunks ready for analysis
        """
        files = self.discover_files()
        chunks = self.create_chunks(files)
        
        for chunk in chunks:
            logger.info(f"Processing chunk {chunk.id} ({chunk.file_count} files, {chunk.primary_language})")
            yield chunk