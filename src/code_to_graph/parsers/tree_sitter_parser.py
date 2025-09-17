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
    # RELATIONSHIP_FIX_APPLIED - Fix for null target_id issue
    
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
            
            # Use enhanced relationship mapping for better resolution
            relationship_data = []
            for parsed_rel in parsed_relations:
                relationship_data.append({
                    'source_name': parsed_rel.source.split(":")[-1] if ":" in parsed_rel.source else parsed_rel.source,
                    'target_name': parsed_rel.target.split(":")[-1] if ":" in parsed_rel.target else parsed_rel.target,
                    'relation_type': parsed_rel.relation_type,
                    'line_number': parsed_rel.metadata.get('line', 0),
                    'column_number': 0,
                    'current_package': None  # Could be extracted from file analysis
                })
            
            # Use enhanced relationship creation
            relationships = self._create_relationships_with_mapping(
                relationship_data, entities, str(file_info.path)
            )
            
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
        
        # Walk the syntax tree with SIMPLE relationship creation
        # First pass: collect all entities
        self._collect_go_entities(root, content, file_path, entities, content_lines)
        
        # Second pass: collect all relationships using entity list
        self._collect_go_relationships(root, content, file_path, entities, relations)
        
        return entities, relations
    
    def _collect_go_entities(self, node: Node, content: str, file_path: str, entities: List[ParsedEntity], content_lines: List[str]) -> None:
        """Collect all Go entities in first pass."""
        
        # Function declarations
        if node.type == "function_declaration":
            func_name = None
            for child in node.children:
                if child.type == "identifier":
                    func_name = self._get_node_text(child, content)
                    break
            
            if func_name:
                entity = ParsedEntity(
                    name=func_name,
                    type="function",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    language="go",
                    metadata={"signature": self._extract_go_function_signature(node, content)}
                )
                entities.append(entity)
                from loguru import logger
                logger.debug(f"🏗️  Collected function: {func_name} (lines {entity.start_line}-{entity.end_line})")
        
        # Method declarations
        elif node.type == "method_declaration":
            method_name = None
            receiver_type = None
            
            for child in node.children:
                if child.type == "field_identifier":
                    method_name = self._get_node_text(child, content)
                elif child.type == "parameter_list" and not method_name:
                    receiver_type = self._extract_go_receiver_type(child, content)
            
            if method_name:
                entity = ParsedEntity(
                    name=method_name,
                    type="method",
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path,
                    language="go",
                    metadata={
                        "receiver_type": receiver_type,
                        "signature": self._extract_go_function_signature(node, content)
                    }
                )
                entities.append(entity)
                from loguru import logger
                logger.debug(f"🏗️  Collected method: {method_name} (lines {entity.start_line}-{entity.end_line})")
        
        # Recursively collect from children
        for child in node.children:
            self._collect_go_entities(child, content, file_path, entities, content_lines)
    
    def _collect_go_relationships(self, node: Node, content: str, file_path: str, entities: List[ParsedEntity], relations: List[ParsedRelation]) -> None:
        """Collect all Go relationships in second pass using collected entities."""
        
        # Look for function calls
        if node.type == "call_expression":
            called_func = self._extract_go_call_target(node, content)
            if called_func:
                call_line = node.start_point[0] + 1
                
                # Find the enclosing function by checking which entity contains this line
                enclosing_function = None
                for entity in entities:
                    if (entity.type in ["function", "method"] and 
                        entity.start_line <= call_line <= entity.end_line):
                        enclosing_function = entity.name
                        break
                
                if enclosing_function:
                    # Create external entity if target doesn't exist
                    target_exists = any(e.name == called_func for e in entities)
                    if not target_exists:
                        external_entity = ParsedEntity(
                            name=called_func,
                            type="function",
                            start_line=call_line,
                            end_line=call_line,
                            file_path="external",
                            language="go",
                            metadata={"external": True, "called_from": file_path}
                        )
                        entities.append(external_entity)
                    
                    # Create relationship
                    relation = ParsedRelation(
                        source=enclosing_function,
                        target=called_func,
                        relation_type="calls",
                        metadata={"line": call_line}
                    )
                    relations.append(relation)
                    
                    from loguru import logger
                    logger.info(f"🔗 Created relationship: {enclosing_function} -> {called_func} (line {call_line})")
                else:
                    from loguru import logger
                    logger.warning(f"⚠️  Call to {called_func} at line {call_line} outside any function")
        
        # Recursively collect from children  
        for child in node.children:
            self._collect_go_relationships(child, content, file_path, entities, relations)
    
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
            if called_func:
                # Find the current function we're in by looking for parent function
                current_function = parent_entity
                if not current_function:
                    # Try to find the enclosing function by walking up
                    current_function = self._find_enclosing_function(node, content, entities)
                
                if current_function:
                    # Create entity for external function if it doesn't exist
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
                    
                    # Create relationship
                    relation = ParsedRelation(
                        source=current_function,
                        target=called_func,
                        relation_type="calls",
                        metadata={"line": node.start_point[0] + 1}
                    )
                    relations.append(relation)
                    
                    # Debug logging
                    from loguru import logger
                    logger.debug(f"Created relationship: {current_function} -> {called_func}")
        
        # Recursively process children
        for child in node.children:
            self._walk_go_node(child, content, file_path, entities, relations, content_lines, entity_id or parent_entity)
    
    def _find_enclosing_function(self, call_node: Node, content: str, entities: List) -> Optional[str]:
        """Find the enclosing function for a call node."""
        # Look through existing entities to find one that contains this call
        call_line = call_node.start_point[0] + 1
        
        for entity in entities:
            if (entity.type in ["function", "method"] and 
                entity.start_line <= call_line <= entity.end_line):
                return f"{entity.file_path}:{entity.name}"
        
        return None
    
    def _walk_go_node_with_context(
        self, 
        node: Node, 
        content: str, 
        file_path: str, 
        entities: List[ParsedEntity], 
        relations: List[ParsedRelation],
        content_lines: List[str],
        function_context: Dict,
        parent_entity: Optional[str] = None
    ) -> None:
        """Walk Go AST nodes with proper function context tracking."""
        
        entity_id = None
        current_function = parent_entity
        
        # Extract different types of entities
        if node.type == "function_declaration":
            func_name = None
            for child in node.children:
                if child.type == "identifier":
                    func_name = self._get_node_text(child, content)
                    break
            
            if func_name:
                entity_id = f"{file_path}:{func_name}"
                current_function = func_name  # Set as current function for children
                
                # Track function boundaries
                function_context[func_name] = {
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'entity_id': entity_id
                }
                
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
                logger.debug(f"Created function entity: {func_name}")
        
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
                current_function = method_name  # Set as current function for children
                
                # Track method boundaries
                function_context[method_name] = {
                    'start_line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'entity_id': entity_id
                }
                
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
                logger.debug(f"Created method entity: {method_name}")
        
        elif node.type == "call_expression":
            # Extract function calls for relationships
            called_func = self._extract_go_call_target(node, content)
            if called_func:
                # Find which function we're currently in
                call_line = node.start_point[0] + 1
                enclosing_function = None
                
                # Check function context to find enclosing function
                for func_name, context in function_context.items():
                    if context['start_line'] <= call_line <= context['end_line']:
                        enclosing_function = func_name
                        break
                
                if enclosing_function:
                    # Create entity for external function if it doesn't exist
                    external_entity_exists = any(e.name == called_func for e in entities)
                    if not external_entity_exists:
                        # Create external function entity
                        external_entity = ParsedEntity(
                            name=called_func,
                            type="function",
                            start_line=call_line,
                            end_line=call_line,
                            file_path="external",  # Mark as external
                            language="go",
                            parent=None,
                            metadata={"external": True, "called_from": file_path}
                        )
                        entities.append(external_entity)
                        logger.debug(f"Created external entity: {called_func}")
                    
                    # Create relationship
                    relation = ParsedRelation(
                        source=enclosing_function,  # Use function name directly
                        target=called_func,
                        relation_type="calls",
                        metadata={"line": call_line}
                    )
                    relations.append(relation)
                    
                    logger.info(f"✅ Created relationship: {enclosing_function} -> {called_func} (line {call_line})")
                else:
                    logger.warning(f"⚠️  Call to {called_func} at line {call_line} not inside any function")
        
        # Recursively process children
        for child in node.children:
            self._walk_go_node_with_context(
                child, content, file_path, entities, relations, content_lines, 
                function_context, current_function or parent_entity
            )
    
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
    
    def _create_robust_entity_mapping(self, entities: List[Entity]) -> Dict[str, str]:
        """
        Create a robust mapping from entity names to IDs with multiple name variants.
        This fixes the null target_id issue by handling name variations.
        """
        name_to_id = {}
        
        for entity in entities:
            # Primary mapping: exact name
            name_to_id[entity.name] = entity.id
            
            # Handle Go-specific name variations
            if entity.language == "go":
                # Add package-qualified names
                if entity.package and entity.package != "main":
                    qualified_name = f"{entity.package}.{entity.name}"
                    name_to_id[qualified_name] = entity.id
                
                # Add receiver method names (for Go methods)
                if hasattr(entity, 'properties') and entity.properties:
                    receiver_type = entity.properties.get('receiver_type')
                    if receiver_type:
                        method_name = f"{receiver_type}.{entity.name}"
                        name_to_id[method_name] = entity.id
                        # Also add pointer receiver variant
                        if not receiver_type.startswith('*'):
                            ptr_method = f"*{receiver_type}.{entity.name}"
                            name_to_id[ptr_method] = entity.id
            
            # Handle case variations
            name_to_id[entity.name.lower()] = entity.id
            name_to_id[entity.name.upper()] = entity.id
            
            # Add file-scoped names
            if entity.file_path:
                file_name = Path(entity.file_path).stem
                scoped_name = f"{file_name}.{entity.name}"
                name_to_id[scoped_name] = entity.id
        
        return name_to_id
    
    def _resolve_entity_name(self, name: str, name_to_id: Dict[str, str], 
                           current_file: str = None, current_package: str = None) -> Optional[str]:
        """
        Resolve entity name to ID with fallback strategies.
        """
        # Direct match
        if name in name_to_id:
            return name_to_id[name]
        
        # Try case-insensitive match
        name_lower = name.lower()
        if name_lower in name_to_id:
            return name_to_id[name_lower]
        
        # Try package-qualified name
        if current_package and current_package != "main":
            qualified = f"{current_package}.{name}"
            if qualified in name_to_id:
                return name_to_id[qualified]
        
        # Try file-scoped name
        if current_file:
            file_name = Path(current_file).stem
            scoped = f"{file_name}.{name}"
            if scoped in name_to_id:
                return name_to_id[scoped]
        
        # Try finding partial matches (for external dependencies)
        for mapped_name, entity_id in name_to_id.items():
            if name in mapped_name or mapped_name in name:
                return entity_id
        
        return None
    
    def _create_external_entity(self, name: str, entity_type: str = "function", 
                              current_file: str = None) -> Entity:
        """
        Create an entity for external dependencies.
        """
        from ..core.models import Entity, EntityType
        
        # Map string types to EntityType enum
        type_mapping = {
            "function": EntityType.FUNCTION,
            "method": EntityType.METHOD,
            "class": EntityType.CLASS,
            "struct": EntityType.STRUCT,
            "package": EntityType.PACKAGE,
            "variable": EntityType.VARIABLE,
            "constant": EntityType.CONSTANT,
        }
        
        entity_type_enum = type_mapping.get(entity_type, EntityType.FUNCTION)
        
        return Entity(
            id=f"external_{name}_{hash(name) % 10000}",
            name=name,
            type=entity_type_enum,
            file_path="external",
            language="go",
            package="external",
            properties={"external": True, "source_file": current_file}
        )

    def _create_relationships_with_mapping(self, relationships: List, entities: List[Entity], 
                                         current_file: str = None) -> List:
        """
        Create relationships with enhanced entity name-to-ID mapping.
        COMPREHENSIVE_NULL_FIX_APPLIED - Complete fix for null target_ids
        """
        from ..core.models import Relationship, RelationType
        import uuid
        
        # Create robust entity mapping with ALL variations
        name_to_id = self._create_robust_entity_mapping(entities)
        
        # Also create ID-to-entity mapping for validation
        id_to_entity = {entity.id: entity for entity in entities}
        
        # Track external entities to create
        external_entities = {}
        
        enhanced_relationships = []
        
        logger.info(f"🔧 Processing {len(relationships)} relationships with {len(entities)} entities")
        logger.debug(f"📋 Available entities: {[e.name for e in entities[:10]]}")
        
        for i, rel_data in enumerate(relationships):
            # Handle different relationship data formats
            if hasattr(rel_data, 'source'):
                # ParsedRelation object
                source_name = rel_data.source
                target_name = rel_data.target
                relation_type = rel_data.relation_type
                line_number = rel_data.metadata.get('line', 0) if rel_data.metadata else 0
            elif isinstance(rel_data, dict):
                # Dictionary format
                source_name = rel_data.get('source_name', rel_data.get('source', ''))
                target_name = rel_data.get('target_name', rel_data.get('target', ''))
                relation_type = rel_data.get('relation_type', 'references')
                line_number = rel_data.get('line_number', rel_data.get('line', 0))
            else:
                logger.warning(f"⚠️  Unexpected relationship data format: {type(rel_data)}")
                continue
            
            # Clean up names (remove file paths, packages, etc.)
            source_name = self._clean_entity_name(source_name)
            target_name = self._clean_entity_name(target_name)
            
            if not source_name or not target_name:
                logger.warning(f"⚠️  Empty source or target name: '{source_name}' -> '{target_name}'")
                continue
            
            # Resolve source ID with multiple strategies
            source_id = self._resolve_entity_name_comprehensive(
                source_name, name_to_id, current_file, entities
            )
            
            # Resolve target ID with multiple strategies
            target_id = self._resolve_entity_name_comprehensive(
                target_name, name_to_id, current_file, entities
            )
            
            # Create external entities for unresolved targets
            if not target_id and target_name:
                if target_name not in external_entities:
                    external_entity = self._create_external_entity_enhanced(
                        target_name, "function", current_file, entities
                    )
                    external_entities[target_name] = external_entity
                    entities.append(external_entity)
                    name_to_id[target_name] = external_entity.id
                    id_to_entity[external_entity.id] = external_entity
                    logger.debug(f"🆕 Created external entity: {target_name} -> {external_entity.id}")
                
                target_id = external_entities[target_name].id
            
            # Create external entities for unresolved sources (less common)
            if not source_id and source_name:
                if source_name not in external_entities:
                    external_entity = self._create_external_entity_enhanced(
                        source_name, "function", current_file, entities
                    )
                    external_entities[source_name] = external_entity
                    entities.append(external_entity)
                    name_to_id[source_name] = external_entity.id
                    id_to_entity[external_entity.id] = external_entity
                    logger.debug(f"🆕 Created external source entity: {source_name} -> {external_entity.id}")
                
                source_id = external_entities[source_name].id
            
            # Final validation - ensure we have both IDs
            if not source_id or not target_id:
                logger.error(f"❌ Still missing IDs after all resolution attempts:")
                logger.error(f"   Source: '{source_name}' -> {source_id}")
                logger.error(f"   Target: '{target_name}' -> {target_id}")
                logger.error(f"   Available entities: {list(name_to_id.keys())[:10]}")
                continue
            
            # Validate IDs exist in entity list
            if source_id not in id_to_entity:
                logger.error(f"❌ Source ID {source_id} not found in entity list")
                continue
                
            if target_id not in id_to_entity:
                logger.error(f"❌ Target ID {target_id} not found in entity list")
                continue
            
            # Map relation type to enum
            relation_type_mapping = {
                "calls": RelationType.CALLS,
                "contains": RelationType.CONTAINS,
                "imports": RelationType.IMPORTS,
                "uses": RelationType.USES,
                "references": RelationType.REFERENCES,
                "defines": RelationType.DEFINES,
                "extends": RelationType.EXTENDS,
                "implements": RelationType.IMPLEMENTS,
            }
            
            rel_type_enum = relation_type_mapping.get(
                relation_type.lower() if isinstance(relation_type, str) else str(relation_type).lower(), 
                RelationType.REFERENCES
            )
            
            # Create relationship with guaranteed valid IDs
            relationship = Relationship(
                id=f"rel_{uuid.uuid4().hex[:8]}",
                source_id=source_id,
                target_id=target_id,
                relation_type=rel_type_enum,
                file_path=current_file,
                line_number=line_number,
                column_number=0,
                properties={
                    "source_name": source_name,
                    "target_name": target_name,
                    "original_relation_type": str(relation_type),
                    "validation_passed": True
                }
            )
            
            enhanced_relationships.append(relationship)
            
            if i < 5:  # Log first few for debugging
                logger.info(f"✅ [{i+1}] {source_name} -> {target_name} (IDs: {source_id[:8]}...{target_id[:8]})")
        
        logger.info(f"🎯 Created {len(enhanced_relationships)} valid relationships ({len(external_entities)} external entities)")
        
        return enhanced_relationships

    def _clean_entity_name(self, name: str) -> str:
        """Clean entity name by removing file paths and other artifacts."""
        if not name:
            return ""
        
        # Remove file path prefixes (e.g., "file.go:FuncName" -> "FuncName")
        if ":" in name:
            name = name.split(":")[-1]
        
        # Remove package prefixes for local functions (keep for external like "fmt.Println")
        if "." in name and not name.startswith(("fmt.", "log.", "http.", "json.", "strings.", "time.")):
            # Only remove package prefix if it's likely a local package
            parts = name.split(".")
            if len(parts) == 2 and len(parts[0]) > 3:  # Avoid removing short prefixes like "fmt"
                name = parts[-1]
        
        return name.strip()
    
    def _resolve_entity_name_comprehensive(self, name: str, name_to_id: Dict[str, str], 
                                         current_file: str = None, entities: List = None) -> Optional[str]:
        """
        Comprehensive entity name resolution with all possible strategies.
        """
        if not name:
            return None
        
        # Strategy 1: Direct match
        if name in name_to_id:
            return name_to_id[name]
        
        # Strategy 2: Case-insensitive match
        name_lower = name.lower()
        for mapped_name, entity_id in name_to_id.items():
            if mapped_name.lower() == name_lower:
                return entity_id
        
        # Strategy 3: Partial match (ends with the name)
        for mapped_name, entity_id in name_to_id.items():
            if mapped_name.endswith(name) or name.endswith(mapped_name):
                return entity_id
        
        # Strategy 4: Search in entities directly by name
        if entities:
            for entity in entities:
                if entity.name == name:
                    return entity.id
                if entity.name.endswith(name) or name.endswith(entity.name):
                    return entity.id
        
        # Strategy 5: Try without package prefix
        if "." in name:
            simple_name = name.split(".")[-1]
            if simple_name in name_to_id:
                return name_to_id[simple_name]
        
        # Strategy 6: Try with common prefixes
        if current_file and entities:
            file_name = Path(current_file).stem
            prefixed_name = f"{file_name}.{name}"
            if prefixed_name in name_to_id:
                return name_to_id[prefixed_name]
        
        return None
    
    def _create_external_entity_enhanced(self, name: str, entity_type: str = "function", 
                                       current_file: str = None, entities: List = None) -> Entity:
        """
        Create enhanced external entity with unique ID generation.
        """
        from ..core.models import Entity, EntityType
        
        # Ensure unique ID
        entity_id = f"external_{name}_{abs(hash(name + str(current_file)))}"
        
        # Avoid duplicate IDs
        existing_ids = {e.id for e in entities} if entities else set()
        counter = 1
        original_id = entity_id
        while entity_id in existing_ids:
            entity_id = f"{original_id}_{counter}"
            counter += 1
        
        # Map string types to EntityType enum
        type_mapping = {
            "function": EntityType.FUNCTION,
            "method": EntityType.METHOD,
            "class": EntityType.CLASS,
            "struct": EntityType.STRUCT,
            "package": EntityType.PACKAGE,
            "variable": EntityType.VARIABLE,
            "constant": EntityType.CONSTANT,
        }
        
        entity_type_enum = type_mapping.get(entity_type, EntityType.FUNCTION)
        
        return Entity(
            id=entity_id,
            name=name,
            type=entity_type_enum,
            file_path="external",
            language="go",
            package="external",
            line_number=1,
            end_line_number=1,
            properties={
                "external": True, 
                "source_file": current_file,
                "auto_created": True,
                "unique_id": entity_id
            }
        )
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