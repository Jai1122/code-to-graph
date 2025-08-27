"""Core data models for CodeToGraph."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class EntityType(str, Enum):
    """Types of entities that can be extracted from code."""
    
    PACKAGE = "package"
    FILE = "file"
    CLASS = "class"
    INTERFACE = "interface" 
    STRUCT = "struct"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    TYPE = "type"
    IMPORT = "import"
    MODULE = "module"
    NAMESPACE = "namespace"


class RelationType(str, Enum):
    """Types of relationships between entities."""
    
    CONTAINS = "contains"
    CALLS = "calls"
    IMPORTS = "imports"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    USES = "uses"
    DEFINES = "defines"
    REFERENCES = "references"
    DEPENDS_ON = "depends_on"
    ANNOTATED_BY = "annotated_by"
    RETURNS = "returns"
    PARAMETER = "parameter"
    FIELD = "field"


class Entity(BaseModel):
    """Represents a code entity (class, function, variable, etc.)."""
    
    id: str = Field(..., description="Unique identifier for the entity")
    name: str = Field(..., description="Name of the entity")
    type: EntityType = Field(..., description="Type of entity")
    file_path: Optional[str] = Field(None, description="Path to the source file")
    line_number: Optional[int] = Field(None, description="Line number in source file")
    column_number: Optional[int] = Field(None, description="Column number in source file")
    end_line_number: Optional[int] = Field(None, description="End line number")
    end_column_number: Optional[int] = Field(None, description="End column number")
    
    # Additional properties
    language: Optional[str] = Field(None, description="Programming language")
    package: Optional[str] = Field(None, description="Package/module name")
    namespace: Optional[str] = Field(None, description="Namespace")
    signature: Optional[str] = Field(None, description="Function/method signature")
    return_type: Optional[str] = Field(None, description="Return type for functions")
    access_modifier: Optional[str] = Field(None, description="Access modifier (public, private, etc.)")
    is_static: Optional[bool] = Field(None, description="Whether entity is static")
    is_abstract: Optional[bool] = Field(None, description="Whether entity is abstract")
    
    # Metadata
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    annotations: List[str] = Field(default_factory=list, description="Annotations/decorators")
    
    class Config:
        use_enum_values = True


class Relationship(BaseModel):
    """Represents a relationship between two entities."""
    
    id: str = Field(..., description="Unique identifier for the relationship")
    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    relation_type: RelationType = Field(..., description="Type of relationship")
    
    # Location information
    file_path: Optional[str] = Field(None, description="File where relationship is defined")
    line_number: Optional[int] = Field(None, description="Line number where relationship occurs")
    column_number: Optional[int] = Field(None, description="Column number where relationship occurs")
    
    # Additional properties
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    
    class Config:
        use_enum_values = True


class CodeLocation(BaseModel):
    """Represents a location in source code."""
    
    file_path: str = Field(..., description="Path to source file")
    line_number: int = Field(..., description="Line number")
    column_number: int = Field(default=0, description="Column number")
    end_line_number: Optional[int] = Field(None, description="End line number")
    end_column_number: Optional[int] = Field(None, description="End column number")


class AnalysisStats(BaseModel):
    """Statistics about code analysis results."""
    
    total_entities: int = Field(default=0, description="Total number of entities")
    total_relationships: int = Field(default=0, description="Total number of relationships")
    entities_by_type: Dict[str, int] = Field(default_factory=dict, description="Entity counts by type")
    relationships_by_type: Dict[str, int] = Field(default_factory=dict, description="Relationship counts by type")
    files_processed: int = Field(default=0, description="Number of files processed")
    processing_time: float = Field(default=0.0, description="Processing time in seconds")