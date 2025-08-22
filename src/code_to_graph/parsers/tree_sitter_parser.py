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
        self.languages = {
            "go": Language(ts_go.language()),
            "java": Language(ts_java.language()),
            "python": Language(ts_python.language()),
            "javascript": Language(ts_javascript.language()),
            "typescript": Language(ts_javascript.language()),  # Use JS parser for TS
        }
        
        self.parsers = {}
        for lang_name, language in self.languages.items():
            parser = Parser(language)
            self.parsers[lang_name] = parser
        
        logger.info(f"Initialized Tree-sitter parser with {len(self.languages)} languages")
    
    def parse_file(self, file_info: FileInfo) -> Tuple[List[ParsedEntity], List[ParsedRelation]]:
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
            if file_info.language == "go":
                return self._parse_go(tree.root_node, content, str(file_info.path))
            elif file_info.language == "java":
                return self._parse_java(tree.root_node, content, str(file_info.path))
            elif file_info.language == "python":
                return self._parse_python(tree.root_node, content, str(file_info.path))
            elif file_info.language in ["javascript", "typescript"]:
                return self._parse_javascript(tree.root_node, content, str(file_info.path))
            else:
                return [], []
                
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