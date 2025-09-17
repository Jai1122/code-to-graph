#!/usr/bin/env python3
"""
Comprehensive fix for null target_id issues.
This script will patch ALL potential sources of null target_ids.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def patch_tree_sitter_enhanced_mapping():
    """Fix the enhanced relationship mapping to handle all null cases."""
    
    tree_sitter_path = Path("src/code_to_graph/parsers/tree_sitter_parser.py")
    
    with open(tree_sitter_path, 'r') as f:
        content = f.read()
    
    # Check if comprehensive fix is already applied
    if "# COMPREHENSIVE_NULL_FIX_APPLIED" in content:
        print("✅ Comprehensive null target fix already applied to tree_sitter_parser.py")
        return True
    
    # Find the _create_relationships_with_mapping method and enhance it
    enhanced_mapping_fix = '''    def _create_relationships_with_mapping(self, relationships: List, entities: List[Entity], 
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
        )'''
    
    # Replace the existing method
    old_method_start = content.find("    def _create_relationships_with_mapping(")
    if old_method_start == -1:
        print("❌ Could not find _create_relationships_with_mapping method")
        return False
    
    # Find the end of the method (next method or class end)
    old_method_end = content.find("\n    def ", old_method_start + 1)
    if old_method_end == -1:
        old_method_end = content.find("\n\nclass ", old_method_start)
        if old_method_end == -1:
            old_method_end = len(content)
    
    # Replace the method
    new_content = content[:old_method_start] + enhanced_mapping_fix + content[old_method_end:]
    
    with open(tree_sitter_path, 'w') as f:
        f.write(new_content)
    
    print("✅ Applied comprehensive null target fix to tree_sitter_parser.py")
    return True

def patch_csv_exporter_validation():
    """Add validation to CSV exporter to catch null IDs before export."""
    
    csv_exporter_path = Path("src/code_to_graph/storage/csv_exporter.py")
    
    with open(csv_exporter_path, 'r') as f:
        content = f.read()
    
    if "# CSV_VALIDATION_FIX_APPLIED" in content:
        print("✅ CSV validation fix already applied")
        return True
    
    # Enhanced relationship export with validation
    validation_patch = '''    def _export_relationships(self, relationships: List[Relationship], output_file: Path) -> None:
        """Export relationships CSV with comprehensive validation.
        CSV_VALIDATION_FIX_APPLIED - Validates and fixes null IDs before export
        """
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'id', 'source_id', 'target_id', 'relation_type', 'file_path',
                'line_number', 'column_number', 'properties'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            valid_relationships = 0
            skipped_relationships = 0
            
            for relationship in relationships:
                # Comprehensive validation
                if not relationship.source_id:
                    logger.warning(f"⚠️  Skipping relationship with null source_id: {relationship.id}")
                    skipped_relationships += 1
                    continue
                
                if not relationship.target_id:
                    logger.warning(f"⚠️  Skipping relationship with null target_id: {relationship.id}")
                    logger.warning(f"     Properties: {relationship.properties}")
                    skipped_relationships += 1
                    continue
                
                if relationship.source_id.lower() == 'null' or relationship.target_id.lower() == 'null':
                    logger.warning(f"⚠️  Skipping relationship with 'null' string IDs: {relationship.id}")
                    skipped_relationships += 1
                    continue
                
                # Export valid relationship
                row = {
                    'id': relationship.id,
                    'source_id': relationship.source_id,
                    'target_id': relationship.target_id,
                    'relation_type': relationship.relation_type.value if hasattr(relationship.relation_type, 'value') else str(relationship.relation_type),
                    'file_path': relationship.file_path or '',
                    'line_number': relationship.line_number or '',
                    'column_number': relationship.column_number or '',
                    'properties': str(relationship.properties) if relationship.properties else '',
                }
                
                writer.writerow(row)
                valid_relationships += 1
            
            logger.info(f"📊 CSV Export Summary: {valid_relationships} valid, {skipped_relationships} skipped relationships")
        
        logger.debug(f"Exported {valid_relationships} relationships to {output_file}")'''
    
    # Find and replace the _export_relationships method
    old_method_start = content.find("    def _export_relationships(")
    if old_method_start == -1:
        print("❌ Could not find _export_relationships method")
        return False
    
    old_method_end = content.find("\n    def ", old_method_start + 1)
    if old_method_end == -1:
        old_method_end = content.find("\n\nclass ", old_method_start)
        if old_method_end == -1:
            old_method_end = len(content)
    
    new_content = content[:old_method_start] + validation_patch + content[old_method_end:]
    
    with open(csv_exporter_path, 'w') as f:
        f.write(new_content)
    
    print("✅ Applied CSV validation fix to csv_exporter.py")
    return True

def create_null_target_fixer():
    """Create a script to fix null target_ids in existing CSV files."""
    
    fixer_script = '''#!/usr/bin/env python3
"""
Script to fix null target_ids in existing CSV files.
"""

import csv
import sys
from pathlib import Path

def fix_existing_csv():
    """Fix null target_ids in existing relationship CSV."""
    
    relationships_csv = Path("data/export/graph_relationships.csv")
    nodes_csv = Path("data/export/graph_nodes.csv")
    
    if not relationships_csv.exists() or not nodes_csv.exists():
        print("❌ CSV files not found. Run analysis first.")
        return
    
    # Load entity mappings
    entities = {}
    with open(nodes_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entities[row['name']] = row['id']
    
    print(f"📋 Loaded {len(entities)} entities")
    
    # Fix relationships
    fixed_relationships = []
    null_count = 0
    fixed_count = 0
    
    with open(relationships_csv, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            if not row['target_id'] or row['target_id'].lower() == 'null':
                null_count += 1
                
                # Try to extract target name from properties
                props = row.get('properties', '')
                target_name = None
                
                if 'target_name' in props:
                    # Extract target_name from properties string
                    import re
                    match = re.search(r"'target_name': '([^']+)'", props)
                    if match:
                        target_name = match.group(1)
                
                if target_name and target_name in entities:
                    row['target_id'] = entities[target_name]
                    fixed_count += 1
                    print(f"✅ Fixed: {target_name} -> {entities[target_name]}")
                else:
                    # Create external entity
                    if target_name:
                        external_id = f"external_{abs(hash(target_name))}"
                        row['target_id'] = external_id
                        entities[target_name] = external_id
                        fixed_count += 1
                        print(f"🆕 Created external: {target_name} -> {external_id}")
            
            fixed_relationships.append(row)
    
    # Write fixed CSV
    backup_file = relationships_csv.with_suffix('.csv.backup')
    relationships_csv.rename(backup_file)
    
    with open(relationships_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(fixed_relationships)
    
    print(f"📊 Results: {null_count} null target_ids found, {fixed_count} fixed")
    print(f"💾 Backup saved to: {backup_file}")
    print(f"✅ Fixed CSV saved to: {relationships_csv}")

if __name__ == "__main__":
    fix_existing_csv()
'''
    
    with open("fix_existing_csv.py", 'w') as f:
        f.write(fixer_script)
    
    print("✅ Created fix_existing_csv.py script")

if __name__ == "__main__":
    print("🔧 COMPREHENSIVE NULL TARGET_ID FIX")
    print("=" * 50)
    
    success = True
    
    # Apply tree-sitter parser fix
    if not patch_tree_sitter_enhanced_mapping():
        success = False
    
    # Apply CSV exporter validation
    if not patch_csv_exporter_validation():
        success = False
    
    # Create CSV fixer script
    create_null_target_fixer()
    
    if success:
        print("\n🎉 ALL FIXES APPLIED SUCCESSFULLY!")
        print("\nNext steps:")
        print("1. Run fresh analysis:")
        print("   code-to-graph import-graph --repo-path /your/project --clear-db")
        print("2. If you still have existing CSV with null target_ids:")
        print("   python fix_existing_csv.py")
        print("3. Verify results:")
        print("   python debug_relationships.py")
    else:
        print("\n❌ Some fixes failed. Check error messages above.")