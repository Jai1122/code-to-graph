"""Configuration management for CodeToGraph."""

from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import Field
from pydantic_settings import BaseSettings


class Neo4jSettings(BaseSettings):
    """Neo4j database configuration."""
    
    uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    username: str = Field(default="neo4j", description="Neo4j username")
    password: str = Field(default="password", description="Neo4j password")
    database: str = Field(default="neo4j", description="Neo4j database name")
    max_connection_lifetime: int = Field(default=3600, description="Max connection lifetime in seconds")
    max_connection_pool_size: int = Field(default=50, description="Max connection pool size")
    
    class Config:
        env_prefix = "NEO4J_"


class LLMSettings(BaseSettings):
    """VLLM configuration for remote inference."""
    
    # VLLM is the only supported provider
    provider: str = Field(default="vllm", description="LLM provider (vllm only)")
    
    # VLLM settings (for remote inference)
    vllm_base_url: str = Field(default="https://vllm.example.com", description="VLLM server base URL")
    vllm_api_key: Optional[str] = Field(default=None, description="VLLM API key for authentication")
    vllm_model: str = Field(default="/app/models/qwen3:14b", description="VLLM model name")
    
    # General LLM settings
    max_tokens: int = Field(default=2048, description="Maximum tokens per request")
    temperature: float = Field(default=0.1, description="LLM temperature")
    timeout: int = Field(default=120, description="Request timeout in seconds")
    
    # Query optimization
    enable_caching: bool = Field(default=True, description="Enable query result caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    
    class Config:
        env_prefix = "LLM_"


class ProcessingSettings(BaseSettings):
    """Repository processing configuration."""
    
    # Chunking strategy
    chunk_strategy: str = Field(default="package", description="Chunking strategy: package, size, hybrid")
    max_chunk_size: int = Field(default=100, description="Maximum files per chunk")
    max_memory_gb: int = Field(default=16, description="Maximum memory usage in GB")
    
    # Parsing settings
    enable_tree_sitter: bool = Field(default=True, description="Enable Tree-sitter for fast parsing")
    enable_joern: bool = Field(default=True, description="Enable Joern CPG for semantic analysis")
    joern_heap_size: str = Field(default="8G", description="Joern JVM heap size")
    
    # Languages to process
    supported_languages: List[str] = Field(
        default=["go", "java", "python", "javascript", "typescript"],
        description="Supported programming languages"
    )
    
    # File filtering
    exclude_patterns: List[str] = Field(
        default=["**/test/**", "**/tests/**", "**/*_test.go", "**/*Test.java", "**/node_modules/**", "**/vendor/**"],
        description="File patterns to exclude from processing"
    )
    
    # Incremental processing
    enable_incremental: bool = Field(default=True, description="Enable incremental processing")
    track_file_hashes: bool = Field(default=True, description="Track file hashes for change detection")
    
    class Config:
        env_prefix = "PROCESSING_"


class VisualizationSettings(BaseSettings):
    """Visualization configuration."""
    
    # Server settings
    host: str = Field(default="localhost", description="Visualization server host")
    port: int = Field(default=8080, description="Visualization server port")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Graph rendering
    max_nodes_per_view: int = Field(default=1000, description="Maximum nodes per visualization")
    default_layout: str = Field(default="force", description="Default graph layout algorithm")
    enable_physics: bool = Field(default=True, description="Enable physics simulation")
    
    # Hierarchical navigation
    enable_drill_down: bool = Field(default=True, description="Enable hierarchical drill-down")
    hierarchy_levels: List[str] = Field(
        default=["repository", "package", "class", "function"],
        description="Hierarchy levels for navigation"
    )
    
    class Config:
        env_prefix = "VIZ_"


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application metadata
    app_name: str = Field(default="CodeToGraph", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Subsystem settings
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    visualization: VisualizationSettings = Field(default_factory=VisualizationSettings)
    
    # Paths
    data_dir: Path = Field(default=Path("./data"), description="Data directory")
    cache_dir: Path = Field(default=Path("./cache"), description="Cache directory")
    logs_dir: Path = Field(default=Path("./logs"), description="Logs directory")
    temp_dir: Path = Field(default=Path("./tmp"), description="Temporary directory")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        description="Log format string"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables
    
    def model_post_init(self, __context) -> None:
        """Create necessary directories after model initialization."""
        for path in [self.data_dir, self.cache_dir, self.logs_dir, self.temp_dir]:
            path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()