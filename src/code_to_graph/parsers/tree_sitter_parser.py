"""Tree-sitter based fast code parsing."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

import tree_sitter_go as ts_go
import tree_sitter_java as ts_java
import tree_sitter_python as ts_python
import tree_sitter_javascript as ts_javascript
from tree_sitter import Language, Parser, Node
from loguru import logger
from pydantic import BaseModel

from ..processors.chunked_processor import FileInfo
from ..core.models import Entity, Relationship, EntityType, RelationType
import hashlib


class ParsedEntity(BaseModel):
    """Represents a parsed code entity."""
    
    name: str
    type: str  # function, class, method, variable, etc.
    start_line: int
    end_line: int
    file_path: str
    language: str
    parent: Optional[str] = None
    children: List[str] = []
    metadata: Dict[str, Any] = {}


class ParsedRelation(BaseModel):
    """Represents a relationship between code entities."""
    
    source: str
    target: str
    relation_type: str  # calls, inherits, imports, etc.
    metadata: Dict[str, Any] = {}


class TreeSitterParser:
    """Fast parsing using Tree-sitter for syntax analysis."""
    
    def __init__(self):
        """Initialize Tree-sitter parser with language support."""
        # Initialize languages with the correct Tree-sitter API
        self.languages = {}
        self.parsers = {}
        
        # Language initialization with error handling
        logger.debug("Loading Tree-sitter language modules...")
        try:
            language_configs = {
                "go": ts_go.language(),
                "java": ts_java.language(),
                "python": ts_python.language(), 
                "javascript": ts_javascript.language(),
                "typescript": ts_javascript.language(),  # Use JS parser for TS
            }
            logger.debug(f"Successfully loaded {len(language_configs)} language configs")
        except Exception as e:
            logger.error(f"Failed to load Tree-sitter language modules: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
        
        for lang_name, language_capsule in language_configs.items():
            try:
                logger.debug(f"Attempting to initialize {lang_name} parser...")
                logger.debug(f"  Language capsule type: {type(language_capsule)}")
                
                # Create Language object from capsule
                language = Language(language_capsule)
                self.languages[lang_name] = language
                logger.debug(f"  Successfully created Language object for {lang_name}")
                
                # Create parser for this language with the language parameter
                parser = Parser(language)
                self.parsers[lang_name] = parser
                logger.debug(f"  Successfully created Parser object for {lang_name}")
                
                logger.info(f"✅ Successfully initialized {lang_name} parser")
            except Exception as e:
                logger.error(f"❌ Failed to initialize {lang_name} parser: {e}")
                logger.error(f"   Error type: {type(e).__name__}")
                logger.error(f"   Language capsule: {language_capsule}")
                import traceback
                logger.error(f"   Full traceback: {traceback.format_exc()}")
                # Continue without this language
                continue
        
        if not self.languages:
            raise RuntimeError("No Tree-sitter languages could be initialized")
            
        logger.info(f"Initialized Tree-sitter parser with {len(self.languages)} languages: {list(self.languages.keys())}")
    
    def parse_file(self, file_info: FileInfo) -> Tuple[List[Entity], List[Relationship]]:
        """Parse a single file and extract entities and relationships.
        
        Args:
            file_info: File information to parse
            
        Returns:
            Tuple of (entities, relationships)
        """
        if file_info.language not in self.parsers:
            logger.warning(f"Language {file_info.language} not supported by Tree-sitter")
            return [], []
        
        try:
            content = file_info.path.read_text(encoding='utf-8', errors='ignore')
            parser = self.parsers[file_info.language]
            
            # Parse the file
            tree = parser.parse(bytes(content, 'utf-8'))
            
            # Extract entities and relationships based on language
            parsed_entities, parsed_relations = [], []
            if file_info.language == "go":
                parsed_entities, parsed_relations = self._parse_go(tree.root_node, content, str(file_info.path))
            elif file_info.language == "java":
                parsed_entities, parsed_relations = self._parse_java(tree.root_node, content, str(file_info.path))
            elif file_info.language == "python":
                parsed_entities, parsed_relations = self._parse_python(tree.root_node, content, str(file_info.path))
            elif file_info.language in ["javascript", "typescript"]:
                parsed_entities, parsed_relations = self._parse_javascript(tree.root_node, content, str(file_info.path))
            
            # Convert parsed objects to standard models
            entities = self._convert_to_entities(parsed_entities)
            
            # Create name-to-ID mapping for relationship resolution
            entity_name_to_id = {entity.name: entity.id for entity in entities}
            relationships = self._convert_to_relationships(parsed_relations, entity_name_to_id)
            
            return entities, relationships
                
        except Exception as e:
            logger.error(f"Failed to parse {file_info.path}: {e}")
            return [], []
    
    def _parse_go(self, root: Node, content: str, file_path: str) -> Tuple[List[ParsedEntity], List[ParsedRelation]]:
        """Parse Go source code."""
        entities = []
        relations = []
        content_lines = content.split('\n')
        
        # Extract package declaration
        package_name = None
        for node in root.children:
            if node.type == "package_clause":
                package_name = self._get_node_text(node.children[1], content)
                break
        
        # Walk the syntax tree
        self._walk_go_node(root, content, file_path, entities, relations, content_lines)
        
        return entities, relations
    
    def _walk_go_node(
        self, 
        node: Node, 
        content: str, 
        file_path: str, 
        entities: List[ParsedEntity], 
        relations: List[ParsedRelation],
        content_lines: List[str],
        parent_entity: Optional[str] = None
    ) -> None:
        """Walk Go AST nodes recursively."""
        node_text = self._get_node_text(node, content)
        
        entity_id = None
        
        # Extract different types of entities
        if node.type == "function_declaration":
            func_name = None
            for child in node.children:
                if child.type == "identifier":
                    func_name = self._get_node_text(child, content)
                    break
            
            if func_name:
                entity_id = f"{file_path}:{func_name}"
                entity = ParsedEntity(
                    name=func_name,
                    type="function",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    language="go",
                    parent=parent_entity,
                    metadata={
                        "signature": self._extract_go_function_signature(node, content)
                    }
                )
                entities.append(entity)
        
        elif node.type == "method_declaration":
            method_name = None
            receiver_type = None
            
            for child in node.children:
                if child.type == "field_identifier":
                    method_name = self._get_node_text(child, content)
                elif child.type == "parameter_list" and not method_name:
                    # This is the receiver
                    receiver_type = self._extract_go_receiver_type(child, content)
            
            if method_name:
                entity_id = f"{file_path}:{method_name}"
                entity = ParsedEntity(
                    name=method_name,
                    type="method",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    language="go",
                    parent=parent_entity,
                    metadata={
                        "receiver_type": receiver_type,
                        "signature": self._extract_go_function_signature(node, content)
                    }
                )
                entities.append(entity)
        
        elif node.type == "type_declaration":
            # Handle struct, interface declarations
            for spec in node.children:
                if spec.type == "type_spec":
                    type_name = None
                    for child in spec.children:
                        if child.type == "type_identifier":
                            type_name = self._get_node_text(child, content)
                            break
                    
                    if type_name:
                        entity_id = f"{file_path}:{type_name}"
                        entity = ParsedEntity(
                            name=type_name,
                            type="type",
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            file_path=file_path,
                            language="go",
                            parent=parent_entity
                        )
                        entities.append(entity)
        
        elif node.type == "call_expression":
            # Extract function calls for relationships
            called_func = self._extract_go_call_target(node, content)
            if called_func and parent_entity:
                # Create entity for external function if it doesn't exist
                called_func_id = f"{file_path}:{called_func}"
                
                # Check if this external function entity already exists
                external_entity_exists = any(e.name == called_func for e in entities)
                if not external_entity_exists:
                    # Create external function entity
                    external_entity = ParsedEntity(
                        name=called_func,
                        type="function",
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        file_path="external",  # Mark as external
                        language="go",
                        parent=None,
                        metadata={"external": True, "called_from": file_path}
                    )
                    entities.append(external_entity)
                
                relation = ParsedRelation(
                    source=parent_entity,
                    target=called_func,
                    relation_type="calls",
                    metadata={"line": node.start_point[0] + 1}
                )
                relations.append(relation)
        
        # Recursively process children
        for child in node.children:
            self._walk_go_node(child, content, file_path, entities, relations, content_lines, entity_id or parent_entity)
    
    def _parse_java(self, root: Node, content: str, file_path: str) -> Tuple[List[ParsedEntity], List[ParsedRelation]]:
        """Parse Java source code."""
        entities = []
        relations = []
        
        self._walk_java_node(root, content, file_path, entities, relations)
        
        return entities, relations
    
    def _walk_java_node(
        self,
        node: Node,
        content: str,
        file_path: str,
        entities: List[ParsedEntity],
        relations: List[ParsedRelation],
        parent_entity: Optional[str] = None
    ) -> None:
        """Walk Java AST nodes recursively."""
        entity_id = None
        
        if node.type == "class_declaration":
            class_name = None
            for child in node.children:
                if child.type == "identifier":
                    class_name = self._get_node_text(child, content)
                    break
            
            if class_name:
                entity_id = f"{file_path}:{class_name}"
                entity = ParsedEntity(
                    name=class_name,
                    type="class",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    language="java",
                    parent=parent_entity
                )
                entities.append(entity)
        
        elif node.type == "method_declaration":
            method_name = None
            for child in node.children:
                if child.type == "identifier":
                    method_name = self._get_node_text(child, content)
                    break
            
            if method_name:
                entity_id = f"{file_path}:{method_name}"
                entity = ParsedEntity(
                    name=method_name,
                    type="method",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    language="java",
                    parent=parent_entity
                )
                entities.append(entity)
        
        elif node.type == "method_invocation":
            # Extract method calls
            called_method = self._extract_java_call_target(node, content)
            if called_method and parent_entity:
                relation = ParsedRelation(
                    source=parent_entity,
                    target=called_method,
                    relation_type="calls",
                    metadata={"line": node.start_point[0] + 1}
                )
                relations.append(relation)
        
        # Recursively process children
        for child in node.children:
            self._walk_java_node(child, content, file_path, entities, relations, entity_id or parent_entity)
    
    def _parse_python(self, root: Node, content: str, file_path: str) -> Tuple[List[ParsedEntity], List[ParsedRelation]]:
        """Parse Python source code."""
        entities = []
        relations = []
        
        self._walk_python_node(root, content, file_path, entities, relations)
        
        return entities, relations
    
    def _walk_python_node(
        self,
        node: Node,
        content: str,
        file_path: str,
        entities: List[ParsedEntity],
        relations: List[ParsedRelation],
        parent_entity: Optional[str] = None
    ) -> None:
        """Walk Python AST nodes recursively."""
        entity_id = None
        
        if node.type == "class_definition":
            class_name = None
            for child in node.children:
                if child.type == "identifier":
                    class_name = self._get_node_text(child, content)
                    break
            
            if class_name:
                entity_id = f"{file_path}:{class_name}"
                entity = ParsedEntity(
                    name=class_name,
                    type="class",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    language="python",
                    parent=parent_entity
                )
                entities.append(entity)
        
        elif node.type == "function_definition":
            func_name = None
            for child in node.children:
                if child.type == "identifier":
                    func_name = self._get_node_text(child, content)
                    break
            
            if func_name:
                entity_id = f"{file_path}:{func_name}"
                entity = ParsedEntity(
                    name=func_name,
                    type="function",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    language="python",
                    parent=parent_entity
                )
                entities.append(entity)
        
        elif node.type == "call":
            # Extract function calls
            called_func = self._extract_python_call_target(node, content)
            if called_func and parent_entity:
                relation = ParsedRelation(
                    source=parent_entity,
                    target=called_func,
                    relation_type="calls",
                    metadata={"line": node.start_point[0] + 1}
                )
                relations.append(relation)
        
        # Recursively process children
        for child in node.children:
            self._walk_python_node(child, content, file_path, entities, relations, entity_id or parent_entity)
    
    def _parse_javascript(self, root: Node, content: str, file_path: str) -> Tuple[List[ParsedEntity], List[ParsedRelation]]:
        """Parse JavaScript/TypeScript source code."""
        entities = []
        relations = []
        
        self._walk_js_node(root, content, file_path, entities, relations)
        
        return entities, relations
    
    def _walk_js_node(
        self,
        node: Node,
        content: str,
        file_path: str,
        entities: List[ParsedEntity],
        relations: List[ParsedRelation],
        parent_entity: Optional[str] = None
    ) -> None:
        """Walk JavaScript AST nodes recursively."""
        entity_id = None
        
        if node.type == "function_declaration":
            func_name = None
            for child in node.children:
                if child.type == "identifier":
                    func_name = self._get_node_text(child, content)
                    break
            
            if func_name:
                entity_id = f"{file_path}:{func_name}"
                entity = ParsedEntity(
                    name=func_name,
                    type="function",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    language="javascript",
                    parent=parent_entity
                )
                entities.append(entity)
        
        elif node.type == "class_declaration":
            class_name = None
            for child in node.children:
                if child.type == "identifier":
                    class_name = self._get_node_text(child, content)
                    break
            
            if class_name:
                entity_id = f"{file_path}:{class_name}"
                entity = ParsedEntity(
                    name=class_name,
                    type="class",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    language="javascript",
                    parent=parent_entity
                )
                entities.append(entity)
        
        elif node.type == "call_expression":
            # Extract function calls
            called_func = self._extract_js_call_target(node, content)
            if called_func and parent_entity:
                relation = ParsedRelation(
                    source=parent_entity,
                    target=called_func,
                    relation_type="calls",
                    metadata={"line": node.start_point[0] + 1}
                )
                relations.append(relation)
        
        # Recursively process children
        for child in node.children:
            self._walk_js_node(child, content, file_path, entities, relations, entity_id or parent_entity)
    
    def _get_node_text(self, node: Node, content: str) -> str:
        """Extract text content of a node."""
        return content[node.start_byte:node.end_byte]
    
    def _extract_go_function_signature(self, node: Node, content: str) -> str:
        """Extract Go function signature."""
        try:
            return self._get_node_text(node, content).split('{')[0].strip()
        except:
            return ""
    
    def _extract_go_receiver_type(self, node: Node, content: str) -> Optional[str]:
        """Extract Go method receiver type."""
        try:
            receiver_text = self._get_node_text(node, content)
            # Simple parsing to extract type
            parts = receiver_text.strip('()').split()
            if len(parts) >= 2:
                return parts[1].strip('*')
            return None
        except:
            return None
    
    def _extract_go_call_target(self, node: Node, content: str) -> Optional[str]:
        """Extract Go function call target."""
        try:
            for child in node.children:
                if child.type == "selector_expression":
                    return self._get_node_text(child, content)
                elif child.type == "identifier":
                    return self._get_node_text(child, content)
            return None
        except:
            return None
    
    def _extract_java_call_target(self, node: Node, content: str) -> Optional[str]:
        """Extract Java method call target."""
        try:
            for child in node.children:
                if child.type == "identifier":
                    return self._get_node_text(child, content)
            return None
        except:
            return None
    
    def _extract_python_call_target(self, node: Node, content: str) -> Optional[str]:
        """Extract Python function call target."""
        try:
            for child in node.children:
                if child.type == "identifier":
                    return self._get_node_text(child, content)
                elif child.type == "attribute":
                    return self._get_node_text(child, content)
            return None
        except:
            return None
    
    def _extract_js_call_target(self, node: Node, content: str) -> Optional[str]:
        """Extract JavaScript function call target."""
        try:
            for child in node.children:
                if child.type == "identifier":
                    return self._get_node_text(child, content)
                elif child.type == "member_expression":
                    return self._get_node_text(child, content)
            return None
        except:
            return None
    
    def _convert_to_entities(self, parsed_entities: List[ParsedEntity]) -> List[Entity]:
        """Convert ParsedEntity objects to Entity objects."""
        entities = []
        for parsed in parsed_entities:
            # Generate a unique ID for the entity
            entity_id = self._generate_entity_id(parsed.name, parsed.file_path, parsed.start_line)
            
            # Map entity type
            entity_type = self._map_entity_type(parsed.type)
            
            entity = Entity(
                id=entity_id,
                name=parsed.name,
                type=entity_type,
                file_path=parsed.file_path,
                line_number=parsed.start_line,
                end_line_number=parsed.end_line,
                language=parsed.language,
                properties=parsed.metadata
            )
            entities.append(entity)
        return entities
    
    def _convert_to_relationships(self, parsed_relations: List[ParsedRelation], entity_name_to_id: dict = None) -> List[Relationship]:
        """Convert ParsedRelation objects to Relationship objects."""
        relationships = []
        entity_name_to_id = entity_name_to_id or {}
        
        for parsed in parsed_relations:
            # Debug logging to understand the ID matching issue
            if len(relationships) < 3:  # Only log first few for debugging
                logger.debug(f"Relationship debug: source='{parsed.source}', target='{parsed.target}'")
                logger.debug(f"Available entity names: {list(entity_name_to_id.keys())[:10]}")
            
            # Extract entity names from full source/target paths (e.g., "file.go:GetUsers" -> "GetUsers")
            source_name = parsed.source.split(":")[-1] if ":" in parsed.source else parsed.source
            target_name = parsed.target.split(":")[-1] if ":" in parsed.target else parsed.target
            
            # Try to resolve entity IDs from the entity mapping first
            source_id = entity_name_to_id.get(source_name)
            target_id = entity_name_to_id.get(target_name)
            
            # Debug logging with extracted names
            if len(relationships) < 3:  # Only log first few for debugging
                logger.debug(f"Extracted names: source='{source_name}', target='{target_name}'")
                logger.debug(f"Found source_id: {source_id}, target_id: {target_id}")
            
            # Fallback: create external entities if not found in mapping
            if not source_id:
                # For missing source entities, create external entity ID
                source_id = self._generate_entity_id(source_name, "external", 0)
                logger.debug(f"Created external source entity ID for '{source_name}': {source_id}")
            if not target_id:
                # For missing target entities, create external entity ID  
                target_id = self._generate_entity_id(target_name, "external", 0)
                logger.debug(f"Created external target entity ID for '{target_name}': {target_id}")
            
            # Generate relationship ID (include line number for uniqueness)
            line_number = parsed.metadata.get("line", 0)
            rel_id = self._generate_relationship_id(source_id, target_id, parsed.relation_type, line_number)
            
            # Map relation type
            relation_type = self._map_relation_type(parsed.relation_type)
            
            relationship = Relationship(
                id=rel_id,
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                line_number=parsed.metadata.get("line"),
                properties=parsed.metadata
            )
            relationships.append(relationship)
        return relationships
    
    def _generate_entity_id(self, name: str, file_path: str, line: int) -> str:
        """Generate a unique ID for an entity."""
        content = f"{name}:{file_path}:{line}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _generate_relationship_id(self, source_id: str, target_id: str, relation_type: str, line_number: int = 0) -> str:
        """Generate a unique ID for a relationship."""
        content = f"{source_id}:{target_id}:{relation_type}:{line_number}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _map_entity_type(self, parsed_type: str) -> EntityType:
        """Map parsed entity type to EntityType enum."""
        type_mapping = {
            "function": EntityType.FUNCTION,
            "method": EntityType.METHOD,
            "class": EntityType.CLASS,
            "struct": EntityType.STRUCT,
            "interface": EntityType.INTERFACE,
            "variable": EntityType.VARIABLE,
            "constant": EntityType.CONSTANT,
            "type": EntityType.TYPE,
            "package": EntityType.PACKAGE,
            "module": EntityType.MODULE,
            "import": EntityType.IMPORT,
            "file": EntityType.FILE,
            "namespace": EntityType.NAMESPACE
        }
        return type_mapping.get(parsed_type.lower(), EntityType.FUNCTION)
    
    def _map_relation_type(self, parsed_type: str) -> RelationType:
        """Map parsed relation type to RelationType enum."""
        type_mapping = {
            "calls": RelationType.CALLS,
            "contains": RelationType.CONTAINS,
            "imports": RelationType.IMPORTS,
            "extends": RelationType.EXTENDS,
            "implements": RelationType.IMPLEMENTS,
            "uses": RelationType.USES,
            "defines": RelationType.DEFINES,
            "references": RelationType.REFERENCES,
            "depends_on": RelationType.DEPENDS_ON,
            "annotated_by": RelationType.ANNOTATED_BY,
            "returns": RelationType.RETURNS,
            "parameter": RelationType.PARAMETER,
            "field": RelationType.FIELD
        }
        return type_mapping.get(parsed_type.lower(), RelationType.REFERENCES)